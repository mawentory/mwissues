---
id: 012
title: JSON import validation and rollback
created: 2026-06-13T09:35:00Z
category: enhancement
state: needs-triage
summary: Validate JSON entries and rollback on any error
---

# JSON import validation and rollback

## Parent

`.scratch/011-json-import.md`

## What to build

Add comprehensive validation for each JSON entry in the import command, with clear error messages and full transaction rollback on any failure.

**Validation rules:**
- `title` must be a non-empty string
- `priority` must be one of `A`, `B`, `C`, `D`, `E` if provided
- All other fields (description, details) must be strings if provided

**Error output format:**
```
Error at index N: field 'title' is required
```
or
```
Error at index N: field 'priority' must be one of A, B, C, D, E (got 'X')
```

**Transaction behavior:**
- Open transaction before processing
- Roll back on any validation error
- Commit only if all entries are valid

## Acceptance criteria

- [ ] Missing title → error with row index
- [ ] Invalid priority value → error with allowed values
- [ ] Non-string description/details → error with field name
- [ ] Verify no partial inserts on validation failure

## Blocked by

- `.scratch/011-json-import.md`
