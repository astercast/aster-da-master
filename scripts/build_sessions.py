#!/usr/bin/env python3
"""Cluster SoundCloud vault uploads into studio sessions.

An upload session = consecutive uploads where the gap between uploads is
7 days or fewer. Each session becomes a "studio diary" entry: date span,
track count, total plays, and the tracks themselves.

Output:
  sessions.html            - standalone studio-diary page (root)
  data/sessions.json       - machine-readable sessions (site use)
  data/v1/sessions.json     - machine-readable sessions (public API)
  data/v1/schema/sessions.json - draft-07 schema
  (registers the endpoint in data/v1/index.json; bumps data to 0.10.0)

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
import nav_data  # noqa: E402  (canonical nav data — scripts/nav_data.py)

DATA = ROOT / "data" / "artist.json"
DATA_OUT = ROOT / "data" / "sessions.json"
API_OUT = ROOT / "data" / "v1" / "sessions.json"
API_INDEX = ROOT / "data" / "v1" / "index.json"
API_ARTIST = ROOT / "data" / "v1" / "artist.json"
SCHEMA_OUT = ROOT / "data" / "v1" / "schema" / "sessions.json"
PAGE_OUT = ROOT / "sessions.html"

NAV = "      " + nav_data.nav_chunk("", "ledger", "sessions.html")
FOOTNAV = "      " + nav_data.footer_block("", "ledger", "sessions.html")

NEW_VERSION = "0.19.0"  # wave 35: data version 0.18.0 (verified-data expansion)
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

    # Sleek-minimal rework (2026-10-15): this generator no longer
    # emits a page. The presented site is the catalogue plus three
    # plain doors; this builder's data outputs are unchanged.

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
