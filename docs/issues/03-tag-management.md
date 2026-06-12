# 03-tag-management

## Parent

- `docs/prd-mwissues-cli.md`

## What to build

Tag management for issues: add-tags, remove-tags, rename-tags.

## Commands

### `mwissues add-tags <id> <tag1> [tag2] ...`

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

### `mwissues remove-tags <id> <tag1> [tag2] ...`

Remove one or more tags from an issue. Reports which were not found.

```bash
$ mwissues remove-tags 1 bug
Removed: bug

$ mwissues remove-tags 1 nonexistent1 nonexistent2
Not found: 'nonexistent1' not on issue #1
Not found: 'nonexistent2' not on issue #1
```

### `mwissues rename-tags <old-tag> <new-tag>`

Rename a tag globally across all issues.

```bash
$ mwissues rename-tags bug defect
Renamed 'bug' → 'defect' (2 issues affected)
```

## Implementation

```python
def cmd_add_tags(issue_id: int, *tags: str):
    verify_issue_exists(issue_id)
    for tag in tags:
        existing = db.execute("""
            SELECT id FROM tags WHERE issue_id = ? AND name = ?
        """, (issue_id, tag)).fetchone()
        
        if existing:
            print(f"Skipped: '{tag}' already exists on issue #{issue_id}")
            continue
        
        db.execute("INSERT INTO tags (issue_id, name) VALUES (?, ?)", (issue_id, tag))
        print(f"Added: {tag}")

def cmd_remove_tags(issue_id: int, *tags: str):
    verify_issue_exists(issue_id)
    for tag in tags:
        existing = db.execute("""
            SELECT id FROM tags WHERE issue_id = ? AND name = ?
        """, (issue_id, tag)).fetchone()
        
        if not existing:
            print(f"Not found: '{tag}' not on issue #{issue_id}")
            continue
        
        db.execute("DELETE FROM tags WHERE id = ?", (existing['id'],))
        print(f"Removed: {tag}")

def cmd_rename_tags(old_tag: str, new_tag: str):
    result = db.execute("""
        UPDATE tags SET name = ? WHERE name = ?
    """, (new_tag, old_tag))
    
    count = result.rowcount
    print(f"Renamed '{old_tag}' → '{new_tag}' ({count} issues affected)")
```

## Tag display in show/list

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

## Acceptance criteria

- [ ] `mwissues add-tags 1 urgent` adds single tag
- [ ] `mwissues add-tags 1 urgent auth bug` adds multiple tags
- [ ] `mwissues add-tags 1 urgent` on existing tag shows "Skipped" message
- [ ] `mwissues remove-tags 1 bug` removes tag
- [ ] `mwissues remove-tags 1 nonexistent` shows "Not found" message
- [ ] `mwissues rename-tags bug defect` renames globally
- [ ] Tags appear in `mwissues show` and `mwissues list` output
- [ ] Tag on non-existent issue shows "Failed: Issue #X not found"

## Blocked by

- #00-mwissues-init
