# iCEFARM Evaluation Hang Bug Report

## Summary

BitstreamEvolution hangs indefinitely during remote circuit evaluation when an iCEFARM worker becomes temporarily unreachable. The evolution process gets stuck and never recovers, even after the worker comes back online. This has been reproduced twice in succession, both times around generation 33-35 of a 5000-generation run using `mode = all` with 4 devices.

## Reproduction

**Config (farmconfig.ini):**
```ini
[ICEFARM PARAMETERS]
url = http://localhost:8080
mode = all
devices = 4
```

**Steps:**
1. Start an evolution run with `mode = all` and 4 devices
2. Wait ~30-35 generations (~30+ minutes)
3. Observe the container output stall after `Sending circuits for remote evaluation...`
4. The message `Remote evaluation complete.` never appears
5. The process loops indefinitely refreshing device reservations but never progresses

## Observed Container Output at Failure

```
Sending circuits for remote evaluation...
[EventServer] [socket@http://localhost:8081] disconnected: client disconnect
[EventServer] [socket@http://localhost:8080] received reservation end event
reservation for EFB54F1CAC02552B ended
Failed to send request to worker http://localhost:8081 for serials ['EFB54F1CAC02552B']
Failed to send request to worker http://localhost:8081 for serials ['B6E59229BFBEB098']
Failed to send request to worker http://localhost:8081 for serials ['800CE6BD9F87C6F5']
```

After this, the output is an infinite loop of:
```
[EventServer] [socket@http://localhost:8080] received reservation ending soon event
refreshed reservation of <SERIAL>
```

The iCEFARM worker logs show it recovers and responds to heartbeats, but no new evaluation requests are sent to it.

## Root Cause Analysis

The hang occurs in `EvolutionClient.get_result()` in `BitstreamEvolutionPico2ice/src/Circuit/RemoteCircuit.py` (lines 73-106):

```python
def get_result(self, circuit: FileBasedCircuit) -> Dict[str, Any]:
    if not self._result_map:
        assigned_evaluations = [PulseCountEvaluation(serials, filepath)
            for serials, filepath in self._command_queue if serials]
        # ...
        self._logger.info("Sending circuits for remote evaluation...")

        # THIS LINE HANGS:
        for serial, evaluation, result in self._client.evaluateEvaluations(assigned_evaluations):
            # ...

        self._logger.info("Remote evaluation complete.")
```

The call to `self._client.evaluateEvaluations(assigned_evaluations)` is a blocking iterator provided by the `icefarm` Python package (`PulseCountClient`). When one or more worker requests fail (as seen in the `Failed to send request to worker` messages), the iterator appears to block indefinitely waiting for results that will never arrive. There is:

1. **No timeout** on the evaluation request — it waits forever
2. **No retry mechanism** — failed requests are not re-sent to recovered workers
3. **No error propagation** — the `Failed to send request` messages are logged by icefarm but not raised as exceptions to the caller
4. **No circuit-level recovery** — even if a single circuit's evaluation fails, the entire generation (all 50 circuits) is lost

## Affected Code Paths

### In `icefarm` package (where the fix should go):
- `PulseCountClient.evaluateEvaluations()` — needs timeout and error handling
- Worker request sending logic — needs retry on transient failures
- The event/socket connection to `localhost:8081` — needs reconnection logic

### In `BitstreamEvolutionPico2ice` (caller side, `src/Circuit/RemoteCircuit.py`):
- `EvolutionClient.get_result()` line 95 — could wrap in a timeout as a defensive measure
- No mechanism to skip or retry a failed generation

## Suggested Fixes (in order of priority)

### 1. Add a timeout to `evaluateEvaluations()` (icefarm)
The evaluation iterator should raise a `TimeoutError` if results aren't received within a configurable duration (e.g., 60-120 seconds per circuit batch).

### 2. Retry failed worker requests (icefarm)
When a `Failed to send request to worker` occurs, the evaluation should be re-queued and sent to the same or a different available worker, with a maximum retry count.

### 3. Propagate errors to the caller (icefarm)
Failed evaluations should raise exceptions or return error sentinels rather than silently hanging. The caller can then decide whether to retry, skip the circuit, or abort.

### 4. Add defensive timeout in BitstreamEvolution (caller side)
As a safety net, `EvolutionClient.get_result()` could wrap `evaluateEvaluations()` with a `signal.alarm` or `threading.Timer` timeout, and re-raise with context about which generation/circuits failed.

### 5. Add worker health check before sending evaluations (icefarm)
Before dispatching evaluations, verify that all required workers are reachable. If a worker is down, either wait for recovery or reassign its devices to available workers.

## Environment

- **BitstreamEvolution repo:** BitstreamEvolutionPico2ice (Pico2ice fork)
- **icefarm package:** installed via pip in Docker container
- **Docker image:** `bitstreamevolution` (Ubuntu noble-20251013 base)
- **iCEFARM architecture:** control server on `:8080`, worker on `:8081`, 4 devices
- **Failure timing:** Consistently around generation 33-35 with `mode = all`
