from unittest.mock import patch

import pytest

from src.commit_bot.main import commands, run, run_command

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
    else:
        print(f"--- Calling original run_command with: {command} ---")
        return original_run_command(command, extra_args)


# fmt: off
@pytest.mark.parametrize(
    argenames=[
        "behavior"
    ],
    argvalues=[
        ("s", "r", "r", "n")
    ]
)
# fmt: on
def test_conditional_patch(behavior):
    """
    Tests that run_command is only mocked for a specific argument.
    """
    with patch("builtins.input", side_effect=behavior), patch("src.commit_bot.main.run_command", side_effect=run_command_hook):
        run()

    # You can still assert calls to the mock
    # assert mock_run_command.call_count >= 1
