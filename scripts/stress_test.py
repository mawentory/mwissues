#!/usr/bin/env python3
"""Stress test script for mwissues: inserts 1000+ issues with tags and todos."""
import random
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "mwissues.db"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "src" / "mwissues" / "cli.py"

ISSUE_COUNT = 1200

TITLES = [
    "Fix login bug", "Update docs", "Add dark mode", "Improve error messages",
    "Refactor auth module", "Add unit tests", "Fix memory leak", "Update dependencies",
    "Add search feature", "Improve performance", "Fix UI glitch", "Add export feature",
    "Update README", "Fix race condition", "Add logging", "Improve validation",
    "Fix timezone bug", "Add notifications", "Update API version", "Fix null pointer",
    "Add caching layer", "Improve mobile UI", "Fix SSL issue", "Add webhooks",
    "Update database schema", "Fix import error", "Add rate limiting", "Improve error handling",
    "Fix encoding bug", "Add batch processing", "Improve dashboard", "Fix pagination",
    "Add keyboard shortcuts", "Fix modal overlay", "Add undo feature", "Improve search ranking",
    "Fix clipboard issue", "Add drag and drop", "Update icons", "Fix dropdown menu",
    "Add keyboard navigation", "Improve accessibility", "Fix focus trap", "Add voice input",
    "Fix text selection", "Add markdown support", "Improve code highlighting", "Fix scroll sync",
    "Add offline mode", "Improve sync reliability", "Fix conflict resolution", "Add version history",
    "Fix data corruption", "Add auto-save", "Improve backup system", "Fix restore failure",
    "Add multi-user support", "Improve permissions", "Fix permission bypass", "Add audit logging",
    "Fix data export", "Add import from CSV", "Improve CSV parsing", "Fix date parsing",
    "Add timezone support", "Improve date display", "Fix DST handling", "Add calendar view",
    "Improve list view", "Fix sorting bug", "Add column customizer", "Improve filtering",
    "Fix bulk operations", "Add batch edit", "Improve performance on large datasets", "Fix memory pressure",
    "Add pagination controls", "Improve infinite scroll", "Fix loading states", "Add skeleton screens",
    "Improve error recovery", "Fix retry logic", "Add circuit breaker", "Improve timeout handling",
    "Fix connection pooling", "Add request queuing", "Improve throughput", "Fix bottleneck analysis",
    "Add metrics dashboard", "Improve monitoring", "Fix alerting", "Add health checks",
    "Improve deployment", "Fix rollback", "Add canary deploy", "Improve blue-green deploy",
    "Fix config management", "Add feature flags", "Improve A/B testing", "Fix experiment tracking",
    "Add user feedback", "Improve NPS scores", "Fix support tickets", "Add live chat",
    "Improve onboarding", "Fix tutorial", "Add walkthrough", "Improve documentation",
]

DESCRIPTIONS = [
    "Users can't log in after recent deployment",
    "API docs need updating for v2 endpoints",
    "Users are requesting a dark mode toggle",
    "Error messages are too technical for end users",
    "Auth module has grown too large and needs splitting",
    "Core modules lack adequate test coverage",
    "Memory usage grows over time during batch jobs",
    "Several dependencies are several versions behind",
    "Users need to search across all their issues",
    "List view loads slowly with more than 100 issues",
    "Modal closes unexpectedly on mobile devices",
    "Users want to export issues to CSV/JSON",
    "README is missing setup instructions for Windows",
    "Concurrent requests sometimes overwrite each other",
    "Operations lack structured logging for debugging",
    "Form validation allows invalid input in edge cases",
    "Timestamps are off by one day in some timezones",
    "Users want email notifications for assigned issues",
    "API version header is not enforced consistently",
    "Crash occurs when optional fields are null",
    "Repeated queries are slowing down the dashboard",
    "Mobile layout breaks on screens smaller than 320px",
    "SSL handshake fails with certain certificate chains",
    "Integrations need webhook support for external tools",
    "Database schema needs migration for new features",
    "Import fails when requirements files contain markers",
    "API needs rate limiting to prevent abuse",
    "Exceptions are swallowed in background jobs",
    "Unicode characters are corrupted in issue titles",
    "Large imports should run in smaller batches",
    "Search results are not returning expected matches",
    "Pagination is broken on the second page",
    "Keyboard shortcuts conflict with browser defaults",
    "Modal backdrop doesn't close on outside click",
    "Undo operation doesn't work for deleted items",
    "Search ranking doesn't prioritize recent items",
    "Copy to clipboard fails in headless browsers",
    "Drag and drop doesn't work on touch devices",
    "Icons don't render correctly on HiDPI displays",
    "Dropdown menu closes when scrolling",
    "Tab navigation skips certain elements",
    "Screen reader can't access modal content",
    "Focus trap doesn't work in nested modals",
    "Voice input accuracy is poor in noisy environments",
    "Text selection doesn't work on mobile",
    "Markdown tables don't render correctly",
    "Code blocks lose syntax highlighting on copy",
    "Scroll sync is jittery between panels",
    "Offline mode doesn't sync pending changes",
    "Sync occasionally drops data during reconnection",
    "Conflict resolution picks wrong version",
    "Version history doesn't record all changes",
    "Data corruption occurs after long-running operations",
    "Auto-save conflicts with manual edits",
    "Backup fails silently when disk is full",
    "Restore fails with checksum mismatch",
    "Multi-user editing causes race conditions",
    "Permissions don't cascade to child resources",
    "Admin can access other users' private data",
    "Audit log doesn't capture delete operations",
    "Data export is missing critical fields",
    "CSV import rejects valid UTF-8 characters",
    "CSV parsing mishandles quoted fields with commas",
    "Date parser doesn't handle ISO 8601 format",
    "Timezone conversion is wrong for negative offsets",
    "Date display shows wrong format in some locales",
    "DST transitions cause double bookings",
    "Calendar view doesn't show recurring events",
    "List view items overlap when zoomed",
    "Sorting doesn't handle null values correctly",
    "Column resizing breaks layout on small screens",
    "Filter state isn't persisted on refresh",
    "Bulk operations fail after partial completion",
    "Batch edit doesn't update all selected items",
    "Large datasets cause browser tab to freeze",
    "Memory pressure causes random crashes",
    "Pagination controls don't update URL",
    "Infinite scroll causes performance degradation",
    "Loading states show stale data briefly",
    "Skeleton screens don't match final layout",
    "Error recovery doesn't restore previous state",
    "Retry logic causes infinite loops",
    "Circuit breaker doesn't reset properly",
    "Timeout values are too aggressive for slow networks",
    "Connection pool exhaustion causes cascading failures",
    "Request queue overflow loses requests",
    "Throughput degrades after sustained load",
    "Bottleneck analysis tools give conflicting data",
    "Metrics dashboard doesn't refresh automatically",
    "Monitoring alerts fire for false positives",
    "Alert routing doesn't respect business hours",
    "Health check endpoint returns incorrect status",
    "Deployment takes too long on CI",
    "Rollback doesn't clean up new resources",
    "Canary deployment traffic split is uneven",
    "Blue-green switch causes brief downtime",
    "Config changes require full restart",
    "Feature flags don't work in local development",
    "A/B test results aren't statistically significant",
    "Experiment tracking misses conversion events",
    "User feedback form doesn't submit",
    "NPS score shows unexpected dip",
    "Support ticket links are broken",
    "Live chat widget is missing",
    "Onboarding checklist doesn't mark items complete",
    "Tutorial doesn't respect user preferences",
    "Walkthrough step counter is wrong",
    "Documentation search returns irrelevant results",
]

DETAILS_TEMPLATES = [
    "Steps to reproduce:\n1. Go to /login\n2. Enter credentials\n3. Click login\nExpected: Redirect to dashboard\nActual: Error 500",
    "Affects endpoints:\n- GET /api/v2/users\n- POST /api/v2/users\nSee swagger for request/response formats.",
    "Design proposal:\n- Add theme toggle in settings\n- Persist preference to localStorage\n- Default to system preference",
    "Current message: 'Internal Server Error'\nProposed: 'Something went wrong. Please try again.'",
    "Proposed split:\n- auth/login.py\n- auth/session.py\n- auth/permissions.py",
    "Target coverage: 80%\nFocus on:\n- auth flows\n- issue CRUD\n- tag management",
    "Observed in:\n- batch_import.py\n- report_generator.py\nRSS grows by ~5MB/hour",
    "Affected:\n- click==8.0.0 -> 8.1.0\n- pydantic==1.10.0 -> 2.5.0",
    "Requirements:\n- Full-text search across title/description\n- Highlighted matches in results",
    "Benchmarks:\n- Current: 1.2s for 200 issues\n- Target: <300ms",
    "Reproduction:\n1. Open issue on iPhone SE\n2. Tap edit button\n3. Modal appears off-screen",
    "Formats:\n- CSV with all fields\n- JSON with nested tags/todos\n- Markdown summary",
    "Add:\n- prerequisites\n- installation\n- troubleshooting\n- contributing guide",
    "Scenario:\n1. Two users edit same issue\n2. Last write wins silently\n3. Data loss occurs",
    "Add structured logger:\n- request_id\n- user_id\n- duration_ms\n- error details",
    "Examples:\n- email: require @ in input\n- priority: reject values outside A-E",
    "Root cause: datetime.utcnow() used instead of local time\nFix: use timezone-aware timestamps",
    "Settings:\n- notify_on_assign\n- notify_on_comment\n- daily digest option",
    "Breaking changes:\n- /v1/users -> /v2/users\n- Old version deprecated 2026-06-01",
    "Guard clauses needed for:\n- description\n- details\n- priority when optional",
    "Implementation:\n- Redis cache for frequent queries\n- TTL: 5 minutes\n- Invalidation on write",
    "Breakpoints:\n- 320px: stack navigation\n- 768px: tab navigation\n- Desktop: sidebar",
    "Root cause: cert chain uses SHA-1 signature\nFix: update cert or allow override in dev",
    "Payload format:\n{\n  \"event\": \"issue.created\",\n  \"data\": { ... }\n}",
    "Migration adds:\n- issues.updated_at\n- issues.metadata JSON\n- todos.position INTEGER",
    "Fix:\n- Parse markers before installing\n- Show friendly error for invalid lines",
    "Limits:\n- 100 req/min per user\n- 1000 req/min per IP\n- 429 with Retry-After header",
    "Add:\n- try/except with logging\n- Dead letter queue for failures\n- Retry with backoff",
    "Fix:\n- Normalize to UTF-8 NFC\n- Update collation in queries\n- Test with emoji input",
    "Use:\n- asyncio.Semaphore(10)\n- Chunk size: 50\n- Progress reporting every 100 rows",
]

TAG_POOL = [
    "bug", "enhancement", "feature", "documentation", "performance",
    "security", "ux", "accessibility", "mobile", "desktop",
    "backend", "frontend", "api", "database", "devops",
    "urgent", "low-priority", "wontfix", "duplicate", "blocked",
    "good-first-issue", "help-wanted", "needs-review", "needs-tests",
    "breaking-change", "tech-debt", "refactor", "optimization",
]

TODO_TEMPLATES = [
    "Write failing test",
    "Fix the bug",
    "Add documentation",
    "Update tests",
    "Review code",
    "Deploy to staging",
    "Test in production",
    "Update dependencies",
    "Write release notes",
    "Add logging",
    "Refactor for clarity",
    "Add error handling",
    "Optimize query",
    "Add index",
    "Write migration",
    "Review security",
    "Add validation",
    "Fix edge case",
    "Update UI",
    "Add fallback",
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    schema = """
    CREATE TABLE IF NOT EXISTS issues (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      description TEXT,
      details TEXT,
      priority TEXT CHECK(priority IN ('A','B','C','D','E')) NOT NULL,
      status TEXT DEFAULT 'open' CHECK(status IN ('open','closed')) NOT NULL,
      visibility TEXT DEFAULT 'visible' CHECK(visibility IN ('visible','hidden')) NOT NULL,
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

    CREATE INDEX IF NOT EXISTS idx_todos_issue_id ON todos(issue_id);
    CREATE INDEX IF NOT EXISTS idx_tags_issue_id ON tags(issue_id);
    CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
    """
    conn.executescript(schema)


def random_created_at(base_offset_days: int = 365) -> str:
    """Generate a random ISO timestamp within the past base_offset_days."""
    now = datetime.now()
    days_ago = random.randint(0, base_offset_days)
    hours_ago = random.randint(0, 23)
    minutes_ago = random.randint(0, 59)
    dt = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def generate_issue_data(count: int):
    priorities = ["A", "A", "B", "B", "C", "C", "D", "E"]
    statuses = ["open", "open", "open", "closed"]  # 75% open
    visibilities = ["visible", "visible", "visible", "hidden"]  # 75% visible

    for i in range(1, count + 1):
        title_idx = (i - 1) % len(TITLES)
        title = TITLES[title_idx]
        if i > len(TITLES):
            title = f"{TITLES[title_idx]} #{i}"

        description = DESCRIPTIONS[(i - 1) % len(DESCRIPTIONS)]
        details = DETAILS_TEMPLATES[(i - 1) % len(DETAILS_TEMPLATES)]
        priority = priorities[(i - 1) % len(priorities)]
        status = statuses[(i - 1) % len(statuses)]
        visibility = visibilities[(i - 1) % len(visibilities)]
        created_at = random_created_at()

        yield {
            "title": title,
            "description": description,
            "details": details,
            "priority": priority,
            "status": status,
            "visibility": visibility,
            "created_at": created_at,
        }


def generate_tags_for_issue(issue_id: int, seed: int) -> list:
    """Generate random tags for an issue. ~60% of issues have tags."""
    rng = random.Random(seed)
    if rng.random() < 0.4:
        return []

    num_tags = rng.choices([1, 2, 3], weights=[50, 35, 15])[0]
    tags = rng.sample(TAG_POOL, min(num_tags, len(TAG_POOL)))
    return [(issue_id, tag) for tag in tags]


def generate_todos_for_issue(issue_id: int, seed: int) -> list:
    """Generate random todos for an issue. ~50% of issues have todos."""
    rng = random.Random(seed)
    if rng.random() < 0.5:
        return []

    num_todos = rng.choices([1, 2, 3, 4, 5], weights=[30, 30, 25, 10, 5])[0]
    todos = []
    for j in range(num_todos):
        text = rng.choice(TODO_TEMPLATES)
        if j == 0:
            text = f"Step 1: {text}"
        done = 1 if rng.random() < 0.4 else 0
        todos.append((issue_id, text, done))
    return todos


def main() -> int:
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found at {DB_PATH}. Run 'mwissues init' first.")

    start = time.perf_counter()

    rows = list(generate_issue_data(ISSUE_COUNT))
    issue_count = len(rows)

    with get_connection() as conn:
        ensure_schema(conn)
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO issues (title, description, details, priority, status, visibility, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(r["title"], r["description"], r["details"],
              r["priority"], r["status"], r["visibility"], r["created_at"]) for r in rows],
        )
        conn.commit()
        print(f"Inserted {issue_count} issues")

    tag_rows = []
    todo_rows = []
    for i in range(1, issue_count + 1):
        tag_rows.extend(generate_tags_for_issue(i, i * 17))
        todo_rows.extend(generate_todos_for_issue(i, i * 31))

    with get_connection() as conn:
        cursor = conn.cursor()
        if tag_rows:
            cursor.executemany(
                "INSERT INTO tags (issue_id, name) VALUES (?, ?)",
                tag_rows,
            )
            print(f"Inserted {len(tag_rows)} tags")

        if todo_rows:
            cursor.executemany(
                "INSERT INTO todos (issue_id, text, done) VALUES (?, ?, ?)",
                todo_rows,
            )
            print(f"Inserted {len(todo_rows)} todos")

        conn.commit()

    elapsed = time.perf_counter() - start
    print(f"Total: {issue_count} issues, {len(tag_rows)} tags, {len(todo_rows)} todos in {elapsed:.3f}s")
    print(f"Database: {DB_PATH}")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM issues")
        db_issues = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tags")
        db_tags = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM todos")
        db_todos = cursor.fetchone()[0]
        print(f"Verified: {db_issues} issues, {db_tags} tags, {db_todos} todos in DB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
