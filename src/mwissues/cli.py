"""mwissues CLI - Personal issue tracker."""
import json
import os
from pathlib import Path

import click
import sqlite3


DB_NAME = "mwissues.db"
INSTRUCTIONS_NAME = "mwissues.md"

SCHEMA = """
CREATE TABLE IF NOT EXISTS issues (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  details TEXT,
  priority TEXT CHECK(priority IN ('A','B','C','D','E')) NOT NULL,
  status TEXT DEFAULT 'active' CHECK(status IN ('active','inactive')) NOT NULL,
  created_at TEXT DEFAULT (datetime('now')) NOT NULL
);

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

INSTRUCTIONS_CONTENT = """# mwissues

Personal issue tracker for managing tasks, bugs, and feature requests.

## Commands

- `mwissues init` - Initialize database and instructions
- `mwissues add <title> [-d <description>] [-p <priority>]` - Add new issue
- `mwissues list [--json|--human]` - List all issues
- `mwissues show <id>` - Show issue details
- `mwissues archive <id>` - Archive an issue
- `mwissues delete <id>` - Permanently delete an issue
- `mwissues add-todo <id> <text>` - Add a todo to an issue
- `mwissues check-todo <id> <index>` - Mark a todo as done
- `mwissues uncheck-todo <id> <index>` - Mark a todo as not done
- `mwissues remove-todo <id> <index>` - Remove a todo
- `mwissues edit-todo <id> <index> <text>` - Edit todo text

## Priority Levels

- **A** - Critical, must be addressed immediately
- **B** - High priority
- **C** - Medium priority (default)
- **D** - Low priority
- **E** - Nice to have

## Examples

```bash
# Initialize
mwissues init

# Add an issue
mwissues add "Fix login bug" -d "Users cannot log in with special chars" -p A

# List issues
mwissues list
mwissues list --json

# Show details
mwissues show 1

# Archive/Delete
mwissues archive 1
mwissues delete 1

# Todo management
mwissues add-todo 1 "Write unit tests"
mwissues check-todo 1 1
mwissues edit-todo 1 1 "Write comprehensive tests"
mwissues remove-todo 1 1
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
def init():
    """Initialize database and instructions."""
    db_path = Path.cwd() / DB_NAME
    instructions_path = Path.cwd() / INSTRUCTIONS_NAME
    
    if db_path.exists():
        click.echo(f"{DB_NAME} already exists")
        return
    
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.close()
    
    instructions_path.write_text(INSTRUCTIONS_CONTENT)
    
    click.echo(f"Initialized {DB_NAME}")
    click.echo(f"Created {INSTRUCTIONS_NAME}")


@cli.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--human", "output_human", is_flag=True, help="Human-readable table output")
def list(output_json, output_human):
    """List all issues."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, description, priority, status, created_at
            FROM issues
            WHERE status = 'active'
            ORDER BY priority, created_at DESC
        """)
        
        issues = []
        for row in cursor.fetchall():
            issue_id, title, description, priority, status, created_at = row
            
            cursor.execute("SELECT COUNT(*), SUM(done) FROM todos WHERE issue_id = ?", (issue_id,))
            todo_total, todo_done = cursor.fetchone() or (0, 0)
            
            cursor.execute("SELECT name FROM tags WHERE issue_id = ?", (issue_id,))
            tags = [t[0] for t in cursor.fetchall()]
            
            issues.append({
                "id": issue_id,
                "title": title,
                "description": description or "",
                "priority": priority,
                "status": status,
                "tags": tags,
                "todos_total": todo_total or 0,
                "todos_done": todo_done or 0,
                "created_at": created_at
            })
        
        conn.close()
        
        if output_json:
            click.echo(json.dumps({"issues": issues}, indent=2))
        elif output_human:
            if not issues:
                click.echo("No issues found.")
                return
            click.echo(f"{'ID':<4} {'Priority':<10} {'Status':<8} {'Title':<40} {'Tags':<15} {'Todos'}")
            click.echo("-" * 90)
            for issue in issues:
                tags_str = ",".join(issue["tags"]) if issue["tags"] else ""
                todos_str = f"{issue['todos_done']}/{issue['todos_total']}"
                click.echo(f"{issue['id']:<4} {issue['priority']:<10} {issue['status']:<8} {issue['title'][:38]:<40} {tags_str:<15} {todos_str}")
        else:
            if not issues:
                click.echo("No issues found.")
                return
            click.echo(f"# Issues ({len(issues)} total)\n")
            for issue in issues:
                click.echo(f"## Issue #{issue['id']}: {issue['title']}\n")
                click.echo(f"- **Priority:** {issue['priority']}")
                tags_str = ", ".join(issue["tags"]) if issue["tags"] else ""
                click.echo(f"- **Tags:** {tags_str}")
                click.echo(f"- **Status:** {issue['status']}")
                click.echo(f"- **Created:** {issue['created_at']}")
                if issue['description']:
                    click.echo(f"- **Description:** {issue['description']}")
                tags_str = ", ".join(issue["tags"]) if issue["tags"] else ""
                click.echo(f"- **Tags:** {tags_str}")
                click.echo(f"- **Todos:** {issue['todos_done']}/{issue['todos_total']}")
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
    _verify_issue_exists(issue_id)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, description, details, priority, status, created_at
        FROM issues
        WHERE id = ?
    """, (issue_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise click.ClickException(f"Issue #{issue_id} not found")

    issue_id, title, description, details, priority, status, created_at = row

    cursor.execute("SELECT name FROM tags WHERE issue_id = ?", (issue_id,))
    tags = [t[0] for t in cursor.fetchall()]

    cursor.execute("SELECT id, text, done FROM todos WHERE issue_id = ? ORDER BY id", (issue_id,))
    todos = cursor.fetchall()
    conn.close()

    tag_text = ", ".join(tags) if tags else "None"
    todo_text = ", ".join([f"[{'x' if todo[2] else ' '}] {todo[0]}. {todo[1]}" for todo in todos]) if todos else "None"

    click.echo(f"# Issue #{issue_id}: {title}\n")
    click.echo(f"- **ID:** {issue_id}")
    click.echo(f"- **Priority:** {priority}")
    click.echo(f"- **Status:** {status}")
    click.echo(f"- **Created:** {created_at}")
    if description:
        click.echo(f"- **Description:** {description}")
    if details:
        click.echo(f"- **Details:** {details}")
    click.echo(f"- **Tags:** {tag_text}")
    click.echo(f"- **Todos:** {todo_text}")
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


if __name__ == "__main__":
    cli()
