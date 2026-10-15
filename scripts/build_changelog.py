#!/usr/bin/env python3
"""Generate the site changelog from real git history.

The site documenting its own becoming: every commit on main becomes a
changelog entry with date, short hash, message, and files changed.

Output:
  changelog.html             - standalone changelog page (root)
  data/v1/changelog.json      - machine-readable changelog
  data/v1/schema/changelog.json - draft-07 schema
  (registers the endpoint in data/v1/index.json; no version bump here)

Idempotent: regenerates cleanly. Re-run after every push.
"""
import json
import subprocess
import sys
from html import escape
from pathlib import Path

import nav_data  # noqa: E402  (canonical nav data — scripts/nav_data.py)

ROOT = Path(__file__).resolve().parent.parent
API_OUT = ROOT / "data" / "v1" / "changelog.json"
API_INDEX = ROOT / "data" / "v1" / "index.json"
SCHEMA_OUT = ROOT / "data" / "v1" / "schema" / "changelog.json"
PAGE_OUT = ROOT / "changelog.html"

NAV = "      " + nav_data.nav_chunk("", "ledger", "changelog.html")
FOOTNAV = "      " + nav_data.footer_block("", "ledger", "changelog.html")

SNAPSHOT = "2026-10-11"

def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True,
        check=True).stdout

def main() -> int:
    log = git("log", "--format=%H|%ad|%s", "--date=short", "main")
    entries = []
    for line in log.splitlines():
        if not line.strip():
            continue
        sha, dat, msg = line.split("|", 2)
        files = git("diff-tree", "--no-commit-id", "--name-only",
                    "-r", sha).splitlines()
        entries.append({
            "hash": sha[:7],
            "date": dat,
            "message": msg,
            "files_changed": len([f for f in files if f.strip()]),
        })

    record = {
        "generated": SNAPSHOT,
        "method": ("Parsed from `git log main`: every commit becomes an "
                   "entry. The site documenting its own becoming."),
        "entry_count": len(entries),
        "entries": entries,
    }
    API_OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")

    SCHEMA_OUT.write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Site changelog",
        "description": "Every commit on main: the site's construction history, from git log.",
        "type": "object",
        "required": ["entries"],
        "properties": {
            "entries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["hash", "date", "message", "files_changed"],
                    "properties": {
                        "hash": {"type": "string"},
                        "date": {"type": "string"},
                        "message": {"type": "string"},
                        "files_changed": {"type": "integer"},
                    },
                },
            },
        },
    }, indent=2) + "\n")

    # Sleek-minimal rework (2026-10-15): this generator no longer
    # emits a page. The presented site is the catalogue plus three
    # plain doors; this builder's data outputs are unchanged.

    idx = json.loads(API_INDEX.read_text())
    # idempotent: never re-append on re-run
    if "Changelog endpoint" not in idx["provenance"]:
        idx["provenance"] += " Changelog endpoint (site construction history from git log)."
    from api_manifest import render_manifest
    render_manifest(idx, ROOT)

    print(f"changelog: {len(entries)} entries -> changelog.html + JSON")
    return 0

if __name__ == "__main__":
    sys.exit(main())
