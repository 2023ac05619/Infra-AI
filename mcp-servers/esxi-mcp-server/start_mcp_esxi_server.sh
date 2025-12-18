#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
SERVER_DIR="${SCRIPT_DIR}/esxi-mcp-server"
PID_FILE="${SERVER_DIR}/server.pid"

start() {
    # Navigate to the esxi-mcp-server directory
    cd "${SERVER_DIR}" || { echo "Failed to change directory to ${SERVER_DIR}" >&2; exit 1; }

    # Start the server in the background using nohup, redirecting output to a log file
    echo "Starting ESXi MCP server in the background..."
    nohup venv/bin/python3 server.py -c config.yaml > logs/server.out 2> logs/server.err &

    # Save the PID of the background process
    echo $! > "${PID_FILE}"

    echo "ESXi MCP server started in the background. PID: $(cat "${PID_FILE}")"
    echo "Logs can be found in esxi-mcp-server/logs/server.out and esxi-mcp-server/logs/server.err"
}

stop() {
    if [ -f "${PID_FILE}" ]; then
        PID=$(cat "${PID_FILE}")
        echo "Stopping ESXi MCP server with PID: ${PID}"
        kill "${PID}"
        rm "${PID_FILE}"
    else
        echo "PID file not found. Is the server running?"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
esac
