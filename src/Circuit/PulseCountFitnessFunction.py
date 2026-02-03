from Circuit.FitnessFunction import FitnessFunction
import math
from functools import reduce
from operator import mul
from decimal import Decimal, getcontext
getcontext().prec = 128

def variance(data: list[float]) -> float:
    u = sum(data) / len(data)
    return sum((point - u) ** 2 for point in data)  / len(data)

def tolorant_variance(data: list[float], tolerance) -> float:
    u = sum(data) / len(data)
    return sum(max(abs(point - u) - tolerance, 0) ** 2 for point in data) / len(data)

def MSE(data: list[float], target: int) -> float:
    return sum((point - target) ** 2 for point in data)


class PulseCountFitnessFunction(FitnessFunction):
    def __init__(self):
        FitnessFunction.__init__(self)

    def get_measurements(self) -> list[float]:
        self._microcontroller.simple_measure_pulses(self._data_filepath)
        pulses = self.__count_pulses()
        return pulses

    def mse_over_tolorant_var(self, data: list[float]) -> float:
        TOLERANCE = 0.03

        target = self._config.get_desired_frequency()

        return 1 / MSE(data, target) * sum(x != 0 for x in data)
        # mse = MSE(data, target)
        var = tolorant_variance(data, target * TOLERANCE) / target
        return (1 / mse) / (var + 1)

    def calculate_fitness(self, data: list[float]) -> float:
        desired_freq = self._config.get_desired_frequency()
        # data = list(Decimal(point) for point in data)
        # Get the pulse that is furthest away from the target, and calculate with that
        # dist = 0
        # pulse_count = -1
        # for pc in data:
        #     this_dist = abs(pc - self._config.get_desired_frequency())
        #     if this_dist >= dist:
        #         dist = this_dist
        #         pulse_count = pc

        # self._extra_data['pulses'] = pulse_count
        # if not max(data) or all(data[0] == point for point in data):
        #     multiplier = 1
        # else:
        #     u = sum(data) / len(data)
        #     s2 = sum((point - u) ** 2 for point in data)  / len(data)
        #     multiplier = 1 / (s2 / max(data))

        # might be best to go back to original method but cap effectiveness at % of distance from target

        self._extra_data['pulses'] = data[0]
        # return reduce(mul, (Decimal(self.__calculate_pulse_fitness(float(point))) for point in data), 1) * multiplier

        # av = sum(data) / len(data)
        # var = sum((point - av) ** 2 for point in data) / target
        # multiplier = math.sqrt(var)

        # return multiplier / reduce(mul, ((point - target) ** 2 for point in data), 1)
        return self.mse_over_tolorant_var(data)

    def get_waveform(self):
        return []

    def _get_all_live_reported_value(self) -> list[float]:
        return self._data

    def __count_pulses(self) -> list[float]:
        data_file = open(self._data_filepath, "r")
        data = data_file.readlines()

        # Extract the integer value from the log file indicating the pulses counted from
        # the microcontroller. Pulses are currently measured by Rising or Falling edges
        # that cross the microcontrollers reference voltage (currently ~2.25 Volts) [TODO: verify]
        pulse_counts = []
        for i in range(len(data)):
            pulse_counts.append(int(data[i]))
        return pulse_counts

    def __is_tolerant_pulse_count(self):
        return self._config.get_fitness_func() == 'TOLERANT_PULSE_COUNT'

    def __calculate_pulse_fitness(self, pulses: int) -> float:
        desired_freq = self._config.get_desired_frequency()
        fitness = 0
        if self.__is_tolerant_pulse_count():
            # Build a normal-ish distribution function where the "mean" is desired_freq,
            # and the "standard deviation" is of our choosing (here we select 0.025*freq)
            # deviation = 0.025 * desired_freq # 25 for 1,000 Hz, 250 for 10,000 Hz
            # TODO 0.05 for multi
            deviation = 0.05 * desired_freq # 25 for 1,000 Hz, 250 for 10,000 Hz
            # No need to check for this because it's included in the function
            # Note: Fitness is still from 0-1
            fitness = math.exp(-0.5 * math.pow((pulses - desired_freq) / deviation, 2))
        else:
            if pulses == desired_freq:
                # self.__logger.event(1, "Unity achieved: {}".format(self))
                fitness = 1
            elif pulses == 0:
                fitness = 0
            else:
                fitness = Decimal(1.0) / abs(desired_freq - pulses)

        # if pulses > 0:
            # Give fitness bonus for getting above 0 pulses
            # fitness = fitness + 1
        return fitness
