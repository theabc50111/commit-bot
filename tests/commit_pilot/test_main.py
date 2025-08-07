import subprocess

import pytest

from src.commit_pilot.main import run_command


@pytest.mark.parametrize(
    argnames = "command, extra_args, expected",
    argvalues = [
        ("echo", ["hi~"], "hi~"),
        ("git", ["rev-parse", "--git-dir"], ".git")
    ],
    ids = ["echo", "check git dir"]
)
def test_run_command(command, extra_args, expected):
    res = run_command(command, extra_args)
    assert expected in res

@pytest.mark.parametrize(
    argnames = "command, extra_args, expected_exception",
    argvalues = [
        ("git", ["invalid-command"], subprocess.CalledProcessError),
        ("no_such_command", None, FileNotFoundError),
    ],
    ids = ["invalid args", "invalid command"]
)
def test_run_command_invalid(command, extra_args, expected_exception):
    with pytest.raises(expected_exception):
        run_command(command, extra_args)
