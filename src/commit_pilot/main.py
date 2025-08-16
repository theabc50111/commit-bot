import os
import subprocess
import sys
from typing import Optional, Union

from src.commit_pilot.ai_models import AIModels
from src.commit_pilot.utils import load_config

commands = {
    "is_git_repo": "git rev-parse --git-dir",
    "clear_screen": ["cls" if os.name == "nt" else "clear"],
    "commit": "git commit -m",
    "get_stashed_changes": "git diff --cached",
}


def generate_commit_message(changes: str) -> str:
    """Generates a commit message using the specified AI model."""
    try:
        model_name = load_config("job.conf")["used_model"]
        ai_models = AIModels()
        model = ai_models.get_model(model_name)
        if not model:
            raise ValueError(f"Model '{model_name}' is not available.")

        response_chunks = model.stream(
            [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that generates concise commit messages based on code changes.",
                },
                {
                    "role": "user",
                    "content": f"Generate a concise commit message for the following changes:\n{changes}",
                },
            ]
        )
        commit_message = ""
        for chunk in response_chunks:
            commit_message += chunk.content
            print(chunk.content, end="", flush=True)
    except Exception as e:
        print(f"❌ Error generating commit message: {e}")
        sys.exit(1)

    return commit_message


changes = "Added new feature X and fixed bug Y."
generate_commit_message(changes)


def run_command(command: Union[list[str], str], extra_args: Optional[list[str]] = None):
    """Runs a command and returns its output."""
    try:
        shell_command = command.split() if isinstance(command, str) else command
        extra_args = extra_args if extra_args else []
        result = subprocess.run(
            shell_command + extra_args,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
            encoding="utf-8",
        )
        return result.stdout
    except FileNotFoundError as e:
        print(f"❌ command might be wrong, command: {command},\nError message: \n{e}")
        raise e


def run():
    """Runs the main command to check if the current directory is a git repository."""
    try:
        output = run_command(commands["is_git_repo"])
        print(f"✅ Current directory is a git repository: {output.strip()}")
        staged_changes = run_command(commands["get_stashed_changes"]).strip()
        if not staged_changes:
            print("No staged changes found.")
            sys.exit(0)
    except subprocess.CalledProcessError as e:
        if "not a git repository" in e.stderr:
            print("❌ Current directory is not a git repository.")
            sys.exit(1)
        else:
            print(f"❌ Error: \n{e.stderr}")
            raise e


if __name__ == "__main__":
    run()
