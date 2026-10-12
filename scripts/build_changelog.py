#!/usr/bin/env python3
"""Generate the site changelog from real git history.

The site documenting its own becoming: every commit on main becomes a
changelog entry with date, short hash, message, and files changed.

Output:
  changelog.html             - standalone changelog page (root)
  api/v1/changelog.json      - machine-readable changelog
  api/v1/schema/changelog.json - draft-07 schema
  (registers the endpoint in api/v1/index.json; no version bump here)

Idempotent: regenerates cleanly. Re-run after every push.
"""
import json
import subprocess
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_OUT = ROOT / "api" / "v1" / "changelog.json"
API_INDEX = ROOT / "api" / "v1" / "index.json"
SCHEMA_OUT = ROOT / "api" / "v1" / "schema" / "changelog.json"
PAGE_OUT = ROOT / "changelog.html"

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

    # ---- changelog.html ----
    rows = []
    for e in entries:
        rows.append(
            f'<li class="cl-entry reveal">'
            f'<span class="cl-hash" aria-label="commit {escape(e["hash"])}">'
            f'{escape(e["hash"])}</span>'
            f'<div><h3>{escape(e["message"])}</h3>'
            f'<p class="chart-sub">{escape(e["date"])} \u00b7 '
            f'{e["files_changed"]} file{"s" if e["files_changed"] != 1 else ""} changed</p>'
            f'</div></li>'
        )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Changelog \u2014 Aster da Master</title>
  <meta name="description" content="The construction history of the Aster da Master archive, generated from the site's own git log.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/css/tokens.css">
  <link rel="stylesheet" href="assets/css/base.css">
  <link rel="stylesheet" href="assets/css/layout.css">
  <link rel="stylesheet" href="assets/css/components.css">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="container header-bar">
      <a class="brand" href="./" aria-label="Aster da Master home">
        <span class="brand-mark" aria-hidden="true">A\u2726</span>
        <span>ASTER DA MASTER</span>
      </a>
      <nav class="site-nav" aria-label="Primary">
        <a href="./#discography">Discography</a>
        <a href="releases/">Releases</a>
        <a href="years/">Years</a>
        <a href="timeline.html">Timeline</a>
        <a href="network.html">Network</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="sessions.html">Sessions</a>
        <a href="changelog.html" aria-current="page">Changelog</a>
        <a href="method.html">Method</a>
        <a href="trilogy.html">Trilogy</a>
        <a href="glance.html">Glance</a>
        <a href="press-kit.html">Press kit</a>
      </nav>
      <details class="mnav">
        <summary><span class="bars" aria-hidden="true"><i></i><i></i><i></i></span>Menu</summary>
        <nav class="mnav-panel" aria-label="Mobile">
        <a href="./#discography">Discography</a>
        <a href="releases/">Releases</a>
        <a href="years/">Years</a>
        <a href="timeline.html">Timeline</a>
        <a href="network.html">Network</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="sessions.html">Sessions</a>
        <a href="changelog.html" aria-current="page">Changelog</a>
        <a href="method.html">Method</a>
        <a href="trilogy.html">Trilogy</a>
        <a href="glance.html">Glance</a>
        <a href="press-kit.html">Press kit</a>
      
        </nav>
      </details>
      <button class="search-btn" id="search-open" type="button" aria-label="Search the archive (keyboard shortcut: slash)">
        <span aria-hidden="true">\u2315</span><kbd aria-hidden="true">/</kbd>
      </button>
    </div>
  </header>

  <div class="search-overlay" id="search-overlay" hidden>
    <div class="search-box" role="dialog" aria-modal="true" aria-labelledby="search-title">
      <p class="kicker" id="search-title"><span class="numeral">\u2726</span>Search the archive</p>
      <input id="search-input" type="search" placeholder="Tracks, collaborators, eras, the codex\u2026" aria-label="Search the archive" role="combobox" aria-expanded="true" aria-controls="search-results" autocomplete="off" spellcheck="false">
      <div id="search-results" role="listbox" aria-label="Search results"></div>
      <p class="search-hint"><kbd>/</kbd> to open \u00b7 <kbd>\u2191</kbd><kbd>\u2193</kbd> to move \u00b7 <kbd>Enter</kbd> to go \u00b7 <kbd>Esc</kbd> to close</p>
    </div>
  </div>

  <main id="main">
    <div class="container">
      <div class="section-head reveal">
        <span class="kicker"><span class="numeral">\u2726</span>The becoming</span>
        <h1>Changelog</h1>
        <p>Every wave of this site's construction, newest first \u2014 generated from the repository's own git history. Nothing summarized, nothing invented.</p>
        <p class="chart-sub">{len(entries)} entries \u00b7 also at <a href="api/v1/changelog.json">api/v1/changelog.json</a></p>
      </div>
      <ol class="cl-list">{"".join(rows)}</ol>
    </div>
  </main>

  <footer class="site-footer">
    <div class="container footer-grid">
      <p>\u00a9 2026 ASTER DA MASTER \u2014 ALL SIGNALS RESERVED</p>
      <nav aria-label="Footer">
        <a href="./">Home</a>
        <a href="./#discography">Discography</a>
        <a href="releases/">Releases</a>
        <a href="years/">Years</a>
        <a href="timeline.html">Timeline</a>
        <a href="network.html">Network</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="sessions.html">Sessions</a>
        <a href="changelog.html" aria-current="page">Changelog</a>
        <a href="method.html">Method</a>
        <a href="trilogy.html">Trilogy</a>
        <a href="glance.html">Glance</a>
        <a href="press-kit.html">Press kit</a>
      </nav>
    </div>
  </footer>

  <script src="assets/js/common.js"></script>
</body>
</html>
"""
    PAGE_OUT.write_text(page, encoding="utf-8")

    idx = json.loads(API_INDEX.read_text())
    idx["endpoints"]["changelog"] = "api/v1/changelog.json"
    idx["provenance"] += " Changelog endpoint (site construction history from git log)."
    API_INDEX.write_text(json.dumps(idx, indent=2, ensure_ascii=False) + "\n")

    print(f"changelog: {len(entries)} entries -> changelog.html + JSON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
