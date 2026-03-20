# Hardware E2E Tests

This suite runs short BitstreamEvolution jobs against a live iCEFARM deployment.

## What It Covers

- Single-device remote smoke runs for pulse-count and variance fitness modes
- Per-device smoke runs so each listed serial is exercised individually
- Two-device remote smoke runs to cover multi-device distribution paths

The tests do not assert a target fitness level. They only assert that the run
completes cleanly, produces expected workspace artifacts, and returns the
reserved devices to the available pool.

## Running

From the `BitstreamEvolutionPico2ice` repository root:

```bash
pytest test_e2e -m hardware_e2e \
  --run-hardware-e2e \
  --e2e-control-url http://localhost:8080 \
  --e2e-serials SERIAL_A,SERIAL_B
```

Optional flags:

- `--e2e-python /path/to/python`
- `--e2e-icefarm-root /path/to/iCEFARM`
- `--e2e-live-output`

Without `--run-hardware-e2e`, the suite is collected but skipped.

With `--e2e-live-output`, child process logs are streamed live to the terminal with prefixes like
`[e2e:remote_varmax_quick_smoke:stdout] ...` so it is obvious they are coming
from the BitstreamEvolution subprocess instead of pytest itself.
