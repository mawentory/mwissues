#!/usr/bin/env python3
"""Stress test script for mwissues: inserts 200+ issues into the local database."""
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "mwissues.db"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "src" / "mwissues" / "cli.py"

# Number of issues to insert
ISSUE_COUNT = 220

# Sample data pools
TITLES = [
    "Fix login bug", "Update docs", "Add dark mode", "Improve error messages",
    "Refactor auth module", "Add unit tests", "Fix memory leak", "Update dependencies",
    "Add search feature", "Improve performance", "Fix UI glitch", "Add export feature",
    "Update README", "Fix race condition", "Add logging", "Improve validation",
    "Fix timezone bug", "Add notifications", "Update API version", "Fix null pointer",
    "Add caching layer", "Improve mobile UI", "Fix SSL issue", "Add webhooks",
    "Update database schema", "Fix import error", "Add rate limiting", "Improve error handling",
    "Fix encoding bug", "Add batch processing"
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
    "Large imports should run in smaller batches"
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
    "Use:\n- asyncio.Semaphore(10)\n- Chunk size: 50\n- Progress reporting every 100 rows"
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

    CREATE INDEX IF NOT EXISTS idx_todos_issue_id ON todos(issue_id);
    CREATE INDEX IF NOT EXISTS idx_tags_issue_id ON tags(issue_id);
    CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
    """
    conn.executescript(schema)


def generate_issues(count: int):
    priorities = ["A", "A", "B", "B", "C", "C", "D", "E"]
    for i in range(1, count + 1):
        title = TITLES[(i - 1) % len(TITLES)]
        if i > len(TITLES):
            title = f"{TITLES[(i - 1) % len(TITLES)]} #{i}"
        description = DESCRIPTIONS[(i - 1) % len(DESCRIPTIONS)]
        details = DETAILS_TEMPLATES[(i - 1) % len(DETAILS_TEMPLATES)]
        priority = priorities[(i - 1) % len(priorities)]
        yield {
            "title": title,
            "description": description,
            "details": details,
            "priority": priority,
        }


def main() -> int:
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found at {DB_PATH}. Run 'mwissues init' first.")

    start = time.perf_counter()
    with get_connection() as conn:
        ensure_schema(conn)
        cursor = conn.cursor()

        # Use executemany for faster inserts.
        rows = [
            (issue["title"], issue["description"], issue["details"], issue["priority"])
            for issue in generate_issues(ISSUE_COUNT)
        ]
        cursor.executemany(
            "INSERT INTO issues (title, description, details, priority) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        inserted = cursor.rowcount

    elapsed = time.perf_counter() - start
    print(f"Inserted {inserted} issues in {elapsed:.3f}s into {DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
