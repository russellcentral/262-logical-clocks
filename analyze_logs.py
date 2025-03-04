import json
import sys
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def parse_json_log_file(filename, machine_id=None):
    """
    Reads each line of filename as JSON, returns a DataFrame.
    """
    rows = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            record['machine_id'] = machine_id
            rows.append(record)
    return pd.DataFrame(rows)

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_logs.py <logfile1> [<logfile2> ...]")
        sys.exit(1)
    
    log_files = sys.argv[1:]
    if not log_files:
        print("No log files specified.")
        sys.exit(1)

    # assumes all log files are in the same directory
    out_dir = os.path.dirname(os.path.abspath(log_files[0]))
    if not out_dir:
        out_dir = os.getcwd()  # fallback to current dir
    
    all_dfs = []
    for logf in log_files:
        guessed_id = None
        base = os.path.basename(logf)
        match = re.search(r'machine_(\d+)', base)
        guessed_id = int(match.group(1)) if match else None
        
        df = parse_json_log_file(logf, machine_id=guessed_id)
        df['log_file'] = logf  # keep track of which file
        all_dfs.append(df)
    
    data = pd.concat(all_dfs, ignore_index=True)
    data = data.sort_values(by='system_time')
    
    # Plot new_clock vs system_time for each machine
    plt.figure(figsize=(10, 6))
    for machine_id, grp in data.groupby('machine_id'):
        plt.plot(grp['system_time'], grp['new_clock'], label=f"Machine {machine_id}")
    plt.xlabel("System Time (s)")
    plt.ylabel("Lamport Clock (new_clock)")
    plt.title("Lamport Clock vs. System Time")
    plt.legend()
    plt.tight_layout()
    plot_path = os.path.join(out_dir, "lamport_clock_vs_time.png")
    plt.savefig(plot_path)
    plt.show()
    
    # Plot queue_len vs. system_time for RECEIVE events only
    receives = data[data['event'] == 'RECEIVE'].copy()
    plt.figure(figsize=(10, 6))
    for machine_id, grp in receives.groupby('machine_id'):
        plt.plot(grp['system_time'], grp['queue_len'], marker='o', linestyle='-', label=f"Machine {machine_id}")
    plt.xlabel("System Time (s)")
    plt.ylabel("Queue Length")
    plt.title("Message Queue Length on RECEIVE Events")
    plt.legend()
    plt.tight_layout()
    plot_path = os.path.join(out_dir, "queue_length_vs_time.png")
    plt.savefig(plot_path)
    plt.show()
    
    # Plot clock_jump vs system_time for each machine
    # A jump is (new_clock - old_clock)
    data['clock_jump'] = data['new_clock'] - data['old_clock']
    plt.figure(figsize=(10, 6))
    for machine_id, grp in data.groupby('machine_id'):
        # Filter out NaN clock_jump values
        jumps = grp[~grp['clock_jump'].isna()]
        plt.plot(jumps['system_time'], jumps['clock_jump'], label=f"Machine {machine_id}")
    plt.xlabel("System Time (s)")
    plt.ylabel("Clock Jump (new_clock - old_clock)")
    plt.title("Size of Clock Jumps Over Time")
    plt.legend()
    plt.tight_layout()
    plot_path = os.path.join(out_dir, "clock_jumps_vs_time.png")
    plt.savefig(plot_path)
    plt.show()
    
    print(f"Analysis complete. Plots saved in '{out_dir}'.")

if __name__ == "__main__":
    main()
