#!/bin/bash

# A script to stop a VLLM server

# --- Initial Setup ---
set -u  # Treat unset variables as an error and exit immediately.
set -o pipefail  # The return value of a pipeline is the status of the last

# --- Load Utility Functions ---
source "$(dirname "$0")/vllm_utils.sh"

# --- Main Script to Stop VLLM Server ---
echo "Stopping VLLM server..."
graceful_shutdown_vllm
echo "VLLM server stopped."

echo "Stopping VLLM launcher script..."
graceful_shutdown_vllm_launcher
echo "VLLM launcher script stopped."
