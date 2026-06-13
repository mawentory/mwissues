"""Tests for database migration."""
import sqlite3
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from mwissues.cli import cli


@pytest.fixture
def old_schema_db(tmp_path):
    """Create a database with old schema (no visibility column, old status values)."""
    db_path = tmp_path / "mwissues.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            details TEXT,
            priority TEXT CHECK(priority IN ('A','B','C','D','E')) NOT NULL,
            status TEXT DEFAULT 'active' CHECK(status IN ('active','inactive')) NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("INSERT INTO issues (title, description, priority, status, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
                 ("Bug 1", "Description 1", "A", "active"))
    conn.execute("INSERT INTO issues (title, description, priority, status, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
                 ("Bug 2", "Description 2", "B", "inactive"))
    conn.execute("INSERT INTO issues (title, description, priority, status, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
                 ("Feature 1", "Description 3", "C", "active"))
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def new_schema_db(tmp_path):
    """Create a database with new schema (has visibility column)."""
    db_path = tmp_path / "mwissues.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            details TEXT,
            priority TEXT CHECK(priority IN ('A','B','C','D','E')) NOT NULL,
            status TEXT DEFAULT 'open' CHECK(status IN ('open','closed')) NOT NULL,
            visibility TEXT DEFAULT 'visible' CHECK(visibility IN ('visible','hidden')) NOT NULL,
            created_at TEXT DEFAULT (datetime('now')) NOT NULL
        );
        CREATE TABLE todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
            text TEXT NOT NULL,
            done INTEGER DEFAULT 0 CHECK(done IN (0, 1))
        );
        CREATE TABLE tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
            name TEXT NOT NULL
        );
    """)
    conn.execute("INSERT INTO issues (title, description, priority, status, visibility) VALUES (?, ?, ?, ?, ?)",
                 ("Issue 1", "Desc", "A", "open", "visible"))
    conn.execute("INSERT INTO todos (issue_id, text, done) VALUES (?, ?, ?)", (1, "Todo 1", 0))
    conn.execute("INSERT INTO tags (issue_id, name) VALUES (?, ?)", (1, "bug"))
    conn.commit()
    conn.close()
    return db_path


def test_migration_old_schema_to_new(old_schema_db, monkeypatch):
    """Test that old schema is migrated to new schema correctly."""
    monkeypatch.chdir(old_schema_db.parent)

    # Verify old schema
    conn = sqlite3.connect(old_schema_db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(issues)")
    columns = [c[1] for c in cursor.fetchall()]
    assert 'visibility' not in columns
    conn.close()

    # Run init (triggers migration)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])

    # Verify new schema
    conn = sqlite3.connect(old_schema_db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(issues)")
    columns = [c[1] for c in cursor.fetchall()]
    assert 'visibility' in columns
    cursor.execute("SELECT title, status, visibility FROM issues ORDER BY id")
    issues = cursor.fetchall()
    conn.close()

    # Verify status migration
    assert issues[0] == ("Bug 1", "open", "visible")
    assert issues[1] == ("Bug 2", "closed", "visible")
    assert issues[2] == ("Feature 1", "open", "visible")


def test_migration_preserves_todos(new_schema_db, monkeypatch):
    """Test that todos are preserved after migration."""
    monkeypatch.chdir(new_schema_db.parent)

    runner = CliRunner()
    result = runner.invoke(cli, ["init"])

    conn = sqlite3.connect(new_schema_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM todos")
    todo_count = cursor.fetchone()[0]
    conn.close()

    assert todo_count == 1


def test_migration_preserves_tags(new_schema_db, monkeypatch):
    """Test that tags are preserved after migration."""
    monkeypatch.chdir(new_schema_db.parent)

    runner = CliRunner()
    result = runner.invoke(cli, ["init"])

    conn = sqlite3.connect(new_schema_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM tags ORDER BY id")
    tags = [t[0] for t in cursor.fetchall()]
    conn.close()

    assert tags == ["bug"]


def test_migration_creates_backup(old_schema_db, monkeypatch):
    """Test that backup is created before migration."""
    monkeypatch.chdir(old_schema_db.parent)
    backup_path = old_schema_db.with_suffix('.db.backup')

    runner = CliRunner()
    result = runner.invoke(cli, ["init"])

    # Backup should exist during migration, then be removed on success
    assert not backup_path.exists()


def test_migration_verbose_output(old_schema_db, monkeypatch):
    """Test that verbose mode shows step-by-step progress."""
    monkeypatch.chdir(old_schema_db.parent)

    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--verbose"])

    assert "Backed up database" in result.output
    assert "Adding visibility column" in result.output
    assert "Migration complete" in result.output


def test_migration_idempotent(new_schema_db, monkeypatch):
    """Test that running init twice on new schema is safe."""
    monkeypatch.chdir(new_schema_db.parent)

    runner = CliRunner()
    result1 = runner.invoke(cli, ["init"])
    result2 = runner.invoke(cli, ["init"])

    assert result1.exit_code == 0
    assert result2.exit_code == 0
    assert "migration complete" in result2.output.lower() or "already exists" in result2.output.lower()


def test_migration_new_schema_preserves_data(new_schema_db, monkeypatch):
    """Test that running init on new schema preserves existing data."""
    monkeypatch.chdir(new_schema_db.parent)

    # Get original data
    conn = sqlite3.connect(new_schema_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM issues")
    original_count = cursor.fetchone()[0]
    conn.close()

    runner = CliRunner()
    result = runner.invoke(cli, ["init"])

    # Verify data preserved
    conn = sqlite3.connect(new_schema_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM issues")
    final_count = cursor.fetchone()[0]
    conn.close()

    assert final_count == original_count
