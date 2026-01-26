from typing import Protocol, TYPE_CHECKING
from logging import Logger
import math

from Selection.SelectionMethod import SelectionMethod
from Selection.ClassicTournamentSelection import ClassicTournamentSelection
from Selection.FitnessProportionalSelection import FitnessProportionalSelection
from Selection.FractionalEliteTournament import FractionalEliteTournament
from Selection.MapElitesSelection import MapElitesSelection
from Selection.RankProportionalSelection import RankProportionalSelection
from Selection.SingleEliteTournamentSelection import SingleEliteTournamentSelection

from Circuit.Circuit import Circuit
from Config import Config

if TYPE_CHECKING:
    import numpy as np


class Crossover(Protocol):
    def __call__(self, source: Circuit, dest: Circuit):...

def crossover_fac(config: Config, logger: Logger, rand: "np.random.Generator"):
    # TODO obtain bitstream len from config
    num_rows = 3
    if config.get_routing_type() == "NEWSE":
        num_rows = 2
    elif config.get_routing_type() == "ALL":
        num_rows = 16
    BITSTREAM_LEN = 660 * num_rows * len(config.get_accessed_columns())

    # TODO add more crossover methods - will move this to a separate module eventually
    # TODO add these cols to config
    if config.get_simulation_mode() == "FULLY_SIM":
        crossover_point = rand.integers(
            1, BITSTREAM_LEN - 1)
    elif config.get_routing_type() == "MOORE":
        crossover_point = rand.integers(1, 3)
    elif config.get_routing_type() == "NWSE":
        crossover_point = rand.integers(13, 15)
    elif config.get_routing_type() == "ALL":
        crossover_point = rand.integers(1, 16)
    else:
        logger.error(
            1, "Invalid routing type specified in config.ini. Exiting...")
        exit()

    def crossover(source: Circuit, dest: Circuit):
        dest.crossover(source, crossover_point)

    return crossover

def selection_fac(config: Config, logger: Logger, rand: "np.random.Generator") -> SelectionMethod:
    crossover = crossover_fac(config, logger, rand)
    n_elites = int(math.ceil(config.get_elitism_fraction() * config.get_population_size()))

    match config.get_selection_type():
        case "SINGLE_ELITE":
            return SingleEliteTournamentSelection(crossover, config.get_crossover_probability(), logger, rand)
        case "FRAC_ELITE":
            return FractionalEliteTournament(crossover, config.get_crossover_probability(), n_elites, logger, rand)
        case "CLASSIC_TOURN":
            return ClassicTournamentSelection(crossover, config.get_crossover_probability(), logger, rand)
        case "FIT_PROP_SEL":
            return FitnessProportionalSelection(crossover, config.get_crossover_probability(), n_elites, logger, rand)
        case "RANK_PROP_SEL":
            return RankProportionalSelection(crossover, config.get_crossover_probability(), n_elites, logger, rand)
        case "MAP_ELITES":
            return MapElitesSelection(config.get_map_elites_dimension(), logger, rand)
        case _:
            logger.error("Invalid Selection method in config.ini. Exiting...")
            exit()
