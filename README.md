# 262-logical-clocks

To run locally: python run_machine.py
To parse logs and generate plots: python analyze_logs.py logs/RUN-NAME/machine_*.log
(assumes that all logs for a given run are in the same folder)
To run on multiple physical machines: python machine.py --id 1 --port 5001 \
    --peers "SECOND-IP:SECOND-PORT,THIRD-IP:THIRD-PORT" \
    --log "logs/machine_1.log" \
    --duration 60
(note that a corresponding command needs to be executed for each machine)

We now provide implementation details for the machines:
    •    In the machine class, we record the following variables:
    ◦    machine_id: id of the machine 
    ◦    listen_port: TCP port to listen for connections
    ◦    peer_addresses: list of addresses so that it can communicate with other machines
    ◦    clock_rate: randomly generated integer in [1,6]. This is the #ticks/sec
    ◦    local_clock: this is the value of the local clock. 
    ◦    incoming_queue: we maintain a queue of incoming messages, which upon a read will be read. 
    ◦    server_socket: socket used to accept connections
    ◦    log_file: file for logging results / clock values / etc.
    •    Handling connections:
    ◦    Relatively standard: given a connection, we receive data and parse the data appropriately. Each message should be the sender’s clock value, so we parse each line of data as an integer.
    •    Main loop:
    ◦    Every 1/clock_rate seconds (up to total #seconds to run), we either (1) process a message in the queue or (2) choose one of 4 actions: send to 1 peer (x2), send to both peers, and internal action
    •    `handle_no_message`: handles the logic of choosing the 4 actions probabilistically. 
    •    Handling actions:
    ◦    `handle_receive`: for when we receive a message. We obtain the clock timestamp of the message and update the local clock according to Lamport’s rule: 
    ▪    local_clock ← max(local_clock , timestamp) + 1.
        We then log the queue length, machine_id, and clock values.
    •    `send_message`: to send a message. We update our local clock by +1, then use the socket to send to the desired recipients. Logs all relevant values.
    •    `internal_event`: increments the local clock by +1, and logs all relevant values.  
    •    In general, all logging includes the event, system_time, machine_id, and clock values. 
To run multiple machines simultaneously, we use separate processes and use the Python multiprocessing module. The following implementation is done in `run_machine.py`:
    •    Assign each machine a unique port for communication
    •    Spawn and begin 3 processes, one for each machine
    •    Wait ~60s for completion (in our code, we give some buffer and we wait 70s, though the individual machines should all have finished operation by then).
    •    Clean up processes upon completion.
