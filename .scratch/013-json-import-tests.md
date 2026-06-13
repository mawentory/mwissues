---
id: 013
title: Tests for JSON import command
created: 2026-06-13T09:35:00Z
category: enhancement
state: needs-triage
summary: Unit tests for import command
---

# Tests for JSON import command

## Parent

`.scratch/011-json-import.md`

## What to build

Add unit tests for the `import` CLI command in `tests/test_issue_crud.py`, following the existing test patterns (using CliRunner and tmp_path fixtures).

**Test cases:**

1. **Valid stdin import** — import array via stdin, verify all issues created
2. **Valid file path import** — import array from file, verify all issues created
3. **Default priority** — import without priority field, verify defaults to `B`
4. **Missing title** — should error, no issues created
5. **Invalid priority** — should error, no issues created
6. **Partial invalid** — one bad entry in array, verify rollback (no issues created)

## Acceptance criteria

- [ ] Test valid stdin import
- [ ] Test valid file path import
- [ ] Test default priority when omitted
- [ ] Test error on missing title
- [ ] Test error on invalid priority
- [ ] Test error rollback (verify no partial inserts)

## Blocked by

- `.scratch/011-json-import.md`
