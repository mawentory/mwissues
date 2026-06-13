from click.testing import CliRunner

from mwissues.cli import cli


def _init_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["init"])


def test_add_requires_priority_and_description(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()

    result = runner.invoke(cli, ["add", "foo"])
    assert result.exit_code != 0
    assert "Usage:" in result.output


def test_add_then_show_issue(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "add",
            "Fix login bug",
            "--priority",
            "A",
            "--description",
            "Users can't log in after recent deployment",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Issue #1 created: [A] Fix login bug" in result.output

    result = runner.invoke(cli, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "# Issue #1: Fix login bug" in result.output
    assert "**Priority:** A" in result.output
    assert "**Status:** open" in result.output
    assert "Users can't log in after recent deployment" in result.output


def test_list_default_markdown_output(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "add",
            "Fix login bug",
            "--priority",
            "A",
            "--description",
            "Users can't log in after recent deployment",
        ],
    )

    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0, result.output
    assert "# Issues (1 total)" in result.output
    assert "## Issue #1: Fix login bug" in result.output
    assert "- **Priority:** A" in result.output


def test_archive_marks_inactive(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "add",
            "Fix login bug",
            "--priority",
            "A",
            "--description",
            "Users can't log in after recent deployment",
        ],
    )

    result = runner.invoke(cli, ["archive", "1"])
    assert "deprecated" in result.output.lower() or result.exit_code == 0
    result = runner.invoke(cli, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "**Visibility:** hidden" in result.output


def test_edit_issue(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "add",
            "Fix login bug",
            "--priority",
            "A",
            "--description",
            "Users can't log in after recent deployment",
        ],
    )

    result = runner.invoke(
        cli,
        ["edit", "1", "--description", "Updated: root cause found", "--priority", "B"],
    )
    assert result.exit_code == 0, result.output
    assert "Updated: issue #1" in result.output

    result = runner.invoke(cli, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "Updated: root cause found" in result.output
    assert "**Priority:** B" in result.output


def test_delete_issue(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "add",
            "Fix login bug",
            "--priority",
            "A",
            "--description",
            "Users can't log in after recent deployment",
        ],
    )

    result = runner.invoke(cli, ["delete", "1"])
    assert result.exit_code == 0, result.output
    assert "Issue #1 deleted" in result.output

    result = runner.invoke(cli, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "Issue #1 not found" in result.output


def test_show_invalid_id(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["show", "999"])
    assert result.exit_code == 0, result.output
    assert "Issue #999 not found" in result.output


def test_add_with_details(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "add",
            "Fix login bug",
            "--priority",
            "A",
            "--description",
            "Users can't log in after recent deployment",
            "--details",
            "Steps to reproduce:\n1. Go to /login\n2. Enter credentials",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Issue #1 created: [A] Fix login bug" in result.output

    result = runner.invoke(cli, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "**Details:**" in result.output
    assert "Steps to reproduce:" in result.output


def test_show_with_tags_and_todos(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "add",
            "Fix login bug",
            "--priority",
            "A",
            "--description",
            "Users can't log in after recent deployment",
        ],
    )
    import sqlite3

    conn = sqlite3.connect(tmp_path / "mwissues.db")
    conn.execute("INSERT INTO tags (issue_id, name) VALUES (?, ?)", (1, "auth"))
    conn.execute(
        "INSERT INTO todos (issue_id, text, done) VALUES (?, ?, ?)",
        (1, "Write failing test", 1),
    )
    conn.execute(
        "INSERT INTO todos (issue_id, text, done) VALUES (?, ?, ?)",
        (1, "Fix the bug", 0),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "**Tags:** auth" in result.output
    assert "- [x] 1. Write failing test" in result.output
    assert "- [ ] 2. Fix the bug" in result.output


def test_edit_description_only(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "add",
            "Fix login bug",
            "--priority",
            "A",
            "--description",
            "Users can't log in after recent deployment",
        ],
    )

    result = runner.invoke(
        cli, ["edit", "1", "--description", "Updated: root cause found"]
    )
    assert result.exit_code == 0, result.output
    assert "Updated: issue #1 description" in result.output

    result = runner.invoke(cli, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "Updated: root cause found" in result.output


def test_edit_details_only(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "add",
            "Fix login bug",
            "--priority",
            "A",
            "--description",
            "Users can't log in after recent deployment",
        ],
    )

    result = runner.invoke(
        cli,
        ["edit", "1", "--details", "New steps:\n1. Clear cache\n2. Retry login"],
    )
    assert result.exit_code == 0, result.output
    assert "Updated: issue #1 details" in result.output

    result = runner.invoke(cli, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "New steps:" in result.output


def test_edit_priority_and_title(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "add",
            "Fix login bug",
            "--priority",
            "A",
            "--description",
            "Users can't log in after recent deployment",
        ],
    )

    result = runner.invoke(
        cli,
        ["edit", "1", "--priority", "A", "--title", "Fix critical login bug"],
    )
    assert result.exit_code == 0, result.output
    assert "Updated: issue #1 title, priority" in result.output

    result = runner.invoke(cli, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "Fix critical login bug" in result.output
    assert "**Priority:** A" in result.output


def test_archive_invalid_id(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["archive", "999"])
    assert "Issue #999 not found" in result.output
    assert result.exit_code == 1


def test_delete_invalid_id(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["delete", "999"])
    assert "Issue #999 not found" in result.output


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------

import json


def test_import_valid_stdin(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()

    json_data = json.dumps([
        {"title": "Fix auth", "description": "Users can't log in", "priority": "A"},
        {"title": "Add dark mode", "description": "Support dark theme", "priority": "B"},
    ])

    result = runner.invoke(cli, ["import-issues"], input=json_data)
    assert result.exit_code == 0, result.output
    assert "Imported 2 issues successfully" in result.output

    result = runner.invoke(cli, ["list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data["issues"]) == 2
    titles = [i["title"] for i in data["issues"]]
    assert "Fix auth" in titles
    assert "Add dark mode" in titles


def test_import_valid_file(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()

    json_file = tmp_path / "issues.json"
    json_file.write_text(json.dumps([
        {"title": "Bug in parser", "description": "Parser fails", "priority": "A"},
        {"title": "Feature request", "description": "Add export", "priority": "C"},
    ]))

    result = runner.invoke(cli, ["import-issues", str(json_file)])
    assert result.exit_code == 0, result.output
    assert "Imported 2 issues successfully" in result.output

    result = runner.invoke(cli, ["list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data["issues"]) == 2


def test_import_default_priority(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()

    json_data = json.dumps([
        {"title": "Issue without priority"},
    ])

    result = runner.invoke(cli, ["import-issues"], input=json_data)
    assert result.exit_code == 0, result.output
    assert "Imported 1 issues successfully" in result.output

    result = runner.invoke(cli, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "**Priority:** B" in result.output


def test_import_missing_title(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()

    json_data = json.dumps([
        {"description": "No title provided"},
    ])

    result = runner.invoke(cli, ["import-issues"], input=json_data)
    assert result.exit_code != 0
    assert "Error at index 0: field 'title' is required" in result.output

    result = runner.invoke(cli, ["list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data["issues"]) == 0


def test_import_invalid_priority(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()

    json_data = json.dumps([
        {"title": "Bad priority", "priority": "Z"},
    ])

    result = runner.invoke(cli, ["import-issues"], input=json_data)
    assert result.exit_code != 0
    assert "Error at index 0: field 'priority' must be one of A, B, C, D, E" in result.output

    result = runner.invoke(cli, ["list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data["issues"]) == 0


def test_import_partial_invalid_rollback(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()

    json_data = json.dumps([
        {"title": "Valid issue", "description": "This one is fine"},
        {"description": "Missing title"},
    ])

    result = runner.invoke(cli, ["import-issues"], input=json_data)
    assert result.exit_code != 0
    assert "Error at index 1: field 'title' is required" in result.output

    result = runner.invoke(cli, ["list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data["issues"]) == 0


def test_import_with_tags_and_todos(tmp_path, monkeypatch):
    _init_db(tmp_path, monkeypatch)
    runner = CliRunner()

    json_data = json.dumps([
        {
            "title": "Complex issue",
            "description": "With tags and todos",
            "priority": "A",
            "tags": ["bug", "auth"],
            "todos": [
                {"text": "Check logs", "done": False},
                {"text": "Reproduce bug", "done": True},
            ],
        },
    ])

    result = runner.invoke(cli, ["import-issues"], input=json_data)
    assert result.exit_code == 0, result.output
    assert "Imported 1 issues successfully" in result.output

    result = runner.invoke(cli, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "**Tags:** bug, auth" in result.output
    assert "- [ ] 1. Check logs" in result.output
    assert "- [x] 2. Reproduce bug" in result.output
