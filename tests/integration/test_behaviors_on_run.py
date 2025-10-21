import time
from unittest.mock import patch

import pytest

from src.commit_bot.main import commands, run, run_command
from src.commit_bot.utils import load_config

# 1. Save a reference to the original, un-patched function
original_run_command = run_command


def run_command_hook(command, extra_args=None):
    """
    This function will be the side_effect of our mock.
    It checks the arguments and decides what to do.
    """
    if command == commands["get_stashed_changes"]:
        print("--- Mocking run_command for 'get_stashed_changes' ---")
        return "## fake diff from mock"
    elif command == commands["commit"]:
        print(f"--- Mocking run_command for 'commit' with message: {extra_args[0]} ---")
        return f"[main 1234567] {extra_args[0]}"
    else:
        print(f"--- Calling original run_command with: {command} ---")
        return original_run_command(command, extra_args)


def create_input_hook(inputs):
    """
    Creates a side_effect function for mocking builtins.input that can handle a 'sleep' command.
    """
    input_iterator = iter(inputs)
    idle_min = load_config("job.conf").get("server_idle_timeout_minutes")

    def input_hook(*args, **kwargs):
        while True:
            try:
                next_input = next(input_iterator)
                if next_input == "sleep":
                    print("Sleeping for test...")
                    time.sleep((idle_min + 1) * 60)
                    # Continue to next input after sleeping
                else:
                    return next_input
            except StopIteration:
                raise EOFError("End of mocked inputs")

    return input_hook


# fmt: off
@pytest.mark.parametrize(
    argnames=[
        "user_inputs",
        "expected_keywords"
    ],
    argvalues=[
        pytest.param(
            ("y",),
            ["Committing changes...", "Committed with message:"],
            id="commit_immediately",
        ),
        pytest.param(
            ("n",),
            ["Commit aborted by user."],
            id="abort_immediately",
        ),
        pytest.param(
            ("s", "r", "y"),
            ["Current staged changes:", "Regenerating commit message...", "Committing changes...", "Committed with message:"],
            id="show_regenerate_commit",
        ),
        pytest.param(
            ("r", "m", "ollama-gemma3:4b", "r", "y"),
            [
                "Regenerating commit message...",
                "Model changed to: ollama-gemma3:4b",
                "Committing changes...",
                "Committed with message:",
            ],
            id="regenerate_change_model_regenerate_commit",
        ),
        pytest.param(
            ("r", "m", "vllm-qwen3:4b", "r", "m", "vllm-gpt-oss:20b", "r", "m", "ollama-gemma3:4b", "r", "m", "vllm-gpt-oss:20b", "y"),
            [
                "Regenerating commit message...",
                "Model changed to: vllm-qwen3:4b",
                "Model changed to: vllm-gpt-oss:20b",
                "Model changed to: ollama-gemma3:4b",
                "Committing changes...",
                "Committed with message:",
            ],
            id="multiple_model_changes_before_commit",
        ),
        pytest.param(
            ("r", "sleep", "r", "y"),
            ["Regenerating commit message...", "Sleeping for test...", "Committing changes...", "Committed with message:"],
            id="regenerate_sleep_regenerate_commit",
        ),
        pytest.param(
            ("r", "m", "vllm-qwen3:4b", "sleep", "r", "m", "ollama-gemma3:4b", "sleep", "r", "m", "vllm-gpt-oss:20b", "y"),
            [
                "Regenerating commit message...",
                "Model changed to: vllm-qwen3:4b",
                "Sleeping for test...",
                "Model changed to: ollama-gemma3:4b",
                "Sleeping for test...",
                "Model changed to: vllm-gpt-oss:20b",
                "Committing changes...",
                "Committed with message:",
            ],
            id="multiple_model_changes_with_sleeps_before_commit",
        ),
    ],
)
# fmt: on
def test_conditional_patch(capsys, user_inputs, expected_keywords):
    """
    Tests that run_command is only mocked for a specific argument.
    """
    input_hook = create_input_hook(user_inputs)
    with patch("builtins.input", side_effect=input_hook), patch("src.commit_bot.main.run_command", side_effect=run_command_hook) as mock_run_command:
        run()
    captured = capsys.readouterr()
    # DEBUGGING: Print the captured output explicitly
    print("\n--- Captured Output ---")
    print(captured.out)
    print("-----------------------\n")
    for keyword in expected_keywords:
        assert keyword in captured.out
    assert mock_run_command.call_count >= 1
