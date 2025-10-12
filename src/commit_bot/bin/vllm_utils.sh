#!/bin/bash

# Collection of utility functions for VLLM server management.

# Function to gracefully shut down
graceful_shutdown_vllm() {
    echo "Attempting to shut down VLLM server..."
    # Find the specific PID associated with the running VLLM server.
    VLLM_PID=$(ps aux | grep "vllm.entrypoints.openai.api_server" | grep -v "grep" | awk '{print $2}')

    if [ -z "$VLLM_PID" ]; then
        echo "No VLLM server process found."
    else
        echo "Found VLLM server process with PID: $VLLM_PID"

        # Send a graceful termination signal (SIGTERM).
        kill "$VLLM_PID"

        # Wait for the process to exit for up to 10 seconds.
        echo "Waiting for process to terminate..."
        if ! timeout 10 tail --pid="$VLLM_PID" -f /dev/null; then
            echo "Graceful shutdown failed. Forcefully killing the process."
            kill -9 "$VLLM_PID" 
        else
            echo "VLLM server process terminated successfully."
        fi
    fi
}

# Function to shut down the launcher script itself
graceful_shutdown_vllm_launcher() {
    echo "Shutting down VLLM launcher script..."
    LAUNCHER_PATH="$(dirname "$0")/exec_vllm.sh"
    LAUNCHER_PID=$(ps aux | grep "$LAUNCHER_PATH" | grep -v "grep" | awk '{print $2}')
    if [ -z "$LAUNCHER_PID" ]; then
        echo "No VLLM launcher script process found."
    else
        echo "Found VLLM launcher script process with PID: $LAUNCHER_PID"
        kill "$LAUNCHER_PID"

        echo "Waiting for launcher script process to terminate..."
        if ! timeout 10 tail --pid="$LAUNCHER_PID" -f /dev/null; then
            echo "Graceful shutdown of launcher script failed. Forcefully killing the process."
            kill -9 "$LAUNCHER_PID"
        else
            echo "VLLM launcher script process terminated successfully."
        fi
    fi
}

monitor_and_shutdown_vllm() {
    # Function to monitor the server for idle time and shut it down.
    # Counter for consecutive idle minutes
    consecutive_idle_minutes=0
    echo "Starting VLLM idle timeout monitor..."

    while true; do
        # Fetch the number of running requests using a more robust method
        # This uses `awk` to find the exact line and print the second field.
        # It's less prone to errors than chained pipes.
        RUNNING_REQUESTS=$(curl -s "${VLLM_METRICS_URL}" | awk '/^vllm:num_requests_running/ {print $2; exit}' | sed 's/\.[0-9]*//')

        # Check if curl command succeeded and returned a value.
        if [ $? -ne 0 ] || [ -z "$RUNNING_REQUESTS" ]; then
            echo "VLLM server not reachable. It may have been shut down or is not running."
            graceful_shutdown_vllm
            exit 1
        fi

        # Check if any requests are running
        if [ "$RUNNING_REQUESTS" -eq 0 ]; then
            consecutive_idle_minutes=$((consecutive_idle_minutes + 1))
            echo "No active requests. Idle for ${consecutive_idle_minutes} of ${idle_timeout_minutes} minutes."
        else
            consecutive_idle_minutes=0
            echo "Active requests found. Resetting idle timer."
        fi

        # If idle timeout is reached, shut down the server
        if [ "$consecutive_idle_minutes" -ge "$idle_timeout_minutes" ]; then
            echo "Server idle for ${idle_timeout_minutes} minutes. Shutting down VLLM."
            graceful_shutdown_vllm
            exit 0
        fi

        # Wait for one minute before checking again
        sleep 60
    done
}

check_running_vllm() {
    # Check if a VLLM server is already running
    VLLM_PID=$(ps aux | grep "vllm.entrypoints.openai.api_server" | grep -v "grep" | awk '{print $2}')
    if [ -n "$VLLM_PID" ]; then
        echo "A VLLM server instance is already running. Please shut it down before starting a new one."
        exit 1
    else
        echo "No existing VLLM server instance found. Proceeding to start a new one."
    fi
}

count_down_seconds() {
    SECONDS_LEFT=$1
    while [ $SECONDS_LEFT -gt 0 ]; do
        echo -ne "Please wait... $SECONDS_LEFT seconds remaining\r"
        sleep 1
        SECONDS_LEFT=$((SECONDS_LEFT - 1))
    done
    echo -ne "\n"
}
