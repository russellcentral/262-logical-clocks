```markdown
# 262-Logical-Clocks

This repository implements a **small distributed system** in Python using **Lamport logical clocks**. It features:

- Multiple “virtual machines,” each with:
  - **Random clock rates** (1–6 ticks per real second),
  - **Lamport clock** logic for send/receive/internal events,
  - **TCP socket** communication,
  - **JSON-based logging** of all events.
- A **helper script** (`run_machine.py`) to launch multiple local machines.
- An **analysis script** (`analyze_logs.py`) that merges logs, computes clock drift, queue lengths, etc., and generates plots.
- A **Pytest test suite** covering both unit and integration tests.

---

## 1. Running the System Locally

1. **Clone** or copy this repository to your local machine.  
2. **Navigate** to the project root directory:
   ```bash
   cd 262-logical-clocks
   ```
3. **Launch** multiple local machines using:
   ```bash
   python run_machine.py
   ```
   - This spawns **three** local processes, each listening on a unique port (`5001, 5002, 5003` by default).
   - By default, each machine runs for **60 seconds**, and logs are saved in a time-stamped subdirectory under `logs/`, e.g. `logs/run_2025-03-05_15-30-01/`.
   - After ~70 seconds, any remaining processes are terminated.

---

## 2. Running on Multiple Physical Machines

To truly distribute the system across separate hosts:

1. **Pick** a unique port for each machine.  
2. **Machine 1** (Host A, IP `192.168.1.10`):
   ```bash
   python machine.py \
       --id 1 \
       --port 5001 \
       --peers "192.168.1.20:5002,192.168.1.30:5003" \
       --log "logs/machine_1.log" \
       --duration 60
   ```
3. **Machine 2** (Host B, IP `192.168.1.20`):
   ```bash
   python machine.py \
       --id 2 \
       --port 5002 \
       --peers "192.168.1.10:5001,192.168.1.30:5003" \
       --log "logs/machine_2.log" \
       --duration 60
   ```
4. **Machine 3** (Host C, IP `192.168.1.30`):
   ```bash
   python machine.py \
       --id 3 \
       --port 5003 \
       --peers "192.168.1.10:5001,192.168.1.20:5002" \
       --log "logs/machine_3.log" \
       --duration 60
   ```

Each machine runs independently, logging events to its own file. After 60 seconds, each stops. Collect the logs from each host and run the **analysis** script locally to visualize results (see below).

---

## 3. Parsing Logs & Generating Plots

After running the system (locally or across multiple machines), you’ll have JSON log files (e.g., `machine_1.log`, `machine_2.log`, etc.). To parse them and produce analysis plots:

```bash
python analyze_logs.py logs/run_2025-03-05_15-30-01/machine_*.log
```

- **Process**:
  1. **Merges** all specified log files into a single Pandas DataFrame.  
  2. **Computes** key metrics:
     - **Final drift** (`max(final_clock) - min(final_clock)`),
     - **Average jump size** (`(new_clock - old_clock)` across SEND/RECEIVE/INTERNAL),
     - **Max queue length** (for RECEIVE events),
     - Etc.
  3. **Generates** two files in the same directory:
     - `analysis_subplots.png`: Subplots for Lamport clock vs. time, queue length vs. time, clock jumps vs. time.
     - `analysis_summary.md`: A Markdown summary with final drift, average jump, and a summary table of machine stats.

---

## 4. Implementation Details

### 4.1 `machine.py` – The Machine Class

Each machine acts as a **TCP server** to receive timestamps from peers and a **client** to send its local clock to other machines. Key points:

1. **Initialization** (`__init__`):
   - **`machine_id`**: Unique ID for the machine (1, 2, 3, etc.).
   - **`listen_port`**: TCP port where this machine **listens**.
   - **`peer_addresses`**: List of `(host, port)` tuples for other machines.
   - **`clock_rate`**: Random integer in `[1..6]` chosen at startup, meaning the machine processes `clock_rate` “ticks” per second.
   - **`local_clock`**: The machine’s Lamport clock, initially 0.
   - **`incoming_queue`**: A `queue.Queue()` for timestamps received from peers.
   - **`server_socket`**: The **listening** socket (TCP). Bound to `(0.0.0.0, listen_port)` and set to listen with a 1s timeout.
   - **`log_file`**: A line-buffered file where every event is logged as JSON.

2. **Server Socket & Receiving**:
   - **`listen_for_connections()`**: In a loop, calls `accept()` on the server socket. For each incoming connection, spawns a thread to handle it (`handle_incoming_connection`).
   - **`handle_incoming_connection(conn)`**: Reads data in chunks, splits by `\n`, parses each line as an integer timestamp, and puts it in `incoming_queue`.

3. **Main Loop** (`main_loop()`):
   - Runs for `run_seconds` total.
   - Sleeps `1.0 / clock_rate` each iteration (simulating “ticks”).
   - Each tick:
     - If `incoming_queue` is **not** empty, **process** a message (`handle_receive()`).
     - Otherwise, calls `handle_no_message()` to pick a random action (SEND to 1 peer, SEND to 2 peers, or INTERNAL event).

4. **Actions**:
   - **`handle_receive()`**:
     - Dequeues a timestamp, updates `local_clock = max(local_clock, received) + 1`.
     - Logs a `RECEIVE` event (with queue length, old/new clock).
   - **`send_message()`**:
     - Increments `local_clock` by 1.
     - For each recipient `(host, port)`, creates a **new** TCP socket, connects, sends `local_clock\n`.
     - Logs a `SEND`.
   - **`internal_event()`**:
     - Increments `local_clock` by 1.
     - Logs an `INTERNAL`.

5. **Shutdown** (`shutdown()`):
   - Logs an `END` event with `final_clock`.
   - Closes the server socket and the log file.

### 4.2 `run_machine.py` – Spawning Multiple Machines Locally

- **Orchestrates** multiple local machines via Python’s `multiprocessing`.  
- **Generates** a timestamp-based folder in `logs/` (e.g., `logs/run_2025-03-05_15-30-01/`) unless `--logs_dir` is specified.  
- For each machine (IDs 1..3):
  - Chooses a **port** (`5001`, `5002`, `5003`),
  - Builds a **log file** path, e.g. `logs/run_2025-03-05_15-30-01/machine_1.log`,
  - Spawns a `Process` that calls `machine.py` with the relevant arguments.
- Waits ~70 seconds to allow them to finish (default `--duration=60`), then terminates any leftover processes.

### 4.3 `analyze_logs.py` – Parsing & Plotting

- **Reads** one or more JSON log files, each containing lines like:
  ```json
  {"event": "SEND", "system_time": 1677782102.9545, "machine_id": 1, "old_clock": 5, "new_clock": 6, "recipients": [["localhost", 5002]]}
  ```
- **Builds** a combined Pandas DataFrame:
  - Sorts by `system_time`.
  - Converts columns like `old_clock`, `new_clock`, `queue_len`, etc. to numeric.
- **Computes**:
  - **Final clock** from `END` events,
  - **Drift** = `max(final_clock) - min(final_clock)`,
  - **Average jump** = mean of `(new_clock - old_clock)` for `SEND/RECEIVE/INTERNAL`,
  - **Max queue length** per machine.
- **Generates** subplots:
  1. **Lamport clock vs. time**,
  2. **Queue length** vs. time (only for `RECEIVE`),
  3. **Clock jump** vs. time.
- **Writes** `analysis_subplots.png` and `analysis_summary.md` to the **same** directory as the logs.

---

## 5. Testing Strategy

We use **Pytest** to validate correctness. Run:

```bash
python -m pytest
```

### 5.1 `test_machine.py` (Unit Tests)

- **Tests** the `Machine` class in isolation:
  - **`test_machine_startup_logging`**: Verifies a single machine logs `STARTUP` with a valid clock rate.  
  - **`test_machine_internal_event`**: Calls `internal_event()`, checks the log.  
  - **`test_machine_receive_event`**: Manually enqueues a timestamp, checks `RECEIVE`.  
  - **`test_machine_send_event`**: Mocks sockets to verify `SEND` is logged.  
  - **`test_machine_end_event`**: Ensures `END` is logged at shutdown.

### 5.2 `test_integration.py` (Integration)

- **Spawns** multiple machines locally via `run_machine.py`, passing `--logs_dir` and a short `--duration`.  
- Waits, kills the process, then checks that logs contain `STARTUP`.  
- Confirms the multi-machine orchestration code works.

### 5.3 `test_analyze_logs.py` (Analysis)

- Uses **static sample logs** in `tests/sample_logs/` (like `machine_1.log`, etc.).  
- Copies them to a temporary directory, then calls `analyze_logs.py` with the **real** filenames.  
- Checks the script creates `analysis_subplots.png` and `analysis_summary.md`, and that “Final Drift” / “Summary Table” appear in the summary.

---

## 6. Conclusion

- **`machine.py`**: Defines a single node’s Lamport clock logic, random event generation, socket communication, and JSON logging.  
- **`run_machine.py`**: Spawns multiple local machines in separate processes for easy testing.  
- **`analyze_logs.py`**: Parses the resulting logs, computes drift, and plots the data.  
- **Tests** ensure that each component (machine logic, multi-machine integration, log analysis) is correct and robust.

This architecture **cleanly demonstrates** Lamport clock synchronization with real network communication and comprehensive logging/analysis. You can expand it with additional machines, custom event distributions, or more sophisticated analysis as needed.
```

---
