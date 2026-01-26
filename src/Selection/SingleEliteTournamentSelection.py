from logging import Logger
from typing import TYPE_CHECKING

from Selection.SelectionMethod import SelectionMethod

if TYPE_CHECKING:
    import numpy as np
    from Selection.utils import Crossover

class SingleEliteTournamentSelection(SelectionMethod):
    """
    Selection Algorithm that mutates the hardware of every circuit that is not the current best circuit
    """

    def __init__(self, crossover: "Crossover", crossover_prob: float, logger: Logger, rand: "np.random.Generator"):
        super().__init__(logger, rand)
        self._crossover = crossover
        self._crossover_prob = crossover_prob

    def __call__(self, circuits):
        circuits = sorted(circuits, key=lambda c: c.get_fitness(), reverse=True)

        best = circuits[0]
        self._protected_elites.append(best)
        for ckt in circuits:
            # Mutate the hardware of every circuit that is not the best
            if ckt is not best:
                ckt.mutate()
            else:
                self._logger.info(ckt, "is current BEST")

        return circuits
