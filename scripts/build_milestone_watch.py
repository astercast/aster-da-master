#!/usr/bin/env python3
"""Milestone watch: vault tracks near round-number play counts.

Bands (from the 2026-10-11 play-count snapshot):
  - closing in on 1,000 plays   (900-999)
  - closing in on 10,000 plays  (9,000-9,999)
  - the 30k summit              (27,000-29,999; Take Me already crossed)

Output:
  data/milestone-watch.json
  api/v1/milestone-watch.json
  api/v1/schema/milestone-watch.json
  (registers the endpoint in api/v1/index.json; bumps data to 0.11.0)

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
DATA_OUT = ROOT / "data" / "milestone-watch.json"
API_OUT = ROOT / "api" / "v1" / "milestone-watch.json"
API_INDEX = ROOT / "api" / "v1" / "index.json"
API_ARTIST = ROOT / "api" / "v1" / "artist.json"
SCHEMA_OUT = ROOT / "api" / "v1" / "schema" / "milestone-watch.json"

NEW_VERSION = "0.11.0"
SNAPSHOT = "2026-10-11"

BANDS = [
    {
        "id": "near-1k",
        "target": 1000,
        "lo": 900,
        "hi": 999,
        "name": "Closing in on 1,000 plays",
        "blurb": "Transmissions within 100 plays of the thousand mark.",
    },
    {
        "id": "near-10k",
        "target": 10000,
        "lo": 9000,
        "hi": 9999,
        "name": "Closing in on 10,000 plays",
        "blurb": "Transmissions within 1,000 plays of five figures.",
    },
    {
        "id": "near-30k",
        "target": 30000,
        "lo": 27000,
        "hi": 29999,
        "name": "The 30k summit",
        "blurb": "Transmissions approaching 30,000 plays — the highest summit in the vault.",
    },
]


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

    vault = [r for r in releases if r.get("type") == "SoundCloud-only"]

    bands = []
    for b in BANDS:
        tracks = sorted(
            (r for r in vault if b["lo"] <= (r.get("plays") or 0) <= b["hi"]),
            key=lambda r: -(r.get("plays") or 0),
        )
        bands.append({
            "id": b["id"],
            "name": b["name"],
            "target": b["target"],
            "blurb": b["blurb"],
            "tracks": [{
                "title": r["title"],
                "plays": r["plays"],
                "needed": b["target"] - r["plays"],
                "date": r.get("date"),
                "page": f"releases/{slug_of[id(r)]}.html",
            } for r in tracks],
        })

    # Summit holder: the highest-play vault track (context for the 30k band).
    champ = max(vault, key=lambda r: r.get("plays") or 0)

    record = {
        "version": NEW_VERSION,
        "generated": SNAPSHOT,
        "plays_snapshot": SNAPSHOT,
        "method": ("Vault tracks grouped by proximity to round-number play counts, "
                   "from the 2026-10-11 snapshot. Play counts drift; the watch "
                   "is a snapshot, not a live leaderboard."),
        "summit": {
            "title": champ["title"],
            "plays": champ["plays"],
            "date": champ.get("date"),
            "page": f"releases/{slug_of[id(champ)]}.html",
            "note": ("The highest-play transmission in the vault. "
                     "Nothing else is within 3,000 plays of 30,000.") if champ["plays"] >= 30000
            else "The highest-play transmission in the vault.",
        },
        "bands": bands,
    }
    DATA_OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    API_OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")

    SCHEMA_OUT.write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Milestone watch",
        "description": "Vault tracks near round-number play counts (2026-10-11 snapshot).",
        "type": "object",
        "required": ["bands", "summit"],
        "properties": {
            "bands": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name", "target", "tracks"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "target": {"type": "integer"},
                        "blurb": {"type": "string"},
                        "tracks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["title", "plays", "needed", "page"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "plays": {"type": "integer"},
                                    "needed": {"type": "integer"},
                                    "date": {"type": ["string", "null"]},
                                    "page": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
            "summit": {"type": "object"},
        },
    }, indent=2) + "\n")

    d["version"] = NEW_VERSION
    DATA.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    ad = json.loads(API_ARTIST.read_text())
    ad["version"] = NEW_VERSION
    API_ARTIST.write_text(json.dumps(ad, indent=2, ensure_ascii=False) + "\n")
    idx = json.loads(API_INDEX.read_text())
    idx["version"] = NEW_VERSION
    idx["observed"] = SNAPSHOT
    idx["endpoints"]["milestone-watch"] = "api/v1/milestone-watch.json"
    idx["provenance"] += (" v0.11.0: milestone-watch endpoint "
                          "(vault tracks near round-number play counts).")
    API_INDEX.write_text(json.dumps(idx, indent=2, ensure_ascii=False) + "\n")

    counts = ", ".join(f"{b['id']}: {len(b['tracks'])}" for b in bands)
    print(f"milestone-watch: {counts} -> JSON + schema, version {NEW_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
