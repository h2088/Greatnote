#!/usr/bin/env python3
"""PreToolUse hook: prevent destructive operations on the SQLite database file."""

import json
import sys

DB_PATHS = ["db.sqlite3", "backend/db.sqlite3"]

def main():
    data = json.load(sys.stdin)
    tool_name = data.get("tool_name", "")
    params = data.get("tool_params", {})

    # Block any direct Write/Edit to the DB file
    if tool_name in ("Write", "Edit"):
        file_path = params.get("file_path", "")
        if any(db in file_path for db in DB_PATHS):
            print(
                "Blocked: direct file operations on the SQLite database are not allowed. "
                "Use Django migrations (python manage.py migrate) to manage the database.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Block destructive Bash commands that target the DB file
    if tool_name == "Bash":
        command = params.get("command", "")
        cmd_lower = command.lower()
        if any(db in command for db in DB_PATHS):
            destructive = [
                "rm ", "del ", "mv ", "move ", "ren ", "rename",
                "rd ", "rmdir ", "truncate", "cp ", "copy ", "xcopy",
                "shred", "dd ", ">",
            ]
            if any(kw in cmd_lower for kw in destructive):
                print(
                    "Blocked: destructive command targeting SQLite database detected. "
                    "Use Django migrations (python manage.py migrate) instead.",
                    file=sys.stderr,
                )
                sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
