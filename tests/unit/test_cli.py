"""Tests for the AccessMatrix CLI."""

from typer.testing import CliRunner

from accessmatrix.cli.app import app

runner = CliRunner()


def test_version_option() -> None:
    """The CLI should display its version."""

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "AccessMatrix" in result.output


def test_doctor_command() -> None:
    """The doctor command should inspect the environment."""

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Environment check passed" in result.output
    assert "Python Version" in result.output
