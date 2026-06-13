---
id: 011
title: Add JSON import CLI command
created: 2026-06-13T09:35:00Z
category: enhancement
state: needs-triage
summary: Add `import` command for batch inserting issues from JSON
---

# Add JSON import CLI command

## What to build

Add a new `import` CLI command that reads a JSON array of issues and inserts them into the database in a single transaction.

**Input sources:**
- Stdin: `mwissues import < file.json`
- File path: `mwissues import issues.json`

**JSON schema (array of objects):**
```json
[
  {
    "title": "Fix auth",
    "description": "Users can't log in",
    "details": "Steps to reproduce...",
    "priority": "A",
    "tags": ["bug", "auth"],
    "todos": [
      { "text": "Check logs", "done": false },
      { "text": "Reproduce bug", "done": true }
    ]
  }
]
```

**Field rules:**
- `title` — required, string
- `description` — optional, string
- `details` — optional, string
- `priority` — optional, one of `A/B/C/D/E`, defaults to `B`
- `tags` — optional, array of strings
- `todos` — optional, array of objects with `text` (string, required) and `done` (boolean, optional, defaults to false)

**Behavior:**
- All entries inserted in a single DB transaction
- Output: `"Imported N issues successfully"` on success
- All-or-nothing: any validation error aborts the entire transaction

## Acceptance criteria

- [ ] `mwissues import < file.json` reads from stdin
- [ ] `mwissues import issues.json` reads from a file path
- [ ] Priority defaults to `B` if omitted
- [ ] Tags are imported if present in JSON
- [ ] Todos are imported if present in JSON
- [ ] Validation errors abort the entire import (all-or-nothing)
- [ ] Output shows count of issues imported on success
- [ ] Unit tests cover the import path (including tags and todos)

## Blocked by

- None — can start immediately
