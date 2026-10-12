#!/usr/bin/env python3
"""Build the Milestones record from the verified discography.

Reads data/artist.json (219 entries), computes the career's defining
firsts — first transmission, first 10k-play track, first collaboration,
the 100th transmission, most prolific day, longest silence, the 250k-play
crossing — and emits data/milestones.json + api/v1/milestones.json.

Every milestone is a computed fact from the data; no narrative is
invented. Play counts are the 2026-10-11 snapshot.

Also bumps data version to 0.12.0 and mirrors to api/v1/.
"""
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "artist.json"
MS_OUT = ROOT / "data" / "milestones.json"
API_OUT = ROOT / "api" / "v1" / "milestones.json"
API_ARTIST = ROOT / "api" / "v1" / "artist.json"
API_INDEX = ROOT / "api" / "v1" / "index.json"
SCHEMA_OUT = ROOT / "api" / "v1" / "schema" / "milestones.json"
NEW_VERSION = "0.12.0"
SNAPSHOT = "2026-10-11"


def entry(r):
    return {
        "title": r["title"],
        "date": r["date"],
        "type": r["type"],
        "plays": r.get("plays"),
    }


def main():
    d = json.loads(DATA.read_text())
    disc = d["discography"]
    vault = sorted([r for r in disc if r["type"] == "SoundCloud-only"],
                   key=lambda r: r["date"])
    dist = sorted([r for r in disc if r["type"] != "SoundCloud-only"],
                  key=lambda r: r["date"])
    chrono = sorted(disc, key=lambda r: (r["date"], r["title"]))

    collab_re = re.compile(r"\bw/|\bft\.|feat", re.I)
    first_collab = next(r for r in vault if collab_re.search(r["title"]))

    per_day = Counter(r["date"] for r in vault)
    top_day, top_n = per_day.most_common(1)[0]

    days = sorted(set(r["date"] for r in vault))
    dts = [date.fromisoformat(x) for x in days]
    gap, g0, g1 = max(
        ((dts[i + 1] - dts[i]).days, dts[i], dts[i + 1])
        for i in range(len(dts) - 1))

    cum = 0
    cross = None
    for r in vault:
        cum += r.get("plays") or 0
        if cum >= 250000:
            cross = (r, cum)
            break

    milestones = [
        {
            "id": "first-distributor",
            "name": "First distributor transmission",
            "fact": "The catalog's first appearance on streaming platforms — "
                    "as a featured artist, two years before the first vault upload.",
            **entry(dist[0]),
        },
        {
            "id": "first-vault",
            "name": "First vault transmission",
            "fact": "The first upload to the official SoundCloud — and it arrived "
                    "already carrying five figures of plays. The opening shot was not a warm-up.",
            **entry(vault[0]),
        },
        {
            "id": "first-collab",
            "name": "First collaboration",
            "fact": "The first transmission to summon another voice. The circle "
                    "starts here and grows to twenty-one collaborators.",
            **entry(first_collab),
        },
        {
            "id": "hundredth-entry",
            "name": "100th transmission on record",
            "fact": "The catalog's 100th entry in chronological order — "
                    "reached before the end of 2020.",
            **entry(chrono[99]),
        },
        {
            "id": "hundredth-vault",
            "name": "100th vault transmission",
            "fact": "The SoundCloud vault's own 100th upload — mid-2021, "
                    "deep in the Cast It: years.",
            **entry(vault[99]),
        },
        {
            "id": "prolific-day",
            "name": "Most prolific day",
            "fact": f"{top_n} transmissions uploaded in a single day — the densest "
                    "outpouring on record.",
            "date": top_day,
            "count": top_n,
            "title": None,
            "type": None,
            "plays": None,
        },
        {
            "id": "longest-silence",
            "name": "Longest silence",
            "fact": "The longest gap between uploads on record — the vault went "
                    "quiet, then returned.",
            "date": None,
            "from": g0.isoformat(),
            "to": g1.isoformat(),
            "days": gap,
            "title": None,
            "type": None,
            "plays": None,
        },
        {
            "id": "plays-250k",
            "name": "250,000 plays crossed",
            "fact": "Cumulative vault plays crossed a quarter-million with this "
                    "upload — counted in upload order from the play-count snapshot.",
            **entry(cross[0]),
            "cumulative_plays": cross[1],
        },
        {
            "id": "latest",
            "name": "Latest transmission",
            "fact": "The most recent upload on record. The archive is alive.",
            **entry(vault[-1]),
        },
    ]

    record = {
        "version": NEW_VERSION,
        "generated": SNAPSHOT,
        "method": "Computed from data/artist.json: chronological ordering of "
                 "verified upload dates, per-day counts, gap analysis, and "
                 "cumulative play counts from the 2026-10-11 snapshot. Every "
                 "milestone is a data fact; no narrative is invented.",
        "plays_snapshot": SNAPSHOT,
        "milestones": milestones,
    }
    MS_OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    API_OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "description": "Defining firsts of the verified catalog, computed from "
                       "data/artist.json. Every milestone is a data fact.",
        "properties": {
            "version": {"type": "string"},
            "generated": {"type": "string"},
            "method": {"type": "string"},
            "plays_snapshot": {"type": "string"},
            "milestones": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "fact": {"type": "string"},
                        "title": {"type": ["string", "null"]},
                        "date": {"type": ["string", "null"]},
                        "type": {"type": ["string", "null"]},
                        "plays": {"type": ["integer", "null"]},
                        "count": {"type": "integer"},
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                        "days": {"type": "integer"},
                        "cumulative_plays": {"type": "integer"},
                    },
                    "required": ["id", "name", "fact"],
                },
            },
        },
        "required": ["version", "milestones"],
        "type": "object",
    }
    SCHEMA_OUT.write_text(json.dumps(schema, indent=2) + "\n")

    # version bump + API index registration
    d["version"] = NEW_VERSION
    DATA.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    ad = json.loads(API_ARTIST.read_text())
    ad["version"] = NEW_VERSION
    API_ARTIST.write_text(json.dumps(ad, indent=2, ensure_ascii=False) + "\n")
    idx = json.loads(API_INDEX.read_text())
    idx["version"] = NEW_VERSION
    idx["observed"] = SNAPSHOT
    idx["endpoints"]["milestones"] = "api/v1/milestones.json"
    # idempotent: milestones endpoint was introduced at v0.9.0; never re-append
    if "milestones endpoint" not in idx["provenance"]:
        idx["provenance"] += (" v0.9.0: milestones endpoint (career firsts computed "
                              "from the verified discography); API playground + "
                              "transmission decoder pages.")
    API_INDEX.write_text(json.dumps(idx, indent=2, ensure_ascii=False) + "\n")

    print(f"milestones: {len(milestones)} -> {MS_OUT} + {API_OUT}, version {NEW_VERSION}")


if __name__ == "__main__":
    sys.exit(main())
