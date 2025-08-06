import pytest

from src.commit_pilot.main import run_command


@pytest.mark.parametrize(
    argnames = "command, extra_args, expected",
    argvalues = [("echo", "hi~", "hi~\n")],
    ids = ["echo"]
)
def test_run_command(command, extra_args, expected):
    res = run_command(command, extra_args)
    assert res == expected
