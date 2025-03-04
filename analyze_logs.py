import json
import sys
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def parse_json_log_file(filename):
    """
    Returns a DataFrame of all events in the given JSON log file.
    Each row has keys like: event, system_time, machine_id, old_clock, new_clock, queue_len, etc.
    """
    rows = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            record['log_file'] = filename
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
        df = parse_json_log_file(logf)
        all_dfs.append(df)
    
    data = pd.concat(all_dfs, ignore_index=True)
    data = data.sort_values(by='system_time')

    for col in ['old_clock', 'new_clock', 'queue_len', 'final_clock', 'clock_rate']:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
    
    # 1) Summaries: clock_rate, final drift, average jump, max queue length
    # ---------------------------------------------------------------------

    # Gather STARTUP events for each machine
    startup_df = data[data['event'] == 'STARTUP'].copy()

    # Gather END events for each machine (final_clock)
    end_df = data[data['event'] == 'END'].copy()

    # For each machine, we can find the final_clock from the END event
    # We'll build a summary table
    summary_rows = []

    # Identify unique machines
    machines = data['machine_id'].dropna().unique()
    machines = sorted(machines)

    # We'll store final clocks to compute drift
    final_clocks = []

    for m_id in machines:
        # clock rate
        rate = None
        # final clock
        fclock = None

        # startup row
        srow = startup_df[startup_df['machine_id'] == m_id]
        if not srow.empty and 'clock_rate' in srow.columns:
            rate = srow['clock_rate'].iloc[0]

        # end row
        erow = end_df[end_df['machine_id'] == m_id]
        if not erow.empty and 'final_clock' in erow.columns:
            fclock = erow['final_clock'].iloc[0]
            final_clocks.append(fclock)

        # average jump size
        # we define jump as (new_clock - old_clock) for SEND, RECEIVE, INTERNAL
        # ignoring rows that lack old_clock/new_clock
        events_m = data[(data['machine_id'] == m_id) & 
                        (data['old_clock'].notna()) & 
                        (data['new_clock'].notna())]
        jumps = events_m['new_clock'] - events_m['old_clock']
        avg_jump = jumps.mean() if not jumps.empty else np.nan

        # max queue length
        # only valid for RECEIVE events
        rec_m = data[(data['machine_id'] == m_id) & (data['event'] == 'RECEIVE')]
        max_q = rec_m['queue_len'].max() if not rec_m.empty else 0

        summary_rows.append({
            "machine_id": m_id,
            "clock_rate": rate,
            "final_clock": fclock,
            "avg_jump_size": avg_jump,
            "max_queue_len": max_q
        })

    summary_df = pd.DataFrame(summary_rows)

    # compute final drift = max final clock - min final clock
    drift = None
    if len(final_clocks) > 1:
        drift = max(final_clocks) - min(final_clocks)
    else:
        drift = 0

    # 2) Plotting
    # We'll produce a single figure with 2 or 3 subplots:
    #   Subplot A: new_clock vs. system_time
    #   Subplot B: queue_len vs. system_time (for RECEIVE)
    #   Subplot C (optional): clock_jump vs. system_time

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=False)

    # Subplot A: new_clock vs. system_time
    ax1 = axes[0]
    for m_id, grp in data.groupby('machine_id'):
        # skip if no new_clock
        if 'new_clock' not in grp.columns:
            continue
        ax1.plot(grp['system_time'], grp['new_clock'], label=f"M{int(m_id)}")
    ax1.set_title("Lamport Clock vs. Time")
    ax1.set_xlabel("System Time (s)")
    ax1.set_ylabel("Lamport Clock")
    ax1.legend()

    # Subplot B: queue_len vs. system_time (RECEIVE only)
    ax2 = axes[1]
    receives = data[data['event'] == 'RECEIVE'].copy()
    for m_id, grp in receives.groupby('machine_id'):
        ax2.plot(grp['system_time'], grp['queue_len'], marker='o', linestyle='-', label=f"M{int(m_id)}")
    ax2.set_title("Queue Length (RECEIVE)")
    ax2.set_xlabel("System Time (s)")
    ax2.set_ylabel("Queue Len")
    ax2.legend()

    # Subplot C: (Optional) clock_jump vs. system_time
    # We'll do average jump or a line if we want. Let's do the line for illustration,
    # but you could skip it or just plot a single average point.
    ax3 = axes[2]
    data['clock_jump'] = data['new_clock'] - data['old_clock']
    # We only consider rows with old_clock/new_clock
    for m_id, grp in data.groupby('machine_id'):
        valid = grp[grp['clock_jump'].notna()]
        ax3.plot(valid['system_time'], valid['clock_jump'], label=f"M{int(m_id)}")
    ax3.set_title("Clock Jump vs. Time")
    ax3.set_xlabel("System Time (s)")
    ax3.set_ylabel("Jump (new_clock - old_clock)")
    ax3.legend()

    plt.tight_layout()
    # Save figure to same folder as logs
    fig_path = os.path.join(out_dir, "analysis_subplots.png")
    plt.savefig(fig_path)
    plt.close(fig)

    md_path = os.path.join(out_dir, "analysis_summary.md")
    with open(md_path, "w") as md_file:
        md_file.write("# Analysis Summary\n\n")

        md_file.write("## Summary Table\n\n")
        md_file.write(summary_df.to_markdown(index=False))
        md_file.write("\n\n")

        md_file.write(f"**Final Drift (max - min final_clock)**: {drift}\n\n")

        md_file.write("## Observations\n")
        md_file.write("- Here you can add your own notes or automated observations.\n")
        md_file.write("- For instance, check if the drift is large or small.\n")
        md_file.write("- Compare average jump sizes across machines.\n")
        md_file.write("- Check if max queue length indicates any backlog.\n\n")

        md_file.write(f"## Plot\n\n")
        md_file.write(f"![analysis_subplots](analysis_subplots.png)\n")

    print(f"Analysis complete. See '{md_path}' for details and '{fig_path}' for plots.")

if __name__ == "__main__":
    main()
