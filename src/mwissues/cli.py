"""mwissues CLI - Personal issue tracker."""
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import click

DB_NAME = "mwissues.db"
INSTRUCTIONS_NAME = "mwissues.md"

SCHEMA = """
CREATE TABLE IF NOT EXISTS issues (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  details TEXT,
  priority TEXT CHECK(priority IN ('A','B','C','D','E')) NOT NULL,
  status TEXT DEFAULT 'open' CHECK(status IN ('open','closed')) NOT NULL,
  visibility TEXT DEFAULT 'visible' CHECK(visibility IN ('visible','hidden')) NOT NULL,
  created_at TEXT DEFAULT (datetime('now')) NOT NULL
);

-- Migration: rename status values and add visibility column
-- Only run if old schema exists
-- UPDATE issues SET status = 'open' WHERE status = 'active';
-- UPDATE issues SET status = 'closed' WHERE status = 'inactive';
-- ALTER TABLE issues ADD COLUMN visibility TEXT DEFAULT 'visible' CHECK(visibility IN ('visible','hidden'));

CREATE TABLE IF NOT EXISTS todos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  done INTEGER DEFAULT 0 CHECK(done IN (0, 1))
);

CREATE TABLE IF NOT EXISTS tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
  name TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_todos_issue_id ON todos(issue_id);
CREATE INDEX IF NOT EXISTS idx_tags_issue_id ON tags(issue_id);
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
"""


def _migrate_db(db_path, verbose=False):
    """Migrate existing database to new schema with visibility column and open/closed status.
    
    Non-destructive: creates backup, uses ALTER TABLE when possible, rolls back on failure.
    """
    # 1. Create backup first
    backup_path = db_path.with_suffix('.db.backup')
    shutil.copy2(db_path, backup_path)
    if verbose:
        click.echo(f"Backed up database to {backup_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 2. Check current schema
        cursor.execute("PRAGMA table_info(issues)")
        columns = [col[1] for col in cursor.fetchall()]
        if verbose:
            click.echo(f"Current columns: {columns}")

        # 3. If visibility column exists, just migrate status values
        if 'visibility' in columns:
            if verbose:
                click.echo("Checking status values...")
            cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'active' OR status = 'inactive'")
            count = cursor.fetchone()[0]
            if count > 0:
                cursor.execute("UPDATE issues SET status = 'open' WHERE status = 'active'")
                cursor.execute("UPDATE issues SET status = 'closed' WHERE status = 'inactive'")
                if verbose:
                    click.echo(f"Migrated {count} status values")
            conn.commit()
            conn.close()
            if verbose:
                click.echo("Database already at latest schema, status values migrated.")
            return

        # 4. Try to add visibility column using ALTER TABLE (safe, no data loss)
        try:
            if verbose:
                click.echo("Adding visibility column...")
            cursor.execute("""
                ALTER TABLE issues ADD COLUMN visibility TEXT DEFAULT 'visible'
                CHECK(visibility IN ('visible','hidden'))
            """)
            if verbose:
                click.echo("Column added.")

            # 5. Migrate status values
            if verbose:
                click.echo("Migrating status values: active→open, inactive→closed...")
            cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'active' OR status = 'inactive'")
            count = cursor.fetchone()[0]
            if count > 0:
                cursor.execute("UPDATE issues SET status = 'open' WHERE status = 'active'")
                cursor.execute("UPDATE issues SET status = 'closed' WHERE status = 'inactive'")
                if verbose:
                    click.echo(f"Migrated {count} status values")

            conn.commit()
            conn.close()

        except sqlite3.IntegrityError:
            # Old schema has CHECK constraint blocking status update - need table recreation
            if verbose:
                click.echo("CHECK constraint detected, recreating table...")
            
            # Restore connection for fresh transaction
            conn.close()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=off")

            # Get all existing data
            cursor.execute("SELECT * FROM issues")
            existing_issues = cursor.fetchall()
            cursor.execute("PRAGMA table_info(issues)")
            old_columns = [col[1] for col in cursor.fetchall()]

            # Drop old table
            cursor.execute("DROP TABLE issues")

            # Create new table
            cursor.execute("""
                CREATE TABLE issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    details TEXT,
                    priority TEXT CHECK(priority IN ('A','B','C','D','E')) NOT NULL,
                    status TEXT DEFAULT 'open' CHECK(status IN ('open','closed')) NOT NULL,
                    visibility TEXT DEFAULT 'visible' CHECK(visibility IN ('visible','hidden')) NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')) NOT NULL
                )
            """)

            # Copy data with conversion
            for row in existing_issues:
                row_dict = dict(zip(old_columns, row))
                old_status = row_dict.get('status', 'active')
                new_status = 'open' if old_status == 'active' else ('closed' if old_status == 'inactive' else old_status)
                cursor.execute("""
                    INSERT INTO issues (id, title, description, details, priority, status, visibility, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'visible', ?)
                """, (
                    row_dict['id'],
                    row_dict['title'],
                    row_dict.get('description'),
                    row_dict.get('details'),
                    row_dict['priority'],
                    new_status,
                    row_dict.get('created_at')
                ))

            cursor.execute("PRAGMA foreign_keys=on")
            conn.commit()
            conn.close()
            
            if verbose:
                click.echo(f"Recreated table with {len(existing_issues)} issues migrated")

        # 6. Remove backup on success
        backup_path.unlink(missing_ok=True)
        
        if verbose:
            click.echo("Migration complete.")
            click.echo(f"Database updated to latest schema.")

    except Exception as e:
        # Rollback on failure
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        
        # Remove backup as it's now identical to DB (no need to keep)
        backup_path.unlink(missing_ok=True)
        
        raise click.ClickException(f"Migration failed: {e}. Database unchanged.")

INSTRUCTIONS_CONTENT = """# mwissues

Personal issue tracker for managing tasks, bugs, and feature requests.

## Commands

- `mwissues init [-d|--default] [-v|--verbose]` - Initialize database and instructions; `--default` restores `mwissues.md` without touching the database; `--verbose` shows migration details
- `mwissues add <title> [-d <description>] [--details <details>] [-p <priority>]` - Add new issue
- `mwissues list [--json|--human] [--all]` - List issues (use `--all` to include hidden)
- `mwissues show <id>` - Show issue details
- `mwissues hide <id>` - Hide an issue from the default list
- `mwissues unhide <id>` - Make a hidden issue visible again
- `mwissues delete <id>` - Permanently delete an issue
- `mwissues add-tags <id> <tag>...` - Add tags to an issue
- `mwissues remove-tags <id> <tag>...` - Remove tags from an issue
- `mwissues rename-tags <old> <new>` - Rename a tag across all issues
- `mwissues add-todo <id> <text>` - Add a todo to an issue
- `mwissues check-todo <id> <index>` - Mark a todo as done
- `mwissues uncheck-todo <id> <index>` - Mark a todo as not done
- `mwissues remove-todo <id> <index>` - Remove a todo
- `mwissues edit-todo <id> <index> <text>` - Edit todo text

## Web Interface

- `mwissues web start [--port <port>] [--no-browser]` - Start the web interface (Ctrl+C to stop)

## Status and Visibility

- **Status**: `open` (default) or `closed` - workflow state (mark as done/resolved)
- **Visibility**: `visible` (default) or `hidden` - controls whether issue appears in default list

## Tag Notes

- Tags are case-sensitive, unique per issue, and similar to username in term of rules. example tags: auth, bug, upload-image
- Use multiple tags in one command for batch operations.
- `add-tags` skips tags that already exist on the issue.
- `rename-tags` updates every occurrence of the old tag.

## Examples

```bash
# Initialize
mwissues init

# Add an issue
mwissues add "Fix login bug" -d "Users cannot log in with special chars" --details "Steps to reproduce:\n1. Go to /login\n2. Enter credentials" -p A

# List issues
mwissues list
mwissues list --human
mwissues list --all  # includes hidden issues

# Show details
mwissues show 1

# Hide/Unhide
mwissues hide 1
mwissues unhide 1

# Delete
mwissues delete 1

# Tag management
mwissues add-tags 1 auth bug
mwissues add-tags 1 frontend
mwissues remove-tags 1 bug
mwissues rename-tags auth login
mwissues remove-tags 1 auth login

# Todo management
mwissues add-todo 1 "Write unit tests"
mwissues check-todo 1 1
mwissues edit-todo 1 1 "Write comprehensive tests"
mwissues remove-todo 1 1

# Web interface
mwissues web start
```
"""


def get_db_connection():
    """Get database connection."""
    db_path = Path.cwd() / DB_NAME
    if not db_path.exists():
        raise click.ClickException(f"Database not found. Run 'mwissues init' first.")
    return sqlite3.connect(db_path)


@click.group()
def cli():
    """mwissues - Personal issue tracker."""
    pass


@cli.command()
@click.option("-d", "--default", is_flag=True, help="Restore mwissues.md without touching the database")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed migration progress")
def init(default, verbose):
    """Initialize database and instructions."""
    db_path = Path.cwd() / DB_NAME
    instructions_path = Path.cwd() / INSTRUCTIONS_NAME

    if db_path.exists() and not default:
        # Run migration if needed
        _migrate_db(db_path, verbose=verbose)
        click.echo(f"{DB_NAME} already exists (migration complete)")
        instructions_path.write_text(INSTRUCTIONS_CONTENT)
        click.echo(f"Updated {INSTRUCTIONS_NAME}")
        return

    if not db_path.exists():
        conn = sqlite3.connect(db_path)
        conn.executescript(SCHEMA)
        conn.close()
        click.echo(f"Initialized {DB_NAME}")

    instructions_path.write_text(INSTRUCTIONS_CONTENT)
    if default:
        click.echo(f"Restored {INSTRUCTIONS_NAME}")
        return
    click.echo(f"Created {INSTRUCTIONS_NAME}")


@cli.command()
@click.argument("title")
@click.option("--priority", required=True, type=click.Choice(["A", "B", "C", "D", "E"]), help="Priority level")
@click.option("--description", required=True, help="Issue description")
@click.option("--details", default="", help="Additional details")
def add(title, priority, description, details):
    """Add a new issue."""
    conn = sqlite3.connect(Path.cwd() / DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO issues (title, description, details, priority) VALUES (?, ?, ?, ?)",
        (title, description, details, priority),
    )
    issue_id = cursor.lastrowid
    conn.commit()
    conn.close()
    click.echo(f"Issue #{issue_id} created: [{priority}] {title}")


def _hide_issue(issue_id):
    """Internal function to hide an issue. Used by archive command."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, visibility FROM issues WHERE id = ?", (issue_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise click.ClickException(f"Issue #{issue_id} not found")
    cursor.execute("UPDATE issues SET visibility = 'hidden' WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()
    click.echo(f"Issue #{issue_id} hidden")


@cli.command()
@click.argument("issue_id", type=int)
def hide(issue_id):
    """Hide an issue from the default list."""
    _hide_issue(issue_id)


@cli.command()
@click.argument("issue_id", type=int)
def unhide(issue_id):
    """Unhide an issue (make it visible again)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM issues WHERE id = ?", (issue_id,))
    if cursor.fetchone() is None:
        conn.close()
        click.echo(f"Issue #{issue_id} not found")
        return
    cursor.execute("UPDATE issues SET visibility = 'visible' WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()
    click.echo(f"Issue #{issue_id} unhidden")


@cli.command()
@click.argument("issue_id", type=int)
def archive(issue_id):
    """Archive an issue (deprecated: use 'hide' instead)."""
    click.echo("Warning: 'archive' is deprecated. Use 'hide' instead.", err=True)
    _hide_issue(issue_id)


@cli.command()
@click.argument("issue_id", type=int)
@click.option("--title", help="Issue title")
@click.option("--description", help="Issue description")
@click.option("--details", help="Additional details")
@click.option("--priority", type=click.Choice(["A", "B", "C", "D", "E"]), help="Priority level")
def edit(issue_id, title, description, details, priority):
    """Edit an issue."""
    _verify_issue_exists(issue_id)
    if not any([title, description, details, priority]):
        raise click.ClickException("No update fields provided")

    fields = []
    values = []
    if title:
        fields.append("title = ?")
        values.append(title)
    if description is not None:
        fields.append("description = ?")
        values.append(description)
    if details is not None:
        fields.append("details = ?")
        values.append(details)
    if priority:
        fields.append("priority = ?")
        values.append(priority)
    values.append(issue_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE issues SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()

    updated_fields = []
    if title:
        updated_fields.append("title")
    if description is not None:
        updated_fields.append("description")
    if details is not None:
        updated_fields.append("details")
    if priority:
        updated_fields.append("priority")
    click.echo(f"Updated: issue #{issue_id} {', '.join(updated_fields)}")


@cli.command()
@click.argument("issue_id", type=int)
def delete(issue_id):
    """Permanently delete an issue."""
    _verify_issue_exists(issue_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()
    click.echo(f"Issue #{issue_id} deleted")


@cli.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--human", "output_human", is_flag=True, help="Human-readable table output")
@click.option("--all", "show_hidden", is_flag=True, help="Include hidden issues")
def list(output_json, output_human, show_hidden):
    """List all visible issues (use --all to include hidden)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        visibility_clause = "" if show_hidden else "WHERE visibility = 'visible' "

        cursor.execute(f"""
            SELECT id, title, description, priority, status, visibility, created_at
            FROM issues
            {visibility_clause}
            ORDER BY priority, created_at DESC
        """)

        issues = []
        for row in cursor.fetchall():
            issue_id, title, description, priority, status, visibility, created_at = row

            cursor.execute("SELECT COUNT(*), SUM(done) FROM todos WHERE issue_id = ?", (issue_id,))
            todo_total, todo_done = cursor.fetchone() or (0, 0)

            cursor.execute("SELECT name FROM tags WHERE issue_id = ?", (issue_id,))
            tags = [t[0] for t in cursor.fetchall()]

            cursor.execute("SELECT id, text, done FROM todos WHERE issue_id = ? ORDER BY id", (issue_id,))
            todos = [{"id": row[0], "text": row[1], "done": bool(row[2])} for row in cursor.fetchall()]

            issues.append({
                "id": issue_id,
                "title": title,
                "description": description or "",
                "priority": priority,
                "status": status,
                "visibility": visibility,
                "tags": tags,
                "todos_total": todo_total or 0,
                "todos_done": todo_done or 0,
                "todos": todos,
                "created_at": created_at
            })

        conn.close()

        if output_json:
            click.echo(json.dumps({"issues": issues}, indent=2))
        elif output_human:
            if not issues:
                click.echo("No issues found.")
                return
            click.echo(f"{'ID':<4} {'Priority':<10} {'Status':<8} {'Visibility':<10} {'Title':<35} {'Tags':<15} {'Todos'}")
            click.echo("-" * 100)
            for issue in issues:
                tags_str = ",".join(issue["tags"]) if issue["tags"] else ""
                todos_str = f"{issue['todos_done']}/{issue['todos_total']}"
                visibility_indicator = "[H]" if issue['visibility'] == 'hidden' else ""
                click.echo(f"{issue['id']:<4} {issue['priority']:<10} {issue['status']:<8} {issue['visibility']:<10} {issue['title'][:33]:<35} {tags_str:<15} {todos_str} {visibility_indicator}")
        else:
            if not issues:
                click.echo("No issues found.")
                return
            click.echo(f"# Issues ({len(issues)} total)\n")
            for issue in issues:
                click.echo(f"## Issue #{issue['id']}: {issue['title']}\n")
                click.echo(f"- **Priority:** {issue['priority']}")
                click.echo(f"- **Status:** {issue['status']}")
                click.echo(f"- **Created:** {issue['created_at']}")
                if issue['description']:
                    click.echo(f"- **Description:** {issue['description']}")
                tags_str = ", ".join(issue["tags"]) if issue["tags"] else ""
                if tags_str:
                    click.echo(f"- **Tags:** {tags_str}")
                todo_parts = []
                for todo in issue.get("todos", []):
                    done = "x" if todo["done"] else " "
                    todo_parts.append(f"- [{done}] {todo['text']}")
                if todo_parts:
                    click.echo("- **Todos:**")
                    for part in todo_parts:
                        click.echo(part)
                click.echo("")
                click.echo("---")
                click.echo("")

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@cli.command()
@click.argument("issue_id", type=int)
def show(issue_id):
    """Show issue details."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, description, details, priority, status, visibility, created_at
        FROM issues
        WHERE id = ?
    """, (issue_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        click.echo(f"Issue #{issue_id} not found")
        return

    issue_id, title, description, details, priority, status, visibility, created_at = row

    cursor.execute("SELECT name FROM tags WHERE issue_id = ?", (issue_id,))
    tags = [t[0] for t in cursor.fetchall()]

    cursor.execute("SELECT id, text, done FROM todos WHERE issue_id = ? ORDER BY id", (issue_id,))
    todos = cursor.fetchall()
    conn.close()

    click.echo(f"# Issue #{issue_id}: {title}\n")
    click.echo(f"- **ID:** {issue_id}")
    click.echo(f"- **Priority:** {priority}")
    click.echo(f"- **Status:** {status}")
    click.echo(f"- **Visibility:** {visibility}")
    click.echo(f"- **Created:** {created_at}")
    if description:
        click.echo(f"- **Description:** {description}")
    if details:
        click.echo(f"- **Details:** {details}")
    tag_text = ", ".join(tags) if tags else "None"
    click.echo(f"- **Tags:** {tag_text}")
    if todos:
        click.echo("- **Todos:**")
        for todo in todos:
            done = "x" if todo[2] else " "
            click.echo(f"- [{done}] {todo[0]}. {todo[1]}")
    else:
        click.echo("- **Todos:** None")
    click.echo("")
    click.echo("---")
    click.echo("")


def _verify_issue_exists(issue_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM issues WHERE id = ?", (issue_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise click.ClickException(f"Issue #{issue_id} not found")
    conn.close()


@cli.command()
@click.argument("issue_id", type=int)
@click.argument("tags", nargs=-1, required=True)
def add_tags(issue_id, tags):
    """Add tags to an issue."""
    _verify_issue_exists(issue_id)

    conn = get_db_connection()
    cursor = conn.cursor()

    for tag in tags:
        cursor.execute("SELECT id FROM tags WHERE issue_id = ? AND name = ?", (issue_id, tag))
        if cursor.fetchone():
            click.echo(f"Skipped: '{tag}' already exists on issue #{issue_id}")
            continue

        cursor.execute("INSERT INTO tags (issue_id, name) VALUES (?, ?)", (issue_id, tag))
        click.echo(f"Added: {tag}")

    conn.commit()
    conn.close()


@cli.command()
@click.argument("issue_id", type=int)
@click.argument("tags", nargs=-1, required=True)
def remove_tags(issue_id, tags):
    """Remove tags from an issue."""
    _verify_issue_exists(issue_id)

    conn = get_db_connection()
    cursor = conn.cursor()

    for tag in tags:
        cursor.execute("SELECT id FROM tags WHERE issue_id = ? AND name = ?", (issue_id, tag))
        row = cursor.fetchone()
        if row is None:
            click.echo(f"Not found: '{tag}' not on issue #{issue_id}")
            continue

        cursor.execute("DELETE FROM tags WHERE id = ?", (row[0],))
        click.echo(f"Removed: {tag}")

    conn.commit()
    conn.close()


@cli.command()
@click.argument("old_tag")
@click.argument("new_tag")
def rename_tags(old_tag, new_tag):
    """Rename a tag globally across all issues."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE tags SET name = ? WHERE name = ?", (new_tag, old_tag))
    count = cursor.rowcount

    conn.commit()
    conn.close()

    click.echo(f"Renamed '{old_tag}' → '{new_tag}' ({count} issues affected)")


@cli.command()
@click.argument("issue_id", type=int)
@click.argument("text")
def add_todo(issue_id, text):
    """Add a todo to an issue."""
    _verify_issue_exists(issue_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO todos (issue_id, text, done) VALUES (?, ?, 0)", (issue_id, text))
    index = cursor.lastrowid
    conn.commit()
    conn.close()

    click.echo(f"Todo added to issue #{issue_id}: {index}. {text}")


@cli.command()
@click.argument("issue_id", type=int)
@click.argument("index", type=int)
def check_todo(issue_id, index):
    """Mark a todo as done."""
    _verify_issue_exists(issue_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, text, done FROM todos WHERE issue_id = ? ORDER BY id LIMIT 1 OFFSET ?", (issue_id, index - 1))
    todo = cursor.fetchone()

    if todo is None:
        conn.close()
        raise click.ClickException(f"Failed: Todo #{index} not found")

    todo_id, text, done = todo
    if done:
        conn.close()
        raise click.ClickException(f"Failed: Todo #{index} is already checked")

    cursor.execute("UPDATE todos SET done = 1 WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()

    click.echo(f'Todo #{index} checked: "{text}"')


@cli.command()
@click.argument("issue_id", type=int)
@click.argument("index", type=int)
def uncheck_todo(issue_id, index):
    """Mark a todo as not done."""
    _verify_issue_exists(issue_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, text, done FROM todos WHERE issue_id = ? ORDER BY id LIMIT 1 OFFSET ?", (issue_id, index - 1))
    todo = cursor.fetchone()

    if todo is None:
        conn.close()
        raise click.ClickException(f"Failed: Todo #{index} not found")

    todo_id, text, done = todo
    if not done:
        conn.close()
        raise click.ClickException(f"Failed: Todo #{index} is already unchecked")

    cursor.execute("UPDATE todos SET done = 0 WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()

    click.echo(f'Todo #{index} unchecked: "{text}"')


@cli.command()
@click.argument("issue_id", type=int)
@click.argument("index", type=int)
def remove_todo(issue_id, index):
    """Remove a todo."""
    _verify_issue_exists(issue_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, text FROM todos WHERE issue_id = ? ORDER BY id LIMIT 1 OFFSET ?", (issue_id, index - 1))
    todo = cursor.fetchone()

    if todo is None:
        conn.close()
        raise click.ClickException(f"Failed: Todo #{index} not found")

    todo_id, text = todo
    cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()

    click.echo(f'Todo #{index} removed: "{text}"')


@cli.command()
@click.argument("issue_id", type=int)
@click.argument("index", type=int)
@click.argument("text")
def edit_todo(issue_id, index, text):
    """Edit todo text."""
    _verify_issue_exists(issue_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM todos WHERE issue_id = ? ORDER BY id LIMIT 1 OFFSET ?", (issue_id, index - 1))
    todo = cursor.fetchone()

    if todo is None:
        conn.close()
        raise click.ClickException(f"Failed: Todo #{index} not found")

    todo_id = todo[0]
    cursor.execute("UPDATE todos SET text = ? WHERE id = ?", (text, todo_id))
    conn.commit()
    conn.close()

    click.echo(f'Todo #{index} updated: "{text}"')


@cli.group()
def web():
    """Manage the local web server."""


@web.command()
@click.option("--port", default=5173, show_default=True, type=int, help="Port to listen on")
@click.option("--no-browser", is_flag=True, help="Do not open a browser window")
def start(port, no_browser):
    """Start the web interface."""
    from pathlib import Path
    import sys

    # Add project root to path so webapp can be imported
    _root = Path(__file__).resolve().parent.parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    from webapp import app

    if not no_browser:
        try:
            import webbrowser
            webbrowser.open(f"http://127.0.0.1:{port}")
        except Exception:
            pass

    click.echo(f"Web running on http://127.0.0.1:{port} — press Ctrl+C to stop")
    app.run(host="127.0.0.1", port=port)


if __name__ == "__main__":
    cli()
