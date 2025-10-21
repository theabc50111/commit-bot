# Commit Bot

<!-- Badges will go here -->

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [License](#license)

## Description

Commit Bot is a command-line tool that uses Large Language Models (LLMs) to automatically generate git commit messages from your staged changes. It streamlines the commit process by providing well-formatted, context-aware messages, which you can then accept, edit, or regenerate on the fly.

## Features

- **AI-Powered Commit Messages**: Automatically generates descriptive commit messages from your code diffs.
- **Interactive Workflow**: Allows you to accept, edit, regenerate, or change models before committing.
- **Multiple Backends**: Supports both Ollama and VLLM for running local LLMs.
- **Configurable Models**: Easily configure which model to use and its generation parameters.
- **Automatic Server Management**: Can automatically start and stop the vLLM server to manage resources.

## Installation

### Prerequisites

- Python 3.10
- Git
- Docker and Docker Compose (for the Ollama backend)

### 1. Backend Setup

You must have a model backend running. Choose one of the following:

#### Ollama Backend

1.  **Start the Server**: Use Docker Compose to launch the Ollama server.
    ```bash
    docker-compose up -d
    ```
2.  **Pull Models**: `docker-compose` will automatically execute `pull_ollama_model.sh` to download the default models.

#### VLLM Backend

For the VLLM backend, you must manually download model weights from Hugging Face. The application will automatically start and stop the VLLM server as needed.
- where to put the model weights:
    - You can edit `commit_bot/conf/job.conf` to set the path for `vllm_model_weights_root_dir`.
    - Or specify a different path in `~/.config/commit_bot/job.conf` under the key `vllm_model_weights_root_dir`.
        - You can create this config file by copying `commit_bot/conf/job.conf` to `~/.config/commit_bot/job.conf` and modifying it as needed.

_(For more details on backend setup, see the README in `commit_bot/conf/`)_

### 2. Install the Package

Clone the repository and use `pip` to install the package in editable mode.

```bash
git clone <repository-url>
cd commit-bot
pip install -e .
```

## Usage

Once installed, simply run the `commit-bot` command in your git repository after staging your changes (`git add .`).

```bash
commit-bot
```

This will start an interactive session where the tool generates a commit message and prompts you for action:

- **(y)es**: Accept the message and commit.
- **(n)o**: Abort the commit.
- **(s)how**: Show the staged diff and the generated message again.
- **(r)egenerate**: Generate a new commit message.
- **(m)odel**: Change the LLM used for generation.
- **(e)dit**: Manually edit the commit message in your default text editor.

## Configuration

The behavior of Commit Bot is controlled by two configuration files located in `commit_bot/conf/`:

- **`job.conf`**: Defines runtime settings, such as the currently active model, server timeouts, and resource limits (e.g., GPU utilization for VLLM).
- **`model.conf`**: Acts as a catalog for all available models, defining their connection details, backend type (Ollama, VLLM, or third-party), and default generation parameters.

For detailed information, please refer to the `Readme.md` inside the `commit_bot/conf/` directory.

## TODO

- Automatically create `~/.config/commit_bot/job.conf`  if they do not exist.
  - Based on the default config files in `commit_bot/conf/`.
- Warn/Stop `commit-bot` if `~/.config/commit_bot/job.conf` is not available or misconfigured.

## License

This project is licensed under the **MIT License**. See the [LICENSE](./LICENSE) file for details.
