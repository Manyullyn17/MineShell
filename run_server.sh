#!/bin/bash

SESSION_NAME="mcserver"
JAR="fabric-server-launch.jar"
MEM="10G"
CWD="/home/manyullyn/mineshell/installed_modpack"

cd "$CWD" || { echo "Failed to change directory to $CWD"; exit 1; }

# Only start if not already running
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux new-session -d -s "$SESSION_NAME" "java -Xms$MEM -Xmx$MEM -jar $JAR nogui"
    echo "Server started in tmux session '$SESSION_NAME'"
else
    echo "Server is already running in tmux session '$SESSION_NAME'"
fi