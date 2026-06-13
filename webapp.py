"""mwissues Flask web app — mirrors all CLI functionality."""
import math
import markdown
import re
from pathlib import Path

import flask
import sqlite3

# Import DB_NAME from the CLI module so both tools share the same database file.
from mwissues.cli import DB_NAME

app = flask.Flask(__name__)
app.secret_key = "mwissues-secret-key-change-in-production"

DB_PATH = Path.cwd() / DB_NAME

# Markdown filter for Jinja2 templates
@app.template_filter("markdown")
def render_markdown(text):
    """Render markdown to HTML with sanitization."""
    if not text:
        return ""
    return markdown.markdown(text, extensions=["fenced_code", "tables", "sane_lists"])

# ---------------------------------------------------------------------------
# Priority helpers
# ---------------------------------------------------------------------------

PRIORITY_LABELS = {
    "A": "Must Do (A)",
    "B": "Should Do (B)",
    "C": "Nice to Do (C)",
    "D": "Think about (D)",
    "E": "Eliminate (E)",
}


def get_db():
    """Return a sqlite3 connection with Row factory (column access by name)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def issue_exists(issue_id):
    conn = get_db()
    row = conn.execute("SELECT 1 FROM issues WHERE id = ?", (issue_id,)).fetchone()
    conn.close()
    return row is not None


def build_issue_row(conn, issue_id):
    """Fetch a single issue with its tags and todos."""
    row = conn.execute(
        "SELECT * FROM issues WHERE id = ?", (issue_id,)
    ).fetchone()
    if row is None:
        return None

    tags = [t["name"] for t in conn.execute(
        "SELECT name FROM tags WHERE issue_id = ?", (issue_id,)
    ).fetchall()]

    todos_raw = conn.execute(
        "SELECT id, text, done FROM todos WHERE issue_id = ? ORDER BY id",
        (issue_id,),
    ).fetchall()
    todos = [dict(t) for t in todos_raw]

    return dict(row), tags, todos


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    q = (flask.request.args.get("q") or "").strip()
    tag_filter = (flask.request.args.get("tag") or "").strip()
    status_filter = flask.request.args.get("status", "open").strip()
    visibility_filter = flask.request.args.get("visibility", "visible").strip()
    try:
        page = max(1, int(flask.request.args.get("page", 1)))
    except ValueError:
        page = 1

    per_page = 20

    conn = get_db()

    # Build WHERE clause
    conditions = []
    params = []
    if status_filter in ("open", "closed"):
        conditions.append("i.status = ?")
        params.append(status_filter)
    if visibility_filter in ("visible", "hidden"):
        conditions.append("i.visibility = ?")
        params.append(visibility_filter)
    elif visibility_filter == "all":
        pass  # No visibility filter
    if q:
        conditions.append("(i.title LIKE ? OR i.description LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if tag_filter:
        conditions.append("EXISTS (SELECT 1 FROM tags t WHERE t.issue_id = i.id AND t.name = ?)")
        params.append(tag_filter)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    count_params = params[:]

    total = conn.execute(
        f"SELECT COUNT(*) FROM issues i {where_clause}", count_params
    ).fetchone()[0]

    total_pages = max(1, math.ceil(total / per_page))
    page = min(page, total_pages)

    offset = (page - 1) * per_page

    rows = conn.execute(
        f"""
        SELECT i.id, i.title, i.description, i.priority, i.status, i.visibility, i.created_at,
               SUM(t2.done) as todos_done,
               COUNT(t2.id) as todos_total
        FROM issues i
        LEFT JOIN todos t2 ON t2.issue_id = i.id
        {where_clause}
        GROUP BY i.id
        ORDER BY i.priority, i.created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + [per_page, offset],
    ).fetchall()

    issues = []
    for r in rows:
        tags = [t["name"] for t in conn.execute(
            "SELECT name FROM tags WHERE issue_id = ?", (r["id"],)
        ).fetchall()]
        issues.append(dict(r, tags=tags, todos_done=r["todos_done"] or 0, todos_total=r["todos_total"] or 0))

    all_tags = [t["name"] for t in conn.execute(
        "SELECT DISTINCT name FROM tags ORDER BY name"
    ).fetchall()]

    conn.close()

    def page_url(p):
        args = {}
        if q:
            args["q"] = q
        if tag_filter:
            args["tag"] = tag_filter
        if status_filter != "open":
            args["status"] = status_filter
        if visibility_filter != "visible":
            args["visibility"] = visibility_filter
        if p > 1:
            args["page"] = p
        qs = "&".join(f"{k}={v}" for k, v in args.items())
        return "?" + qs if qs else "/"

    return flask.render_template(
        "index.html",
        issues=issues,
        all_tags=all_tags,
        q=q,
        tag_filter=tag_filter,
        status_filter=status_filter,
        visibility_filter=visibility_filter,
        page=page,
        total_pages=total_pages,
        total=total,
        page_url=page_url,
    )


@app.route("/issue/new", methods=["GET"])
def new_issue():
    return flask.render_template("new_issue.html")


@app.route("/issue/new", methods=["POST"])
def create_issue():
    title = flask.request.form.get("title", "").strip()
    description = flask.request.form.get("description", "").strip()
    details = flask.request.form.get("details", "").strip()
    priority = flask.request.form.get("priority", "").strip()

    if not title:
        flask.flash("Title is required.", "danger")
        return flask.redirect(flask.url_for("new_issue"))
    if not description:
        flask.flash("Description is required.", "danger")
        return flask.redirect(flask.url_for("new_issue"))
    if priority not in PRIORITY_LABELS:
        flask.flash("Invalid priority.", "danger")
        return flask.redirect(flask.url_for("new_issue"))

    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO issues (title, description, details, priority) VALUES (?, ?, ?, ?)",
        (title, description, details, priority),
    )
    issue_id = cursor.lastrowid
    conn.commit()
    conn.close()

    flask.flash(f"Issue #{issue_id} created.", "success")
    return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))


@app.route("/issue/<int:issue_id>")
def show_issue(issue_id):
    conn = get_db()
    result = build_issue_row(conn, issue_id)
    conn.close()

    if result is None:
        flask.abort(404)

    issue, tags, todos = result
    return flask.render_template(
        "view_issue.html",
        issue=issue,
        tags=tags,
        todos=todos,
        priority_labels=PRIORITY_LABELS,
    )


@app.route("/issue/<int:issue_id>/edit", methods=["GET"])
def edit_issue_page(issue_id):
    conn = get_db()
    result = build_issue_row(conn, issue_id)
    conn.close()

    if result is None:
        flask.abort(404)

    issue, tags, todos = result
    return flask.render_template(
        "edit_issue.html",
        issue=issue,
        tags=tags,
        todos=todos,
        priority_labels=PRIORITY_LABELS,
    )


@app.route("/issue/<int:issue_id>/edit", methods=["POST"])
def edit_issue(issue_id):
    if not issue_exists(issue_id):
        flask.flash(f"Issue #{issue_id} not found.", "danger")
        return flask.redirect(flask.url_for("index"))

    title = flask.request.form.get("title", "").strip()
    description = flask.request.form.get("description", "").strip()
    details = flask.request.form.get("details", "").strip()
    priority = flask.request.form.get("priority", "").strip()
    status = flask.request.form.get("status", "").strip()

    fields = []
    values = []
    if title:
        fields.append("title = ?")
        values.append(title)
    if description:
        fields.append("description = ?")
        values.append(description)
    if "details" in flask.request.form:
        fields.append("details = ?")
        values.append(details)
    if priority in PRIORITY_LABELS:
        fields.append("priority = ?")
        values.append(priority)
    if status in ("open", "closed"):
        fields.append("status = ?")
        values.append(status)

    if fields:
        values.append(issue_id)
        conn = get_db()
        conn.execute(f"UPDATE issues SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        conn.close()
        flask.flash(f"Issue #{issue_id} updated.", "success")
    else:
        flask.flash("No fields to update.", "warning")

    return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))


@app.route("/issue/<int:issue_id>/hide", methods=["POST"])
def hide_issue(issue_id):
    if not issue_exists(issue_id):
        flask.flash(f"Issue #{issue_id} not found.", "danger")
        return flask.redirect(flask.url_for("index"))

    conn = get_db()
    conn.execute("UPDATE issues SET visibility = 'hidden' WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()

    flask.flash(f"Issue #{issue_id} hidden.", "success")
    return flask.redirect(flask.url_for("index"))


@app.route("/issue/<int:issue_id>/unhide", methods=["POST"])
def unhide_issue(issue_id):
    if not issue_exists(issue_id):
        flask.flash(f"Issue #{issue_id} not found.", "danger")
        return flask.redirect(flask.url_for("index"))

    conn = get_db()
    conn.execute("UPDATE issues SET visibility = 'visible' WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()

    flask.flash(f"Issue #{issue_id} unhidden.", "success")
    return flask.redirect(flask.url_for("index"))


@app.route("/issue/<int:issue_id>/archive", methods=["POST"])
def archive_issue(issue_id):
    """Deprecated: redirects to hide."""
    flask.flash("'archive' is deprecated. Use 'hide' instead.", "warning")
    return hide_issue(issue_id)


@app.route("/issue/<int:issue_id>/delete", methods=["POST"])
def delete_issue(issue_id):
    if not issue_exists(issue_id):
        flask.flash(f"Issue #{issue_id} not found.", "danger")
        return flask.redirect(flask.url_for("index"))

    conn = get_db()
    conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()

    flask.flash(f"Issue #{issue_id} deleted.", "success")
    return flask.redirect(flask.url_for("index"))


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

@app.route("/issue/<int:issue_id>/add-tags", methods=["POST"])
def add_tags(issue_id):
    if not issue_exists(issue_id):
        flask.flash(f"Issue #{issue_id} not found.", "danger")
        return flask.redirect(flask.url_for("index"))

    raw = flask.request.form.get("tags", "").strip()
    names = [t.strip() for t in re.split(r"[,\s]+", raw) if t.strip()]

    if not names:
        flask.flash("No tags provided.", "warning")
        return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))

    conn = get_db()
    added = 0
    for name in names:
        existing = conn.execute(
            "SELECT id FROM tags WHERE issue_id = ? AND name = ?",
            (issue_id, name),
        ).fetchone()
        if existing:
            continue
        conn.execute("INSERT INTO tags (issue_id, name) VALUES (?, ?)", (issue_id, name))
        added += 1
    conn.commit()
    conn.close()

    flask.flash(f"Added {added} tag(s).", "success")
    return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))


@app.route("/issue/<int:issue_id>/remove-tag/<tag_name>", methods=["POST"])
def remove_tag(issue_id, tag_name):
    if not issue_exists(issue_id):
        flask.flash(f"Issue #{issue_id} not found.", "danger")
        return flask.redirect(flask.url_for("index"))

    conn = get_db()
    conn.execute(
        "DELETE FROM tags WHERE issue_id = ? AND name = ?", (issue_id, tag_name)
    )
    conn.commit()
    conn.close()

    flask.flash(f"Removed tag '{tag_name}'.", "success")
    return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))


@app.route("/issue/rename-tags", methods=["POST"])
def rename_tags():
    old_tag = flask.request.form.get("old_tag", "").strip()
    new_tag = flask.request.form.get("new_tag", "").strip()

    if not old_tag or not new_tag:
        flask.flash("Both old and new tag names are required.", "warning")
        return flask.redirect(flask.url_for("index"))

    conn = get_db()
    conn.execute("UPDATE tags SET name = ? WHERE name = ?", (new_tag, old_tag))
    count = conn.rowcount
    conn.commit()
    conn.close()

    flask.flash(
        f"Renamed '{old_tag}' to '{new_tag}' ({count} occurrence(s) updated).",
        "success",
    )
    return flask.redirect(flask.url_for("index"))


# ---------------------------------------------------------------------------
# Todos — 1-based index mirrors the CLI's OFFSET logic
# ---------------------------------------------------------------------------

def _todo_id_by_index(conn, issue_id, idx):
    """Return the todo id for 1-based index, or None if not found."""
    row = conn.execute(
        "SELECT id FROM todos WHERE issue_id = ? ORDER BY id LIMIT 1 OFFSET ?",
        (issue_id, idx - 1),
    ).fetchone()
    return row["id"] if row else None


@app.route("/issue/<int:issue_id>/add-todo", methods=["POST"])
def add_todo(issue_id):
    if not issue_exists(issue_id):
        flask.flash(f"Issue #{issue_id} not found.", "danger")
        return flask.redirect(flask.url_for("index"))

    text = flask.request.form.get("text", "").strip()
    if not text:
        flask.flash("Todo text is required.", "warning")
        return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))

    conn = get_db()
    conn.execute(
        "INSERT INTO todos (issue_id, text, done) VALUES (?, ?, 0)", (issue_id, text)
    )
    conn.commit()
    conn.close()

    flask.flash("Todo added.", "success")
    return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))


@app.route("/issue/<int:issue_id>/check-todo/<int:idx>", methods=["POST"])
def check_todo(issue_id, idx):
    if not issue_exists(issue_id):
        flask.flash(f"Issue #{issue_id} not found.", "danger")
        return flask.redirect(flask.url_for("index"))

    conn = get_db()
    todo_id = _todo_id_by_index(conn, issue_id, idx)
    if todo_id is None:
        conn.close()
        flask.flash(f"Todo #{idx} not found.", "danger")
        return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))

    conn.execute("UPDATE todos SET done = 1 WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()

    flask.flash(f"Todo #{idx} checked.", "success")
    return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))


@app.route("/issue/<int:issue_id>/uncheck-todo/<int:idx>", methods=["POST"])
def uncheck_todo(issue_id, idx):
    if not issue_exists(issue_id):
        flask.flash(f"Issue #{issue_id} not found.", "danger")
        return flask.redirect(flask.url_for("index"))

    conn = get_db()
    todo_id = _todo_id_by_index(conn, issue_id, idx)
    if todo_id is None:
        conn.close()
        flask.flash(f"Todo #{idx} not found.", "danger")
        return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))

    conn.execute("UPDATE todos SET done = 0 WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()

    flask.flash(f"Todo #{idx} unchecked.", "success")
    return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))


@app.route("/issue/<int:issue_id>/remove-todo/<int:idx>", methods=["POST"])
def remove_todo(issue_id, idx):
    if not issue_exists(issue_id):
        flask.flash(f"Issue #{issue_id} not found.", "danger")
        return flask.redirect(flask.url_for("index"))

    conn = get_db()
    todo_id = _todo_id_by_index(conn, issue_id, idx)
    if todo_id is None:
        conn.close()
        flask.flash(f"Todo #{idx} not found.", "danger")
        return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))

    conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()

    flask.flash(f"Todo #{idx} removed.", "success")
    return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))


@app.route("/issue/<int:issue_id>/edit-todo/<int:idx>", methods=["POST"])
def edit_todo(issue_id, idx):
    if not issue_exists(issue_id):
        flask.flash(f"Issue #{issue_id} not found.", "danger")
        return flask.redirect(flask.url_for("index"))

    text = flask.request.form.get("text", "").strip()
    if not text:
        flask.flash("Todo text is required.", "warning")
        return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))

    conn = get_db()
    todo_id = _todo_id_by_index(conn, issue_id, idx)
    if todo_id is None:
        conn.close()
        flask.flash(f"Todo #{idx} not found.", "danger")
        return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))

    conn.execute("UPDATE todos SET text = ? WHERE id = ?", (text, todo_id))
    conn.commit()
    conn.close()

    flask.flash(f"Todo #{idx} updated.", "success")
    return flask.redirect(flask.url_for("show_issue", issue_id=issue_id))


if __name__ == "__main__":
    app.run(debug=True, port=5000)


# ---------------------------------------------------------------------------
# Web control endpoints
# ---------------------------------------------------------------------------

@app.route("/web/status")
def web_status():
    return flask.jsonify({"status": "ok"})


@app.route("/web/stop", methods=["POST"])
def web_stop():
    func = flask.request.environ.get("werkzeug.server.shutdown")
    if func is None:
        return flask.jsonify({"error": "not supported"}), 500
    func()
    return "", 204
