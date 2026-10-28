"""Run a pipeline script from a Databricks notebook so its output survives a crash.

`subprocess.run(..., capture_output=True)` prints a script's output only after it finishes, so when the
notebook's Python dies mid-run (seen on serverless GPU: "Py4JException: Error while obtaining a new
communication channel") everything the script printed is lost. `run` instead prints each line as it
comes, appends it to a log file (on Databricks, the landing volume, which outlives the notebook), and says
how the script ended: an exit code, or the signal that killed it, with the machine's free memory.
"""

from __future__ import annotations

import datetime as dt
import signal
import subprocess
from pathlib import Path

from .telemetry import traced

_SIGNAL_HINT = {signal.SIGKILL: "usually out of memory", signal.SIGTERM: "stopped from outside"}


def _free_memory() -> str:
    try:
        lines = Path("/proc/meminfo").read_text().splitlines()
        info = {k.strip(): v.strip() for k, v in (x.split(":", 1) for x in lines if ":" in x)}
        return f"memory available {info.get('MemAvailable', '?')} of {info.get('MemTotal', '?')}"
    except OSError:
        return "memory unknown"


def _ending(code: int) -> str:
    if code < 0:
        sig = signal.Signals(-code)
        hint = _SIGNAL_HINT.get(sig, "")
        return f"killed by signal {-code} ({sig.name}{', ' + hint if hint else ''}); {_free_memory()}"
    return f"exit code {code}"


@traced
def run(cmd: list[str], log_path: str | Path | None = None, cwd: str | Path | None = None,
        check: bool = False) -> int:
    """Run `cmd`, printing stdout and stderr line by line and appending them to `log_path`.
    Returns the exit code (negative: killed by that signal); with check=True, raises unless it's 0."""
    log = None
    if log_path:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        log = open(log_path, "a", buffering=1)  # noqa: SIM115 - line-buffered, closed below
        log.write(f"--- {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S} UTC: {' '.join(map(str, cmd))}\n")
    try:
        with subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              bufsize=1) as p:
            for line in p.stdout:
                print(line, end="", flush=True)
                if log:
                    log.write(line)
        code = p.returncode
        ending = _ending(code)
        print(f"--- {Path(str(cmd[1] if len(cmd) > 1 else cmd[0])).name}: {ending}", flush=True)
        if log:
            log.write(f"--- {ending}\n")
    finally:
        if log:
            log.close()
    if check and code != 0:
        raise RuntimeError(f"{' '.join(map(str, cmd[:2]))} failed: {ending}")
    return code


@traced
def log_dir(catalog: str) -> str:
    """Where notebooks keep script logs on Databricks: the landing volume (same name in every target)."""
    return f"/Volumes/{catalog}/landing_dental_omop_perio/data/logs"
