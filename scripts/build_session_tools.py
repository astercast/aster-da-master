#!/usr/bin/env python3
"""Wave 25: session explorer 2.0 - session tools.

Turns the session archaeology data into agent/human tooling:
data/v1/session-tools.json (endpoint #20) - per-session compare profiles,
the honest snapshot-history state (a single play-count snapshot exists, so
no per-session play trajectory can be drawn), a transparently-formulated
"deepest sessions" editorial ranking, a track-level "deepest transmissions"
editorial ranking (the site's first track-level quiet ranking - the
deep-cuts-finder skill knew the bottom 5, the site never showed them), and
cross-links (session deep dives, era deep dives, codex families,
Transmission journey stops).

Every figure is recomputed here and the script exits non-zero on any
disagreement. Sources (all real archive data):
  - data/sessions.json            (64 sessions, per-track plays + dates)
  - data/v1/session-clusters.json  (enriched sessions: era, loudest +
                                    deepest-cut tracks, title-credited
                                    collaborators, deep-dive + journey links)
  - data/v1/eras.json              (era deep-dive page links)
  - data/v1/codex-families.json    (key_sessions -> family cross-links)
  - scripts/build_years.py        (parse_collabs - the shared title-credit
                                    rule, for per-track voices)

No payload shape changes to any existing endpoint block; the new
track_deep_cuts block is additive. Data version 0.17.0 -> 0.18.0 for the
new verified data slice (wave-33 directive). Titles and metadata only -
never lyrics, never invented bio facts.

Runs after build_milestone_races in the validate.sh generator chain
(build_chronicle.py runs last).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "data" / "v1"
NEW_VERSION = "0.19.0"  # wave 35: data version 0.18.0 (verified-data expansion)
SNAPSHOT = "2026-10-11"

sys.path.insert(0, str(ROOT / "scripts"))
from api_manifest import render_manifest  # noqa: E402
from build_years import parse_collabs  # noqa: E402

SESS = json.loads((ROOT / "data" / "sessions.json").read_text())["sessions"]
CL = json.loads((API / "session-clusters.json").read_text())
ERAS = {e["id"]: e for e in json.loads((API / "eras.json").read_text())["eras"]}
CF = json.loads((API / "codex-families.json").read_text())["families"]

# --- pure logic (imported by scripts/test_session_tools.py) ---

MIN_TRACKS_DEEP = 2  # editorial rule: a single-transmission session is a
                     # quiet single, not a deep session


def avg_plays_per_track(total_plays, track_count):
    """Average lifetime plays per transmission (single-snapshot arithmetic)."""
    return total_plays / track_count


def compare_pair(a, b):
    """Pure pairwise comparison of two session profiles.

    a, b carry track_count, total_plays, days, collaborators[].
    Returns numeric deltas (b - a) plus collaborator overlap sets.
    """
    rows = {}
    for key in ("track_count", "total_plays", "days"):
        rows[key] = {"a": a[key], "b": b[key], "delta": b[key] - a[key]}
    aa = avg_plays_per_track(a["total_plays"], a["track_count"])
    bb = avg_plays_per_track(b["total_plays"], b["track_count"])
    rows["avg_plays_per_track"] = {"a": aa, "b": bb, "delta": bb - aa}
    ca, cb = set(a["collaborators"]), set(b["collaborators"])
    rows["collaborator_overlap"] = {
        "only_a": sorted(ca - cb),
        "only_b": sorted(cb - ca),
        "both": sorted(ca & cb),
    }
    return rows


def deepest_cut_ranking(sessions, min_tracks=MIN_TRACKS_DEEP):
    """Transparent editorial ranking: lowest average plays per transmission.

    sessions carry session_id, track_count, total_plays.
    Tiebreaks: lower total_plays, then fewer transmissions, then session id.
    Sessions below min_tracks are excluded (stated editorial rule).
    Returns [(rank, session, avg), ...] with 1-based ranks.
    """
    scored = []
    for s in sessions:
        if s["track_count"] < min_tracks:
            continue
        scored.append((avg_plays_per_track(s["total_plays"], s["track_count"]), s))
    scored.sort(key=lambda t: (t[0], t[1]["total_plays"],
                               t[1]["track_count"], t[1]["session_id"]))
    return [(i + 1, s, avg) for i, (avg, s) in enumerate(scored)]


TRACK_DEEP_N = 25  # editorial: the quietest 25 individual transmissions


def track_deep_cut_ranking(tracks):
    """Transparent editorial ranking: lowest snapshot plays per transmission.

    tracks carry title, plays, date.
    Tiebreaks: earlier upload date, then title. No exclusions - every one
    of the 185 vault tracks is ranked.
    Returns [(rank, track), ...] with 1-based ranks.
    """
    ordered = sorted(tracks, key=lambda t: (t["plays"], t["date"], t["title"]))
    return [(i + 1, t) for i, t in enumerate(ordered)]


def nearest_rank(sorted_vals, pct):
    """Nearest-rank percentile: ceil(p/100 * n)-th value (1-based rank)."""
    import math
    n = len(sorted_vals)
    rank = max(1, min(n, math.ceil(pct / 100 * n)))
    return sorted_vals[rank - 1]


# --- payload build ---

SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "session-tools",
    "type": "object",
    "required": ["version", "generated", "plays_snapshot", "method",
                 "snapshot_history", "sessions", "deepest_cuts",
                 "track_deep_cuts", "insights"],
    "properties": {
        "version": {"type": "string"},
        "generated": {"type": "string"},
        "plays_snapshot": {"type": "string"},
        "method": {"type": "string"},
        "snapshot_history": {
            "type": "object",
            "required": ["available", "snapshot_count", "snapshot_at", "note"],
            "properties": {
                "available": {"type": "boolean"},
                "snapshot_count": {"type": "integer"},
                "snapshot_at": {"type": "string"},
                "note": {"type": "string"},
            },
        },
        "sessions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "start", "end", "days",
                             "track_count", "total_plays",
                             "avg_plays_per_track", "era_id", "era_name",
                             "era_deep_dive", "loudest", "deepest_cut",
                             "collaborators", "deep_dive", "journey",
                             "play_profile", "profile_note", "families"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "days": {"type": "integer"},
                    "track_count": {"type": "integer"},
                    "total_plays": {"type": "integer"},
                    "avg_plays_per_track": {"type": "number"},
                    "era_id": {"type": "string"},
                    "era_name": {"type": "string"},
                    "era_deep_dive": {"type": "string"},
                    "loudest": {"type": "object"},
                    "deepest_cut": {"type": "object"},
                    "collaborators": {"type": "array",
                                      "items": {"type": "string"}},
                    "deep_dive": {"type": ["string", "null"]},
                    "journey": {"type": "string"},
                    "play_profile": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["title", "date", "plays", "page"],
                        },
                    },
                    "profile_note": {"type": "string"},
                    "families": {"type": "array"},
                },
            },
        },
        "deepest_cuts": {
            "type": "object",
            "required": ["editorial", "formula", "min_tracks",
                         "excluded_single_track_sessions", "ranking"],
            "properties": {
                "editorial": {"type": "boolean"},
                "formula": {"type": "string"},
                "min_tracks": {"type": "integer"},
                "excluded_single_track_sessions": {"type": "integer"},
                "ranking": {"type": "array"},
            },
        },
        "track_deep_cuts": {
            "type": "object",
            "required": ["editorial", "formula", "track_count",
                         "bottom_25", "insights"],
            "properties": {
                "editorial": {"type": "boolean"},
                "formula": {"type": "string"},
                "track_count": {"type": "integer"},
                "bottom_25": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["rank", "title", "plays", "date",
                                     "session_id", "session_name", "era_id",
                                     "era_name", "page", "voices"],
                        "properties": {
                            "rank": {"type": "integer"},
                            "title": {"type": "string"},
                            "plays": {"type": "integer"},
                            "date": {"type": "string"},
                            "session_id": {"type": "string"},
                            "session_name": {"type": "string"},
                            "era_id": {"type": "string"},
                            "era_name": {"type": "string"},
                            "page": {"type": "string"},
                            "voices": {"type": "array",
                                       "items": {"type": "string"}},
                        },
                    },
                },
                "insights": {"type": "object"},
            },
        },
        "insights": {"type": "object"},
    },
}

PROFILE_NOTE = (
    "Play profile: each transmission's lifetime plays in upload order from "
    "the single 2026-10-11 snapshot. Not a trajectory - earlier tracks have "
    "had longer to accumulate plays, and one snapshot cannot show change "
    "over time."
)

FORMULA = (
    "average plays per transmission = total_plays / track_count, ranked "
    "ascending. Minimum 2 transmissions: a single-transmission session is "
    "a quiet single, not a deep session (stated editorial rule). "
    "Tiebreaks: lower total_plays, then fewer transmissions, then session "
    "id. An editorial ranking, not an artist fact."
)

TRACK_FORMULA = (
    "individual transmissions ranked by 2026-10-11 snapshot plays, "
    "ascending. Tiebreaks: earlier upload date, then title. No exclusions "
    "- all 185 vault tracks are ranked. An editorial ranking, not an "
    "artist fact."
)


def main() -> int:
    assert len(SESS) == 64, f"session count drift: {len(SESS)}"
    cl_by_id = {s["id"]: s for s in CL["sessions"]}
    assert len(cl_by_id) == 64, "session-clusters session drift"

    # family cross-links: session id -> families where it is a key session
    fam_by_session = {}
    for fam in CF:
        for ks in fam.get("key_sessions", []):
            assert ks["id"] in cl_by_id, \
                f"codex family {fam['slug']} key session {ks['id']} not a session"
            fam_by_session.setdefault(ks["id"], []).append({
                "name": fam["name"],
                "slug": fam["slug"],
                "page": fam["page"],
                "family_transmissions": ks.get("family_transmissions"),
                "family_plays": ks.get("family_plays"),
            })

    sessions = []
    for raw in SESS:
        sid = raw["id"]
        enr = cl_by_id[sid]
        # cross-check the enrichment against the raw session record
        assert enr["total_plays"] == raw["total_plays"], \
            f"{sid} plays drift vs session-clusters"
        assert enr["track_count"] == raw["track_count"] == len(raw["tracks"]), \
            f"{sid} track-count drift"
        assert enr["era_id"] in ERAS, f"{sid} era {enr['era_id']} not in eras.json"
        era = ERAS[enr["era_id"]]
        # plays must be present for every track (snapshot has no gaps)
        for t in raw["tracks"]:
            assert isinstance(t["plays"], int), \
                f"{sid} track {t['title']!r} has non-integer plays"
        profile = [{
            "title": t["title"],
            "date": t["date"],
            "plays": t["plays"],
            "page": t["page"],
        } for t in raw["tracks"]]
        sessions.append({
            "id": sid,
            "name": raw["name"],
            "start": raw["start"],
            "end": raw["end"],
            "days": raw["days"],
            "track_count": raw["track_count"],
            "total_plays": raw["total_plays"],
            "avg_plays_per_track": round(
                avg_plays_per_track(raw["total_plays"], raw["track_count"]), 1),
            "era_id": enr["era_id"],
            "era_name": enr["era_name"],
            "era_deep_dive": era["deep_dive"],
            "loudest": enr["loudest"],
            "deepest_cut": enr["deepest_cut"],
            "collaborators": enr["collaborators"],
            "deep_dive": enr["deep_dive"],
            "journey": enr["journey"],
            "play_profile": profile,
            "profile_note": PROFILE_NOTE,
            "families": fam_by_session.get(sid, []),
        })

    # deepest-cuts editorial ranking (recomputed from the same figures)
    slim = [{"session_id": s["id"], "track_count": s["track_count"],
             "total_plays": s["total_plays"]} for s in sessions]
    ranking = deepest_cut_ranking(slim, MIN_TRACKS_DEEP)
    excluded = sum(1 for s in sessions if s["track_count"] < MIN_TRACKS_DEEP)
    ranked_rows = []
    prof_by_id = {s["id"]: s for s in sessions}
    for rank, s, avg in ranking:
        p = prof_by_id[s["session_id"]]
        ranked_rows.append({
            "rank": rank,
            "session_id": p["id"],
            "name": p["name"],
            "start": p["start"],
            "end": p["end"],
            "track_count": p["track_count"],
            "total_plays": p["total_plays"],
            "avg_plays_per_track": p["avg_plays_per_track"],
            "era_id": p["era_id"],
            "era_name": p["era_name"],
            "deep_dive": p["deep_dive"],
            "journey": p["journey"],
        })
    # asserted: the deepest multi-track session on record
    assert ranked_rows[0]["session_id"] == "session-44", \
        f"deepest drift: {ranked_rows[0]['session_id']}"
    assert ranked_rows[0]["avg_plays_per_track"] == 83.5, "deepest avg drift"

    # track-level deep cuts: every vault transmission ranked by plays
    sess_by_id = {s["id"]: s for s in sessions}
    all_tracks = []
    for raw in SESS:
        prof = sess_by_id[raw["id"]]
        for t in raw["tracks"]:
            all_tracks.append({
                "title": t["title"],
                "plays": t["plays"],
                "date": t["date"],
                "page": t["page"],
                "session_id": raw["id"],
                "session_name": raw["name"],
                "era_id": prof["era_id"],
                "era_name": prof["era_name"],
                "voices": parse_collabs(t["title"]),
            })
    assert len(all_tracks) == 185, f"vault track drift: {len(all_tracks)}"
    track_ranking = track_deep_cut_ranking(all_tracks)
    bottom_rows = []
    for rank, t in track_ranking[:TRACK_DEEP_N]:
        assert (ROOT / t["page"]).exists(), \
            f"deep-cut track page missing: {t['page']}"
        bottom_rows.append({"rank": rank, **t})
    # asserted: the quietest transmission on record (matches the
    # deep-cuts-finder skill's pinned bottom-5)
    q = bottom_rows[0]
    assert q["title"] == "nitemode2019 w/ Max+Vetty prod. NaXi.wav", \
        f"quietest track drift: {q['title']!r}"
    assert q["plays"] == 17, "quietest plays drift"
    plays_sorted = sorted(t["plays"] for t in all_tracks)
    median = plays_sorted[len(plays_sorted) // 2]
    assert median == 450, f"median drift: {median}"
    under_100 = sum(1 for p in plays_sorted if p < 100)
    under_50 = sum(1 for p in plays_sorted if p < 50)
    loudest = track_ranking[-1][1]
    track_insights = {
        "quietest": {"title": q["title"], "plays": q["plays"],
                     "date": q["date"], "page": q["page"],
                     "session_name": q["session_name"]},
        "median_plays": median,
        "p10_plays": nearest_rank(plays_sorted, 10),
        "p25_plays": nearest_rank(plays_sorted, 25),
        "p75_plays": nearest_rank(plays_sorted, 75),
        "p90_plays": nearest_rank(plays_sorted, 90),
        "under_100_plays": under_100,
        "under_50_plays": under_50,
        "loudest": {"title": loudest["title"], "plays": loudest["plays"],
                    "page": loudest["page"]},
        "note": "individual transmissions ranked by the single 2026-10-11 "
                "snapshot; no trajectories exist (editorial)",
    }

    ins = CL["insights"]
    insights = {
        "deepest_session": {
            "session_id": ranked_rows[0]["session_id"],
            "name": ranked_rows[0]["name"],
            "avg_plays_per_track": ranked_rows[0]["avg_plays_per_track"],
            "note": "lowest average plays per transmission among sessions "
                    "with 2+ transmissions (editorial)",
        },
        "most_prolific": ins["most_prolific"],
        "loudest_session": ins["loudest_session"],
        "quietest_session": ins["quietest_session"],
    }
    assert ins["most_prolific"]["id"] == "session-41", "most-prolific drift"
    assert ins["loudest_session"]["total_plays"] == 30088, "loudest drift"
    assert ins["quietest_session"]["total_plays"] == 167, "quietest drift"

    doc = {
        "version": NEW_VERSION,
        "generated": SNAPSHOT,
        "plays_snapshot": SNAPSHOT,
        "method": (
            "Session explorer 2.0 tooling, computed from data/sessions.json "
            "(per-session track plays + dates), data/v1/session-clusters.json "
            "(era, loudest + deepest-cut tracks, title-credited "
            "collaborators, deep-dive + journey links), data/v1/eras.json "
            "(era deep-dive links), and data/v1/codex-families.json "
            "(key sessions -> family cross-links). Powers session compare, "
            "the deepest-sessions editorial ranking, the track-level "
            "deepest-transmissions ranking, the timeline scrubber, "
            "and per-session play profiles on sessions-explorer.html. Play "
            "counts are the single 2026-10-11 snapshot; no per-track play "
            "trajectory exists in the archive, so none is drawn."
        ),
        "snapshot_history": {
            "available": False,
            "snapshot_count": 1,
            "snapshot_at": SNAPSHOT,
            "note": (
                "The archive holds a single play-count snapshot (2026-10-11). "
                "Per-track play trajectories over time are not computable "
                "from one snapshot - no trend is shown anywhere on the "
                "page. Session play profiles are each transmission's "
                "lifetime plays in upload order, not a time series."
            ),
        },
        "sessions": sessions,
        "deepest_cuts": {
            "editorial": True,
            "formula": FORMULA,
            "min_tracks": MIN_TRACKS_DEEP,
            "excluded_single_track_sessions": excluded,
            "ranking": ranked_rows,
        },
        "track_deep_cuts": {
            "editorial": True,
            "formula": TRACK_FORMULA,
            "track_count": len(all_tracks),
            "bottom_25": bottom_rows,
            "insights": track_insights,
        },
        "insights": insights,
    }
    (API / "session-tools.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (API / "schema" / "session-tools.json").write_text(
        json.dumps(SCHEMA, indent=2) + "\n", encoding="utf-8")
    print(f"session-tools: {len(sessions)} compare profiles, "
          f"deepest = {ranked_rows[0]['session_id']} "
          f"({ranked_rows[0]['avg_plays_per_track']} avg), "
          f"{excluded} single-track sessions excluded, "
          f"quietest track = {q['title']!r} ({q['plays']} plays), "
          f"median {median}")

    idx = json.loads((API / "index.json").read_text())
    idx["version"] = NEW_VERSION
    render_manifest(idx, ROOT)
    print(f"version -> {NEW_VERSION}; manifest re-rendered")


if __name__ == "__main__":
    raise SystemExit(main())
