# MUST IMPLEMENT

# mwissues

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

### Import from JSON

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

Priority defaults to `B` if omitted. Validation errors abort entire import (all-or-nothing).

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
