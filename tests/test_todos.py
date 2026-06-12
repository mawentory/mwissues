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


def test_check_todo_already_checked(tmp_path, monkeypatch):
    """check-todo on an already-checked todo fails with expected message."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    runner.invoke(cli, ["add-todo", "1", "Write tests"])
    runner.invoke(cli, ["check-todo", "1", "1"])

    result = runner.invoke(cli, ["check-todo", "1", "1"])
    assert result.exit_code != 0
    assert "Failed: Todo #1 is already checked" in result.output


def test_uncheck_todo(tmp_path, monkeypatch):
    """mwissues uncheck-todo <id> <index> marks todo not done."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    runner.invoke(cli, ["add-todo", "1", "Write tests"])
    runner.invoke(cli, ["check-todo", "1", "1"])

    result = runner.invoke(cli, ["uncheck-todo", "1", "1"])
    assert result.exit_code == 0, result.output
    assert 'Todo #1 unchecked: "Write tests"' in result.output


def test_uncheck_todo_already_unchecked(tmp_path, monkeypatch):
    """uncheck-todo on an already-unchecked todo fails with expected message."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    runner.invoke(cli, ["add-todo", "1", "Write tests"])

    result = runner.invoke(cli, ["uncheck-todo", "1", "1"])
    assert result.exit_code != 0
    assert "Failed: Todo #1 is already unchecked" in result.output


def test_remove_todo(tmp_path, monkeypatch):
    """mwissues remove-todo <id> <index> deletes todo with confirmation."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    runner.invoke(cli, ["add-todo", "1", "Write tests"])

    result = runner.invoke(cli, ["remove-todo", "1", "1"])
    assert result.exit_code == 0, result.output
    assert 'Todo #1 removed: "Write tests"' in result.output

    import sqlite3
    conn = sqlite3.connect(tmp_path / "mwissues.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM todos WHERE issue_id = ?", (1,))
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 0


def test_edit_todo(tmp_path, monkeypatch):
    """mwissues edit-todo <id> <index> <text> updates todo text."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    runner.invoke(cli, ["add-todo", "1", "Write tests"])

    result = runner.invoke(cli, ["edit-todo", "1", "1", "Write comprehensive tests"])
    assert result.exit_code == 0, result.output
    assert 'Todo #1 updated: "Write comprehensive tests"' in result.output


def test_check_todo_not_found(tmp_path, monkeypatch):
    """check-todo with invalid index shows not found."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["check-todo", "1", "2"])
    assert result.exit_code != 0
    assert "Todo #2 not found" in result.output


def test_uncheck_todo_not_found(tmp_path, monkeypatch):
    """uncheck-todo with invalid index shows not found."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["uncheck-todo", "1", "2"])
    assert result.exit_code != 0
    assert "Todo #2 not found" in result.output


def test_remove_todo_not_found(tmp_path, monkeypatch):
    """remove-todo with invalid index shows not found."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["remove-todo", "1", "2"])
    assert result.exit_code != 0
    assert "Todo #2 not found" in result.output


def test_edit_todo_not_found(tmp_path, monkeypatch):
    """edit-todo with invalid index shows not found."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["edit-todo", "1", "2", "New text"])
    assert result.exit_code != 0
    assert "Todo #2 not found" in result.output


def test_add_todo_issue_not_found(tmp_path, monkeypatch):
    """add-todo on non-existent issue shows issue not found."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["add-todo", "99", "Write tests"])
    assert result.exit_code != 0
    assert "Issue #99 not found" in result.output


def test_check_todo_issue_not_found(tmp_path, monkeypatch):
    """check-todo on non-existent issue shows issue not found."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["check-todo", "99", "1"])
    assert result.exit_code != 0
    assert "Issue #99 not found" in result.output


def test_uncheck_todo_issue_not_found(tmp_path, monkeypatch):
    """uncheck-todo on non-existent issue shows issue not found."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["uncheck-todo", "99", "1"])
    assert result.exit_code != 0
    assert "Issue #99 not found" in result.output


def test_remove_todo_issue_not_found(tmp_path, monkeypatch):
    """remove-todo on non-existent issue shows issue not found."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["remove-todo", "99", "1"])
    assert result.exit_code != 0
    assert "Issue #99 not found" in result.output


def test_edit_todo_issue_not_found(tmp_path, monkeypatch):
    """edit-todo on non-existent issue shows issue not found."""
    monkeypatch.chdir(tmp_path)
    _init_and_create_issue(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["edit-todo", "99", "1", "New text"])
    assert result.exit_code != 0
    assert "Issue #99 not found" in result.output
