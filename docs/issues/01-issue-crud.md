# 01-issue-crud

## Parent

- `docs/prd-mwissues-cli.md`

## What to build

Core issue management: add, show, list, archive, delete.

## Commands

### `mwissues add <title> --priority A-E [--description "..."] [--details "..."]`

Create new issue. **Priority is required** (no prompts). Description is required, details is optional.

```bash
$ mwissues add "Fix login bug" --priority A --description "Users can't log in after recent deployment" --details "Steps to reproduce:
1. Go to /login
2. Enter credentials
3. Click login
Expected: Redirect to dashboard
Actual: Error 500"
Issue #1 created: [A] Fix login bug

$ mwissues add "Update docs" --priority B --description "API docs need updating"
Issue #2 created: [B] Update docs
```

### `mwissues show <id>`

Show full details of a single issue. LLM uses this to get complete context.

```bash
$ mwissues show 1
# Issue #1: Fix login bug

**Priority:** A
**Status:** active
**Created:** 2026-06-12 10:30:00

**Description:** Users can't log in after recent deployment

**Details:**
- Steps to reproduce:
  1. Go to /login
  2. Enter credentials
  3. Click login
- Expected: Redirect to dashboard
- Actual: Error 500

**Tags:** auth, urgent

**Todos:**
- [x] 1. Identify the bug
- [ ] 2. Write failing test
- [ ] 3. Fix the bug
- [ ] 4. Run tests
```

### `mwissues list [--status active|inactive|all] [page]`

List all issues (active and inactive). Default 10/page, sorted by priority then created_at.

**Default markdown output:**
```bash
$ mwissues list
| ID | Priority | Status    | Title          | Description    | Tags | Todos |
|----|----------|-----------|----------------|-----------------|------|-------|
| 1  | A        | active    | Fix login bug  | Users can't...  | auth | 0/4   |
| 2  | B        | inactive  | Update docs    | API docs need...|      | 0/0   |

Page 1 of 1 (2 issues)
```

**JSON output:**
```bash
$ mwissues list --json
{
  "page": 1,
  "total_pages": 1,
  "total_issues": 2,
  "issues": [
    {"id": 1, "priority": "A", "status": "active", "title": "Fix login bug", "description": "Users can't...", "tags": ["auth"], "todos_done": 0, "todos_total": 4},
    {"id": 2, "priority": "B", "status": "inactive", "title": "Update docs", "description": "API docs need...", "tags": [], "todos_done": 0, "todos_total": 0}
  ]
}
```

**Filter by status:**
```bash
$ mwissues list --status active    # only active issues
$ mwissues list --status inactive  # only inactive issues
$ mwissues list --status all       # same as default
```

### `mwissues archive <id>`

Mark an issue as inactive. LLM manually archives when work is done.

```bash
$ mwissues archive 1
Issue #1 archived
```

### `mwissues edit <id> [--title "..."] [--description "..."] [--details "..."] [--priority A-E]`

Edit issue fields. At least one field is required.

```bash
$ mwissues edit 1 --description "Updated: root cause found"
Updated: issue #1 description

$ mwissues edit 1 --details "New steps:
1. Clear cache
2. Retry login"
Updated: issue #1 details

$ mwissues edit 1 --priority A --title "Fix critical login bug"
Updated: issue #1 title, priority
```

### `mwissues delete <id>`

Permanently delete an issue and all associated todos/tags.

```bash
$ mwissues delete 2
Issue #2 deleted
```

## Priority levels

| Level | Label | Meaning |
|-------|-------|---------|
| A | Must Do | High consequence if not done |
| B | Should Do | Important, but no major consequences if delayed |
| C | Nice to Do | Extra feature if time allows |
| D | Think about | Requires deliberation |
| E | Eliminate | Unnecessary, no added value |

## Issue status

| Status | Meaning |
|--------|---------|
| active | Needs attention |
| inactive | No longer needs attention (archived) |

## Implementation

```python
def cmd_add(title: str, priority: str, description: str = None, details: str = None):
    db.execute(
        "INSERT INTO issues (title, description, details, priority, status) VALUES (?, ?, ?, ?, 'active')",
        (title, description, details, priority)
    )
    issue_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    print(f"Issue #{issue_id} created: [{priority}] {title}")

def cmd_show(issue_id: int):
    issue = db.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
    if not issue:
        print(f"Issue #{issue_id} not found")
        return
    
    tags = db.execute("SELECT name FROM tags WHERE issue_id = ?", (issue_id,)).fetchall()
    todos = db.execute("SELECT id, text, done FROM todos WHERE issue_id = ?", (issue_id,)).fetchall()
    
    # render markdown output (or JSON if --json flag)

def cmd_list(page: int = 1, page_size: int = 10, status: str = 'all', json: bool = False):
    offset = (page - 1) * page_size
    
    where_clause = ""
    params = []
    if status == 'active':
        where_clause = "WHERE i.status = 'active'"
    elif status == 'inactive':
        where_clause = "WHERE i.status = 'inactive'"
    
    issues = db.execute(f"""
        SELECT i.*,
               GROUP_CONCAT(t.name) as tags,
               SUM(t2.done) as done_count,
               COUNT(t2.id) as total_todos
        FROM issues i
        LEFT JOIN tags t ON t.issue_id = i.id
        LEFT JOIN todos t2 ON t2.issue_id = i.id
        {where_clause}
        GROUP BY i.id
        ORDER BY i.priority, i.created_at
        LIMIT ? OFFSET ?
    """, (*params, page_size, offset)).fetchall()
    
    # render markdown or JSON based on json flag

def cmd_archive(issue_id: int):
    db.execute("UPDATE issues SET status = 'inactive' WHERE id = ?", (issue_id,))
    print(f"Issue #{issue_id} archived")

def cmd_edit(issue_id: int, **fields):
    if not fields:
        print("Error: at least one field required")
        return
    
    set_clauses = []
    params = []
    for field in ['title', 'description', 'details', 'priority']:
        if field in fields and fields[field] is not None:
            set_clauses.append(f"{field} = ?")
            params.append(fields[field])
    
    if not set_clauses:
        print("Error: at least one field required")
        return
    
    params.append(issue_id)
    db.execute(f"UPDATE issues SET {', '.join(set_clauses)} WHERE id = ?", params)
    
    updated = ', '.join(fields.keys())
    print(f"Updated: issue #{issue_id} {updated}")

def cmd_delete(issue_id: int):
    db.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
    print(f"Issue #{issue_id} deleted")
```

## Acceptance criteria

- [ ] `mwissues add "Fix login bug" --priority A --description "..."` creates issue with all fields
- [ ] `mwissues add "foo"` without --priority or --description shows error
- [ ] `mwissues show 1` shows title, description, details, tags, todos
- [ ] `mwissues list` shows description column
- [ ] `mwissues edit 1 --description "..."` updates description
- [ ] `mwissues edit 1 --details "..."` updates details
- [ ] `mwissues edit 1 --priority B --title "..."` updates multiple fields
- [ ] `mwissues archive 1` marks issue as inactive
- [ ] `mwissues delete 2` removes issue permanently
- [ ] Invalid ID shows "Issue #X not found"

## Blocked by

- #00-mwissues-init
