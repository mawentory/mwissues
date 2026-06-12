"""Tests for mwissues CLI init command."""
import json

from click.testing import CliRunner

from mwissues.cli import cli


def test_mwissues_shows_help_with_no_args():
    """Running mwissues with no args should show help."""
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert "Usage:" in result.output or "usage:" in result.output.lower()
    assert "mwissues" in result.output


def test_mwissues_init_creates_db_and_instructions(tmp_path, monkeypatch):
    """mwissues init should create database and mwissues.md."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0, result.output

    db_path = tmp_path / "mwissues.db"
    instructions_path = tmp_path / "mwissues.md"

    assert db_path.exists(), f"Database not created at {db_path}"
    assert instructions_path.exists(), f"Instructions not created at {instructions_path}"

    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "issues" in tables
    assert "todos" in tables
    assert "tags" in tables
    conn.close()


def test_mwissues_init_is_idempotent(tmp_path, monkeypatch):
    """Running mwissues init twice should succeed (idempotent)."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result1 = runner.invoke(cli, ["init"])
    assert result1.exit_code == 0, result1.output

    result2 = runner.invoke(cli, ["init"])
    assert result2.exit_code == 0, result2.output
    assert "already" in result2.output.lower() or "exists" in result2.output.lower()


def test_mwissues_list_json_flag(tmp_path, monkeypatch):
    """mwissues list --json should output valid JSON."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["init"])

    result = runner.invoke(cli, ["list", "--json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert "issues" in data
    assert isinstance(data["issues"], list)


def test_mwissues_list_human_flag(tmp_path, monkeypatch):
    """mwissues list --human should output pretty table."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["init"])

    result = runner.invoke(cli, ["list", "--human"])
    assert result.exit_code == 0, result.output
    assert "ID" in result.output or "No issues" in result.output
