import os
import subprocess
import sys
from typing import Optional, Union

commands = {
    "is_git_repo": "git rev-parse --git-dir",
    "clear_screen": ["cls" if os.name == "nt" else "clear"],
    "commit": "git commit -m",
    "get_stashed_changes": "git diff --cached",
}


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
    except subprocess.CalledProcessError as e:
        print(f"❌ extra_args might be wrong, extra_args: {extra_args},\nError message: \n{e.stderr}")
        raise e
