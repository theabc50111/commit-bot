import subprocess

import pytest

from src.commit_bot.main import generate_commit_message, run_command


@pytest.mark.parametrize(argnames="command, extra_args, expected", argvalues=[("echo", ["hi~"], "hi~"), ("git", ["rev-parse", "--git-dir"], ".git")], ids=["echo", "check git dir"])
def test_run_command(command, extra_args, expected):
    res = run_command(command, extra_args)
    assert expected in res


@pytest.mark.parametrize(
    argnames="command, extra_args, expected_exception",
    argvalues=[
        ("git", ["invalid-command"], subprocess.CalledProcessError),
        ("no_such_command", None, FileNotFoundError),
    ],
    ids=["invalid args", "invalid command"],
)
def test_run_command_invalid(command, extra_args, expected_exception):
    with pytest.raises(expected_exception):
        run_command(command, extra_args)


def test_generate_commit_message():
    changes = "Added new feature X and fixed bug Y."
    message = generate_commit_message(changes)
    print(f"Generated commit message: {message}")

    assert message.isspace() is False, "Generated commit message should not be empty or whitespace only."
