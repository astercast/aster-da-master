#!/usr/bin/env python3
"""Pinned-fixture tests for the session-tools pure logic
(scripts/build_session_tools.py): compare math + deepest-cut formula.

Run: python3 scripts/test_session_tools.py  (exit 0 = all pass)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from build_session_tools import (  # noqa: E402
    avg_plays_per_track,
    compare_pair,
    deepest_cut_ranking,
    nearest_rank,
    track_deep_cut_ranking,
)

PASS, FAIL = 0, 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


def approx(a, b, tol=1e-9):
    return abs(a - b) < tol


# --- pinned fixtures: small hand-written sessions ---
# fixture A: 4 tracks, 1000 plays, 5 days, two collaborators
# fixture B: 2 tracks, 100 plays, 1 day, one overlapping collaborator
# fixture C: 1 track, 5000 plays (excluded by the min-tracks rule)
# fixture D: 2 tracks, 100 plays (ties B on average; tiebreak = total_plays,
#            then track_count, then id)
FA = {"session_id": "session-FA", "track_count": 4, "total_plays": 1000,
      "days": 5, "collaborators": ["Max Ferrari", "JAX"]}
FB = {"session_id": "session-FB", "track_count": 2, "total_plays": 100,
      "days": 1, "collaborators": ["JAX", "Lil Yu"]}
FC = {"session_id": "session-FC", "track_count": 1, "total_plays": 5000,
      "days": 1, "collaborators": []}
FD = {"session_id": "session-FD", "track_count": 2, "total_plays": 100,
      "days": 3, "collaborators": ["JAX"]}

# --- avg math ---
check("avg A = 250.0", approx(avg_plays_per_track(1000, 4), 250.0))
check("avg B = 50.0", approx(avg_plays_per_track(100, 2), 50.0))

# --- compare_pair: deltas are b - a ---
cmp_ab = compare_pair(FA, FB)
check("tracks delta = -2", cmp_ab["track_count"] == {"a": 4, "b": 2, "delta": -2})
check("plays delta = -900",
      cmp_ab["total_plays"] == {"a": 1000, "b": 100, "delta": -900})
check("days delta = -4", cmp_ab["days"] == {"a": 5, "b": 1, "delta": -4})
check("avg delta = -200.0",
      approx(cmp_ab["avg_plays_per_track"]["delta"], -200.0))
check("avg a/b pinned",
      approx(cmp_ab["avg_plays_per_track"]["a"], 250.0)
      and approx(cmp_ab["avg_plays_per_track"]["b"], 50.0))
check("overlap only_a = [Max Ferrari]",
      cmp_ab["collaborator_overlap"]["only_a"] == ["Max Ferrari"])
check("overlap only_b = [Lil Yu]",
      cmp_ab["collaborator_overlap"]["only_b"] == ["Lil Yu"])
check("overlap both = [JAX]",
      cmp_ab["collaborator_overlap"]["both"] == ["JAX"])

# self-compare is a clean zero
cmp_aa = compare_pair(FA, FA)
check("self-compare deltas all 0",
      all(cmp_aa[k]["delta"] == 0 for k in
          ("track_count", "total_plays", "days"))
      and approx(cmp_aa["avg_plays_per_track"]["delta"], 0.0))
check("self-compare overlap all both",
      cmp_aa["collaborator_overlap"]["both"] == ["JAX", "Max Ferrari"]
      and cmp_aa["collaborator_overlap"]["only_a"] == []
      and cmp_aa["collaborator_overlap"]["only_b"] == [])

# reversed args flip the delta sign
cmp_ba = compare_pair(FB, FA)
check("reversed compare flips sign",
      cmp_ba["total_plays"]["delta"] == 900
      and approx(cmp_ba["avg_plays_per_track"]["delta"], 200.0))

# --- deepest_cut_ranking ---
ranked = deepest_cut_ranking([FA, FB, FC, FD], min_tracks=2)
ids = [s["session_id"] for _, s, _ in ranked]
check("single-track FC excluded", "session-FC" not in ids)
check("3 sessions ranked", len(ranked) == 3)
# B and D tie at avg 50.0; tiebreak: total_plays (tie) -> track_count (tie)
# -> session id: FB < FD, so FB ranks first
check("tiebreak order FB, FD, FA", ids == ["session-FB", "session-FD", "session-FA"])
ranks = [r for r, _, _ in ranked]
check("ranks are 1-based 1,2,3", ranks == [1, 2, 3])
check("ranked avg pinned 50.0", approx(ranked[0][2], 50.0))
check("ranked avg pinned 250.0", approx(ranked[2][2], 250.0))

# a 2-track session with the same average but FEWER total plays wins the
# first tiebreak: FB2 (2 tracks, 80 plays, avg 40) beats FB (avg 50)
FB2 = {"session_id": "session-FB2", "track_count": 2, "total_plays": 80,
       "days": 1, "collaborators": []}
ranked2 = deepest_cut_ranking([FB, FB2], min_tracks=2)
check("lower avg wins outright",
      [s["session_id"] for _, s, _ in ranked2] == ["session-FB2", "session-FB"])

# total_plays tiebreak: same avg, lower total plays first
# FE: 4 tracks / 200 plays = avg 50; FF: 2 tracks / 100 plays = avg 50
FE = {"session_id": "session-FE", "track_count": 4, "total_plays": 200,
      "days": 2, "collaborators": []}
FF = {"session_id": "session-FF", "track_count": 2, "total_plays": 100,
      "days": 2, "collaborators": []}
ranked3 = deepest_cut_ranking([FE, FF], min_tracks=2)
check("total_plays tiebreak (FF before FE)",
      [s["session_id"] for _, s, _ in ranked3] == ["session-FF", "session-FE"])

# empty input -> empty ranking, no crash
check("empty ranking", deepest_cut_ranking([], min_tracks=2) == [])

# --- track_deep_cut_ranking: lowest plays first; tiebreaks = earlier
# date, then title; no exclusions; ranks are 1-based ---
TA = {"title": "loud one", "plays": 5000, "date": "2019-01-01"}
TB = {"title": "quiet one", "plays": 17, "date": "2024-11-05"}
TC = {"title": "mid one", "plays": 450, "date": "2020-06-01"}
TD = {"title": "b title", "plays": 100, "date": "2021-03-01"}
TE = {"title": "a title", "plays": 100, "date": "2021-03-01"}
TF = {"title": "early bird", "plays": 100, "date": "2020-01-01"}
tranked = track_deep_cut_ranking([TA, TB, TC, TD, TE, TF])
tids = [t["title"] for _, t in tranked]
# plays order: 17, 100(x3), 450, 5000; the 100s break by date then title
check("track order by plays", tids == ["quiet one", "early bird", "a title",
                                       "b title", "mid one", "loud one"])
check("track ranks 1-based", [r for r, _ in tranked] == [1, 2, 3, 4, 5, 6])
check("single-track tracks are NOT excluded",
      len(track_deep_cut_ranking([TB])) == 1)
check("empty track ranking", track_deep_cut_ranking([]) == [])

# --- nearest_rank: ceil(p/100 * n)-th value ---
vals = list(range(1, 186))  # 1..185
check("p10 nearest-rank", nearest_rank(vals, 10) == 19)
check("p25 nearest-rank", nearest_rank(vals, 25) == 47)
check("p50 nearest-rank", nearest_rank(vals, 50) == 93)
check("p100 nearest-rank", nearest_rank(vals, 100) == 185)
check("nearest-rank clamps low", nearest_rank(vals, 0) == 1)

print(f"test_session_tools: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
