from typing import List, TYPE_CHECKING, Iterable, Any
from logging import Logger
from itertools import zip_longest

from Circuit.Circuit import Circuit
from Selection.SelectionMethod import SelectionMethod

if TYPE_CHECKING:
    import numpy as np
    from Selection.utils import Crossover

def group(iterable: Iterable, groups: int, fillvalue: Any = None):
    """
    Collect data into fixed-length chunks or blocks.
    If the data is not divisible by groups, uses fillvalue for the remaining values.
    #grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    Taken from python recipes.
    """
    args = [iter(iterable)] * groups
    return zip_longest(fillvalue=fillvalue, *args)

class ClassicTournamentSelection(SelectionMethod):
    """
    Selection Algorithm that randomly pairs together circuits, compares their fitness, and preforms crossover on and mutates the "loser"
    """

    # TODO normally would use __annotations __s to solve this but not sure if we want to introduce future
    def __init__(self, crossover: "Crossover", crossover_prob: float, logger: Logger, rand: "np.random.Generator"):
        super().__init__(logger, rand)
        self._crossover = crossover
        self._crossover_prob = crossover_prob

    def __call__(self, circuits: List[Circuit]) -> List[Circuit]:
        population = self._rand.permutation(circuits)

        # For all Circuits in the CircuitPopulation, take two random
        # circuits at a time from the population and compare them. Copy
        # some genes from the fittest of the two to the least fittest of
        # the two and mutate the latter.
        for ckt1, ckt2 in group(population, 2):
            winner = ckt1
            loser = ckt2
            if ckt2.get_fitness() > ckt1.get_fitness():
                winner = ckt2
                loser = ckt1

            self._logger.event(3,
                            "Fitness {}: {} < Fitness {}: {}".format(
                                loser,
                                loser.get_fitness(),
                                winner,
                                winner.get_fitness()
                            ))

            if self._rand.uniform(0, 1) <= self._crossover_prob:
                self._crossover(winner, loser)
            else:
                self._logger.event(3, "Cloning:", winner, " ---> ", loser)
                loser.copy_from(winner)

            loser.mutate()

        return circuits
