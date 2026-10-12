#!/usr/bin/env python3
"""Wave 19: session archaeology interactive.

Turns the `session-archaeology` skill's logic into browsable data:
api/v1/session-clusters.json (endpoint #17) - the 61 upload sessions as an
explorable timeline:

  - sessions[]      - per-session enrichment: era, loudest + deepest-cut
                      tracks (asserted min/max), title-credited collaborators,
                      deep-dive link (top-10 only), era deep-dive + journey
                      cross-links
  - gaps[]          - the 60 inter-session silences, in days
  - silences        - top-5 longest silences (the 553-day record is #1,
                      asserted equal to milestones.json's longest-silence)
  - clusters[]      - "activity seasons": consecutive sessions grouped while
                      the separating silence is <= SEASON_GAP_DAYS (90).
                      A computed browsing convention, stated as such - not
                      an artist fact.
  - eras[]          - the 6 eras with deep_dive + journey links, for the
                      explorer's era filter
  - insights        - session count, most prolific session (session-40,
                      19 tracks, 2023-11-03 -> 2023-11-12, asserted), longest
                      silence, season count, first/last session, loudest and
                      quietest sessions by total plays

Every figure is recomputed here and the script exits non-zero on any
disagreement. Sources (all real archive data):
  - data/sessions.json            (61 sessions, 7-day gap rule)
  - api/v1/sessions.json          (track counts for the records assertion)
  - api/v1/milestones.json        (longest-silence canonical record)
  - api/v1/eras.json              (era ids/names/spans/deep_dive/journey)
  - scripts/build_transmission.py (ERA_YEARS, LONGEST_GAP)
  - scripts/build_years.py        (parse_collabs - shared credit rule)
  - sessions/                     (deep-dive pages that exist on disk)

No payload shape changes to any existing endpoint; data version stays
0.13.0 (no source data changed). Titles and metadata only - never lyrics,
never invented bio facts.

Runs LAST in the validate.sh generator chain (after build_eras).
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "api" / "v1"
NEW_VERSION = "0.15.0"  # wave 30 merge: Uncle re-verified + new facts
SNAPSHOT = "2026-10-11"

sys.path.insert(0, str(ROOT / "scripts"))
from build_transmission import ERA_YEARS, LONGEST_GAP  # noqa: E402
from build_years import parse_collabs  # noqa: E402
from build_session_deepdives import session_slug  # noqa: E402 (shared rule)

SESS = json.loads((ROOT / "data" / "sessions.json").read_text())["sessions"]
API_SESS = json.loads((API / "sessions.json").read_text())
ERAS = json.loads((API / "eras.json").read_text())["eras"]
MS = json.loads((API / "milestones.json").read_text())["milestones"]

# Computed-convention thresholds (stated in the payload's method, not facts)
GAP_RULE_DAYS = 7      # the upload-gap rule sessions are built on
SEASON_GAP_DAYS = 90   # a silence longer than this opens a new activity season
TOP_SILENCES = 5       # how many of the longest silences to name

ERA_BY_YEAR = {}
for name, years in ERA_YEARS.items():
    for y in years:
        ERA_BY_YEAR[y] = name
ERA_BY_ID = {e["id"]: e for e in ERAS}
ERA_BY_NAME = {e["name"]: e for e in ERAS}


def parse(d: str) -> date:
    y, m, day = (int(x) for x in d.split("-"))
    return date(y, m, day)


def era_for_session(s):
    """Map a session to its era by start year (sessions never cross the
    2022->2023 silence or any era boundary except the 7-day rule's own;
    asserted below that every session lands exactly one era)."""
    year = s["start"][:4]
    assert year in ERA_BY_YEAR, f"session {s['id']} start-year {year} has no era"
    return ERA_BY_NAME[ERA_BY_YEAR[year]]


def main() -> int:
    sessions = SESS
    assert len(sessions) == 61, f"session count drift: {len(sessions)}"
    assert [s["id"] for s in sessions] == \
        [f"session-{i:02d}" for i in range(1, 62)], "session id drift"

    # total vault tracks must equal what sessions.json claims
    total_tracks = sum(s["track_count"] for s in sessions)
    assert total_tracks == API_SESS["track_count"], \
        f"vault track drift: {total_tracks} vs {API_SESS['track_count']}"

    # --- inter-session gaps (in days, canonical counting) ---
    gaps = []
    for a, b in zip(sessions, sessions[1:]):
        days = (parse(b["start"]) - parse(a["end"])).days
        # sessions are 7-day clusters, so any inter-session gap is > 7
        assert days > GAP_RULE_DAYS, \
            f"gap {a['id']}->{b['id']} = {days}d, breaks the 7-day rule"
        gaps.append({
            "from_session": a["id"], "to_session": b["id"],
            "from_end": a["end"], "to_start": b["start"], "days": days,
        })
    assert len(gaps) == 60, "gap count drift"

    # the longest silence must match the canonical milestone record
    rec = next(m for m in MS if m["id"] == "longest-silence")
    longest = max(gaps, key=lambda g: g["days"])
    assert rec["days"] == longest["days"] == LONGEST_GAP["days"] == 553, \
        "longest-silence drift"
    assert (rec["from"], rec["to"]) == \
        (longest["from_end"], longest["to_start"]) == \
        (LONGEST_GAP["from"], LONGEST_GAP["to"]) == ("2022-02-22", "2023-08-29"), \
        "longest-silence date drift"

    silences = sorted(gaps, key=lambda g: -g["days"])[:TOP_SILENCES]
    assert len(silences) == TOP_SILENCES and len({s["days"] for s in silences}) == TOP_SILENCES, \
        "top-silence ties would need a named tiebreak"

    # --- activity seasons: consecutive sessions while silence <= 90 days ---
    clusters = []
    cur = [sessions[0]]
    for g, s in zip(gaps, sessions[1:]):
        if g["days"] > SEASON_GAP_DAYS:
            clusters.append(cur)
            cur = []
        cur.append(s)
    clusters.append(cur)
    # seasons partition the 61 sessions exactly once, in order
    assert sum(len(c) for c in clusters) == 61, "season partition drift"
    assert [s["id"] for c in clusters for s in c] == [s["id"] for s in sessions], \
        "season order drift"

    cluster_out = []
    for i, members in enumerate(clusters, 1):
        cluster_out.append({
            "id": f"season-{i:02d}",
            "label": f"Season {i}",
            "start": members[0]["start"],
            "end": members[-1]["end"],
            "session_count": len(members),
            "track_count": sum(s["track_count"] for s in members),
            "total_plays": sum(s["total_plays"] for s in members),
            "session_ids": [s["id"] for s in members],
        })
    season_count = len(cluster_out)
    assert season_count == 9, f"season count drift: {season_count}"

    # --- per-session enrichment ---
    deep_slugs = {p.stem for p in (ROOT / "sessions").glob("*.html")}
    assert len(deep_slugs) == 10, f"deep-dive page drift: {len(deep_slugs)}"

    enriched = []
    for s in sessions:
        era = era_for_session(s)
        # loudest / deepest: deterministic tiebreak (plays, date, title)
        by_loud = sorted(s["tracks"],
                         key=lambda t: (-(t["plays"] or 0), t["date"], t["title"]))
        by_deep = sorted(s["tracks"],
                         key=lambda t: ((t["plays"] or 0), t["date"], t["title"]))
        loud, deep = by_loud[0], by_deep[0]
        # independent recompute guards the sorts
        assert loud["plays"] == max(t["plays"] or 0 for t in s["tracks"])
        assert deep["plays"] == min(t["plays"] or 0 for t in s["tracks"])

        collabs = []
        for t in s["tracks"]:
            for c in parse_collabs(t["title"]):
                if c not in collabs:
                    collabs.append(c)

        # deep-dive link: resolved below via the shared session_slug rule
        deep_dive = None
        enriched.append({
            "id": s["id"], "name": s["name"],
            "start": s["start"], "end": s["end"], "days": s["days"],
            "track_count": s["track_count"], "total_plays": s["total_plays"],
            "era_id": era["id"], "era_name": era["name"],
            "loudest": {"title": loud["title"], "plays": loud["plays"],
                        "date": loud["date"], "page": loud["page"]},
            "deepest_cut": {"title": deep["title"], "plays": deep["plays"],
                            "date": deep["date"], "page": deep["page"]},
            "collaborators": collabs,
            "deep_dive": deep_dive,  # patched below via session_slug
            "journey": era["journey"],
            "season": None,  # patched below
        })

    # map sessions to deep-dive slugs: the deep-dive pages are the top-10 by
    # track count (same rule as build_sessions.py / build_session_deepdives.py)
    deep_ids = {s["id"] for s in sorted(
        enriched, key=lambda s: (-s["track_count"], -s["total_plays"]))[:10]}
    slug_of = {}
    seen_slugs = set()
    for s in SESS:
        if s["id"] not in deep_ids:
            continue  # only the top-10 get deep-dive pages (uniqueness
        # asserted by build_session_deepdives.py; names can repeat outside
        # the top-10, e.g. two "April 28th" single-day sessions)
        sl = session_slug(s["name"])
        assert sl not in seen_slugs, f"deep-dive slug collision: {sl}"
        seen_slugs.add(sl)
        slug_of[s["id"]] = sl
        assert (ROOT / "sessions" / (sl + ".html")).exists(), \
            f"missing deep-dive page for {s['id']}"
    for e in enriched:
        e["deep_dive"] = ("sessions/" + slug_of[e["id"]] + ".html"
                          if e["id"] in deep_ids else None)

    # attach season ids
    for c in cluster_out:
        for sid in c["session_ids"]:
            next(e for e in enriched if e["id"] == sid)["season"] = c["id"]
    assert all(e["season"] for e in enriched), "unseasoned session"

    # every session's era deep-dive page + journey link must exist on disk
    for e in enriched:
        assert (ROOT / ("eras/" + e["era_id"] + ".html")).exists(), \
            f"missing era deep-dive page for {e['id']}"

    # --- insights (all asserted) ---
    most_prolific = max(enriched, key=lambda s: (s["track_count"], s["total_plays"]))
    assert (most_prolific["id"], most_prolific["track_count"],
            most_prolific["start"], most_prolific["end"]) == \
        ("session-40", 19, "2023-11-03", "2023-11-12"), "most-prolific drift"
    loudest = max(enriched, key=lambda s: (s["total_plays"], s["track_count"]))
    quietest = min(enriched, key=lambda s: (s["total_plays"], s["track_count"]))
    assert (loudest["id"], loudest["total_plays"]) == ("session-02", 30088), \
        "loudest-session drift"
    assert (quietest["id"], quietest["total_plays"]) == ("session-52", 17), \
        "quietest-session drift"
    first, last = enriched[0], enriched[-1]
    assert (first["id"], first["start"]) == ("session-01", "2018-01-03")
    assert (last["id"], last["end"]) == ("session-61", "2026-10-02")

    doc = {
        "version": NEW_VERSION,
        "generated": SNAPSHOT,
        "plays_snapshot": SNAPSHOT,
        "method": (
            "Session archaeology, interactive: the 61 upload sessions from "
            "data/sessions.json (7-day upload-gap rule; upload dates are NOT "
            "recording dates) as an explorable timeline. gaps[] are the 60 "
            "inter-session silences in days; clusters[] are 'activity seasons' "
            "- consecutive sessions grouped while the separating silence is "
            "<= %d days, a computed browsing convention, not an artist fact. "
            "loudest/deepest_cut are the session's max/min play counts "
            "(2026-10-11 snapshot); collaborators are w//ft. title credits "
            "parsed by the shared rule (producers excluded). Titles and "
            "metadata only - never lyrics, never invented bio facts."
            % SEASON_GAP_DAYS),
        "gap_rule_days": GAP_RULE_DAYS,
        "season_gap_days": SEASON_GAP_DAYS,
        "archive_totals": {
            "sessions": 61, "tracks": total_tracks,
            "total_plays": sum(s["total_plays"] for s in enriched),
        },
        "eras": [{"id": e["id"], "name": e["name"], "span": e["span"],
                  "deep_dive": e["deep_dive"], "journey": e["journey"]}
                 for e in ERAS],
        "sessions": enriched,
        "gaps": gaps,
        "silences": silences,
        "clusters": cluster_out,
        "insights": {
            "session_count": 61,
            "track_count": total_tracks,
            "season_count": season_count,
            "most_prolific": {
                "id": most_prolific["id"], "name": most_prolific["name"],
                "start": most_prolific["start"], "end": most_prolific["end"],
                "track_count": most_prolific["track_count"],
                "total_plays": most_prolific["total_plays"],
                "deep_dive": most_prolific["deep_dive"],
                "season": most_prolific["season"],
            },
            "longest_silence": {
                "days": longest["days"],
                "from_session": longest["from_session"],
                "to_session": longest["to_session"],
                "from_end": longest["from_end"], "to_start": longest["to_start"],
            },
            "loudest_session": {"id": loudest["id"], "name": loudest["name"],
                                 "total_plays": loudest["total_plays"]},
            "quietest_session": {"id": quietest["id"], "name": quietest["name"],
                                  "total_plays": quietest["total_plays"]},
            "first_session": {"id": first["id"], "start": first["start"]},
            "last_session": {"id": last["id"], "end": last["end"]},
        },
    }

    (API / "session-clusters.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (API / "schema" / "session-clusters.json").write_text(
        json.dumps(SCHEMA, indent=2) + "\n", encoding="utf-8")

    # register the endpoint (same convention as build_eras.py)
    idx_p = API / "index.json"
    idx = json.loads(idx_p.read_text())
    idx["version"] = NEW_VERSION
    from api_manifest import render_manifest
    render_manifest(idx, ROOT)

    print(f"session-clusters.json: {len(enriched)} sessions, "
          f"{len(gaps)} gaps, {season_count} seasons; "
          f"most prolific {most_prolific['id']} x{most_prolific['track_count']}, "
          f"longest silence {longest['days']}d")
    return 0


SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Session clusters",
    "description": ("The 61 upload sessions as an explorable timeline: per-session "
                    "enrichment, inter-session gaps, activity seasons, insights."),
    "type": "object",
    "required": ["sessions", "gaps", "silences", "clusters", "eras", "insights",
                 "gap_rule_days", "season_gap_days"],
    "properties": {
        "version": {"type": "string"},
        "generated": {"type": "string"},
        "plays_snapshot": {"type": "string"},
        "method": {"type": "string"},
        "gap_rule_days": {"type": "integer"},
        "season_gap_days": {"type": "integer"},
        "archive_totals": {
            "type": "object",
            "required": ["sessions", "tracks", "total_plays"],
            "properties": {
                "sessions": {"type": "integer"},
                "tracks": {"type": "integer"},
                "total_plays": {"type": "integer"},
            },
        },
        "eras": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "span", "deep_dive", "journey"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "span": {"type": "string"},
                    "deep_dive": {"type": "string"},
                    "journey": {"type": "string"},
                },
            },
        },
        "sessions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "start", "end", "days",
                             "track_count", "total_plays", "era_id", "era_name",
                             "loudest", "deepest_cut", "collaborators",
                             "journey", "season"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "days": {"type": "integer"},
                    "track_count": {"type": "integer"},
                    "total_plays": {"type": "integer"},
                    "era_id": {"type": "string"},
                    "era_name": {"type": "string"},
                    "loudest": {"$ref": "#/definitions/session_track"},
                    "deepest_cut": {"$ref": "#/definitions/session_track"},
                    "collaborators": {"type": "array",
                                      "items": {"type": "string"}},
                    "deep_dive": {"type": ["string", "null"]},
                    "journey": {"type": "string"},
                    "season": {"type": "string"},
                },
            },
        },
        "gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["from_session", "to_session", "from_end",
                             "to_start", "days"],
                "properties": {
                    "from_session": {"type": "string"},
                    "to_session": {"type": "string"},
                    "from_end": {"type": "string"},
                    "to_start": {"type": "string"},
                    "days": {"type": "integer", "minimum": 8},
                },
            },
        },
        "silences": {
            "type": "array",
            "items": {"$ref": "#/properties/gaps/items"},
        },
        "clusters": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "label", "start", "end", "session_count",
                             "track_count", "total_plays", "session_ids"],
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "session_count": {"type": "integer", "minimum": 1},
                    "track_count": {"type": "integer", "minimum": 1},
                    "total_plays": {"type": "integer", "minimum": 0},
                    "session_ids": {"type": "array",
                                    "items": {"type": "string"}},
                },
            },
        },
        "insights": {
            "type": "object",
            "required": ["session_count", "track_count", "season_count",
                         "most_prolific", "longest_silence",
                         "loudest_session", "quietest_session",
                         "first_session", "last_session"],
            "properties": {
                "session_count": {"type": "integer"},
                "track_count": {"type": "integer"},
                "season_count": {"type": "integer"},
                "most_prolific": {
                    "type": "object",
                    "required": ["id", "name", "start", "end", "track_count",
                                 "total_plays", "season"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "start": {"type": "string"},
                        "end": {"type": "string"},
                        "track_count": {"type": "integer"},
                        "total_plays": {"type": "integer"},
                        "deep_dive": {"type": ["string", "null"]},
                        "season": {"type": "string"},
                    },
                },
                "longest_silence": {
                    "type": "object",
                    "required": ["days", "from_session", "to_session",
                                 "from_end", "to_start"],
                    "properties": {
                        "days": {"type": "integer"},
                        "from_session": {"type": "string"},
                        "to_session": {"type": "string"},
                        "from_end": {"type": "string"},
                        "to_start": {"type": "string"},
                    },
                },
                "loudest_session": {
                    "type": "object",
                    "required": ["id", "name", "total_plays"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "total_plays": {"type": "integer"},
                    },
                },
                "quietest_session": {
                    "type": "object",
                    "required": ["id", "name", "total_plays"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "total_plays": {"type": "integer"},
                    },
                },
                "first_session": {
                    "type": "object",
                    "required": ["id", "start"],
                    "properties": {"id": {"type": "string"},
                                   "start": {"type": "string"}},
                },
                "last_session": {
                    "type": "object",
                    "required": ["id", "end"],
                    "properties": {"id": {"type": "string"},
                                   "end": {"type": "string"}},
                },
            },
        },
    },
    "definitions": {
        "session_track": {
            "type": "object",
            "required": ["title", "plays", "date", "page"],
            "properties": {
                "title": {"type": "string"},
                "plays": {"type": ["integer", "null"]},
                "date": {"type": "string"},
                "page": {"type": "string"},
            },
        },
    },
}


if __name__ == "__main__":
    raise SystemExit(main())
