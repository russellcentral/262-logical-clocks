"""
machine.py

Implements a single "virtual machine" that:
- Runs at a random clock rate (1..6 ticks/sec).
- Maintains a Lamport logical clock.
- Listens on a TCP port for incoming messages.
- Sends messages to peers (one or both) or performs internal events based on random chance.
- Logs all events to a file.

Usage:
    python machine.py \
        --id 1 \
        --port 5001 \
        --peers "192.168.1.10:5002,192.168.1.20:5003" \
        --log "logs/machine_1.log" \
        --duration 60

Explanation:
    --id        : Unique integer ID for this machine (e.g., 1, 2, 3).
    --port      : TCP port to listen on.
    --peers     : Comma-separated list of "host:port" for other machines.
    --log       : Path to the log file.
    --duration  : How long (in seconds) this machine will run before stopping.
"""

import json
import socket
import threading
import time
import random
import queue
import argparse
import sys

class Machine:
    def __init__(self, machine_id, listen_port, peer_addresses, log_filename, run_seconds=60):
        """
        :param machine_id: int - The ID of this machine (e.g. 1, 2, 3).
        :param listen_port: int - The TCP port on which this machine will listen for incoming connections.
        :param peer_addresses: list of (host, port) tuples for the other machines in the system.
        :param log_filename: str - The path to the log file for this machine.
        :param run_seconds: int - How long this machine will run before shutting down.
        """
        self.machine_id = machine_id
        self.listen_port = listen_port
        self.peer_addresses = peer_addresses  # such as [("192.168.1.10", 5002), ("192.168.1.20", 5003)]
        self.log_filename = log_filename
        self.run_seconds = run_seconds

        # Random clock rate: 1 to 6 ticks/sec
        self.clock_rate = random.randint(1, 6)

        # Lamport logical clock
        self.local_clock = 0

        # Queue for incoming messages (timestamps)
        self.incoming_queue = queue.Queue()

        # Log file (line-buffered so you see output in real time)
        self.log_file = open(self.log_filename, "w", buffering=1)

        # TCP server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', self.listen_port))
        self.server_socket.listen(5)
        # A timeout helps us periodically check if we're still running
        self.server_socket.settimeout(1.0)

        # Control flag for shutting down gracefully
        self.running = True

    def start(self):
        """
        Starts the machine:
          1. Launches a listener thread to accept incoming connections.
          2. Enters the main loop, running for `run_seconds`.
          3. Cleans up resources before exiting.
        """
        # Start a separate thread to listen for incoming connections
        listener_thread = threading.Thread(target=self.listen_for_connections, daemon=True)
        listener_thread.start()

        # Enter the main loop
        self.main_loop()

        # Once done, shut down
        self.shutdown()

    def listen_for_connections(self):
        """
        Continuously accept incoming connections and spawn a handler thread for each one.
        This runs in a background thread until `self.running` is set to False.
        """
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                handler_thread = threading.Thread(
                    target=self.handle_incoming_connection,
                    args=(conn,),
                    daemon=True
                )
                handler_thread.start()
            except socket.timeout:
                # We set a timeout to allow checking self.running regularly
                continue
            except Exception as e:
                # Unexpected errors: log or ignore as appropriate
                print(f"[Machine {self.machine_id}] Error accepting connection: {e}", file=sys.stderr)
                break

    def handle_incoming_connection(self, conn):
        """
        Receives data from a single connection, splits it by newline,
        and enqueues each message as an integer (the sender's clock).
        """
        try:
            with conn:
                while self.running:
                    data = conn.recv(1024)
                    if not data:
                        break
                    lines = data.decode('utf-8').strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            try:
                                timestamp = int(line)
                                self.incoming_queue.put(timestamp)
                            except ValueError:
                                # If the line isn't a valid integer, ignore or log an error
                                pass
        except Exception as e:
            # Connection might have been closed or reset
            pass

    def main_loop(self):
        """
        Runs for `run_seconds`, performing clock_rate "ticks" per second.
        Each tick:
          - If there's a message in the queue, process (receive) it.
          - Otherwise, randomly decide to send or do an internal event.
        """
        start_time = time.time()
        tick_interval = 1.0 / self.clock_rate

        while self.running and (time.time() - start_time < self.run_seconds):
            time.sleep(tick_interval)

            if not self.incoming_queue.empty():
                self.handle_receive()
            else:
                self.handle_no_message()

        # Time's up
        self.running = False

    def handle_receive(self):
        """
        Dequeue one message, update local clock (Lamport rule),
        and log the receive event.
        """
        msg_timestamp = self.incoming_queue.get()
        old_clock = self.local_clock
        self.local_clock = max(self.local_clock, msg_timestamp) + 1

        queue_len = self.incoming_queue.qsize()
        sys_time = time.time()
        event_data = {
            "event": "RECEIVE",
            "system_time": sys_time,
            "old_clock": old_clock,
            "new_clock": self.local_clock,
            "queue_len": queue_len
        }
        self.log_file.write(json.dumps(event_data) + "\n")

    def handle_no_message(self):
        """
        If no message is in the queue, randomly pick 1-10:
          - 1 => send to first peer
          - 2 => send to second peer (if exists)
          - 3 => send to both peers (if at least two exist)
          - else => internal event
        """
        r = random.randint(1, 10)

        if r == 1 and len(self.peer_addresses) > 0:
            self.send_message([self.peer_addresses[0]])
        elif r == 2 and len(self.peer_addresses) > 1:
            self.send_message([self.peer_addresses[1]])
        elif r == 3 and len(self.peer_addresses) > 1:
            self.send_message(self.peer_addresses)
        else:
            self.internal_event()

    def send_message(self, recipients):
        """
        Sends this machine's local clock to each peer in `recipients`,
        increments local clock, and logs the event.
        """
        old_clock = self.local_clock
        self.local_clock += 1
        sys_time = time.time()

        for (host, port) in recipients:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((host, port))
                    s.sendall(f"{self.local_clock}\n".encode('utf-8'))
            except Exception as e:
                # If the peer is unreachable, we ignore or log the error
                pass

        event_data = {
            "event": "SEND",
            "system_time": sys_time,
            "old_clock": old_clock,
            "new_clock": self.local_clock,
            "recipients": recipients
        }
        self.log_file.write(json.dumps(event_data) + "\n")

    def internal_event(self):
        """
        Internal event: increments local clock by 1 and logs the event.
        """
        old_clock = self.local_clock
        self.local_clock += 1
        sys_time = time.time()

        event_data = {
            "event": "INTERNAL",
            "system_time": sys_time,
            "old_clock": old_clock,
            "new_clock": self.local_clock
        }
        self.log_file.write(json.dumps(event_data) + "\n")

    def shutdown(self):
        """
        Closes the server socket and the log file.
        """
        self.running = False
        try:
            self.server_socket.close()
        except:
            pass
        self.log_file.close()

def main():
    """
    Entry point if you run `machine.py` directly.
    Parses arguments, creates a Machine instance, and starts it.
    """
    parser = argparse.ArgumentParser(description="Run a single distributed machine node.")
    parser.add_argument("--id", type=int, required=True, help="Machine ID (e.g. 1, 2, 3)")
    parser.add_argument("--port", type=int, required=True, help="TCP port to listen on")
    parser.add_argument("--peers", type=str, default="", help="Comma-separated list of peer host:port pairs")
    parser.add_argument("--log", type=str, default="machine.log", help="Path to log file")
    parser.add_argument("--duration", type=int, default=60, help="How many seconds to run before stopping")
    args = parser.parse_args()

    # Parse the --peers string
    peer_addresses = []
    if args.peers.strip():
        for peer_str in args.peers.split(","):
            hostport = peer_str.strip().split(":")
            if len(hostport) == 2:
                host, port = hostport[0], int(hostport[1])
                peer_addresses.append((host, port))

    machine = Machine(
        machine_id=args.id,
        listen_port=args.port,
        peer_addresses=peer_addresses,
        log_filename=args.log,
        run_seconds=args.duration
    )
    machine.start()

if __name__ == "__main__":
    main()
