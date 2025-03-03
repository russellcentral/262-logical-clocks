#!/usr/bin/env python3
"""
run_machine.py

Helper script to launch multiple local machine processes.
Adjust ports and logs as needed.

Usage:
    python run_machine.py
"""

import multiprocessing
import time
import subprocess
import os

def launch_machine(machine_id, port, peers, log, duration=60):
    """
    Calls 'python machine.py' in a subprocess with the given arguments.
    """
    peer_str = ",".join(f"{host}:{p}" for (host, p) in peers)
    cmd = [
        "python", "machine.py",
        "--id", str(machine_id),
        "--port", str(port),
        "--peers", peer_str,
        "--log", log,
        "--duration", str(duration)
    ]
    print(f"Launching: {' '.join(cmd)}")
    subprocess.run(cmd)

if __name__ == "__main__":
    # Example config for three machines
    machine_configs = [
        {"id": 1, "port": 5001, "log": "logs/machine_1.log"},
        {"id": 2, "port": 5002, "log": "logs/machine_2.log"},
        {"id": 3, "port": 5003, "log": "logs/machine_3.log"},
    ]

    # Build peer lists for each machine
    for cfg in machine_configs:
        peers = []
        for other in machine_configs:
            if other["id"] != cfg["id"]:
                # For a local test, all are "localhost"
                peers.append(("localhost", other["port"]))
        cfg["peers"] = peers

    processes = []
    for cfg in machine_configs:
        p = multiprocessing.Process(
            target=launch_machine,
            args=(cfg["id"], cfg["port"], cfg["peers"], cfg["log"], 60)
        )
        p.start()
        processes.append(p)

    # Wait for them to finish (each runs for 60s by default)
    # or we can sleep a bit longer to ensure logs are written
    time.sleep(70)

    # Optionally, terminate any that are still alive
    for p in processes:
        if p.is_alive():
            p.terminate()
            p.join()
