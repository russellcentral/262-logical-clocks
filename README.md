# 262-Logical-Clocks

This repository implements a **small distributed system** in Python using **Lamport logical clocks** following the design specifications. It features:

- Multiple “virtual machines,” each with:
  - **Random clock rates** (1–6 ticks per real second),
  - **Lamport clock** logic for send/receive/internal events,
  - **TCP socket** communication where each node acts as both a server and a client,
  - **JSON-based logging** of all events in a line-buffered file.
- A **helper script** (`run_machine.py`) to launch multiple local machines.
- An **analysis script** (`analyze_logs.py`) that merges logs, computes statistics like clock drift and queue lengths, and generates plots.
- A **Pytest test suite** that covers both unit and integration tests because we engage in proper coding practices.

For more information, please refer to our engineering notebook.

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
   - By default, each machine runs for **60 seconds**, and logs are saved in a time-stamped subdirectory under `logs/`; an example format is `logs/run_2025-03-05_15-30-01/`.
   - After ~70 seconds, any remaining processes are terminated.

**Tip**: When running the code, you can specify a custom duration or logs directory, for example:
```bash
python run_machine.py --duration 30 --logs_dir "logs/custom_run"
```
This makes each machine run for 30 seconds and store logs in `logs/custom_run/`.

---

## 2. Running on Multiple Physical Machines

To properly distribute the system across separate hosts:

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

Each machine runs independently, logging events to its own file. After 60 seconds, each stops. Collect the logs from each host and run the **analysis** script locally to visualize results (see below for more details).

---

## 3. Parsing Logs & Generating Plots

After running the system (locally or across multiple machines), you’ll have **JSON log files** (e.g., `machine_1.log`, `machine_2.log`, etc.). To parse them and produce analysis plots:

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
     - `analysis_subplots.png`: Subplots for **Lamport clock vs. time**, **queue length vs. time**, **clock jumps vs. time**.
     - `analysis_summary.md`: A Markdown summary with final drift, average jump, and a summary table of machine stats.

**Example** of a typical line in the logs (JSON):
```json
{"event": "SEND", "system_time": 1677782102.9545, "machine_id": 1, "old_clock": 5, "new_clock": 6, "recipients": [["localhost", 5002]]}
```

---

## 4. Implementation Details

### 4.1 `machine.py` – The Machine Class

Each machine acts as a **TCP server** to receive timestamps from peers and a **client** to send its local clock to other machines. Below is a summary of the core logic.

1. **Initialization** (`__init__`):
   - **`machine_id`**: Unique ID for the machine (1, 2, 3, etc.).
   - **`listen_port`**: TCP port where this machine **listens** for incoming connections.
   - **`peer_addresses`**: A list of `(host, port)` tuples for other machines in the system.
   - **`clock_rate`**: A random integer in `[1, ..., 6]` that is chosen at startup, meaning the machine processes `clock_rate` “ticks” per real second.
   - **`local_clock`**: The machine’s Lamport clock, which is initially 0.
   - **`incoming_queue`**: A `queue.Queue()` for timestamps received from peers (via `handle_incoming_connection`).
   - **`server_socket`**: The **listening** socket (TCP), bound to `(0.0.0.0, listen_port)` and set to `listen()`.
   - **`log_file`**: A line-buffered file where every event is logged as JSON.

2. **Server Socket & Receiving**:
   - **`listen_for_connections()`**:  
     - In a loop, calls `accept()` on the server socket. For each incoming connection, spawns a new thread to handle it.
   - **`handle_incoming_connection(conn)`**:  
     - Reads data in chunks (`conn.recv(1024)`), splits by `\n`, parses each line as an integer timestamp, and puts it in `incoming_queue`.

3. **Main Loop** (`main_loop()`):
   - Runs for `run_seconds` total, sleeping `1.0 / clock_rate` between ticks (simulating “ticks”).
   - Each tick:
     1. If `incoming_queue` is **not** empty, **process** a message (`handle_receive()`).
     2. Otherwise, calls `handle_no_message()`, which picks a random action (SEND to 1 peer, SEND to 2 peers, or INTERNAL event).

4. **Actions**:
   - **`handle_receive()`**:
     - Dequeues one timestamp, updates `local_clock = max(local_clock, received) + 1`.
     - Logs a `RECEIVE` event (queue length, old/new clock, etc.).
   - **`send_message()`**:
     - Increments `local_clock` by 1.
     - For each `(host, port)` in recipients, creates a **new** TCP socket, connects, sends `local_clock\n`.
     - Logs a `SEND`.
   - **`internal_event()`**:
     - Increments `local_clock` by 1, logs an `INTERNAL`.

5. **Shutdown** (`shutdown()`):
   - Logs an `END` event with `final_clock`.
   - Closes the server socket and the log file.

### 4.2 `run_machine.py` – Spawning Multiple Machines Locally

- **Orchestrates** multiple local machines via Python’s `multiprocessing`.
- **Generates** a timestamp-based subdirectory in `logs/` (e.g., `logs/run_2025-03-05_15-30-01/`) unless `--logs_dir` is specified.
- For each machine (IDs 1..3):
  - Chooses a **port** (`5001`, `5002`, `5003` by default),
  - Builds a **log file** path, with example format `logs/run_YYYY-MM-DD_HH-MM-SS/machine_1.log`,
  - Spawns a `Process` that calls `machine.py` with the relevant arguments.
- Waits ~70 seconds to allow them to finish (default `--duration=60`), then terminates any leftover processes.

### 4.3 `analyze_logs.py` – Parsing & Plotting

- **Reads** one or more JSON log files, each containing lines like:
  ```json
  {"event": "SEND", "system_time": 1677782102.9545, "machine_id": 1, "old_clock": 5, "new_clock": 6, "recipients": [["localhost", 5002]]}
  ```
- **Builds** a combined Pandas DataFrame:
  - Sorts by `system_time`.
  - Converts columns like `old_clock`, `new_clock`, `queue_len`, etc. to numeric (if present).
- **Computes**:
  - **Final clock** from `END` events,
  - **Drift** = `max(final_clock) - min(final_clock)`,
  - **Average jump** = mean of `(new_clock - old_clock)` for `SEND/RECEIVE/INTERNAL`,
  - **Max queue length** per machine (for `RECEIVE`).
- **Generates** subplots in `analysis_subplots.png`:
  1. **Lamport clock vs. time**,
  2. **Queue length** vs. time (only for `RECEIVE`),
  3. **Clock jump** vs. time.
- **Writes** `analysis_summary.md` summarizing the final drift, average jumps, queue lengths, etc.

---

## 5. Testing Strategy

We use **Pytest** to validate correctness:

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
- Waits ~10s, then terminates the process. We do not run for very long because we are merely performing a test.
- Checks that at least one log file has a `STARTUP` event, confirming that we are able to start up a proacess with multiple machines.

### 5.3 `test_analyze_logs.py` (Analysis)

- Uses **static sample logs** in `tests/sample_logs/` (like `machine_1.log`, etc.).  
- Copies them to a temporary directory, then calls `analyze_logs.py` with the **real** filenames.  
- Checks the script creates `analysis_subplots.png` and `analysis_summary.md`, and that “Final Drift” / “Summary Table” appear in the summary.

---

## 6. Interpreting the Subplots

When you run the analysis script, it should produce `analysis_subplots.png` with three subplots:

1. **Lamport Clock vs. Time**  
   - Plots each machine’s `new_clock` over real `system_time`.  
   - Typically there will be near-linear growth with occasional jumps when a machine receives a higher timestamp from a peer.

2. **Queue Length vs. Time (RECEIVE)**  
   - Shows how many messages were waiting in the queue at each `RECEIVE`.  
   - If a slower machine is bombarded with messages, there might be larger queue lengths because the machine needs to process all of the messages.

3. **Clock Jump vs. Time**  
   - Plots `(new_clock - old_clock)` whenever `SEND`, `RECEIVE`, or `INTERNAL` occurs.  
   - A jump of **1** means the machine incremented normally, and a larger jump indicates it received a bigger timestamp from a peer and had to catch up.
---
