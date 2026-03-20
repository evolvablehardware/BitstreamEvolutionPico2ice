from pathlib import Path

from Config import Config


def test_validate_icefarm_params_accepts_serial_list(tmp_path: Path):
    config_path = tmp_path.joinpath("config.ini")
    config_path.write_text(
        """\
[TOP-LEVEL PARAMETERS]
simulation_mode = REMOTE
base_config = data/default_config.ini

[FITNESS PARAMETERS]
fitness_func = VARIANCE

[GA PARAMETERS]
fitness_metric = mce
population_size = 4
mutation_probability = 0.0021
crossover_probability = 0.7
elitism_fraction = 0.1
selection = FIT_PROP_SEL
diversity_measure = NONE
random_injection = 0.0

[INITIALIZATION PARAMETERS]
init_mode = RANDOM
randomize_until = NO
randomize_threshold = 0
randomize_mode = RANDOM
seed = data/ice27_only_no_logic.asc

[STOPPING CONDITION PARAMETERS]
generations = 2
target_fitness = IGNORE

[PLOTTING PARAMETERS]
launch_plots = false

[ICEFARM PARAMETERS]
url = http://localhost:8080
mode = QUICK
devices = ["SERIAL_A", "SERIAL_B"]
exit_at_devices_remaining = -1
reserve_on_device_failure_limit = NO
client_batch_amount_circuits = 4
buffer_batch_amount = 1
results_flush_interval_seconds = 5
"""
    )

    config = Config(config_path)

    assert config.get_icefarm_devices() == ["SERIAL_A", "SERIAL_B"]
    assert config.get_icefarm_device_count() == 2
    config.validate_icefarm_params()
