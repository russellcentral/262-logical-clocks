# tests/test_integration.py

import pytest
import subprocess
import time
import os
import glob

def test_run_machine_local(tmp_path):
    """
    Launch multiple machines locally (via run_machine.py),
    wait, then check logs for a STARTUP event.
    """
    logs_dir = tmp_path / "logs_run"
    cmd = [
        "python", "run_machine.py",
        "--logs_dir", str(logs_dir),
        "--duration", "5"
    ]
    proc = subprocess.Popen(cmd)
    # Wait ~10s for them to produce logs (they run 60s by default)
    time.sleep(10)
    proc.terminate()
    proc.wait()

    # Glob logs: run_machine.py should create logs/run_<timestamp>/machine_*.log
    log_files = list(glob.glob(os.path.join("logs", "**", "machine_*.log"), recursive=True))
    assert len(log_files) > 0, "Should produce at least one machine log"

    found_startup = False
    for lf in log_files:
        with open(lf, "r") as f:
            content = f.read()
            if '"event": "STARTUP"' in content:
                found_startup = True
                break

    assert found_startup, "No STARTUP event found in any machine log"
