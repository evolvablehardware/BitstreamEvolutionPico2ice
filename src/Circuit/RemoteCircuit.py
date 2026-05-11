import itertools
from logging import Logger
from typing import List, Dict, Any
from icefarm.client.drivers import PulseCountClient, VarMaxClient
from icefarm.client.lib.varmax import VarMaxEvaluation
from Circuit.FileBasedCircuit import FileBasedCircuit
from Circuit import FitnessFunction
from Config import Config
from genome import Tile
import subprocess
from icefarm.client.drivers import MultiPulseCountClient
from icefarm.client.lib.multipulsecount import PulseCountEvaluation

class DeviceTimeoutException(Exception): ...


def _batched(iterable, size):
    if size < 1:
        raise ValueError("batch size must be at least 1")

    iterator = iter(iterable)
    while batch := tuple(itertools.islice(iterator, size)):
        yield batch

class RemoteCircuit(FileBasedCircuit):
    def __init__(self, client: "EvolutionClient", serials: List[str], index, filename, config, template, rand, logger, fitnessfunc: FitnessFunction, genome):
        super().__init__(index, filename, config, template, rand, logger)
        self._client = client
        self._serials = serials
        self._fitnessfunc = fitnessfunc
        self._extra_data = {}
        self._waveform_samples = None
        self._fitnessfunc.attach(filename, None, config, self._extra_data)
        self._data = []

        self.genome = genome

    def collect_data_once(self):
        # data is appended during fitness calculation
        # this allows all the circuits to be sent at once
        self._client.evaluate(self)

    def _get_measurement(self): ...
        # makes abc happy

    def mutate(self, chance=None):
        if not chance:
            chance = 0.01
        self.genome.mutate(chance)

    def crossover(self, parent, crossover_point):
        self.genome.crossover(parent.genome, 0.3)

    def clear_data(self):
        super().clear_data()
        self._extra_data = {}
        self._waveform_samples = None

    def upload(self):
        pass

    # called by randomize until
    def evaluate_once(self):
        self.upload()
        self.collect_data_once()

    def randomize_bitstream(self):
        self.genome.mutate(1)

    def _calculate_fitness(self):
        if not self._data:
            self._data = []
            results = self._client.get_result(self)
            # waveform = self._client.get_waveform(self)
            # # TODO add an additional log file that maps serials to pulses
            # if self._serials:
            #     for serial in self._serials:
            #         for point in results[serial]:
            #             if point is EvaluationFailed:
            #                 raise DeviceTimeoutException()

            #             self._data.append(float(point))
            # else:
            #     for serial in results.keys():
            #         for point in results[serial]:
            #             if point is EvaluationFailed:
            #                 raise DeviceTimeoutException()

            #             self._data.append(float(point))
            self._data = [float(results)]
            self._extra_data["pulses"] = self._data

            # if waveform:
            #     self._waveform_samples = waveform

        return self._fitnessfunc.calculate_fitness(self._data)

    def get_extra_data(self, key):
        return self._extra_data[key]

    def get_waveform(self):
        if self._waveform_samples:
            return [str(x) for x in self._waveform_samples]
        return [str(x) for x in self._data] if self._data else []

    def get_waveform_td(self):
        return [str(x) for x in self._data] if self._data else []

    def _get_all_live_reported_value(self):
        return self._extra_data["pulses"]

class EvolutionClient:
    """
    Wrapper around icefarm client (PulseCountClient or VarMaxClient) to allow RemoteCircuit api to be the same as other circuits.
    """
    def __init__(self, client: PulseCountClient | VarMaxClient, config: Config, logger: Logger, writer):
        self._client = client
        self._command_queue = []
        self._result_map = {}
        self._waveform_map = {}
        self._logger = logger
        self.batch_size = config.get_icefarm_client_batch_amount_circuits()
        self.buffer_batches = config.get_icefarm_buffer_batch_amount()
        self.evaluation_mode_all = config.get_icefarm_mode().lower() == "all"
        self.result_timeout = config.get_icefarm_results_flush_interval_seconds() * 4
        self.circuit_result_map = {}
        self.result_f_pin_map = {}
        self.writer = writer

    def evaluate(self, circuit: FileBasedCircuit):
        """
        Queues circuit to be evaluated on picos with identification of serials.
        If no serial is given, one is assigned based on the optimal evaluation speed.
        """

        self.circuit_result_map = {}
        self.result_f_pin_map = {}
        self._command_queue.append(circuit)

    def get_result(self, circuit: FileBasedCircuit) -> Dict[str, Any]:
        """
        Returns map of serial to results after they arrive from the iCEFARM system.
        The first time this is called, evaluations are sent to iCEFARM.
        """
        if not self.circuit_result_map:
            for i, circuits in enumerate(_batched(self._command_queue, 4)):
                fpath = f"circuits/{i}.asc"
                binpath = f"bins/{i}.bin"

                pins = self.writer.write("test_seed.asc", fpath, [ckt.genome for ckt in circuits], Tile(1, 26))
                subprocess.run(["icepack", fpath, binpath])
                self.result_f_pin_map[binpath] = dict(zip(pins.values(), pins.keys()))

            serial = self._client.getSerials()[0]
            evals = [PulseCountEvaluation([serial], fpath) for fpath in self.result_f_pin_map]

            self._logger.info("Sending circuits for remote evaluation...")

            for serial, evaluation, result in self._client.evaluateEvaluations(evals, batch_size=self.batch_size, target_batches=self.buffer_batches):
                fpath = evaluation.filepath

                for pin, res in zip([9, 11, 25, 27], result):
                    ckt = self.result_f_pin_map[fpath].get(pin)
                    if ckt:
                        self.circuit_result_map[ckt] = res
                        self._logger.debug(f"Received value for file {fpath} pin {pin}: {res}")

        self._logger.info("Remote evaluation complete.")
        self._command_queue = []

        return self.circuit_result_map[circuit.genome]

    def get_waveform(self, circuit: FileBasedCircuit) -> list | None:
        """Returns raw ADC waveform samples for a circuit, or None if not available."""
        return self._waveform_map.get(circuit._bitstream_filepath)
