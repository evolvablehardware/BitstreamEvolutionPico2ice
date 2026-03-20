from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import signal
import shutil
import subprocess
import sys
import textwrap
import threading
import time
import urllib.request


KNOWN_FATAL_PATTERNS = (
    "Reached critical level of devices",
    "Reached exit_at_devices_remaining",
    "Device failed during evaluation stage",
)

DEFAULT_ROUTING = "ALL"
DEFAULT_ACCESSED_COLUMNS = "22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 52"
DEFAULT_SEED = "data/ice27_only_no_logic.asc"


def parse_serials(raw: str) -> list[str]:
    return [serial.strip() for serial in raw.split(",") if serial.strip()]


def available_devices(control_url: str) -> list[str]:
    with urllib.request.urlopen(f"{control_url}/devices") as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass(frozen=True)
class HardwareE2EConfig:
    be_root: Path
    icefarm_root: Path
    python_executable: str
    control_url: str
    serials: list[str]
    live_output: bool = False


@dataclass(frozen=True)
class RemoteEvolutionScenario:
    name: str
    fitness_func: str
    randomize_until: str
    randomize_threshold: float
    icefarm_mode: str = "QUICK"
    desired_freq: int | None = None
    num_samples: int = 1
    num_passes: int = 1
    population_size: int = 4
    generations: int = 2
    selection: str = "FIT_PROP_SEL"
    send_waveform: bool = False
    fitness_metric: str = "mce"
    timeout_seconds: int = 240

    def expected_workspace_files(self) -> list[Path]:
        files = [
            Path("workspace/builtconfig.ini"),
            Path("workspace/alllivedata.log"),
            Path("workspace/bestlivedata.log"),
            Path("workspace/violinlivedata.log"),
            Path("workspace/experiment_asc/hardware1.asc"),
            Path("workspace/experiment_bin/hardware1.bin"),
        ]
        if self.fitness_func == "VARIANCE":
            files.extend(
                [
                    Path("workspace/heatmaplivedata.log"),
                    Path("workspace/waveformlivedata.log"),
                ]
            )
            if self.randomize_until == "VARIANCE":
                files.append(Path("workspace/randomizationdata.log"))
        else:
            files.append(Path("workspace/pulselivedata.log"))

        return files


@dataclass(frozen=True)
class EvolutionRunResult:
    scenario: RemoteEvolutionScenario
    run_root: Path
    config_path: Path
    stdout_path: Path
    stderr_path: Path
    returncode: int

    def read_stdout(self) -> str:
        return self.stdout_path.read_text()

    def read_stderr(self) -> str:
        return self.stderr_path.read_text()

    def assert_success(self) -> None:
        stdout = self.read_stdout()
        stderr = self.read_stderr()

        if self.returncode != 0:
            raise AssertionError(
                textwrap.dedent(
                    f"""\
                    Scenario {self.scenario.name} failed with exit code {self.returncode}.
                    Run root: {self.run_root}
                    Config: {self.config_path}
                    Stdout: {self.stdout_path}
                    Stderr: {self.stderr_path}
                    ---- stdout tail ----
                    {tail(stdout)}
                    ---- stderr tail ----
                    {tail(stderr)}
                    """
                )
            )

        for pattern in KNOWN_FATAL_PATTERNS:
            if pattern in stdout or pattern in stderr:
                raise AssertionError(
                    f"Scenario {self.scenario.name} hit fatal pattern '{pattern}'. See {self.stdout_path} and {self.stderr_path}."
                )

        for rel_path in self.scenario.expected_workspace_files():
            path = self.run_root.joinpath(rel_path)
            if not path.exists():
                raise AssertionError(f"Expected artifact {path} was not created for scenario {self.scenario.name}.")
            if path.stat().st_size == 0:
                raise AssertionError(f"Expected artifact {path} is empty for scenario {self.scenario.name}.")


class HostEvolutionRunner:
    def __init__(self, config: HardwareE2EConfig):
        self._config = config

    def run_remote_scenario(
        self,
        tmp_path: Path,
        scenario: RemoteEvolutionScenario,
        serials: list[str],
    ) -> EvolutionRunResult:
        run_root = tmp_path.joinpath(scenario.name)
        prepare_run_root(run_root, self._config.be_root)

        config_path = run_root.joinpath(f"{scenario.name}.ini")
        config_path.write_text(build_remote_config_text(scenario, self._config.control_url, serials))

        stdout_path = run_root.joinpath("stdout.log")
        stderr_path = run_root.joinpath("stderr.log")

        env = os.environ.copy()
        extra_pythonpath = str(self._config.icefarm_root.joinpath("src"))
        env["PYTHONPATH"] = join_pythonpath(extra_pythonpath, env.get("PYTHONPATH"))
        env["MPLBACKEND"] = "Agg"
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [
            self._config.python_executable,
            "src/evolve.py",
            "-c",
            config_path.name,
            "-d",
            f"hardware-e2e:{scenario.name}",
        ]

        if self._config.live_output:
            stdout_text, stderr_text, returncode = _run_with_live_output(
                cmd=cmd,
                cwd=run_root,
                env=env,
                timeout_seconds=scenario.timeout_seconds,
                scenario_name=scenario.name,
            )
        else:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=run_root,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=scenario.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                stdout_path.write_text(_coerce_text(exc.stdout))
                stderr_path.write_text(_coerce_text(exc.stderr))
                raise AssertionError(
                    f"Scenario {scenario.name} timed out after {scenario.timeout_seconds}s. "
                    f"See {stdout_path} and {stderr_path}."
                ) from exc

            stdout_text = proc.stdout
            stderr_text = proc.stderr
            returncode = proc.returncode

        stdout_path.write_text(stdout_text)
        stderr_path.write_text(stderr_text)

        return EvolutionRunResult(
            scenario=scenario,
            run_root=run_root,
            config_path=config_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            returncode=returncode,
        )


def build_remote_config_text(
    scenario: RemoteEvolutionScenario,
    control_url: str,
    serials: list[str],
) -> str:
    fitness_lines = [f"fitness_func = {scenario.fitness_func}"]
    if scenario.desired_freq is not None:
        fitness_lines.append(f"desired_freq = {scenario.desired_freq}")
    fitness_lines.append(f"num_samples = {scenario.num_samples}")
    fitness_lines.append(f"num_passes = {scenario.num_passes}")
    fitness_block = textwrap.indent("\n".join(fitness_lines), "        ")

    return textwrap.dedent(
        f"""\
        [TOP-LEVEL PARAMETERS]
        simulation_mode = REMOTE
        base_config = data/default_config.ini

        [FITNESS PARAMETERS]
{fitness_block}

        [GA PARAMETERS]
        fitness_metric = {scenario.fitness_metric}
        population_size = {scenario.population_size}
        mutation_probability = 0.0021
        mutation_type = RANK
        crossover_probability = 0.7
        elitism_fraction = 0.1
        selection = {scenario.selection}
        diversity_measure = NONE
        random_injection = 0.0
        chaos_injection = 5

        [INITIALIZATION PARAMETERS]
        init_mode = RANDOM
        randomize_until = {scenario.randomize_until}
        randomize_threshold = {scenario.randomize_threshold}
        randomize_mode = RANDOM
        seed = {DEFAULT_SEED}

        [STOPPING CONDITION PARAMETERS]
        generations = {scenario.generations}
        target_fitness = IGNORE

        [PLOTTING PARAMETERS]
        launch_plots = false
        frame_interval = 1000

        [LOGGING PARAMETERS]
        log_level = 4
        save_log = true
        save_plots = false
        backup_workspace = false
        log_file = ./workspace/log
        plots_dir = ./workspace/plots
        output_dir = ./prev_workspaces
        final_experiment_dir = ./experiments
        asc_dir = ./workspace/experiment_asc
        bin_dir = ./workspace/experiment_bin
        data_dir = ./workspace/experiment_data
        analysis = ./workspace/analysis
        best_file = ./workspace/best.asc
        generations_dir = ./workspace/generations
        src_populations_dir = ./workspace/source_populations

        [HARDWARE PARAMETERS]
        routing = {DEFAULT_ROUTING}
        accessed_columns = {DEFAULT_ACCESSED_COLUMNS}

        [ICEFARM PARAMETERS]
        url = {control_url}
        mode = {scenario.icefarm_mode}
        devices = {json.dumps(serials)}
        exit_at_devices_remaining = -1
        reserve_on_device_failure_limit = NO
        client_batch_amount_circuits = {scenario.population_size}
        buffer_batch_amount = 1
        results_flush_interval_seconds = 5
        send_waveform = {"true" if scenario.send_waveform else "false"}
        """
    )


def join_pythonpath(new_entry: str, existing: str | None) -> str:
    if existing:
        return f"{new_entry}{os.pathsep}{existing}"
    return new_entry


def prepare_run_root(run_root: Path, be_root: Path) -> None:
    if run_root.exists():
        shutil.rmtree(run_root)

    run_root.mkdir(parents=True, exist_ok=True)
    run_root.joinpath("src").symlink_to(be_root.joinpath("src"), target_is_directory=True)
    run_root.joinpath("data").symlink_to(be_root.joinpath("data"), target_is_directory=True)
    run_root.joinpath("workspace").mkdir()


def assert_serials_available_again(control_url: str, serials: list[str], timeout_seconds: int = 15) -> None:
    deadline = time.monotonic() + timeout_seconds
    missing = sorted(serials)

    while time.monotonic() < deadline:
        currently_available = set(available_devices(control_url))
        missing = sorted(set(serials) - currently_available)
        if not missing:
            return

        time.sleep(1)

    raise AssertionError(
        f"Expected devices to be available again after the run, but these serials are still unavailable: {missing}"
    )


def assert_serials_present_before_run(control_url: str, serials: list[str]) -> None:
    currently_available = set(available_devices(control_url))
    missing = sorted(set(serials) - currently_available)
    if missing:
        raise AssertionError(
            f"Cannot start hardware E2E run because these serials are not currently available: {missing}"
        )


def tail(value: str, lines: int = 40) -> str:
    split = value.splitlines()
    return "\n".join(split[-lines:])


def _coerce_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _run_with_live_output(
    *,
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout_seconds: int,
    scenario_name: str,
    stdout_writer=None,
    stderr_writer=None,
) -> tuple[str, str, int]:
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        start_new_session=True,
    )

    if proc.stdout is None or proc.stderr is None:
        raise AssertionError("Could not capture live output from evolve subprocess.")

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    stdout_writer = stdout_writer or sys.__stdout__
    stderr_writer = stderr_writer or sys.__stderr__

    stdout_thread = threading.Thread(
        target=_stream_live_output,
        args=(proc.stdout, stdout_chunks, stdout_writer, scenario_name, "stdout"),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_stream_live_output,
        args=(proc.stderr, stderr_chunks, stderr_writer, scenario_name, "stderr"),
        daemon=True,
    )

    stdout_thread.start()
    stderr_thread.start()

    try:
        returncode = proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        os.killpg(proc.pid, signal.SIGKILL)
        returncode = proc.wait()
        stdout_thread.join()
        stderr_thread.join()
        exc.stdout = "".join(stdout_chunks)
        exc.stderr = "".join(stderr_chunks)
        raise subprocess.TimeoutExpired(
            cmd=exc.cmd,
            timeout=exc.timeout,
            output=exc.stdout,
            stderr=exc.stderr,
        ) from exc

    stdout_thread.join()
    stderr_thread.join()

    return "".join(stdout_chunks), "".join(stderr_chunks), returncode


def _stream_live_output(
    stream,
    buffer: list[str],
    writer,
    scenario_name: str,
    stream_name: str,
) -> None:
    for line in iter(stream.readline, ""):
        buffer.append(line)
        writer.write(_format_live_output_line(line, scenario_name, stream_name))
        writer.flush()

    stream.close()


def _format_live_output_line(line: str, scenario_name: str, stream_name: str) -> str:
    prefix = f"[e2e:{scenario_name}:{stream_name}] "
    normalized = line.rstrip("\n")
    if not normalized:
        return prefix + "\n"

    return prefix + normalized + "\n"
