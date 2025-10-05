#!/bin/bash

# A safer and more reliable script to start and automatically shut down
# a VLLM server when it is idle for a specified period.

# --- Argument Handling with getopt ---

# Define short and long options
SHORT_OPTS="p:n:"
LONG_OPTS="model-path:,model-name:"

# Parse the options using getopt
PARSED=$(getopt --options "$SHORT_OPTS" --long "$LONG_OPTS" --name "$0" -- "$@")

# Check if getopt failed
if [[ $? -ne 0 ]]; then
    # getopt will have printed an error message
    exit 1
fi

# Use the parsed options by resetting the positional parameters
eval set -- "$PARSED"

model_path=""
model_name=""

# Loop through the options and assign them to variables
while true; do
    case "$1" in
        -p|--model-path)
            model_path="$2"
            shift 2 # past argument and value
            ;;
        -n|--model-name)
            model_name="$2"
            shift 2 # past argument and value
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Programming error in argument parsing."
            exit 3
            ;;
    esac
done

# Check if required arguments were provided
if [ -z "$model_path" ] || [ -z "$model_name" ]; then
    echo "Usage: $0 --model-path <path_or_id> --model-name <api_name>"
    echo "   or: $0 -p <path_or_id> -n <api_name>"
    echo ""
    echo "Both --model-path (-p) and --model-name (-n) are required."
    exit 1
fi


# --- Configuration ---
# Set the host, port, and metrics URL.
VLLM_HOST="http://localhost"
VLLM_PORT="8000"
VLLM_METRICS_URL="${VLLM_HOST}:${VLLM_PORT}/metrics"

# Set the number of consecutive minutes without a request before shutdown.
IDLE_TIMEOUT_MINUTES=3

# The command to start the VLLM server.
# Using an array ensures arguments with spaces are handled correctly.
VLLM_START_CMD=(
"python" "-m" "vllm.entrypoints.openai.api_server"
"--port" "${VLLM_PORT}"
"--model" "${model_path}"
"--served-model-name" "${model_name}"
)

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


monitor_and_shutdown_vllm() {
    # Function to monitor the server for idle time and shut it down.
    # Counter for consecutive idle minutes
    IDLE_MINUTES=0
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
            IDLE_MINUTES=$((IDLE_MINUTES + 1))
            echo "No active requests. Idle for ${IDLE_MINUTES} of ${IDLE_TIMEOUT_MINUTES} minutes."
        else
            IDLE_MINUTES=0
            echo "Active requests found. Resetting idle timer."
        fi

        # If idle timeout is reached, shut down the server
        if [ "$IDLE_MINUTES" -ge "$IDLE_TIMEOUT_MINUTES" ]; then
            echo "Server idle for ${IDLE_TIMEOUT_MINUTES} minutes. Shutting down VLLM."
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

# --- Main Logic ---
# Check for existing VLLM server
check_running_vllm

echo "Starting VLLM server..."

# Use nohup to run the command in the background, making it immune to terminal closure.
# The output is redirected to vllm_server.log.
nohup "${VLLM_START_CMD[@]}" > vllm_server.log 2>&1 &

echo "VLLM server started in the background with PID: $!, but it need some warming up time" 
# The waming up time should be longer than 30 seconds.
count_down_seconds 40
echo "VLLM server logs are being written to vllm_server.log"


# Start the monitor function in a separate background process.
echo "Starting idle timeout monitor for VLLM server..."
monitor_and_shutdown_vllm &

echo "$0 has completed. The server will automatically shut down after being idle for ${IDLE_TIMEOUT_MINUTES} minutes."
