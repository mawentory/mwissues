from click.testing import CliRunner
from unittest.mock import patch

from mwissues.cli import cli


def test_web_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["web", "--help"])
    assert result.exit_code == 0
    assert "start" in result.output


def test_web_start_imports_webapp(tmp_path, monkeypatch):
    """Regression: web start must find webapp module when installed as package."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    with patch("webbrowser.open"):
        with patch("mwissues.webapp.app.run"):
            result = runner.invoke(cli, ["web", "start", "--no-browser"])
    assert result.exit_code == 0
    assert "ModuleNotFoundError" not in result.output
