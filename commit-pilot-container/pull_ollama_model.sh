#!/bin/bash

# Start the Ollama server in the background
ollama serve &

# Wait for the server to be ready before pulling the model
sleep 5

# Pull the desired model
ollama pull qwen3:4b
ollama pull qwen3:1.7b
ollama pull gemma3:4b
ollama pull llama3.2:3b
ollama pull gpt-oss:20b

# Wait for the background process to finish to keep the container running
wait
