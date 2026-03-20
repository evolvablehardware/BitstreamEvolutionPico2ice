import io
import os
import sys

from test_e2e.helpers import _run_with_live_output


def test_run_with_live_output_prefixes_and_captures(tmp_path):
    stdout_writer = io.StringIO()
    stderr_writer = io.StringIO()

    stdout, stderr, returncode = _run_with_live_output(
        cmd=[
            sys.executable,
            "-c",
            "import sys; print('hello from child'); print('warning from child', file=sys.stderr)",
        ],
        cwd=tmp_path,
        env=os.environ.copy(),
        timeout_seconds=5,
        scenario_name="demo_scenario",
        stdout_writer=stdout_writer,
        stderr_writer=stderr_writer,
    )

    assert returncode == 0
    assert stdout == "hello from child\n"
    assert stderr == "warning from child\n"
    assert stdout_writer.getvalue() == "[e2e:demo_scenario:stdout] hello from child\n"
    assert stderr_writer.getvalue() == "[e2e:demo_scenario:stderr] warning from child\n"
