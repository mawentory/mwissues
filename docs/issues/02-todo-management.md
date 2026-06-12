# 02-todo-management
 done
## Parent

- `docs/prd-mwissues-cli.md`

## What to build

Todo CRUD for issues: add, check, uncheck, remove, edit.

## Commands

### `mwissues add-todo <id> <text>`

Add a todo to an issue.

```bash
$ mwissues add-todo 1 "Write unit tests"
Todo added to issue #1: 1. Write unit tests

$ mwissues add-todo 1 "Test edge cases"
Todo added to issue #1: 2. Test edge cases

$ mwissues add-todo 1 "Deploy to staging"
Todo added to issue #1: 3. Deploy to staging
```

### `mwissues check-todo <id> <index>`

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

### `mwissues uncheck-todo <id> <index>`

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

### `mwissues remove-todo <id> <index>`

Remove a todo. 1-based index.

```bash
$ mwissues remove-todo 1 2
Todo #2 removed: "Test edge cases"
```

### `mwissues edit-todo <id> <index> <text>`

Edit todo text. 1-based index.

```bash
$ mwissues edit-todo 1 1 "Write comprehensive unit tests with mocks"
Todo #1 updated: "Write comprehensive unit tests with mocks"
```

## Implementation

```python
def cmd_add_todo(issue_id: int, text: str):
    verify_issue_exists(issue_id)
    db.execute("INSERT INTO todos (issue_id, text, done) VALUES (?, ?, 0)", (issue_id, text))
    index = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    print(f"Todo added to issue #{issue_id}: {index}. {text}")

def cmd_check_todo(issue_id: int, index: int):
    verify_issue_exists(issue_id)
    todo = db.execute("""
        SELECT id, text, done FROM todos WHERE issue_id = ? ORDER BY id LIMIT 1 OFFSET ?
    """, (issue_id, index - 1)).fetchone()
    
    if not todo:
        print(f"Failed: Todo #{index} not found")
        return
    
    if todo['done']:
        print(f"Failed: Todo #{index} is already checked")
        return
    
    db.execute("UPDATE todos SET done = 1 WHERE id = ?", (todo['id'],))
    print(f"Todo #{index} checked: \"{todo['text']}\"")

def cmd_uncheck_todo(issue_id: int, index: int):
    verify_issue_exists(issue_id)
    todo = db.execute("""
        SELECT id, text, done FROM todos WHERE issue_id = ? ORDER BY id LIMIT 1 OFFSET ?
    """, (issue_id, index - 1)).fetchone()
    
    if not todo:
        print(f"Failed: Todo #{index} not found")
        return
    
    if not todo['done']:
        print(f"Failed: Todo #{index} is already unchecked")
        return
    
    db.execute("UPDATE todos SET done = 0 WHERE id = ?", (todo['id'],))
    print(f"Todo #{index} unchecked: \"{todo['text']}\"")

def cmd_remove_todo(issue_id: int, index: int):
    verify_issue_exists(issue_id)
    todo = db.execute("""
        SELECT id, text FROM todos WHERE issue_id = ? ORDER BY id LIMIT 1 OFFSET ?
    """, (issue_id, index - 1)).fetchone()
    
    if not todo:
        print(f"Failed: Todo #{index} not found")
        return
    
    db.execute("DELETE FROM todos WHERE id = ?", (todo['id'],))
    print(f"Todo #{index} removed: \"{todo['text']}\"")

def cmd_edit_todo(issue_id: int, index: int, text: str):
    verify_issue_exists(issue_id)
    todo = db.execute("""
        SELECT id FROM todos WHERE issue_id = ? ORDER BY id LIMIT 1 OFFSET ?
    """, (issue_id, index - 1)).fetchone()
    
    if not todo:
        print(f"Failed: Todo #{index} not found")
        return
    
    db.execute("UPDATE todos SET text = ? WHERE id = ?", (text, todo['id']))
    print(f"Todo #{index} updated: \"{text}\"")

def verify_issue_exists(issue_id: int):
    issue = db.execute("SELECT id FROM issues WHERE id = ?", (issue_id,)).fetchone()
    if not issue:
        print(f"Failed: Issue #{issue_id} not found")
        sys.exit(1)
```

## Acceptance criteria

- [ ] `mwissues add-todo 1 "Write tests"` adds todo with confirmation
- [ ] `mwissues check-todo 1 1` marks todo done with success message
- [ ] `mwissues check-todo 1 1` on already-checked todo shows "Failed" message
- [ ] `mwissues uncheck-todo 1 1` marks todo not done with success message
- [ ] `mwissues uncheck-todo 1 1` on already-unchecked todo shows "Failed" message
- [ ] `mwissues remove-todo 1 2` deletes todo with confirmation
- [ ] `mwissues edit-todo 1 1 "New text"` updates todo text
- [ ] Invalid todo index shows "Failed: Todo #X not found"
- [ ] Todo on non-existent issue shows "Failed: Issue #X not found"

## Blocked by

- #00-mwissues-init
