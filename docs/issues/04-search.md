# 04-search

## Parent

- `docs/prd-mwissues-cli.md`

## What to build

Full-text search across issues: title, todo text, and tags.

## Command

### `mwissues query <text> [--status active|inactive|all] [page]`

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

## Implementation

```python
def cmd_query(search_text: str, page: int = 1, page_size: int = 10, 
              status: str = 'all', json: bool = False):
    offset = (page - 1) * page_size
    pattern = f"%{search_text}%"

    where_clause = ""
    if status == 'active':
        where_clause = "AND i.status = 'active'"
    elif status == 'inactive':
        where_clause = "AND i.status = 'inactive'"

    results = db.execute(f"""
        SELECT DISTINCT i.id, i.title, i.description, i.priority, i.status, i.created_at
        FROM issues i
        WHERE (
            i.title LIKE ?
            OR i.description LIKE ?
            OR i.details LIKE ?
            OR i.id IN (
                SELECT t.issue_id FROM todos t WHERE t.text LIKE ?
            )
            OR i.id IN (
                SELECT t2.issue_id FROM tags t2 WHERE t2.name LIKE ?
            )
        )
        {where_clause}
        ORDER BY i.priority, i.created_at
        LIMIT ? OFFSET ?
    """, (pattern, pattern, pattern, pattern, pattern, page_size, offset)).fetchall()

    # Get tags and todo counts for each result
    for issue in results:
        tags = db.execute("""
            SELECT GROUP_CONCAT(name) as tags
            FROM tags WHERE issue_id = ?
        """, (issue['id'],)).fetchone()

        todo_stats = db.execute("""
            SELECT SUM(done) as done, COUNT(*) as total
            FROM todos WHERE issue_id = ?
        """, (issue['id'],)).fetchone()

        # render markdown or JSON

    total = db.execute(f"""
        SELECT COUNT(DISTINCT i.id)
        FROM issues i
        WHERE (
            i.title LIKE ?
            OR i.description LIKE ?
            OR i.details LIKE ?
            OR i.id IN (SELECT t.issue_id FROM todos t WHERE t.text LIKE ?)
            OR i.id IN (SELECT t2.issue_id FROM tags t2 WHERE t2.name LIKE ?)
        )
        {where_clause}
    """, (pattern, pattern, pattern, pattern, pattern)).fetchone()[0]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    if json:
        # output JSON
    else:
        if total == 0:
            print("No matches found")
        else:
            # output markdown table
```

## Acceptance criteria

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

## Blocked by

- #00-mwissues-init
- #01-issue-crud
- #02-todo-management
- #03-tag-management
