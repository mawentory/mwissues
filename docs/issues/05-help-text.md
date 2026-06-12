# 05-help-text

## Parent

- `docs/prd-mwissues-cli.md`

## What to build

Complete help system: `--help` on all commands, full help for `mwissues` with no args.

## Help output

### `mwissues` (no args)

```bash
$ mwissues
mwissues - Personal issue tracker

Usage: mwissues <command> [options]

Run "mwissues --help" for full command list.
Run "mwissues <command> --help" for command-specific help.
```

### `mwissues --help`

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

### Command-specific help

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

## Acceptance criteria

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

## Blocked by

- #00-mwissues-init
- #01-issue-crud
- #02-todo-management
- #03-tag-management
- #04-search
