# 00-mwissues-init
 done
## Parent

- `docs/prd-mwissues-cli.md`

## What to build

Initialize the `mwissues` CLI tool. Creates:
1. `mwissues.md` — instructions file that LLM agents read to understand how to interact with the tool
2. SQLite database `mwissues.db` — with schema for issues, todos, and tags

## How to do it

### 1. Create `mwissues.md` instructions file

Markdown file explaining the tool to LLM agents. Include:
- Overview of what mwissues is
- Available commands and their syntax
- Priority meanings (A-E)
- Examples of common operations

### 2. Create SQLite database

```sql
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

CREATE INDEX idx_todos_issue_id ON todos(issue_id);
CREATE INDEX idx_tags_issue_id ON tags(issue_id);
CREATE INDEX idx_tags_name ON tags(name);
```

### 3. Create CLI entry point

`mwissues` script that:
- Detects if DB exists; if not, runs init
- Parses command-line arguments using argparse
- Dispatches to appropriate handler
- Shows help when run with no args or `--help`

### 4. `mwissues init` subcommand

Runs init manually. Idempotent (safe to run twice).

## Output formats

All list/query commands support two output modes:

**Markdown (default, LLM-optimized):**
```bash
$ mwissues list
| ID | Priority | Status | Title | Description | Tags | Todos |
|----|----------|--------|-------|-------------|------|-------|
| 1  | A        | active | Fix... | Users...    | auth | 0/4   |
| 2  | B        | active | Update | API docs... |      | 0/0   |
```

**JSON (`--json` flag):**
```bash
$ mwissues list --json
{
  "page": 1,
  "total_pages": 1,
  "total_issues": 2,
  "issues": [
    {"id": 1, "priority": "A", "title": "Fix login bug", "tags": ["auth"], "todos_done": 0, "todos_total": 0},
    {"id": 2, "priority": "B", "title": "Update docs", "tags": [], "todos_done": 0, "todos_total": 0}
  ]
}
```

`--human` flag shows pretty-printed tables with colors (human-only).

## Acceptance criteria

- [ ] `mwissues.md` exists and contains complete command documentation
- [ ] `mwissues.db` SQLite database created with correct schema
- [ ] Running `mwissues` with no args shows help
- [ ] Running `mwissues init` is idempotent
- [ ] Default output is markdown format
- [ ] `--json` flag outputs valid JSON
- [ ] `--human` flag outputs pretty table

## Examples

```bash
# Initialize (first time)
$ mwissues init
Initialized mwissues database at ./mwissues.db
Created mwissues.md instructions

# Initialize again (idempotent)
$ mwissues init
mwissues is already initialized

# Run with no args
$ mwissues
mwissues - Personal issue tracker

Usage: mwissues <command> [options]

Commands:
  init              Initialize database and instructions
  add <title>       Add new issue
  show <id>         Show issue details
  list [page]       List all issues
  archive <id>      Archive an issue
  delete <id>       Permanently delete an issue
  ...

# Help for init
$ mwissues init --help
Usage: mwissues init

Initialize the mwissues database and create mwissues.md instructions.
```

## Blocked by

None - can start immediately
