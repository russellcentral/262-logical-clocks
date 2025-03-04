# 262-logical-clocks

To run locally: python run_machine.py
To parse logs and generate plots: python analyze_logs.py logs/RUN-NAME/machine_*.log
(assumes that all logs for a given run are in the same folder)
To run on multiple physical machines: python machine.py --id 1 --port 5001 \
    --peers "SECOND-IP:SECOND-PORT,THIRD-IP:THIRD-PORT" \
    --log "logs/machine_1.log" \
    --duration 60
(note that a corresponding command needs to be executed for each machine)
