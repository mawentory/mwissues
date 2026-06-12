"""Tests for tag management commands."""
from click.testing import CliRunner

from mwissues.cli import cli


def test_add_tags_single(tmp_path, monkeypatch):
    """mwissues add-tags <id> <tag> adds a single tag."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["init"])

    import sqlite3
    conn = sqlite3.connect(tmp_path / "mwissues.db")
    conn.execute("INSERT INTO issues (title, description, priority) VALUES (?, ?, ?)",
                 ("Fix login bug", "Initial issue", "A"))
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["add-tags", "1", "urgent"])
    assert result.exit_code == 0, result.output
    assert "Added: urgent" in result.output


def test_add_tags_duplicate_is_skipped(tmp_path, monkeypatch):
    """Adding an existing tag should output 'Skipped'."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["init"])

    import sqlite3
    conn = sqlite3.connect(tmp_path / "mwissues.db")
    conn.execute("INSERT INTO issues (title, description, priority) VALUES (?, ?, ?)",
                 ("Fix login bug", "Initial issue", "A"))
    conn.commit()
    conn.close()

    runner.invoke(cli, ["add-tags", "1", "urgent"])
    result = runner.invoke(cli, ["add-tags", "1", "urgent"])
    assert result.exit_code == 0, result.output
    assert "Skipped: 'urgent' already exists on issue #1" in result.output


def test_remove_tags_existing(tmp_path, monkeypatch):
    """Removing an existing tag deletes it and prints confirmation."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["init"])

    import sqlite3
    conn = sqlite3.connect(tmp_path / "mwissues.db")
    conn.execute("INSERT INTO issues (title, description, priority) VALUES (?, ?, ?)",
                 ("Fix login bug", "Initial issue", "A"))
    conn.execute("INSERT INTO tags (issue_id, name) VALUES (?, ?)", (1, "bug"))
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["remove-tags", "1", "bug"])
    assert result.exit_code == 0, result.output
    assert "Removed: bug" in result.output

    conn = sqlite3.connect(tmp_path / "mwissues.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tags WHERE issue_id = ? AND name = ?", (1, "bug"))
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 0


def test_remove_tags_missing_reports_not_found(tmp_path, monkeypatch):
    """Removing a tag that doesn't exist reports 'Not found'."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["init"])

    import sqlite3
    conn = sqlite3.connect(tmp_path / "mwissues.db")
    conn.execute("INSERT INTO issues (title, description, priority) VALUES (?, ?, ?)",
                 ("Fix login bug", "Initial issue", "A"))
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["remove-tags", "1", "nonexistent"])
    assert result.exit_code == 0, result.output
    assert "Not found: 'nonexistent' not on issue #1" in result.output


def test_rename_tags_updates_all_issues(tmp_path, monkeypatch):
    """Renaming a tag should update all matching tags and report affected count."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["init"])

    import sqlite3
    conn = sqlite3.connect(tmp_path / "mwissues.db")
    conn.execute("INSERT INTO issues (title, description, priority) VALUES (?, ?, ?)",
                 ("Fix login bug", "Initial issue", "A"))
    conn.execute("INSERT INTO issues (title, description, priority) VALUES (?, ?, ?)",
                 ("Add signup", "New feature", "B"))
    conn.execute("INSERT INTO tags (issue_id, name) VALUES (?, ?)", (1, "bug"))
    conn.execute("INSERT INTO tags (issue_id, name) VALUES (?, ?)", (2, "bug"))
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["rename-tags", "bug", "defect"])
    assert result.exit_code == 0, result.output
    assert "Renamed 'bug' → 'defect' (2 issues affected)" in result.output

    conn = sqlite3.connect(tmp_path / "mwissues.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tags WHERE name = ?", ("defect",))
    assert cursor.fetchone()[0] == 2
    cursor.execute("SELECT COUNT(*) FROM tags WHERE name = ?", ("bug",))
    assert cursor.fetchone()[0] == 0
    conn.close()


