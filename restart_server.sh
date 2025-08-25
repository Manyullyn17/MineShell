#!/bin/bash

SESSION_NAME="mcserver"

# Send save-all and wait a bit
tmux send-keys -t "$SESSION_NAME" "say Saving world..." Enter
tmux send-keys -t "$SESSION_NAME" "save-all" Enter
sleep 10
tmux send-keys -t "$SESSION_NAME" "stop" Enter

# Wait until tmux session is gone
while tmux has-session -t "$SESSION_NAME" 2>/dev/null; do
    sleep 2
done

# Start the server again
/home/manyullyn/mineshell/run_server.sh
