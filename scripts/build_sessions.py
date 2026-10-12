#!/usr/bin/env python3
"""Cluster SoundCloud vault uploads into studio sessions.

An upload session = consecutive uploads where the gap between uploads is
7 days or fewer. Each session becomes a "studio diary" entry: date span,
track count, total plays, and the tracks themselves.

Output:
  sessions.html            - standalone studio-diary page (root)
  data/sessions.json       - machine-readable sessions (site use)
  api/v1/sessions.json     - machine-readable sessions (public API)
  api/v1/schema/sessions.json - draft-07 schema
  (registers the endpoint in api/v1/index.json; bumps data to 0.10.0)

Titles only - no lyrics anywhere. Idempotent: regenerates cleanly.
Re-run after any discography change.
"""
import json
import re
import sys
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_releases import slugify  # noqa: E402  (single source of truth)

DATA = ROOT / "data" / "artist.json"
DATA_OUT = ROOT / "data" / "sessions.json"
API_OUT = ROOT / "api" / "v1" / "sessions.json"
API_INDEX = ROOT / "api" / "v1" / "index.json"
API_ARTIST = ROOT / "api" / "v1" / "artist.json"
SCHEMA_OUT = ROOT / "api" / "v1" / "schema" / "sessions.json"
PAGE_OUT = ROOT / "sessions.html"

NEW_VERSION = "0.13.0"
SNAPSHOT = "2026-10-11"
GAP_DAYS = 7

MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
MON_ABBR = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def parse(d: str) -> date:
    y, m, day = (int(x) for x in d.split("-"))
    return date(y, m, day)


def session_name(start: date, end: date) -> str:
    if start == end:
        return f"The {MONTHS[start.month]} {ordinal(start.day)} Session"
    if start.month == end.month and start.year == end.year:
        return (f"The {MONTHS[start.month]} {ordinal(start.day)}"
                f"\u2013{ordinal(end.day)} Session")
    return (f"The {MON_ABBR[start.month]} {ordinal(start.day)}"
            f" \u2013 {MON_ABBR[end.month]} {ordinal(end.day)} Session")


def session_slug(name: str) -> str:
    """URL slug for a session deep-dive page.

    Single source of truth shared with scripts/build_session_deepdives.py.
    Session names are unique, so no dedup suffix is needed (asserted there).
    """
    return slugify(name)


def main() -> int:
    d = json.loads(DATA.read_text())
    releases = d["discography"]

    # slug map identical to build_releases (dedup by title order)
    used, slugs = set(), []
    for r in releases:
        s = slugify(r["title"])
        base, n = s, 1
        while s in used:
            n += 1
            s = f"{base}-{n}"
        used.add(s)
        slugs.append(s)
    slug_of = {id(r): s for r, s in zip(releases, slugs)}

    vault = [r for r in releases
             if r.get("type") == "SoundCloud-only" and r.get("date")]
    vault.sort(key=lambda r: r["date"])

    sessions = []
    cur = []
    for r in vault:
        if cur and (parse(r["date"]) - parse(cur[-1]["date"])).days > GAP_DAYS:
            sessions.append(cur)
            cur = []
        cur.append(r)
    if cur:
        sessions.append(cur)

    out = []
    for i, tracks in enumerate(sessions, 1):
        start, end = parse(tracks[0]["date"]), parse(tracks[-1]["date"])
        total_plays = sum(t.get("plays") or 0 for t in tracks)
        out.append({
            "id": f"session-{i:02d}",
            "name": session_name(start, end),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": (end - start).days + 1,
            "track_count": len(tracks),
            "total_plays": total_plays,
            "tracks": [{
                "title": t["title"],
                "date": t["date"],
                "plays": t.get("plays"),
                "page": f"releases/{slug_of[id(t)]}.html",
            } for t in tracks],
        })

    record = {
        "version": NEW_VERSION,
        "generated": SNAPSHOT,
        "plays_snapshot": SNAPSHOT,
        "method": ("Vault uploads clustered by date: a new session starts "
                   f"when the gap between uploads exceeds {GAP_DAYS} days. "
                   "Computed from data/artist.json; every session is a data fact."),
        "session_count": len(out),
        "track_count": sum(s["track_count"] for s in out),
        "sessions": out,
    }
    DATA_OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    API_OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")

    SCHEMA_OUT.write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Upload sessions",
        "description": "SoundCloud vault uploads clustered into studio sessions (7-day gap rule), from data/artist.json.",
        "type": "object",
        "required": ["sessions"],
        "properties": {
            "sessions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name", "start", "end", "track_count", "tracks"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "start": {"type": "string"},
                        "end": {"type": "string"},
                        "track_count": {"type": "integer"},
                        "total_plays": {"type": "integer"},
                        "tracks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["title", "date", "page"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "date": {"type": "string"},
                                    "plays": {"type": ["integer", "null"]},
                                    "page": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        },
    }, indent=2) + "\n")

    # ---- sessions.html ----
    def fmt_plays(n):
        return f"{n:,} plays" if n else "plays uncounted"

    # Top-10 sessions by track count get deep-dive pages
    # (scripts/build_session_deepdives.py). Same sort rule there.
    deep_ids = {s["id"] for s in
                sorted(out, key=lambda s: (-s["track_count"], -s["total_plays"]))[:10]}

    cards = []
    for s in reversed(out):  # newest first
        span = s["start"] if s["start"] == s["end"] else f'{s["start"]} \u2013 {s["end"]}'
        tracks_html = "".join(
            f'<li><a href="{escape(t["page"])}">{escape(t["title"])}</a>'
            f' <span class="chart-sub">{escape(t["date"])} \u00b7 '
            f'{escape(fmt_plays(t["plays"]))}</span></li>'
            for t in s["tracks"]
        )
        cards.append(
            f'<article class="session-card reveal" aria-labelledby="{s["id"]}">'
            f'<div class="section-head"><span class="kicker">'
            f'<span class="numeral">\u2726</span>{escape(span)}</span>'
            f'<h3 id="{s["id"]}">{escape(s["name"])}</h3>'
            f'<p>{s["track_count"]} transmission{"s" if s["track_count"] != 1 else ""} '
            f'\u00b7 {escape(fmt_plays(s["total_plays"]))} '
            f'<span class="chart-sub">(snapshot {SNAPSHOT})</span></p></div>'
            f'<ol class="session-tracks">{tracks_html}</ol>'
            + (f'<p><a class="btn btn-sm" href="sessions/{session_slug(s["name"])}.html">'
               f'Deep dive &rarr;</a></p>' if s["id"] in deep_ids else "")
            + '</article>'
        )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Upload sessions \u2014 Aster da Master</title>
  <meta name="description" content="Every SoundCloud upload session, clustered by date: the studio diary of nine years of transmissions.">
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
        <a href="transmission.html">Transmission</a>
        <a href="network.html">Network</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="sessions.html" aria-current="page">Sessions</a>
        <a href="changelog.html">Changelog</a>
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
        <a href="transmission.html">Transmission</a>
        <a href="network.html">Network</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="sessions.html" aria-current="page">Sessions</a>
        <a href="changelog.html">Changelog</a>
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
        <span class="kicker"><span class="numeral">\u2726</span>The studio diary</span>
        <h1>Upload sessions</h1>
        <p>{len(out)} sessions \u00b7 {sum(s["track_count"] for s in out)} vault transmissions. A new session begins whenever the silence between uploads stretches past seven days. Newest first.</p>
        <p class="chart-sub">Computed from upload dates \u00b7 play counts are a {SNAPSHOT} snapshot \u00b7 also at <a href="api/v1/sessions.json">api/v1/sessions.json</a></p>
        <p><a class="btn btn-sm" href="sessions-explorer.html">Sessions explorer &rarr;</a> <span class="chart-sub">the 61 sessions as an explorable timeline: activity seasons, the silences, per-session deepest cuts.</span></p>
      </div>
      {"".join(cards)}
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
        <a href="transmission.html">Transmission</a>
        <a href="network.html">Network</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="sessions.html" aria-current="page">Sessions</a>
        <a href="changelog.html">Changelog</a>
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

    # ---- version bump + API index registration ----
    d["version"] = NEW_VERSION
    (ROOT / "data" / "artist.json").write_text(
        json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    ad = json.loads(API_ARTIST.read_text())
    ad["version"] = NEW_VERSION
    API_ARTIST.write_text(json.dumps(ad, indent=2, ensure_ascii=False) + "\n")
    idx = json.loads(API_INDEX.read_text())
    idx["version"] = NEW_VERSION
    idx["observed"] = SNAPSHOT
    # idempotent: the upload-sessions endpoint was introduced at v0.10.0; never re-append
    if "upload-sessions endpoint" not in idx["provenance"]:
        idx["provenance"] += (" v0.10.0: upload-sessions endpoint "
                              f"({len(out)} sessions clustered from vault upload dates).")
    from api_manifest import render_manifest
    render_manifest(idx, ROOT)

    print(f"sessions: {len(out)} sessions / "
          f"{sum(s['track_count'] for s in out)} tracks -> sessions.html + JSON, "
          f"version {NEW_VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
