import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Optional, Union

from .ai_models import AIModels
from .prompts import deriv_sys_ppt_1 as defautl_sys_ppt
from .utils import get_conf_regen_commit_msg, load_config, post_process_commit_message

commands = {
    "is_git_repo": "git rev-parse --git-dir",
    "clear_screen": ["cls" if os.name == "nt" else "clear"],
    "commit": "git commit -m",
    "get_stashed_changes": "git diff --cached",
}

MODEL_SPEC = load_config("job.conf")["used_model"]


def generate_commit_message(staged_changes: str, random_regen: bool = False) -> str:
    """Generates a commit message using the specified AI model."""
    try:
        global MODEL_SPEC
        ai_models = AIModels()
        model = ai_models.get_model(MODEL_SPEC)
        if not model:
            raise ValueError(f"Model '{MODEL_SPEC}' is not available.")

        if random_regen:
            new_sys_ppt, new_model_gen_conf = get_conf_regen_commit_msg()
            for k, v in new_model_gen_conf.items():
                setattr(model, k, v)
            sys_prompt = new_sys_ppt
        else:
            sys_prompt = defautl_sys_ppt

        response_chunks = model.stream(
            [
                {
                    "role": "system",
                    "content": sys_prompt,
                },
                {
                    "role": "user",
                    "content": f"Here are the staged changes:\n'''\n{staged_changes}\n'''",
                },
            ]
        )
        print(f"🧠 Generating commit message using model '{MODEL_SPEC}'...\n")
        commit_message = ""
        for chunk in response_chunks:
            commit_message += chunk.content
            print(chunk.reasoning or chunk.content, end="", flush=True)
        print("\n" * 3, end="")
    except Exception as e:
        print(f"❌ Error generating commit message: {e}")
        traceback.print_exc()
        sys.exit(1)

    return post_process_commit_message(commit_message)


def handel_edit_commit_message(commit_message: str) -> str:
    """Allows user to edit the generated commit message."""

    editor = os.environ.get("EDITOR", "vim")

    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp") as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(commit_message)
        subprocess.run([editor, temp_file_path], check=True)
        edited_message = Path(temp_file_path).read_text()
        return edited_message
    except FileNotFoundError as e:
        print(f"❌ May not find Editor '{editor}'. Please set the $EDITOR environment variable.")
        print(f"Error details: {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Editor '{editor}' exited with an error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error editing commit message: {e}")
        sys.exit(1)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def show_commit_diff() -> None:
    """Displays the current staged changes."""
    try:
        diff = run_command(commands["get_stashed_changes"])
        if diff:
            print("Current staged changes:\n")
            print(diff)
        else:
            print("No staged changes found.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error retrieving staged changes: {e.stderr}")
        sys.exit(1)


def interaction_loop():
    """Handles user interaction for commit message generation."""
    global MODEL_SPEC
    staged_changes = run_command(commands["get_stashed_changes"]).strip()
    if not staged_changes:
        print("🔎 No staged changes found.")
        sys.exit(0)
    commit_message = generate_commit_message(staged_changes)
    while True:
        action = input("Proceed to commit? [y(yes) | n(no) | s(show) | r(regenerate) | m(model) | e(edit)]:").strip().lower()
        match action:
            case "r" | "regenerate":
                subprocess.run(commands["clear_screen"])
                print("🔄 Regenerating commit message...")
                print("-" * 50 + "\n")
                commit_message = generate_commit_message(staged_changes, random_regen=True)
                continue
            case "s" | "show":
                subprocess.run(commands["clear_screen"])
                show_commit_diff()
                print("=" * 20 + "\n")
                print("Generated commit message:\n")
                print(commit_message)
                print("-" * 50 + "\n")
            case "m" | "model":
                subprocess.run(commands["clear_screen"])
                valid_models = AIModels().list_available_models()
                print(f"Current model: {MODEL_SPEC}")
                new_model_spec = input(f"Enter new model name (or press Enter to keep current):\nAvailable models: {', '.join(valid_models)}\n>>> ")
                if new_model_spec in valid_models:
                    MODEL_SPEC = new_model_spec
                    print(f"🔀 Model changed to: {MODEL_SPEC}")
                else:
                    print("🚧 Model Unchanged.")
            case "y" | "yes":
                print("🔄 Committing changes...")
                res = run_command(command=commands["commit"], extra_args=[commit_message])
                print(f"✅ Committed with message:\n{res.strip()}")
                break
            case "n" | "no":
                print("❌ Commit aborted by user.")
                break
            case "e" | "edit":
                edited_commit_message = handel_edit_commit_message(commit_message)
                commit_message = edited_commit_message
                subprocess.run(commands["clear_screen"])
                print("✨ Edited commit message...")
                print("-" * 50 + "\n")
                print(commit_message)
                print("\n" * 3, end="")
                continue
            case _:
                print("❗ Invalid input. Please enter 'y', 'n', 's', 'r', or 'e'.")
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
