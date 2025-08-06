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
    print(res)
    assert expected in res
