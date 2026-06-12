import sqlite3
import os
import tempfile

from click.testing import CliRunner
from mwissues.cli import cli


def run(args, cwd):
    runner = CliRunner()
    return runner.invoke(cli, args), cwd


def main():
    tmp = tempfile.mkdtemp(prefix="mwissues-repro-")
    cwd = tmp
    runner = CliRunner()

    # init
    result = runner.invoke(cli, ["init"])
    print("INIT:", result.output.strip(), result.exit_code)

    # add
    result = runner.invoke(cli, ["add", "Fix login bug", "--priority", "A", "--description", "x"])
    print("ADD:", result.output.strip(), result.exit_code)

    # show
    result = runner.invoke(cli, ["show", "1"])
    print("SHOW:", result.output.strip().splitlines()[0], result.exit_code)

    # list
    result = runner.invoke(cli, ["list"])
    print("LIST:", result.output.strip().splitlines()[0], result.exit_code)

    # archive
    result = runner.invoke(cli, ["archive", "1"])
    print("ARCHIVE:", result.output.strip(), result.exit_code)

    # edit
    result = runner.invoke(cli, ["edit", "1", "--title", "Fixed"])
    print("EDIT:", result.output.strip(), result.exit_code)

    # delete
    result = runner.invoke(cli, ["delete", "1"])
    print("DELETE:", result.output.strip(), result.exit_code)

    # show after delete
    result = runner.invoke(cli, ["show", "1"])
    print("SHOW AFTER DELETE:", result.output.strip().splitlines()[0], result.exit_code)

    # add-tags
    conn = sqlite3.connect(os.path.join(tmp, "mwissues.db"))
    conn.execute("INSERT INTO issues (title, priority) VALUES (?, ?)", ("T", "A"))
    conn.commit()
    conn.close()
    result = runner.invoke(cli, ["add-tags", "1", "auth"])
    print("ADD-TAG:", result.output.strip(), result.exit_code)

    # remove-tags
    result = runner.invoke(cli, ["remove-tags", "1", "auth"])
    print("REMOVE-TAG:", result.output.strip(), result.exit_code)

    # rename-tags
    conn = sqlite3.connect(os.path.join(tmp, "mwissues.db"))
    conn.execute("INSERT INTO tags (issue_id, name) VALUES (?, ?)", (1, "bug"))
    conn.commit()
    conn.close()
    result = runner.invoke(cli, ["rename-tags", "bug", "defect"])
    print("RENAME-TAG:", result.output.strip(), result.exit_code)

    # add-todo
    result = runner.invoke(cli, ["add-todo", "1", "test"])
    print("ADD-TODO:", result.output.strip(), result.exit_code)


if __name__ == "__main__":
    main()
