# PRD: mwissues CLI

## Problem Statement

The user needs a lightweight, local command-line issue tracker with structured priority management, todo tracking, tagging, search, and manual archiving. The system must support markdown-based output (default) and JSON output while providing a rich CLI experience with pagination and full-text search.

## Solution

A CLI tool `mwissues` that manages issues stored in a SQLite database. Issues have:
- **Title** (required)
- **Description** (required) - brief summary for list view
- **Details** (optional) - extended information for show view
- **Priority** (required, A-E)
- **Status** (active/inactive)
- **Tags** (optional, multiple)
- **Todos** (optional, multiple with check/uncheck)

## Priority System

| Priority | Label | Meaning |
|----------|-------|---------|
| A | Must Do | High consequence if not done |
| B | Should Do | Important, but no major consequences if delayed |
| C | Nice to Do | Extra feature if time allows |
| D | Think about | Tasks that require deliberation |
| E | Eliminate | Unnecessary tasks that do not add value |

## Issue Status

| Status | Meaning |
|--------|---------|
| active | Needs attention now |
| inactive | Archived, no longer needs attention |

## CLI Commands

### Issue Management

| Command | Description |
|---------|-------------|
| `mwissues add <title> --priority A-E --description "..." [--details "..."]` | Add issue |
| `mwissues show <id>` | Show full issue details |
| `mwissues list [--status active\|inactive\|all] [page]` | List issues |
| `mwissues edit <id> [--title "..."] [--description "..."] [--details "..."] [--priority A-E]` | Edit issue |
| `mwissues archive <id>` | Mark as inactive (manual archive) |
| `mwissues delete <id>` | Permanently delete |
| `mwissues query <text> [--status ...]` | Search by title, description, details, todos, tags |

### Todo Management

| Command | Description |
|---------|-------------|
| `mwissues add-todo <id> <text>` | Add todo |
| `mwissues check-todo <id> <index>` | Mark done (returns success or "Failed") |
| `mwissues uncheck-todo <id> <index>` | Mark not done (returns success or "Failed") |
| `mwissues remove-todo <id> <index>` | Remove todo |
| `mwissues edit-todo <id> <index> <text>` | Edit todo text |

### Tag Management

| Command | Description |
|---------|-------------|
| `mwissues add-tags <id> <tag1> [tag2]...` | Add tags (plural - multiple at once) |
| `mwissues remove-tags <id> <tag1> [tag2]...` | Remove tags (plural) |
| `mwissues rename-tags <old> <new>` | Rename tag globally |

## Output Formats

### Markdown (default, LLM-optimized)

```bash
$ mwissues list
| ID | Priority | Status | Title | Description | Tags | Todos |
|----|----------|--------|-------|-------------|------|-------|
| 1  | A        | active | Fix... | Users...    | auth | 0/4   |
```

### JSON (`--json` flag)

```bash
$ mwissues list --json
{
  "page": 1,
  "total_issues": 2,
  "issues": [...]
}
```

### Human (`--human` flag)

Pretty-printed table with colors (human readers only).

## Data Schema

```sql
issues (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  details TEXT,
  priority TEXT CHECK(priority IN ('A','B','C','D','E')) NOT NULL,
  status TEXT DEFAULT 'active' CHECK(status IN ('active','inactive')),
  created_at TEXT DEFAULT (datetime('now'))
)

todos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id INTEGER REFERENCES issues(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  done INTEGER DEFAULT 0
)

tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id INTEGER REFERENCES issues(id) ON DELETE CASCADE,
  name TEXT NOT NULL
)
```

## Search Behavior

`query <text>` performs case-insensitive substring search across:
- Issue title
- Issue description
- Issue details
- Todo text content
- Tag names

Results show all matching issues (active and inactive) by default.

## Archive Behavior

Manual archive only. No auto-archive. LLM decides when to archive an issue.

```bash
$ mwissues archive 1
Issue #1 archived
```

## Error Handling

- Success: "Added: X", "Removed: Y", "Checked: Z"
- Failure: "Failed: ..."
  - "Failed: Todo #X not found"
  - "Failed: Todo #X is already checked"
  - "Failed: Issue #X not found"

## Out of Scope

- Due dates or time tracking
- Issue relationships (parent/child, blocking)
- Export/import functionality
- Cloud sync or collaboration features

## Implementation Order

1. `00-mwissues-init` - Database, schema, CLI entry point
2. `01-issue-crud` - add, show, list, edit, archive, delete
3. `02-todo-management` - add-todo, check-todo, uncheck-todo, remove-todo, edit-todo
4. `03-tag-management` - add-tags, remove-tags, rename-tags
5. `04-search` - query command
6. `05-help-text` - Complete help system
