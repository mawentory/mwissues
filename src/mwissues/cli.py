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
            click.echo("| ID | Priority | Status | Title | Description | Tags | Todos |")
            click.echo("|----|----------|--------|-------|-------------|------|-------|")
            for issue in issues:
                tags_str = ",".join(issue["tags"]) if issue["tags"] else ""
                todos_str = f"{issue['todos_done']}/{issue['todos_total']}"
                desc = (issue["description"][:44] + "...") if len(issue["description"]) > 47 else issue["description"]
                click.echo(f"| {issue['id']} | {issue['priority']} | {issue['status']} | {issue['title'][:20]} | {desc[:45]} | {tags_str} | {todos_str} |")
    
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


if __name__ == "__main__":
    cli()
