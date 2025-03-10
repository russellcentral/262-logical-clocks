#!/usr/bin/env python3
"""
run_machine.py

Helper script to launch multiple local machine processes.
Now creates a unique subdirectory in logs/ for each run,
based on the current date/time.

Usage:
    python run_machine.py
"""

import argparse
import multiprocessing
import time
import subprocess
import os
import datetime

def launch_machine(machine_id, port, peers, log_path, duration=60):
    """
    Calls 'python machine.py' in a subprocess with the given arguments.
    """
    peer_str = ",".join(f"{host}:{p}" for (host, p) in peers)
    cmd = [
        "python", "machine.py",
        "--id", str(machine_id),
        "--port", str(port),
        "--peers", peer_str,
        "--log", log_path,
        "--duration", str(duration)
    ]
    print(f"Launching: {' '.join(cmd)}")
    subprocess.run(cmd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs_dir", type=str, default="", help="Override logs directory")
    parser.add_argument("--duration", type=int, default=60, help="Run duration")
    args = parser.parse_args()

    if args.logs_dir:
        logs_subdir = args.logs_dir
    else:
        run_id = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logs_subdir = os.path.join("logs", f"run_{run_id}")

    os.makedirs(logs_subdir, exist_ok=True)
    
    # Example config for three machines
    machine_configs = [
        {"id": 1, "port": 5001},
        {"id": 2, "port": 5002},
        {"id": 3, "port": 5003},
    ]
    
    # Build peer lists for each machine (local test)
    for cfg in machine_configs:
        peers = []
        for other in machine_configs:
            if other["id"] != cfg["id"]:
                # For a local test, all are "localhost"
                peers.append(("localhost", other["port"]))
        cfg["peers"] = peers
    
    # Create processes for each machine
    processes = []
    for cfg in machine_configs:
        log_file = os.path.join(logs_subdir, f"machine_{cfg['id']}.log")
        p = multiprocessing.Process(
            target=launch_machine,
            args=(
                cfg["id"],
                cfg["port"],
                cfg["peers"],
                log_file,
                args.duration
            )
        )
        p.start()
        processes.append(p)

    # Wait for them to finish (each runs for 60s by default)
    time.sleep(70)

    # Optionally, terminate any that are still alive
    for p in processes:
        if p.is_alive():
            p.terminate()
            p.join()
