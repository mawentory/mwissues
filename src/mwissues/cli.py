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

## Quick Start

```bash
mwissues init                    # Initialize database
mwissues add "Title" -d "Desc" -p A   # Add issue (priority A-E required)
mwissues list                    # Show all visible issues
mwissues show 1                  # Show issue #1 details
```

## Issue Structure

Every issue has:
- **title** (required) — What needs to be done
- **description** (required) — Brief summary for list view
- **details** (optional) — Extended info, steps to reproduce, etc.
- **priority** (required) — A, B, C, D, or E
- **status** — `open` (default) or `closed`
- **visibility** — `visible` (default) or `hidden`
- **tags** — Optional labels (e.g., `bug`, `auth`, `frontend`)
- **todos** — Optional checklist items with check/uncheck

## Priority System

| Priority | Label | When to Use |
|----------|-------|-------------|
| A | Must Do | High consequence if not done. Blockers, critical bugs |
| B | Should Do | Important but no major consequences if delayed |
| C | Nice to Do | Extra features if time allows |
| D | Think about | Tasks requiring review and deliberation |
| E | Eliminate | Unnecessary tasks, remove if possible |

## Commands

### Issue Management

```bash
# Add issue (ALL fields are space-separated after flags)
mwissues add "Fix login bug" -d "Users cannot log in" -p A
mwissues add "Add dark mode" -d "Support dark theme" -p B --details "Consider CSS variables"

# List issues
mwissues list                    # Markdown output (default, LLM-friendly)
mwissues list --human           # Pretty table (human readers)
mwissues list --json            # JSON output
mwissues list --all             # Include hidden issues

# Show issue details
mwissues show 1

# Edit issue
mwissues edit 1 --title "New title"
mwissues edit 1 --description "New desc"
mwissues edit 1 --priority C
mwissues edit 1 --details "New details"
mwissues edit 1 --title "X" --description "Y" --priority A  # Multiple fields

# Hide/Unhide (not deleted, just invisible in default list)
mwissues hide 1
mwissues unhide 1

# Delete permanently
mwissues delete 1

# Close an issue (mark as done)
mwissues edit 1 --status closed
```

### Tag Management

```bash
# Add tags (multiple at once)
mwissues add-tags 1 bug auth

# Remove tags
mwissues remove-tags 1 bug

# Rename tag globally (updates ALL issues with this tag)
mwissues rename-tags auth login
```

**Tag Rules:**
- Case-sensitive: `Bug` ≠ `bug`
- Unique per issue: adding `bug` twice only adds it once
- Format: lowercase, hyphens allowed (e.g., `upload-image`)

### Todo Management

```bash
# Add todo
mwissues add-todo 1 "Write failing test"

# Todos are 1-indexed (first todo = index 1)
mwissues check-todo 1 1      # Mark done
mwissues uncheck-todo 1 1     # Mark not done
mwissues edit-todo 1 1 "Updated text"
mwissues remove-todo 1 1
```

### Import from JSON (Primary Method)

JSON import is the recommended way to add issues with todos.

```bash
# From file
mwissues import-issues issues.json

# From stdin
cat issues.json | mwissues import-issues
```

**JSON Format:**
```json
[
  {
    "title": "Issue title",
    "description": "Brief description",
    "details": "Extended details",
    "priority": "A",
    "tags": ["bug", "auth"],
    "todos": [
      {"text": "Step 1", "done": false},
      {"text": "Step 2", "done": true}
    ]
  }
]
```

Priority defaults to `B` if omitted. All fields except `title` are optional. Validation errors abort entire import (all-or-nothing).

### Web Interface

```bash
mwissues web start [--port 5173]    # Start server
mwissues web start --no-browser     # Don't open browser
```

## Common Patterns

### Reading Issues for LLM Context

```bash
# Get all visible issues in markdown (best for LLM)
mwissues list

# Get specific issue with all details
mwissues show 1

# Get JSON for programmatic access
mwissues list --json
```

### Creating Issues from LLM

```bash
# Basic issue
mwissues add "Fix bug in X" -d "Brief summary" -p A

# With details for complex issues
mwissues add "Fix login bug" -d "Users cannot authenticate" -p A --details "Steps:
1. Go to /login
2. Enter credentials
3. Observe 500 error

Root cause: Null pointer in auth.py line 42"

# Adding tags after creation
mwissues add-tags 1 bug auth
mwissues add-todo 1 "Check logs"
mwissues add-todo 1 "Reproduce issue"
```

### Updating Issues

```bash
# Mark as done
mwissues edit 1 --status closed

# Update priority
mwissues edit 1 --priority A

# Add progress via todos
mwissues add-todo 1 "Research phase"
mwissues check-todo 1 1
```

## Issue Writing Best Practices

### Tracer Bullets (Vertical Slices)

Each issue should be a **vertical slice** that cuts through all layers end-to-end:

- **Good**: "Add JSON import command" — covers CLI, validation, database, tests
- **Bad**: "Add import validation" — only one layer, leaves integration incomplete

A completed slice is demoable or verifiable on its own. Prefer many thin slices over few thick ones.

### AFK vs HITL

Mark each issue with one of these prefixes:

- **AFK** — Can be implemented and merged without human interaction
- **HITL** — Requires human interaction: architectural decisions, design reviews, manual testing

Prefer AFK over HITL where possible. If unsure, ask.

```bash
# AFK issue
mwissues add "Add JSON import" -d "CLI command for batch import" -p B
mwissues add-tags 1 enhancement

# HITL issue
mwissues add "[HITL] Design new dashboard UI" -d "Need design review before implementation" -p B
mwissues add-tags 1 enhancement
```

### Issue Template

For complex work, use this structure in the `details` field:

```bash
mwissues add "Feature name" -d "Brief summary" -p B --details "## What to build

End-to-end behavior description. What does the user experience when this is done?

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by

- Issue #N (if any)

## Notes

Any context, trade-offs, or decisions that inform implementation."
```

### Blocking Relationships

Express dependencies clearly:

```bash
# Issue 5 is blocked by issue 3
mwissues add "Feature X" -d "Blocked until Y is done" -p B --details "## Blocked by

- #3 (must complete first)"
```

When blocking issues are done, update the dependent:

```bash
mwissues edit 5 --details "## Blocked by

- #3 ✓ (done)

## What to build

..."
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


_JSON_EXAMPLE = """
JSON Format Example:

[
  {
    "title": "Issue title",
    "description": "Brief description",
    "details": "Extended details, steps to reproduce, etc.",
    "priority": "A",
    "tags": ["bug", "auth"],
    "todos": [
      {"text": "Step 1", "done": false},
      {"text": "Step 2", "done": true}
    ]
  }
]

Priority defaults to B if omitted. All fields except title are optional.
"""


@cli.command()
@click.argument("source", required=False)
def import_issues(source):
    """Import issues from JSON (file path or stdin).

    Reads a JSON array of issues and inserts them in a single transaction.
    """
    import sys
    import builtins

    # Read JSON from file or stdin
    if source is not None:
        # Read from file path
        file_path = Path(source)
        if not file_path.exists():
            click.echo(f"Error: File not found: {source}")
            click.echo(_JSON_EXAMPLE)
            return
        json_input = file_path.read_text()
    else:
        # Try to read from stdin
        if hasattr(sys.stdin, 'read'):
            json_input = sys.stdin.read()
            if not json_input or json_input.strip() == '':
                click.echo("Error: No input provided. Pass a file path or pipe JSON via stdin.")
                click.echo(_JSON_EXAMPLE)
                return
        else:
            click.echo("Error: Cannot read from stdin.")
            click.echo(_JSON_EXAMPLE)
            return

    # Parse JSON
    try:
        data = json.loads(json_input)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON - {e}")
        click.echo(_JSON_EXAMPLE)
        return

    if not isinstance(data, builtins.list):
        click.echo("Error: JSON must be an array of issues")
        click.echo(_JSON_EXAMPLE)
        return

    if len(data) == 0:
        click.echo("Error: No issues to import (empty array)")
        click.echo(_JSON_EXAMPLE)
        return
    
    # Validate all entries first (before opening transaction)
    VALID_PRIORITIES = ["A", "B", "C", "D", "E"]
    errors = []
    
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"Error at index {idx}: item must be an object")
            continue
        
        # title is required and must be non-empty string
        if "title" not in item:
            errors.append(f"Error at index {idx}: field 'title' is required")
        elif not isinstance(item["title"], str):
            errors.append(f"Error at index {idx}: field 'title' must be a string")
        elif not item["title"].strip():
            errors.append(f"Error at index {idx}: field 'title' cannot be empty")
        
        # priority must be one of A, B, C, D, E if provided
        if "priority" in item:
            if item["priority"] not in VALID_PRIORITIES:
                errors.append(
                    f"Error at index {idx}: field 'priority' must be one of {', '.join(VALID_PRIORITIES)} (got '{item['priority']}')"
                )
        
        # description must be string if provided
        if "description" in item and not isinstance(item["description"], str):
            errors.append(f"Error at index {idx}: field 'description' must be a string")
        
        # details must be string if provided
        if "details" in item and not isinstance(item["details"], str):
            errors.append(f"Error at index {idx}: field 'details' must be a string")
        
        # tags must be array of strings if provided
        if "tags" in item:
            if not isinstance(item["tags"], builtins.list):
                errors.append(f"Error at index {idx}: field 'tags' must be an array")
            else:
                for ti, tag in enumerate(item["tags"]):
                    if not isinstance(tag, str):
                        errors.append(f"Error at index {idx}: field 'tags'[{ti}] must be a string")
        
        # todos must be array of objects with text (string) and done (boolean, optional)
        if "todos" in item:
            if not isinstance(item["todos"], builtins.list):
                errors.append(f"Error at index {idx}: field 'todos' must be an array")
            else:
                for ti, todo in enumerate(item["todos"]):
                    if not isinstance(todo, dict):
                        errors.append(f"Error at index {idx}: field 'todos'[{ti}] must be an object")
                    elif "text" not in todo:
                        errors.append(f"Error at index {idx}: field 'todos'[{ti}] 'text' is required")
                    elif not isinstance(todo["text"], str):
                        errors.append(f"Error at index {idx}: field 'todos'[{ti}] 'text' must be a string")
                    if "done" in todo and type(todo["done"]) is not bool:
                        errors.append(f"Error at index {idx}: field 'todos'[{ti}] 'done' must be a boolean")
    
    if errors:
        for err in errors:
            click.echo(err, err=True)
        click.echo("Validation failed. No issues imported.")
        click.echo(_JSON_EXAMPLE)
        raise SystemExit(1)
    
    # All validations passed — insert all entries in a single transaction
    conn = sqlite3.connect(Path.cwd() / DB_NAME)
    cursor = conn.cursor()
    
    imported_count = 0
    try:
        for item in data:
            title = item["title"]
            description = item.get("description", "")
            details = item.get("details", "")
            priority = item.get("priority", "B")
            tags = item.get("tags", [])
            todos = item.get("todos", [])
            
            cursor.execute(
                "INSERT INTO issues (title, description, details, priority) VALUES (?, ?, ?, ?)",
                (title, description, details, priority),
            )
            issue_id = cursor.lastrowid
            
            # Insert tags
            for tag in tags:
                cursor.execute(
                    "INSERT INTO tags (issue_id, name) VALUES (?, ?)",
                    (issue_id, tag),
                )
            
            # Insert todos
            for todo in todos:
                todo_text = todo["text"]
                todo_done = 1 if todo.get("done", False) else 0
                cursor.execute(
                    "INSERT INTO todos (issue_id, text, done) VALUES (?, ?, ?)",
                    (issue_id, todo_text, todo_done),
                )
            
            imported_count += 1
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise click.ClickException(f"Import failed: {e}. Transaction rolled back.")
    
    conn.close()
    click.echo(f"Imported {imported_count} issues successfully")


@cli.group()
def web():
    """Manage the local web server."""


def _is_port_in_use(port):
    """Check if a port is already in use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _kill_port(port):
    """Kill any process using the specified port."""
    import subprocess
    try:
        # Find PIDs using the port
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                try:
                    subprocess.run(["kill", "-9", pid], check=False)
                except Exception:
                    pass
    except Exception:
        pass


@web.command()
@click.option("--port", default=5173, show_default=True, type=int, help="Port to listen on")
@click.option("--no-browser", is_flag=True, help="Do not open a browser window")
def start(port, no_browser):
    """Start the web interface."""
    if _is_port_in_use(port):
        click.echo(f"Error: Port {port} is already in use.")
        click.echo(f"Use 'mwissues web restart' to stop the existing server and start fresh.")
        return

    from pathlib import Path
    import sys

    _root = Path(__file__).resolve().parent.parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    from mwissues.webapp import app

    if not no_browser:
        try:
            import webbrowser
            webbrowser.open(f"http://127.0.0.1:{port}")
        except Exception:
            pass

    click.echo(f"Web running on http://127.0.0.1:{port} — press Ctrl+C to stop")
    app.run(host="127.0.0.1", port=port)


@web.command()
@click.option("--port", default=5173, show_default=True, type=int, help="Port to listen on")
@click.option("--no-browser", is_flag=True, help="Do not open a browser window")
def restart(port, no_browser):
    """Stop any existing server and start fresh."""
    _kill_port(port)
    click.echo("Starting web server...")

    from pathlib import Path
    import sys

    _root = Path(__file__).resolve().parent.parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    from mwissues.webapp import app

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
