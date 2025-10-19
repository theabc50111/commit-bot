#!/bin/bash

# A safer and more reliable script to start and automatically shut down
# a VLLM server when it is idle for a specified period.

# --- Initial Setup ---
set -u  # Treat unset variables as an error and exit immediately.
set -o pipefail  # The return value of a pipeline is the status of the last command to exit with a non-zero status.

# --- Load Utility Functions ---
source "$(dirname "$0")/vllm_utils.sh"

# --- Argument Handling with getopt ---

# Define short and long options
SHORT_OPTS="p:n:w:i:s:g:"
LONG_OPTS="model-path:,model-name:,warm-up-sec:,idle-timeout-minutes:,server-log-path:,gpu-memory-utilization:"

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
gpu_memory_utilization=0.9 # Default value

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
        -w|--warm-up-sec)
            warm_up_sec="$2"
            shift 2 # past argument and value
            ;;
        -i|--idle-timeout-minutes)
            idle_timeout_minutes="$2"
            shift 2 # past argument and value
            ;;
        -s|--server-log-path)
            server_log_path="$2"
            shift 2 # past argument and value
            ;;
        -g|--gpu-memory-utilization)
            gpu_memory_utilization="$2"
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
if [ -z "$model_path" ] || [ -z "$model_name" ] || [ -z "$warm_up_sec" ] || [ -z "$idle_timeout_minutes" ] || [ -z "$server_log_path" ]; then
    echo "Usage: $0 --model-path <path> --model-name <api_name> --warm-up-sec <seconds> --idle-timeout-minutes <minutes> --server-log-path <path> [--gpu-memory-utilization <fraction>]"
    echo "   or: $0 -p <path> -n <api_name> -w <seconds> -i <minutes> -s <path> [-g <fraction>]"
    echo ""
    echo "--model-path (-p), --model-name (-n), --warm-up-sec (-w), --idle-timeout-minutes (-i) and --server-log-path (-s) are required."
    exit 1
fi


# --- Configuration ---
# Set the host, port, and metrics URL.
VLLM_HOST="http://localhost"
VLLM_PORT="8000"
VLLM_METRICS_URL="${VLLM_HOST}:${VLLM_PORT}/metrics"

# The command to start the VLLM server.
# Using an array ensures arguments with spaces are handled correctly.
VLLM_START_CMD=(
"python" "-m" "vllm.entrypoints.openai.api_server"
"--port" "${VLLM_PORT}"
"--model" "${model_path}"
"--served-model-name" "${model_name}"
"--gpu-memory-utilization" "${gpu_memory_utilization}"
)


# --- Main Logic ---
# Check for existing VLLM server
check_running_vllm

echo "Starting VLLM server..."

# Use nohup to run the command in the background, making it immune to terminal closure.
# The output is redirected to the specified log file.
nohup "${VLLM_START_CMD[@]}" > "${server_log_path}" 2>&1 &

echo "VLLM server started in the background with PID: $!, but it need some warming up time" 
# The waming up time should be longer than 30 seconds.
count_down_seconds ${warm_up_sec}
echo "VLLM server logs are being written to ${server_log_path}"


# Start the monitor function in a separate background process.
echo "Starting idle timeout monitor for VLLM server..."
monitor_and_shutdown_vllm &

echo "$0 has completed. The server will automatically shut down after being idle for ${idle_timeout_minutes} minutes."
