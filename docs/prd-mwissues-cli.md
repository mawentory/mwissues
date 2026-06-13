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
| `mwissues import-issues [file.json]` | Import issues from JSON (file or stdin) |
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

### Import

| Command | Description |
|---------|-------------|
| `mwissues import-issues [file.json]` | Import issues from JSON file or stdin |

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

**Field rules:**
- `title` — required, non-empty string
- `description` — optional, string
- `details` — optional, string
- `priority` — optional, one of `A/B/C/D/E`, defaults to `B`
- `tags` — optional, array of strings
- `todos` — optional, array of `{text: string, done?: boolean}`

**Behavior:**
- All entries inserted in a single transaction (all-or-nothing)
- Validation errors show index and field, no data is written
- Output: `Imported N issues successfully`

**Examples:**

```bash
# From file
mwissues import-issues issues.json

# From stdin
cat issues.json | mwissues import-issues
```

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

## Issues

### Issue 00: mwissues-init (done)

**Parent:** `docs/prd-mwissues-cli.md`

#### What to build

Initialize the `mwissues` CLI tool. Creates:
1. `mwissues.md` — instructions file that LLM agents read to understand how to interact with the tool
2. SQLite database `mwissues.db` — with schema for issues, todos, and tags

#### How to do it

**1. Create `mwissues.md` instructions file**

Markdown file explaining the tool to LLM agents. Include:
- Overview of what mwissues is
- Available commands and their syntax
- Priority meanings (A-E)
- Examples of common operations

**2. Create SQLite database**

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

**3. Create CLI entry point**

`mwissues` script that:
- Detects if DB exists; if not, runs init
- Parses command-line arguments using argparse
- Dispatches to appropriate handler
- Shows help when run with no args or `--help`

**4. `mwissues init` subcommand**

Runs init manually. Idempotent (safe to run twice).

#### Acceptance criteria

- [x] `mwissues.md` exists and contains complete command documentation
- [x] `mwissues.db` SQLite database created with correct schema
- [x] Running `mwissues` with no args shows help
- [x] Running `mwissues init` is idempotent
- [x] Default output is markdown format
- [x] `--json` flag outputs valid JSON
- [x] `--human` flag outputs pretty table

#### Examples

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

---

### Issue 01: issue-crud

**Parent:** `docs/prd-mwissues-cli.md`

#### What to build

Core issue management: add, show, list, archive, delete.

#### Commands

**`mwissues add <title> --priority A-E [--description "..."] [--details "..."]`**

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

**`mwissues show <id>`**

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

**`mwissues list [--status active|inactive|all] [page]`**

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

**`mwissues archive <id>`**

Mark an issue as inactive. LLM manually archives when work is done.

```bash
$ mwissues archive 1
Issue #1 archived
```

**`mwissues edit <id> [--title "..."] [--description "..."] [--details "..."] [--priority A-E]`**

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

**`mwissues delete <id>`**

Permanently delete an issue and all associated todos/tags.

```bash
$ mwissues delete 2
Issue #2 deleted
```

#### Acceptance criteria

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

#### Blocked by

- #00-mwissues-init

---

### Issue 02: todo-management (done)

**Parent:** `docs/prd-mwissues-cli.md`

#### What to build

Todo CRUD for issues: add, check, uncheck, remove, edit.

#### Commands

**`mwissues add-todo <id> <text>`**

Add a todo to an issue.

```bash
$ mwissues add-todo 1 "Write unit tests"
Todo added to issue #1: 1. Write unit tests

$ mwissues add-todo 1 "Test edge cases"
Todo added to issue #1: 2. Test edge cases

$ mwissues add-todo 1 "Deploy to staging"
Todo added to issue #1: 3. Deploy to staging
```

**`mwissues check-todo <id> <index>`**

Mark a todo as done. 1-based index. Explicit action with clear feedback.

```bash
$ mwissues check-todo 1 1
Todo #1 checked: "Write unit tests"

$ mwissues check-todo 1 2
Todo #2 checked: "Test edge cases"

$ mwissues check-todo 1 3
Todo #3 checked: "Deploy to staging"
```

If todo already checked:
```bash
$ mwissues check-todo 1 1
Failed: Todo #1 is already checked
```

**`mwissues uncheck-todo <id> <index>`**

Mark a todo as not done. 1-based index.

```bash
$ mwissues uncheck-todo 1 1
Todo #1 unchecked: "Write unit tests"
```

If todo already unchecked:
```bash
$ mwissues uncheck-todo 1 1
Failed: Todo #1 is already unchecked
```

**`mwissues remove-todo <id> <index>`**

Remove a todo. 1-based index.

```bash
$ mwissues remove-todo 1 2
Todo #2 removed: "Test edge cases"
```

**`mwissues edit-todo <id> <index> <text>`**

Edit todo text. 1-based index.

```bash
$ mwissues edit-todo 1 1 "Write comprehensive unit tests with mocks"
Todo #1 updated: "Write comprehensive unit tests with mocks"
```

#### Acceptance criteria

- [x] `mwissues add-todo 1 "Write tests"` adds todo with confirmation
- [x] `mwissues check-todo 1 1` marks todo done with success message
- [x] `mwissues check-todo 1 1` on already-checked todo shows "Failed" message
- [x] `mwissues uncheck-todo 1 1` marks todo not done with success message
- [x] `mwissues uncheck-todo 1 1` on already-unchecked todo shows "Failed" message
- [x] `mwissues remove-todo 1 2` deletes todo with confirmation
- [x] `mwissues edit-todo 1 1 "New text"` updates todo text
- [x] Invalid todo index shows "Failed: Todo #X not found"
- [x] Todo on non-existent issue shows "Failed: Issue #X not found"

#### Blocked by

- #00-mwissues-init

---

### Issue 03: tag-management

**Parent:** `docs/prd-mwissues-cli.md`

#### What to build

Tag management for issues: add-tags, remove-tags, rename-tags.

#### Commands

**`mwissues add-tags <id> <tag1> [tag2] ...`**

Add one or more tags to an issue. Plural command - LLM can add multiple at once.

```bash
$ mwissues add-tags 1 urgent
Added: urgent

$ mwissues add-tags 1 auth bug
Added: auth
Added: bug

$ mwissues add-tags 1 urgent  # already exists
Skipped: 'urgent' already exists on issue #1
```

**`mwissues remove-tags <id> <tag1> [tag2] ...`**

Remove one or more tags from an issue. Reports which were not found.

```bash
$ mwissues remove-tags 1 bug
Removed: bug

$ mwissues remove-tags 1 nonexistent1 nonexistent2
Not found: 'nonexistent1' not on issue #1
Not found: 'nonexistent2' not on issue #1
```

**`mwissues rename-tags <old-tag> <new-tag>`**

Rename a tag globally across all issues.

```bash
$ mwissues rename-tags bug defect
Renamed 'bug' → 'defect' (2 issues affected)
```

#### Tag display in show/list

Tags appear in `mwissues show` and `mwissues list` output:

```bash
$ mwissues show 1
# Issue #1: Fix login bug

**Tags:** auth, urgent
...

$ mwissues list
| ID | Priority | Status | Title          | Tags     | Todos |
|----|----------|--------|----------------|----------|-------|
| 1  | A        | active | Fix login bug  | auth, urgent | 0/4   |
```

#### Acceptance criteria

- [ ] `mwissues add-tags 1 urgent` adds single tag
- [ ] `mwissues add-tags 1 urgent auth bug` adds multiple tags
- [ ] `mwissues add-tags 1 urgent` on existing tag shows "Skipped" message
- [ ] `mwissues remove-tags 1 bug` removes tag
- [ ] `mwissues remove-tags 1 nonexistent` shows "Not found" message
- [ ] `mwissues rename-tags bug defect` renames globally
- [ ] Tags appear in `mwissues show` and `mwissues list` output
- [ ] Tag on non-existent issue shows "Failed: Issue #X not found"

#### Blocked by

- #00-mwissues-init

---

### Issue 04: search

**Parent:** `docs/prd-mwissues-cli.md`

#### What to build

Full-text search across issues: title, todo text, and tags.

#### Command

**`mwissues query <text> [--status active|inactive|all] [page]`**

Case-insensitive substring search across:
1. Issue title
2. Issue description
3. Issue details
4. Todo text content
5. Tag names

Searches all issues by default (active and inactive).

**Markdown output (default):**
```bash
$ mwissues query "login"
| ID | Priority | Status | Title              | Description        | Tags | Todos |
|----|----------|--------|-------------------|---------------------|------|-------|
| 1  | A        | active | Fix login bug     | Users can't...      | auth | 0/4   |
| 3  | B        | active | Add login timeout | Timeout after...    | auth | 1/2   |

Page 1 of 1 (2 matches)
```

**JSON output:**
```bash
$ mwissues query "login" --json
{
  "query": "login",
  "page": 1,
  "total_pages": 1,
  "total_matches": 2,
  "matches": [
    {"id": 1, "priority": "A", "status": "active", "title": "Fix login bug", "description": "Users can't...", "tags": ["auth"], "todos_done": 0, "todos_total": 4},
    {"id": 3, "priority": "B", "status": "active", "title": "Add login timeout", "description": "Timeout after...", "tags": ["auth"], "todos_done": 1, "todos_total": 2}
  ]
}
```

**Filter by status:**
```bash
$ mwissues query "login" --status active    # only active issues
$ mwissues query "login" --status inactive  # only inactive issues
```

**No matches:**
```bash
$ mwissues query "xyz123"
No matches found
```

#### Acceptance criteria

- [ ] `mwissues query "login"` finds issues with "login" in title
- [ ] `mwissues query "test"` finds issues with "test" in todo text
- [ ] `mwissues query "urgent"` finds issues with "urgent" tag
- [ ] Search is case-insensitive ("Login" matches "login")
- [ ] Searches all issues by default (active and inactive)
- [ ] `mwissues query --status active` filters to active only
- [ ] `mwissues query --json` outputs valid JSON
- [ ] `mwissues query --human` outputs pretty table
- [ ] Results show tags and todo progress
- [ ] No matches shows "No matches found"
- [ ] Pagination works correctly

#### Blocked by

- #00-mwissues-init
- #01-issue-crud
- #02-todo-management
- #03-tag-management

---

### Issue 05: help-text

**Parent:** `docs/prd-mwissues-cli.md`

#### What to build

Complete help system: `--help` on all commands, full help for `mwissues` with no args.

#### Help output

**`mwissues` (no args)**

```bash
$ mwissues
mwissues - Personal issue tracker

Usage: mwissues <command> [options]

Run "mwissues --help" for full command list.
Run "mwissues <command> --help" for command-specific help.
```

**`mwissues --help`**

```bash
$ mwissues --help
mwissues - Personal issue tracker

Usage: mwissues <command> [options]

Commands:
  init                      Initialize database and instructions
  add <title>               Add new issue (requires --priority, --description)
  show <id>                 Show issue details
  list [page]               List all issues
  edit <id>                 Edit issue fields
  archive <id>              Archive an issue (mark inactive)
  delete <id>               Permanently delete an issue
  query <text>              Search issues by title, description, details, todos, tags
  add-todo <id> <text>      Add todo item
  check-todo <id> <index>  Mark todo as done
  uncheck-todo <id> <index> Mark todo as not done
  remove-todo <id> <index>  Remove todo item
  edit-todo <id> <index> <text> Edit todo text
  add-tags <id> <tag1> [tag2]...   Add tags
  remove-tags <id> <tag1> [tag2]... Remove tags
  rename-tags <old> <new>   Rename tag globally

Options:
  --status active|inactive|all  Filter by issue status (default: all)
  --json                        JSON output format
  --human                       Human-friendly table output

Priority:
  A - Must Do: High consequence if not done
  B - Should Do: Important, no major consequences if delayed
  C - Nice to Do: Extra feature if time allows
  D - Think about: Requires deliberation
  E - Eliminate: Unnecessary, no added value

Status:
  active   - Needs attention
  inactive - No longer needs attention (archived)

Use "mwissues <command> --help" for detailed help on a command.
```

**Command-specific help**

```bash
$ mwissues add --help
Usage: mwissues add <title> --priority A-E

Add a new issue with the given title.
Priority is required (A, B, C, D, or E).

Examples:
  mwissues add "Fix login bug" --priority A
  mwissues add "Update docs" --priority B

$ mwissues show --help
Usage: mwissues show <id>

Show full details of an issue including todos and tags.
Output is markdown formatted.

$ mwissues list --help
Usage: mwissues list [--status active|inactive|all] [page]

List all issues, sorted by priority then creation date.
Default 10 issues per page.

Options:
  --status  Filter: active, inactive, or all (default)
  --json    JSON output
  --human   Pretty table output

$ mwissues add-todo --help
Usage: mwissues add-todo <id> <text>

Add a todo item to an issue.

$ mwissues check-todo --help
Usage: mwissues check-todo <id> <index>

Mark a todo as done. 1-based index.
Returns success or "Failed" if already checked.

$ mwissues uncheck-todo --help
Usage: mwissues uncheck-todo <id> <index>

Mark a todo as not done. 1-based index.
Returns success or "Failed" if already unchecked.

$ mwissues remove-todo --help
Usage: mwissues remove-todo <id> <index>

Remove a todo item from an issue. 1-based index.

$ mwissues edit-todo --help
Usage: mwissues edit-todo <id> <index> <text>

Edit the text of a todo item.

$ mwissues add-tags --help
Usage: mwissues add-tags <id> <tag1> [tag2]...

Add one or more tags to an issue.
Plural command - accepts multiple tags at once.

$ mwissues remove-tags --help
Usage: mwissues remove-tags <id> <tag1> [tag2]...

Remove one or more tags from an issue.
Reports tags not found.

$ mwissues rename-tags --help
Usage: mwissues rename-tags <old-tag> <new-tag>

Rename a tag globally across all issues.

$ mwissues query --help
Usage: mwissues query <text> [--status active|inactive|all] [page]

Search issues by title, todo text, or tags.
Case-insensitive substring match.

$ mwissues archive --help
Usage: mwissues archive <id>

Mark an issue as inactive (archived).
Use "mwissues list --status inactive" to view archived issues.

$ mwissues edit --help
Usage: mwissues edit <id> [options]

Edit an issue's fields. At least one field required.

Options:
  --title "..."       New title
  --description "..." New description
  --details "..."     New details (multiline supported)
  --priority A-E     New priority

Examples:
  mwissues edit 1 --description "Updated description"
  mwissues edit 1 --details "New details here"
  mwissues edit 1 --priority B --title "New title"
```

#### Acceptance criteria

- [ ] `mwissues` with no args shows brief usage
- [ ] `mwissues --help` shows full help with all commands and priorities
- [ ] `mwissues add --help` shows add command usage (requires --priority, --description)
- [ ] `mwissues show --help` shows show command usage
- [ ] `mwissues edit --help` shows edit command usage
- [ ] `mwissues add-todo --help` shows add-todo usage
- [ ] `mwissues check-todo --help` shows check-todo usage
- [ ] `mwissues uncheck-todo --help` shows uncheck-todo usage
- [ ] `mwissues remove-todo --help` shows remove-todo usage
- [ ] `mwissues edit-todo --help` shows edit-todo usage
- [ ] `mwissues add-tags --help` shows add-tags usage
- [ ] `mwissues remove-tags --help` shows remove-tags usage
- [ ] `mwissues rename-tags --help` shows rename-tags usage
- [ ] `mwissues query --help` shows query usage
- [ ] `mwissues archive --help` shows archive usage
- [ ] Priority and status meanings always visible in help output
- [ ] All commands show `--help` without error

#### Blocked by

- #00-mwissues-init
- #01-issue-crud
- #02-todo-management
- #03-tag-management
- #04-search

---

## Implementation Order

1. `00-mwissues-init` - Database, schema, CLI entry point (done)
2. `01-issue-crud` - add, show, list, edit, archive, delete
3. `02-todo-management` - add-todo, check-todo, uncheck-todo, remove-todo, edit-todo (done)
4. `03-tag-management` - add-tags, remove-tags, rename-tags
5. `04-search` - query command
6. `05-help-text` - Complete help system
