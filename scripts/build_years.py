#!/usr/bin/env python3
"""Per-year archive data for the Aster da Master site.

RETIRED AS A PAGE GENERATOR in rotation 22 (page consolidation, user
order 2026-10-14): the years/ pages duplicated the Archive's own
listings, so the family is gone. The year's releases live in
releases/ now, the year's story in the eras. This module survives as
(a) the shared credit parser library (parse_collabs / era_for_year,
imported by build_circle and the session generators) and (b) the
emitter of data/v1/years.json, the machine-readable per-year stats
(registered in data/v1/index.json) — data, not a page.

Per year in the JSON: transmission count, total plays, top-10 tracks
by plays, distributor-vs-vault split, the era it belongs to.

Titles only - no lyrics anywhere. Idempotent: regenerates cleanly.
Re-run after any discography change.
"""
import json
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import nav_data  # noqa: E402  (canonical nav data — scripts/nav_data.py)
from build_releases import slugify  # noqa: E402  (single source of truth)

DATA = json.loads((ROOT / "data" / "artist.json").read_text())
YEARS = list(range(2018, 2027))
OUT = ROOT / "years"
API = ROOT / "data" / "v1"

# Rotation 22: no nav chunk — this module emits no pages anymore
# (the "years" nav variant is retired in nav_data.py with the family).

def parse_collabs(title):
    """Port of assets/js/common.js parseCollabs: credit names from the
    title's own w//ft./feat. fragments. Nothing invented."""
    names = []
    for m in re.finditer(r"(?:\bw\/\s*|\bft\.?\s+|\bfeat\.?\s+)", title, re.I):
        rest = title[m.end():]
        rest = re.split(r"[(\[]", rest)[0]
        rest = re.split(r"prod\.?", rest, flags=re.I)[0]
        for p in re.split(r"\s+[xX]\s+|\s*&\s*|\s*\+\s*|,|\s*/\s*|\s+and\s+", rest):
            p = re.sub(r"^[ .!~)\"']+|[ .!~)\"']+$", "", p)
            if (
                p
                and len(p) < 30
                and not re.search(r"aster\s*da\s*master", p, re.I)
                and not re.search(r"prod", p, re.I)
            ):
                names.append(p)
    return names

def era_for_year(year, eras):
    for e in eras:
        m = re.search(r"(\d{4})(?:\s*[–—-]\s*(\d{4}))?", str(e.get("span") or ""))
        if not m:
            continue
        start, end = int(m.group(1)), int(m.group(2) or m.group(1))
        if start <= year <= end:
            return e
    return None

def fmt(n):
    return f"{n:,}"

def main():
    releases = DATA["discography"]
    eras = DATA.get("eras", [])

    # Slug list identical to build_search_index.py (single source of truth).
    used, slugs = set(), []
    for r in releases:
        s = slugify(r["title"])
        base, n = s, 1
        while s in used:
            n += 1
            s = f"{base}-{n}"
        used.add(s)
        slugs.append(s)
    assert len(set(slugs)) == len(releases), "slug collision"
    slug_of = {id(r): s for r, s in zip(releases, slugs)}

    by_year = {y: [] for y in YEARS}
    for r in releases:
        date = r.get("date") or ""
        m = re.match(r"^(\d{4})-\d{2}-\d{2}$", date)
        if m and int(m.group(1)) in by_year:
            by_year[int(m.group(1))].append(r)

    summaries = {}
    api_years = {}
    for y in YEARS:
        entries = by_year[y]
        era = era_for_year(y, eras)
        by_plays = sorted(entries, key=lambda r: -(r.get("plays") or 0))
        summaries[y] = {
            "count": len(entries),
            "plays": sum(r.get("plays") or 0 for r in entries),
            "era": era["name"] if era else "",
            "top": by_plays[0]["title"] if by_plays and (by_plays[0].get("plays") or 0) else "",
        }
        api_years[str(y)] = {
            "page": "releases/",
            "transmissions": len(entries),
            "plays": summaries[y]["plays"],
            "distributor": sum(1 for r in entries if r["type"] != "SoundCloud-only"),
            "vault": sum(1 for r in entries if r["type"] == "SoundCloud-only"),
            "era": era["name"] if era else None,
            "top_tracks": [
                {"title": r["title"], "plays": r.get("plays") or 0, "date": r.get("date")}
                for r in by_plays[:10]
            ],
        }

    # Rotation 22: the year pages are retired; remove any that remain
    # so a rebuild can never resurrect the family.
    if OUT.exists():
        for f in OUT.glob("*.html"):
            f.unlink()
        try:
            OUT.rmdir()
        except OSError:
            pass
    (API / "years.json").write_text(
        json.dumps(api_years, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"years: pages retired (rotation 22); data/v1/years.json only")

if __name__ == "__main__":
    main()
