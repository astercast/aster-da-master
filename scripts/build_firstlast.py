#!/usr/bin/env python3
"""First & last transmission of each year (2018-2026).

"The year opened with X and closed with Y." Pure data: chronological
ordering of every archive entry by its verified date.

Output:
  data/first-last.json        - machine-readable (site use)
  data/v1/first-last.json      - machine-readable (public API)
  data/v1/schema/first-last.json - draft-07 schema
  (registers the endpoint in data/v1/index.json; no version bump here)

Titles only - no lyrics anywhere. Idempotent: regenerates cleanly.
Re-run after any discography change.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_releases import slugify  # noqa: E402  (single source of truth)

DATA = ROOT / "data" / "artist.json"
DATA_OUT = ROOT / "data" / "first-last.json"
API_OUT = ROOT / "data" / "v1" / "first-last.json"
API_INDEX = ROOT / "data" / "v1" / "index.json"
SCHEMA_OUT = ROOT / "data" / "v1" / "schema" / "first-last.json"

SNAPSHOT = "2026-10-11"
YEARS = list(range(2018, 2027))


def main() -> int:
    d = json.loads(DATA.read_text())
    releases = d["discography"]

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

    def entry(r):
        return {
            "title": r["title"],
            "date": r["date"],
            "type": r.get("type"),
            "plays": r.get("plays"),
            "page": f"releases/{slug_of[id(r)]}.html",
        }

    years = []
    for y in YEARS:
        in_year = sorted(
            (r for r in releases if r.get("date", "").startswith(str(y))),
            key=lambda r: r["date"],
        )
        if not in_year:
            continue
        years.append({
            "year": y,
            "count": len(in_year),
            "opened_with": entry(in_year[0]),
            "closed_with": entry(in_year[-1]),
        })

    record = {
        "generated": SNAPSHOT,
        "method": ("Per year 2018-2026: the chronologically first and last "
                   "archive entries by verified date. Computed from "
                   "data/artist.json; every pairing is a data fact."),
        "years": years,
    }
    DATA_OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    API_OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")

    SCHEMA_OUT.write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "First & last transmissions",
        "description": "Per year, the chronologically first and last archive entries by verified date.",
        "type": "object",
        "required": ["years"],
        "properties": {
            "years": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["year", "opened_with", "closed_with"],
                    "properties": {
                        "year": {"type": "integer"},
                        "count": {"type": "integer"},
                        "opened_with": {"$ref": "#/definitions/entry"},
                        "closed_with": {"$ref": "#/definitions/entry"},
                    },
                },
            },
        },
        "definitions": {
            "entry": {
                "type": "object",
                "required": ["title", "date", "page"],
                "properties": {
                    "title": {"type": "string"},
                    "date": {"type": "string"},
                    "type": {"type": ["string", "null"]},
                    "plays": {"type": ["integer", "null"]},
                    "page": {"type": "string"},
                },
            },
        },
    }, indent=2) + "\n")

    idx = json.loads(API_INDEX.read_text())
    # idempotent: never re-append on re-run
    if "First-and-last endpoint" not in idx["provenance"]:
        idx["provenance"] += " First-and-last endpoint (per-year opening/closing transmissions)."
    from api_manifest import render_manifest
    render_manifest(idx, ROOT)

    print(f"first-last: {len(years)} years -> data/first-last.json + JSON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
