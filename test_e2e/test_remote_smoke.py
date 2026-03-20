from __future__ import annotations

from pathlib import Path

import pytest

from test_e2e.helpers import (
    HostEvolutionRunner,
    RemoteEvolutionScenario,
    assert_serials_available_again,
    assert_serials_present_before_run,
)


SINGLE_DEVICE_SMOKE_SCENARIOS = [
    RemoteEvolutionScenario(
        name="remote_pulse_quick_smoke",
        fitness_func="TOLERANT_PULSE_COUNT",
        desired_freq=40_000,
        randomize_until="NO",
        randomize_threshold=0,
    ),
    RemoteEvolutionScenario(
        name="remote_varmax_quick_smoke",
        fitness_func="VARIANCE",
        randomize_until="NO",
        randomize_threshold=0,
    ),
    RemoteEvolutionScenario(
        name="remote_varmax_randomize_smoke",
        fitness_func="VARIANCE",
        randomize_until="VARIANCE",
        randomize_threshold=0.1,
    ),
    RemoteEvolutionScenario(
        name="remote_varmax_waveform_smoke",
        fitness_func="VARIANCE",
        randomize_until="NO",
        randomize_threshold=0,
        send_waveform=True,
    ),
]

PER_DEVICE_SCENARIOS = [
    RemoteEvolutionScenario(
        name="remote_pulse_per_device",
        fitness_func="TOLERANT_PULSE_COUNT",
        desired_freq=40_000,
        randomize_until="NO",
        randomize_threshold=0,
    ),
    RemoteEvolutionScenario(
        name="remote_varmax_per_device",
        fitness_func="VARIANCE",
        randomize_until="NO",
        randomize_threshold=0,
    ),
]

TWO_DEVICE_SCENARIOS = [
    RemoteEvolutionScenario(
        name="remote_varmax_two_device_quick",
        fitness_func="VARIANCE",
        randomize_until="NO",
        randomize_threshold=0,
        icefarm_mode="QUICK",
        population_size=6,
        timeout_seconds=300,
    ),
    RemoteEvolutionScenario(
        name="remote_varmax_two_device_all",
        fitness_func="VARIANCE",
        randomize_until="NO",
        randomize_threshold=0,
        icefarm_mode="ALL",
        population_size=6,
        timeout_seconds=300,
    ),
]


@pytest.mark.hardware_e2e
@pytest.mark.long
@pytest.mark.parametrize("scenario", SINGLE_DEVICE_SMOKE_SCENARIOS, ids=lambda scenario: scenario.name)
def test_remote_single_device_smoke(
    tmp_path: Path,
    hardware_e2e_config,
    first_hardware_serial: str,
    scenario: RemoteEvolutionScenario,
):
    serials = [first_hardware_serial]
    assert_serials_present_before_run(hardware_e2e_config.control_url, serials)

    runner = HostEvolutionRunner(hardware_e2e_config)
    result = runner.run_remote_scenario(tmp_path, scenario, serials)
    result.assert_success()

    assert_serials_available_again(hardware_e2e_config.control_url, serials)


@pytest.mark.hardware_e2e
@pytest.mark.long
@pytest.mark.parametrize("scenario", PER_DEVICE_SCENARIOS, ids=lambda scenario: scenario.name)
def test_remote_each_serial_smoke(
    tmp_path: Path,
    hardware_e2e_config,
    hardware_e2e_serials: list[str],
    scenario: RemoteEvolutionScenario,
):
    runner = HostEvolutionRunner(hardware_e2e_config)

    for serial in hardware_e2e_serials:
        target = [serial]
        assert_serials_present_before_run(hardware_e2e_config.control_url, target)

        result = runner.run_remote_scenario(tmp_path, scenario, target)
        result.assert_success()

        assert_serials_available_again(hardware_e2e_config.control_url, target)


@pytest.mark.hardware_e2e
@pytest.mark.long
@pytest.mark.parametrize("scenario", TWO_DEVICE_SCENARIOS, ids=lambda scenario: scenario.name)
def test_remote_two_device_distribution_smoke(
    tmp_path: Path,
    hardware_e2e_config,
    first_two_hardware_serials: list[str],
    scenario: RemoteEvolutionScenario,
):
    assert_serials_present_before_run(hardware_e2e_config.control_url, first_two_hardware_serials)

    runner = HostEvolutionRunner(hardware_e2e_config)
    result = runner.run_remote_scenario(tmp_path, scenario, first_two_hardware_serials)
    result.assert_success()

    assert_serials_available_again(hardware_e2e_config.control_url, first_two_hardware_serials)
