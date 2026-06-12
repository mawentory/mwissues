from click.testing import CliRunner

from mwissues.cli import cli


def test_web_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["web", "--help"])
    assert result.exit_code == 0
    assert "start" in result.output
