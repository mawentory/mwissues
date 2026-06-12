"""Tests for mwissues CLI todo management commands."""
from click.testing import CliRunner

from mwissues.cli import cli


def _init_and_create_issue(tmp_path):
    """Helper: init DB and insert one issue."""
    runner = CliRunner()
    runner.invoke(cli, ["init"])

    import sqlite3

    conn = sqlite3.connect(tmp_path / "mwissues.db")
    conn.execute("INSERT INTO issues (title, priority) VALUES (?, ?)", ("Test issue", "A"))
    conn.commit()
    conn.close()


def test_add_todo(tmp_path, monkeypatch):
    """mwissues add-todo <id> <text> adds a todo with confirmation."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["add-todo", "1", "Write tests"])
    assert result.exit_code == 0, result.output
    assert "Todo added to issue #1: 1. Write tests" in result.output


def test_check_todo(tmp_path, monkeypatch):
    """mwissues check-todo <id> <index> marks todo done."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    runner.invoke(cli, ["add-todo", "1", "Write tests"])

    result = runner.invoke(cli, ["check-todo", "1", "1"])
    assert result.exit_code == 0, result.output
    assert 'Todo #1 checked: "Write tests"' in result.output
