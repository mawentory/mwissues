"""Tests for mwissues CLI init command."""
import json
import os
import shutil
import subprocess


def test_mwissues_shows_help_with_no_args():
    """Running mwissues with no args should show help."""
    mwissues_cmd = shutil.which("mwissues")
    assert mwissues_cmd is not None, "mwissues command not found in PATH"
    
    result = subprocess.run(
        [mwissues_cmd],
        capture_output=True,
        text=True
    )
    # Help is shown in stderr when no command is provided
    assert "Usage:" in result.stderr or "usage:" in result.stderr.lower()
    assert "mwissues" in result.stderr


def test_mwissues_init_creates_db_and_instructions(tmp_path):
    """mwissues init should create database and mwissues.md."""
    mwissues_cmd = shutil.which("mwissues")
    
    result = subprocess.run(
        [mwissues_cmd, "init"],
        capture_output=True,
        text=True,
        cwd=tmp_path
    )
    
    assert result.returncode == 0, f"init failed: {result.stderr}"
    
    db_path = tmp_path / "mwissues.db"
    instructions_path = tmp_path / "mwissues.md"
    
    assert db_path.exists(), f"Database not created at {db_path}"
    assert instructions_path.exists(), f"Instructions not created at {instructions_path}"
    
    # Verify database has the expected tables
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "issues" in tables
    assert "todos" in tables
    assert "tags" in tables
    conn.close()


def test_mwissues_init_is_idempotent(tmp_path):
    """Running mwissues init twice should succeed (idempotent)."""
    mwissues_cmd = shutil.which("mwissues")
    
    # First init
    result1 = subprocess.run(
        [mwissues_cmd, "init"],
        capture_output=True,
        text=True,
        cwd=tmp_path
    )
    assert result1.returncode == 0, f"first init failed: {result1.stderr}"
    
    # Second init - should not fail
    result2 = subprocess.run(
        [mwissues_cmd, "init"],
        capture_output=True,
        text=True,
        cwd=tmp_path
    )
    assert result2.returncode == 0, f"second init failed: {result2.stderr}"
    # Should indicate already exists
    assert "already" in result2.stdout.lower() or "exists" in result2.stdout.lower()


def test_mwissues_list_json_flag(tmp_path):
    """mwissues list --json should output valid JSON."""
    mwissues_cmd = shutil.which("mwissues")
    
    # Init database
    subprocess.run([mwissues_cmd, "init"], capture_output=True, cwd=tmp_path)
    
    result = subprocess.run(
        [mwissues_cmd, "list", "--json"],
        capture_output=True,
        text=True,
        cwd=tmp_path
    )
    
    assert result.returncode == 0, f"list --json failed: {result.stderr}"
    
    # Should be valid JSON
    data = json.loads(result.stdout)
    assert "issues" in data
    assert isinstance(data["issues"], list)


def test_mwissues_list_human_flag(tmp_path):
    """mwissues list --human should output pretty table."""
    mwissues_cmd = shutil.which("mwissues")
    
    # Init database
    subprocess.run([mwissues_cmd, "init"], capture_output=True, cwd=tmp_path)
    
    result = subprocess.run(
        [mwissues_cmd, "list", "--human"],
        capture_output=True,
        text=True,
        cwd=tmp_path
    )
    
    assert result.returncode == 0, f"list --human failed: {result.stderr}"
    # Should contain formatted table elements (headers/dashes)
    assert "ID" in result.stdout or "No issues" in result.stdout
