# tests/test_machine.py

import pytest
import json
import socket
import time
from machine import Machine
from unittest.mock import patch

@pytest.fixture
def ephemeral_port():
    """Return a random free TCP port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('0.0.0.0', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def test_machine_startup_logging(tmp_path, ephemeral_port):
    """
    Verifies that a Machine logs a STARTUP event with a valid clock_rate.
    """
    log_file = tmp_path / "test_machine.log"
    m = Machine(
        machine_id=1,
        listen_port=ephemeral_port,
        peer_addresses=[],
        log_filename=str(log_file),
        run_seconds=1
    )
    m.start()  # runs for ~1s

    with open(log_file, 'r') as f:
        lines = f.read().strip().splitlines()

    startup_lines = [ln for ln in lines if '"event": "STARTUP"' in ln]
    assert len(startup_lines) == 1, "Expected exactly one STARTUP event"
    record = json.loads(startup_lines[0])
    assert "clock_rate" in record
    assert 1 <= record["clock_rate"] <= 6

def test_machine_internal_event(tmp_path, ephemeral_port):
    """
    Calls internal_event() directly and checks for the INTERNAL log line.
    """
    log_file = tmp_path / "test_machine.log"
    m = Machine(
        machine_id=2,
        listen_port=ephemeral_port,
        peer_addresses=[],
        log_filename=str(log_file),
        run_seconds=1
    )

    old_clock = m.local_clock
    m.internal_event()
    assert m.local_clock == old_clock + 1, "internal_event should increment clock by 1"

    with open(log_file, 'r') as f:
        content = f.read().strip().splitlines()
    internal_lines = [ln for ln in content if '"event": "INTERNAL"' in ln]
    assert len(internal_lines) == 1, "Should log exactly one INTERNAL event"

def test_machine_receive_event(tmp_path, ephemeral_port):
    """
    Test handle_receive() by manually enqueueing a message, then calling handle_receive().
    """
    log_file = tmp_path / "test_machine.log"
    m = Machine(
        machine_id=3,
        listen_port=ephemeral_port,
        peer_addresses=[],
        log_filename=str(log_file),
        run_seconds=1
    )

    m.incoming_queue.put(10)
    old_clock = m.local_clock
    m.handle_receive()
    assert m.local_clock == max(old_clock, 10) + 1

    with open(log_file, 'r') as f:
        content = f.read().strip().splitlines()
    recv_lines = [ln for ln in content if '"event": "RECEIVE"' in ln]
    assert len(recv_lines) == 1, "Should log exactly one RECEIVE event"

@patch("machine.socket.socket")
def test_machine_send_event(mock_socket, tmp_path, ephemeral_port):
    """
    Test send_message() by mocking the socket layer so we don't really connect.
    """
    log_file = tmp_path / "test_machine.log"
    m = Machine(
        machine_id=4,
        listen_port=ephemeral_port,
        peer_addresses=[],
        log_filename=str(log_file),
        run_seconds=1
    )

    old_clock = m.local_clock
    m.send_message([("localhost", 5002)])
    assert m.local_clock == old_clock + 1

    with open(log_file, 'r') as f:
        content = f.read().strip().splitlines()
    send_lines = [ln for ln in content if '"event": "SEND"' in ln]
    assert len(send_lines) == 1, "Should log exactly one SEND event"
    record = json.loads(send_lines[0])
    assert record["recipients"] == [["localhost", 5002]]

def test_machine_end_event(tmp_path, ephemeral_port):
    """
    When the machine stops, it should log an END event with final_clock.
    """
    log_file = tmp_path / "test_machine.log"
    m = Machine(
        machine_id=5,
        listen_port=ephemeral_port,
        peer_addresses=[],
        log_filename=str(log_file),
        run_seconds=1
    )
    m.start()  # ~1s

    with open(log_file, 'r') as f:
        lines = f.read().strip().splitlines()
    end_lines = [ln for ln in lines if '"event": "END"' in ln]
    assert len(end_lines) == 1, "Should log exactly one END event"
    record = json.loads(end_lines[0])
    assert "final_clock" in record
