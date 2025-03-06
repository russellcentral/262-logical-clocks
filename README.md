# 262-logical-clocks

Yes, you can **copy and paste** the following text directly (for example, into a `README.md`). It’s formatted as plain text/Markdown, so it should transfer cleanly without issues.

---

```markdown
# 262-Logical-Clocks

This repository implements a **distributed system** model in Python, featuring:

- **Lamport logical clocks** for each node  
- **Multiple machines** that communicate over **TCP sockets**  
- **Random clock rates** (1–6 ticks per real second)  
- **Event logging** to a file (in JSON lines)  
- **An analysis script** that parses logs and generates plots of clock drift, queue lengths, etc.

---

## 1. Running the System Locally

1. **Clone** or copy this repository to your local machine.  
2. **Navigate** to the project root directory:
   ```bash
   cd 262-logical-clocks
   ```
3. **Start** multiple machines locally using `run_machine.py`:
   ```bash
   python run_machine.py
   ```
   - This spawns **three** local processes, each listening on a unique port (`5001, 5002, 5003`).
   - By default, each machine runs for **60 seconds**, and logs are saved in a **time-stamped** subdirectory under `logs/` (e.g., `logs/run_2025-03-04_15-30-01/`).
   - After ~70 seconds, any remaining processes are terminated.

---

## 2. Parsing Logs & Generating Plots

After a run, you’ll have log files (e.g. `logs/run_2025-03-04_15-30-01/machine_1.log`). To parse them and produce analysis plots:

```bash
python analyze_logs.py logs/run_2025-03-04_15-30-01/machine_*.log
```

- **What happens**:
  1. **Merges** all specified log files into a Pandas DataFrame.  
  2. **Computes** final drift (max - min clock), average jump size, queue lengths, etc.  
  3. **Generates** `analysis_subplots.png` and `analysis_summary.md` in the same directory.  
  4. You’ll see subplots for **Lamport clock vs. time**, **queue length vs. time**, and **clock jump vs. time**.

---

## 3. Running on Multiple Physical Machines

For a truly distributed setup across multiple hosts:

- **Pick** a unique port for each machine.  
- **Machine 1** (Host A, IP `192.168.1.10`):
  ```bash
  python machine.py \
      --id 1 \
      --port 5001 \
      --peers "192.168.1.20:5002,192.168.1.30:5003" \
      --log "logs/machine_1.log" \
      --duration 60
  ```
- **Machine 2** (Host B, IP `192.168.1.20`):
  ```bash
  python machine.py \
      --id 2 \
      --port 5002 \
      --peers "192.168.1.10:5001,192.168.1.30:5003" \
      --log "logs/machine_2.log" \
      --duration 60
  ```
- **Machine 3** (Host C, IP `192.168.1.30`):
  ```bash
  python machine.py \
      --id 3 \
      --port 5003 \
      --peers "192.168.1.10:5001,192.168.1.20:5002" \
      --log "logs/machine_3.log" \
      --duration 60
  ```

Each machine runs independently, logging events to its own file. After 60 seconds, each stops. Collect the logs and run the analysis script locally to visualize results.

---

## 4. Implementation Details

### 4.1 Machine Class (`machine.py`)

Each machine runs as a **TCP server** on a chosen port and also **connects** to peer machines to send messages. Key attributes:

- **`machine_id`**: Unique integer ID (1, 2, 3, etc.).  
- **`listen_port`**: TCP port on which this machine **listens** for connections.  
- **`peer_addresses`**: A list of `(host, port)` tuples for other machines.  
- **`clock_rate`**: Random integer in `[1..6]` chosen at startup (the # of ticks/sec).  
- **`local_clock`**: The machine’s Lamport clock.  
- **`incoming_queue`**: A queue of incoming timestamps from peers.  
- **`server_socket`**: The **listening** socket for inbound connections.  
- **`log_file`**: A line-buffered file where events are recorded in JSON lines.

#### Handling Connections

1. **`listen_for_connections()`**: Accepts inbound connections in a loop, spawning a **thread** for each new connection (`handle_incoming_connection`).  
2. **`handle_incoming_connection()`**: Reads lines from the socket, parses each line as an integer timestamp, and puts it into `incoming_queue`.

#### Main Loop

- Runs for `run_seconds` total.  
- Sleeps **1 / clock_rate** between ticks.  
- Each tick:
  1. If `incoming_queue` is not empty, **process** one message (`handle_receive()`),  
  2. Otherwise, calls `handle_no_message()` to randomly choose a send or internal event.

#### Actions

- **`handle_receive()`**:  
  - Dequeues one timestamp, updates `local_clock = max(local_clock, timestamp) + 1`.  
  - Logs a `RECEIVE` event with queue length, old/new clock, etc.
- **`send_message()`**:  
  - Increments `local_clock` by 1,  
  - Creates a **new** socket for each peer, connects, sends `local_clock\n`, logs a `SEND`.
- **`internal_event()`**:  
  - Increments `local_clock` by 1, logs an `INTERNAL`.

Every event is recorded in JSON lines, e.g.:

```json
{"event": "SEND", "system_time": 1677782102.954512, "machine_id": 1, "old_clock": 5, "new_clock": 6, "recipients": [["localhost", 5002]]}
```

At shutdown, a final **`END`** event is logged with `final_clock`.

---

### 4.2 Multiple Machines: `run_machine.py`

- **Spawns** 3 local machine processes (IDs 1..3).  
- Each machine is assigned a port (`5001, 5002, 5003`) and a log file in a subdirectory (e.g., `logs/run_YYYY-MM-DD_HH-MM-SS/machine_1.log`).  
- Waits ~70s, then kills any leftover processes.

---

### 4.3 Analysis: `analyze_logs.py`

- **Takes** multiple log files as arguments.  
- **Merges** them into one DataFrame, sorted by `system_time`.  
- **Computes** final drift, average jump, queue lengths, etc.  
- **Plots**:
  1. **Lamport clock vs. time**,  
  2. **Queue length** vs. time (for `RECEIVE`),  
  3. **Clock jump** vs. time.  
- **Saves** `analysis_subplots.png` and `analysis_summary.md` to the same folder.

---

## 5. Testing

We use **Pytest** to ensure correctness:

1. **`test_machine.py`**: Unit tests for `Machine`. Checks each event type (`STARTUP, SEND, RECEIVE, INTERNAL, END`).  
2. **`test_integration.py`**: Spawns multiple machines via `run_machine.py`, verifies logs contain `STARTUP`.  
3. **`test_analyze_logs.py`**: Tests the analysis script on **static** sample logs (`tests/sample_logs/`).  
   - Ensures `analysis_subplots.png` and `analysis_summary.md` are generated, checks summary for “Final Drift” and “Summary Table.”

Run all tests with:

```bash
python -m pytest
```

If successful, you’ll see something like:

```
============================ test session starts ============================
collected 7 items

tests/test_analyze_logs.py . [ 14%]
tests/test_integration.py .  [ 28%]
tests/test_machine.py .....  [100%]

============================= 7 passed in 12.34s ============================
```

---

## 6. Conclusion

- **`machine.py`**: One node’s logic (Lamport clock, random events, sockets).  
- **`run_machine.py`**: Spawns multiple local nodes for a test or demo.  
- **`analyze_logs.py`**: Merges logs, computes drift, and plots.  
- **Tests**:
  - Thorough unit/integration checks for the entire pipeline.

This structure cleanly demonstrates **Lamport clock synchronization** in a small distributed system, with real TCP communication and JSON-based logging for easy post-run analysis.
```

---
