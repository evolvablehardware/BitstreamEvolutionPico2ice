from __future__ import annotations

import sys
from pathlib import Path

import pytest

from test_e2e.helpers import HardwareE2EConfig, parse_serials


def pytest_addoption(parser):
    group = parser.getgroup("hardware-e2e")
    group.addoption(
        "--run-hardware-e2e",
        action="store_true",
        default=False,
        help="Run hardware-backed end-to-end tests against a live iCEFARM setup.",
    )
    group.addoption(
        "--e2e-control-url",
        action="store",
        default="http://localhost:8080",
        help="Control server URL for iCEFARM-backed hardware E2E tests.",
    )
    group.addoption(
        "--e2e-serials",
        action="store",
        default="",
        help="Comma-separated list of device serials reserved for hardware E2E tests.",
    )
    group.addoption(
        "--e2e-python",
        action="store",
        default=sys.executable,
        help="Python interpreter used to launch BitstreamEvolution for host-run E2E tests.",
    )
    group.addoption(
        "--e2e-icefarm-root",
        action="store",
        default="",
        help="Path to the local iCEFARM repository root. Defaults to a sibling 'iCEFARM' directory.",
    )
    group.addoption(
        "--e2e-live-output",
        action="store_true",
        default=False,
        help="Stream prefixed live stdout/stderr from the evolve.py subprocess while each hardware E2E test runs.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-hardware-e2e"):
        return

    skip_marker = pytest.mark.skip(reason="need --run-hardware-e2e to run hardware-backed E2E tests")
    for item in items:
        if "hardware_e2e" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def hardware_e2e_config(pytestconfig: pytest.Config) -> HardwareE2EConfig:
    be_root = Path(__file__).resolve().parents[1]

    configured_icefarm_root = pytestconfig.getoption("--e2e-icefarm-root")
    if configured_icefarm_root:
        icefarm_root = Path(configured_icefarm_root).resolve()
    else:
        icefarm_root = be_root.parent.joinpath("iCEFARM").resolve()

    serials = parse_serials(pytestconfig.getoption("--e2e-serials"))

    if pytestconfig.getoption("--run-hardware-e2e"):
        if not serials:
            pytest.fail("--e2e-serials is required when --run-hardware-e2e is enabled.")
        if not icefarm_root.exists():
            pytest.fail(f"Could not locate iCEFARM repository at {icefarm_root}. Use --e2e-icefarm-root.")

    return HardwareE2EConfig(
        be_root=be_root,
        icefarm_root=icefarm_root,
        python_executable=pytestconfig.getoption("--e2e-python"),
        control_url=pytestconfig.getoption("--e2e-control-url"),
        serials=serials,
        live_output=pytestconfig.getoption("--e2e-live-output"),
    )


@pytest.fixture(scope="session")
def hardware_e2e_serials(hardware_e2e_config: HardwareE2EConfig) -> list[str]:
    return hardware_e2e_config.serials


@pytest.fixture(scope="session")
def first_hardware_serial(hardware_e2e_serials: list[str]) -> str:
    return hardware_e2e_serials[0]


@pytest.fixture(scope="session")
def first_two_hardware_serials(hardware_e2e_serials: list[str]) -> list[str]:
    if len(hardware_e2e_serials) < 2:
        pytest.skip("Need at least two serials for this multi-device hardware E2E test.")

    return hardware_e2e_serials[:2]
