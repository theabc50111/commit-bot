import os
import subprocess
import sys
from typing import Optional, Union

from .ai_models import AIModels
from .utils import load_config

commands = {
    "is_git_repo": "git rev-parse --git-dir",
    "clear_screen": ["cls" if os.name == "nt" else "clear"],
    "commit": "git commit -m",
    "get_stashed_changes": "git diff --cached",
}


def generate_commit_message(staged_changes: str) -> str:
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
                    "content": f"Here are the staged changes:\n'''\n{staged_changes}n'''",
                },
            ]
        )
        commit_message = ""
        for chunk in response_chunks:
            commit_message += chunk.content
            print(chunk.content, end="", flush=True)
        print("\n" * 3, end="")
    except Exception as e:
        print(f"❌ Error generating commit message: {e}")
        sys.exit(1)

    return commit_message


def interaction_loop():
    """Handles user interaction for commit message generation."""
    staged_changes = run_command(commands["get_stashed_changes"]).strip()
    if not staged_changes:
        print("🔎 No staged changes found.")
        sys.exit(0)
    commit_message = generate_commit_message(staged_changes)
    while True:
        action = input("Proceed to commit? [y(yes) | n(no) | r(regenerate)]:").strip().lower()
        match action:
            case "r" | "regenerate":
                subprocess.run(commands["clear_screen"])
                print("🔄 Regenerating commit message...")
                commit_message = generate_commit_message(staged_changes)
                continue
            case "y" | "yes":
                print("🔄 Committing changes...")
                res = run_command(command=commands["commit"], extra_args=[commit_message])
                print(f"✅ Committed with message:\n{res.strip()}")
                break
            case "n" | "no":
                print("❌ Commit aborted by user.")
                break
            case _:
                print("❗ Invalid input. Please enter 'y', 'n', or 'r'.")
                break


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
        interaction_loop()
    except subprocess.CalledProcessError as e:
        if "not a git repository" in e.stderr:
            print("❌ Current directory is not a git repository.")
            sys.exit(1)
        else:
            print(f"❌ Error: \n{e.stderr}")
            raise e


if __name__ == "__main__":
    run()
