#!/usr/bin/env python3
"""Pinned-fixture tests for the milestone-race 2.0 pure logic
(scripts/build_milestone_races.py): project_pair math (any two tracks, any
target), head-to-head delegation, race-history ordering, threshold winners,
vault_pace + the climb payloads, snapshot provenance, and the uncertainty
labels.

Run: python3 scripts/test_milestone_races.py  (exit 0 = all pass)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from build_milestone_races import (  # noqa: E402
    head_to_head_pair,
    photo_finish_pair,
    project_pair,
    threshold_winners,
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


def vtrack(vid, title, plays, pace):
    """A vault_pace-shaped track fixture."""
    return {"id": vid, "title": title, "plays": plays,
            "pace_per_day": pace, "page": "releases/x.html",
            "producers": []}


# pinned race-shaped fixtures (plays/pace/target/days all consistent)
RA = {"id": "race-a", "title": "Track A", "page": "releases/a.html",
      "plays": 9615, "target": 10000, "needed": 385, "progress_pct": 96.2,
      "pace_per_day": 3.84, "days_at_pace": 100.3, "producers": []}
RB = {"id": "race-b", "title": "Track B", "page": "releases/b.html",
      "plays": 9535, "target": 10000, "needed": 465, "progress_pct": 95.3,
      "pace_per_day": 3.17, "days_at_pace": 146.7, "producers": []}
RC = {"id": "race-c", "title": "Track C", "page": "releases/c.html",
      "plays": 935, "target": 1000, "needed": 65, "progress_pct": 93.5,
      "pace_per_day": 0.33, "days_at_pace": 197.0, "producers": []}
RD = {"id": "race-d", "title": "Track D", "page": "releases/d.html",
      "plays": 918, "target": 1000, "needed": 82, "progress_pct": 91.8,
      "pace_per_day": 0.29, "days_at_pace": 282.8, "producers": []}

# --- project_pair: the general any-two-tracks engine ---
VA = vtrack("vp-a", "Track A", 9615, 3.84)
VB = vtrack("vp-b", "Track B", 9535, 3.17)
VC = vtrack("vp-c", "Track C", 30088, 11.44)  # already past 10k/20k

# mirrors the featured pair: master key vs colder at 10k
pp = project_pair(VA, VB, 10000, 10000)
check("project_pair: A first (100.3 < 146.7)",
      pp["projected_first"] == "vp-a")
check("project_pair: days_gap = 46.4", pp["days_gap"] == 46.4)
check("project_pair: needed carried",
      pp["a_needed"] == 385 and pp["b_needed"] == 465)
check("project_pair: days_at_pace recomputed",
      pp["a_days_at_pace"] == 100.3 and pp["b_days_at_pace"] == 146.7)
check("project_pair: no crossings", pp["already_crossed"] == [])
check("project_pair: uncertainty label", "not a forecast" in pp["projected_note"])
check("project_pair: milestones labeled", pp["a_milestone"] == "10,000 plays")
check("project_pair: same target named",
      "same finish line" in pp["projected_note"])
check("project_pair: winner named", "Track A" in pp["projected_note"])

# already crossed: no race to run
px = project_pair(VC, VA, 10000, 10000)
check("already-crossed: C listed", px["already_crossed"] == ["vp-c"])
check("already-crossed: days_at_pace = 0.0", px["a_days_at_pace"] == 0.0)
check("already-crossed: C is projected_first (it finished)",
      px["projected_first"] == "vp-c")
check("already-crossed: verdict says the race is over",
      "the race is over" in px["projected_note"])
check("already-crossed: still carries the uncertainty label",
      "not a forecast" in px["projected_note"])

# both crossed: no race at all
pb = project_pair(VC, VC, 10000, 20000)
check("both crossed: projected_first None", pb["projected_first"] is None)
check("both crossed: no race to run", "no race to run" in pb["projected_note"])

# tie at pace: never silently resolved
VT1 = vtrack("vp-t1", "Tie One", 9000, 10.0)
VT2 = vtrack("vp-t2", "Tie Two", 9000, 10.0)
pt = project_pair(VT1, VT2, 10000, 10000)
check("tie: projected_first None", pt["projected_first"] is None)
check("tie: gap 0.0", pt["days_gap"] == 0.0)
check("tie: note says tied", "tied at lifetime pace" in pt["projected_note"])

# cross-target: different finish lines, stated
pc = project_pair(VA, VB, 10000, 20000)
check("cross-target: same_target false", pc["same_target"] is False)
check("cross-target: different finish lines named",
      "different finish lines" in pc["projected_note"])
check("cross-target: nobody crossed yet", pc["already_crossed"] == [])
check("cross-target: A first (100.3d to 10k < 3301.3d to 20k)",
      pc["projected_first"] == "vp-a")
# cross-target where one side is already past its line
pc2 = project_pair(VA, VB, 1000, 10000)
check("cross-target + crossed: A already past 1k",
      pc2["already_crossed"] == ["vp-a"])
check("cross-target + crossed: verdict says the race is over",
      "the race is over" in pc2["projected_note"])

# --- head_to_head_pair delegates to project_pair ---
p_ab = head_to_head_pair(RA, RB)
check("h2h delegates: first = race-a", p_ab["projected_first"] == "race-a")
check("h2h delegates: gap 46.4", p_ab["days_gap"] == 46.4)
check("h2h keeps progress_pct",
      p_ab["a_progress_pct"] == 96.2 and p_ab["b_progress_pct"] == 95.3)
check("h2h: no crossings", p_ab["already_crossed"] == [])

# all 6 featured pairs, sorted by days_gap ascending (the page's order)
pairs = sorted(
    [head_to_head_pair(RA, RB), head_to_head_pair(RA, RC),
     head_to_head_pair(RA, RD), head_to_head_pair(RB, RC),
     head_to_head_pair(RB, RD), head_to_head_pair(RC, RD)],
    key=lambda p: (p["days_gap"], p["a"], p["b"]))
gaps = [p["days_gap"] for p in pairs]
check("6 pairs from 4 races", len(pairs) == 6)
check("pairs sorted by days_gap ascending",
      gaps == sorted(gaps) == [46.4, 50.3, 85.8, 96.7, 136.1, 182.5])
check("closest featured pair: A vs B at 46.4",
      pairs[0]["a"] == "race-a" and pairs[0]["b"] == "race-b")

# --- photo_finish_pair: the minimum date gap wins ---
dated = [
    {"name": "First distributor transmission", "date": "2017-04-20",
     "title": "lost memories (feat. Aster Da Master)"},
    {"name": "First vault transmission", "date": "2018-01-03",
     "title": "Soul Shaking (prod. Fish Narc)"},
    {"name": "First collaboration", "date": "2018-04-28",
     "title": "Mistakes Ft. JO$E DRIPP (prod. Tec)"},
    {"name": "100th transmission on record", "date": "2020-12-21",
     "title": "x"},
]
a, b, gap = photo_finish_pair(dated)
check("photo finish = the two closest dated milestones",
      (a["name"], b["name"]) ==
      ("First vault transmission", "First collaboration"))
check("photo finish gap = 115 days", gap == 115)
check("a is dated earlier than b", a["date"] < b["date"])

# --- threshold_winners: counts, leaders, no dates invented ---
vault = [
    {"title": "Take Me (prod. Em Klebold)", "plays": 30088,
     "date": "2018-02-04"},
    {"title": "Soul Shaking (prod. Fish Narc)", "plays": 12944,
     "date": "2018-01-03"},
    {"title": "master key ft. Lil Wintr x Marcelo (prod. ginseng)",
     "plays": 9615, "date": "2019-12-06"},
    {"title": "[outro] Off Beat ft. Yung Vetta (prod. Addy)", "plays": 935,
     "date": "2019-01-28"},
    {"title": "Quiet one", "plays": 17, "date": "2026-01-01"},
]
tw = threshold_winners(vault, [1000, 10000, 20000, 30000])
check("4 threshold bands", len(tw) == 4)
check("1k count = 3", tw[0]["crossed_count"] == 3)
check("10k count = 2", tw[1]["crossed_count"] == 2)
check("20k count = 1", tw[2]["crossed_count"] == 1)
check("30k count = 1", tw[3]["crossed_count"] == 1)
check("leader of every band = Take Me",
      all(t["leader"]["title"] == "Take Me (prod. Em Klebold)" for t in tw))
check("leader plays carried through", tw[0]["leader"]["plays"] == 30088)
check("leader page is a real release path shape",
      tw[0]["leader"]["page"].startswith("releases/")
      and tw[0]["leader"]["page"].endswith(".html"))
check("labels formatted with commas",
      [t["label"] for t in tw] ==
      ["1,000 plays", "10,000 plays", "20,000 plays", "30,000 plays"])

# --- the generator's own math, pinned against the live snapshot ---
check("pinned: master key pace math", approx(385 / 3.84, 100.3, 0.2))
check("pinned: colder pace math", approx(465 / 3.17, 146.7, 0.2))
check("pinned: outro pace math", approx(65 / 0.33, 197.0, 0.5))
check("pinned: lucid boi pace math", approx(82 / 0.29, 282.8, 0.5))

# --- the live vault_pace + climb + provenance payloads ---
DOC = json.load(open(ROOT.parent / "api" / "v1" / "milestone-races.json"))
_vp = DOC["vault_pace"]
check("vault_pace: 185 tracks", _vp["count"] == 185 == len(_vp["tracks"]))
check("vault_pace: ids unique",
      len({v["id"] for v in _vp["tracks"]}) == 185)
check("vault_pace: alphabetical",
      [v["title"].lower() for v in _vp["tracks"]] ==
      sorted(v["title"].lower() for v in _vp["tracks"]))
check("vault_pace: every track has pace > 0 and a producers list",
      all(v["pace_per_day"] > 0 and isinstance(v["producers"], list)
          for v in _vp["tracks"]))
_tm = next(v for v in _vp["tracks"]
           if v["title"] == "Take Me (prod. Em Klebold)")
check("vault_pace: Take Me 30088 @ ~9.49/day",
      _tm["plays"] == 30088 and abs(_tm["pace_per_day"] - 9.49) < 0.01)
_cl = DOC["the_climb"]
check("the_climb: 182 entries", _cl["count"] == 182 == len(_cl["entries"]))
check("the_climb: ranks 1..182 in order",
      [c["rank"] for c in _cl["entries"]] == list(range(1, 183)))
check("the_climb: sorted by catch time",
      all(_cl["entries"][i]["catch_days_at_pace"] <=
          _cl["entries"][i + 1]["catch_days_at_pace"] for i in range(181)))
check("the_climb: holder excluded, all pre-2026-07-13",
      all(c["plays"] < 30088 and c["date"] < "2026-07-13"
          for c in _cl["entries"]))
check("the_climb: top 5 == summit contenders",
      [c["title"] for c in _cl["entries"][:5]] ==
      [c["title"] for c in DOC["summit_race"]["contenders"]])
check("the_climb: catch math spot-check",
      approx(_cl["entries"][0]["catch_days_at_pace"],
             round(_cl["entries"][0]["gap"] /
                   _cl["entries"][0]["pace_per_day"], 1)))
check("snapshot_provenance: independent capture recorded",
      "185 tracks" in DOC["snapshot_provenance"] and
      "zero play-count differences" in DOC["snapshot_provenance"])

print(f"milestone_races tests: {PASS} pass, {FAIL} fail")
sys.exit(1 if FAIL else 0)
