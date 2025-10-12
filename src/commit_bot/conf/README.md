# commit-bot Configuration

This directory contains the configuration files for `commit-bot`, an AI-powered tool that generates git commit messages based on your staged changes.

## Configuration Files

The behavior of the `commit-bot` tool is controlled by the two files in this directory: `job.conf` and `model.conf`.

### `job.conf`

This file defines the runtime settings for the application. It specifies which model is currently active and controls the behavior of the local model server.

Key settings include:
- `used_model`: The specific model to use for generating commit messages (e.g., `vllm-qwen3:4b`).
- `server_idle_timeout_minutes`: How long the local model server should wait before shutting down automatically.
- `vllm_gpu_memory_utilization_limit`: The GPU memory limit for the VLLM server.

### `model.conf`

This file acts as a catalog for all models that `commit-bot` can use. It defines the available models, their connection details, and default generation parameters.

Key sections include:
- `ollama_base_url` / `vllm_base_url`: The API endpoints for the local model servers.
- `default_gen_configs`: Default parameters for the AI model's text generation (e.g., `temperature`, `max_tokens`).
- `model_configs`: A list of all available models, specifying their `server_type` (ollama, vllm, third-party) and the `model_id` used by the `litellm` library.

## Model Backends

This project provides both VLLM and Ollama backends for hosting large language models (LLMs) locally.

- **VLLM Backend**: Use this for models that you have manually downloaded from Hugging Face.
- **Ollama Backend**: Use this for models that you pull directly from the Ollama registry.
  - **Setup Instructions:**
    1.  **Start the Server**: The Ollama server can be started by running `docker-compose up -d` using the `compose.yaml` file in the project root. This will launch the server in a container named `ollama`.
    1.  **Pull Models**: After the server is running, you can execute the `pull_ollama_model.sh` script. This script will automatically download several default models (like `qwen`, `gemma`, and `llama3`) into your Ollama server.
