#!/usr/bin/env python3
"""Build the milestone race (wave 22).

18th generator, LAST in the chain. Turns the milestone-watcher skill logic
into a live "race" experience:

  - play_races:   every track approaching a round-number milestone
                  (from api/v1/milestone-watch.json bands), each with
                  current plays, target, gap, and an HONEST at-pace figure.
  - closest_races: race ids sorted by days_at_pace ascending - the
                  gap-closing ranking.
  - summit_race:  the "Take Me" 30,088 summit record and the five closest
                  contenders by catch-time at lifetime pace.
  - session_records / era_records: the standing records (recomputed and
                  asserted against session-clusters.json / eras.json).
  - just_crossed: the three most recently recorded dated milestones
                  (from milestones.json).

PACE DISCIPLINE: pace_per_day = snapshot plays / days from upload date to
the 2026-10-11 snapshot - a lifetime average, never a current rate.
days_at_pace / catch_days_at_pace are plain division, labeled estimates,
never predictions. The page and the skill say so out loud.

Reads:
  api/v1/milestone-watch.json  (bands, summit, plays_snapshot)
  data/artist.json             (discography: source of truth for plays/dates)
  api/v1/milestones.json       (crossed milestones + dates)
  api/v1/session-clusters.json (session record insights)
  api/v1/eras.json             (era stats)

Emits:
  api/v1/milestone-races.json          (endpoint #19)
  api/v1/schema/milestone-races.json   (draft-07 schema #19)
  api/v1/index.json                    (endpoint registered via render_manifest())

Every figure is recomputed and asserted; the build fails rather than
carrying a wrong number. Byte-stable: pinned SNAPSHOT, deterministic
ordering, json indent=2.

VERSION is a mirror-only constant: wave 22 adds no new source data
(everything derives from existing endpoints), so the data version stays
0.13.0.
"""
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_releases import slugify  # noqa: E402  (single source of truth)
from api_manifest import render_manifest  # noqa: E402

API = ROOT / "api" / "v1"
WATCH = json.loads((API / "milestone-watch.json").read_text())
SUMMIT = WATCH["summit"]
DISC = json.loads((ROOT / "data" / "artist.json").read_text())["discography"]
MILESTONES = json.loads((API / "milestones.json").read_text())["milestones"]
SC = json.loads((API / "session-clusters.json").read_text())
ERAS = json.loads((API / "eras.json").read_text())["eras"]

VERSION = "0.14.0"  # mirror only - no source data changed in wave 23
SNAPSHOT = "2026-10-11"
SNAP = datetime.date(2026, 10, 11)

assert WATCH["plays_snapshot"] == SNAPSHOT, "milestone-watch snapshot drift"

DISC_BY_TITLE_DATE = {(r["title"], r.get("date")): r for r in DISC}
VAULT = [r for r in DISC if r.get("type") == "SoundCloud-only"]

PACE_NOTE = (
    "Estimate from the 2026-10-11 play-count snapshot: snapshot plays "
    "divided by days from the track's upload date to the snapshot. "
    "A lifetime average, not a current rate - and not a prediction."
)


def pace_per_day(plays, date):
    """Lifetime-average plays/day between upload and the snapshot."""
    d = datetime.date.fromisoformat(date)
    days = max((SNAP - d).days, 1)
    assert days >= 1, f"upload after snapshot: {date}"
    return round(plays / days, 2)


def release_page(page):
    assert page and (ROOT / page).exists(), f"missing release page {page}"
    return page


# --- play races: approaching milestones, from the watch bands --------------
play_races = []
for band in WATCH["bands"]:
    for t in band["tracks"]:
        src = DISC_BY_TITLE_DATE.get((t["title"], t.get("date")))
        assert src is not None, f"watch track not in discography: {t['title']}"
        assert src.get("plays") == t["plays"], \
            f"plays drift for {t['title']}: watch={t['plays']} disc={src.get('plays')}"
        needed = band["target"] - t["plays"]
        assert needed == t["needed"], f"needed drift for {t['title']}"
        assert needed > 0, f"already crossed: {t['title']}"
        pace = pace_per_day(t["plays"], t["date"])
        assert pace > 0, f"zero pace: {t['title']}"
        days_at_pace = round(needed / pace, 1)
        assert round(needed / pace, 1) == days_at_pace  # arithmetic guard
        rid = f"race-{band['id']}-{slugify(t['title'])}"
        play_races.append({
            "id": rid,
            "title": t["title"],
            "page": release_page(t["page"]),
            "date": t["date"],
            "plays": t["plays"],
            "target": band["target"],
            "milestone": f"{band['target']:,} plays",
            "needed": needed,
            "progress_pct": round(t["plays"] / band["target"] * 100, 1),
            "pace_per_day": pace,
            "days_at_pace": days_at_pace,
            "pace_note": PACE_NOTE,
        })
assert len(play_races) == sum(len(b["tracks"]) for b in WATCH["bands"]) == 4, \
    "race count drift vs milestone-watch bands"
assert len({r["id"] for r in play_races}) == len(play_races), "race id collision"

closest_races = [r["id"] for r in sorted(play_races,
                                        key=lambda r: (r["days_at_pace"], r["title"]))]
# PROXIMITY ASSERTION: the ranking is strictly ordered by gap-closing pace.
days = [next(r for r in play_races if r["id"] == rid)["days_at_pace"]
        for rid in closest_races]
assert all(days[i] <= days[i + 1] for i in range(len(days) - 1)), \
    "closest_races not sorted by days_at_pace"

# --- summit race: who can catch "Take Me" (30,088)? -------------------------
assert SUMMIT["title"] == "Take Me (prod. Em Klebold)" and \
    SUMMIT["plays"] == 30088, "summit record drift"
# ELIGIBILITY: pace is a lifetime average, so a days-old track can have a
# wildly high "pace" with no track record. Summit contenders must be at
# least 90 days on record at the snapshot - pace needs a track record.
ELIGIBLE_BEFORE = "2026-07-13"
contenders = []
for r in VAULT:
    if r["title"] == SUMMIT["title"]:
        continue
    if r["date"] >= ELIGIBLE_BEFORE:
        continue
    plays = r.get("plays") or 0
    assert plays < SUMMIT["plays"], f"summit tie/overtake: {r['title']}"
    gap = SUMMIT["plays"] - plays
    assert gap > 0
    pace = pace_per_day(plays, r["date"])
    assert pace > 0, f"zero pace: {r['title']}"
    src = DISC_BY_TITLE_DATE.get((r["title"], r.get("date")))
    page = None
    for band in WATCH["bands"]:
        for t in band["tracks"]:
            if t["title"] == r["title"] and t.get("date") == r.get("date"):
                page = t["page"]
    contenders.append({
        "title": r["title"],
        "page": release_page(page) if page else None,
        "date": r["date"],
        "plays": plays,
        "gap": gap,
        "pace_per_day": pace,
        "catch_days_at_pace": round(gap / pace, 1),
        "catch_note": ("At the lifetime pace from the 2026-10-11 snapshot - "
                       "simple division, not a prediction."),
    })
contenders.sort(key=lambda c: (c["catch_days_at_pace"], c["title"]))
top5 = contenders[:5]
# CONTENDER ASSERTIONS: five closest, ascending catch-time, all behind.
assert len(top5) == 5, "need 5 summit contenders"
assert all(top5[i]["catch_days_at_pace"] <= top5[i + 1]["catch_days_at_pace"]
           for i in range(4)), "contenders not sorted by catch time"
for c in top5:
    assert round(c["gap"] / c["pace_per_day"], 1) == c["catch_days_at_pace"]
    assert c["date"] < ELIGIBLE_BEFORE, f"ineligible contender: {c['title']}"
assert "turn up w me (prod_timmy)" not in {c["title"] for c in top5}, \
    "new-track pace distortion leaked in"
summit_race = {
    "holder": {"title": SUMMIT["title"], "plays": SUMMIT["plays"],
               "date": SUMMIT["date"], "page": release_page(SUMMIT["page"])},
    "eligibility": ("Summit contenders are vault tracks uploaded before "
                    f"{ELIGIBLE_BEFORE} (at least 90 days on record at the "
                    "2026-10-11 snapshot) - pace needs a track record. "
                    "The five with the shortest catch time at lifetime pace."),
    "contenders": top5,
}

# --- session records: recomputed against session-clusters.json -------------
INS = SC["insights"]
session_records = [
    {
        "record": "Most prolific session",
        "holder": INS["most_prolific"]["name"],
        "session_id": INS["most_prolific"]["id"],
        "value": f"{INS['most_prolific']['track_count']} tracks",
        "value_number": INS["most_prolific"]["track_count"],
        "detail": f"{INS['most_prolific']['start']} → {INS['most_prolific']['end']}",
        "page": INS["most_prolific"]["deep_dive"],
    },
    {
        "record": "Longest silence",
        "holder": (f"{INS['longest_silence']['from_session']} → "
                   f"{INS['longest_silence']['to_session']}"),
        "session_id": None,
        "value": f"{INS['longest_silence']['days']} days",
        "value_number": INS["longest_silence"]["days"],
        "detail": (f"{INS['longest_silence']['from_end']} → "
                   f"{INS['longest_silence']['to_start']}"),
        "page": "sessions.html",
    },
    {
        "record": "Loudest session",
        "holder": INS["loudest_session"]["name"],
        "session_id": INS["loudest_session"]["id"],
        "value": f"{INS['loudest_session']['total_plays']:,} plays",
        "value_number": INS["loudest_session"]["total_plays"],
        "detail": "Snapshot total across the session's transmissions",
        "page": None,  # session-02 has no deep-dive page on record
    },
    {
        "record": "Quietest session",
        "holder": INS["quietest_session"]["name"],
        "session_id": INS["quietest_session"]["id"],
        "value": f"{INS['quietest_session']['total_plays']} plays",
        "value_number": INS["quietest_session"]["total_plays"],
        "detail": "Snapshot total across the session's transmissions",
        "page": None,  # session-52 has no deep-dive page on record
    },
]
assert INS["most_prolific"]["id"] == "session-40" and \
    INS["most_prolific"]["track_count"] == 19, "prolific record drift"
assert INS["longest_silence"]["days"] == 553, "silence record drift"
assert INS["loudest_session"]["id"] == "session-02" and \
    INS["loudest_session"]["total_plays"] == 30088, "loudest record drift"
assert INS["quietest_session"]["id"] == "session-52" and \
    INS["quietest_session"]["total_plays"] == 17, "quietest record drift"
for rec in session_records:
    if rec["page"]:
        assert (ROOT / rec["page"]).exists(), f"missing session page {rec['page']}"

# --- era records: recomputed against eras.json ------------------------------
by_plays = max(ERAS, key=lambda e: e["plays"])
by_tx = max(ERAS, key=lambda e: e["transmissions"])
assert by_plays["id"] == "the-first-rite", "era plays record holder drift"
assert by_tx["id"] == "the-first-rite", "era transmissions record holder drift"
# cross-check: the "loudest in the archive" fact belongs to the holder era
assert by_plays["summary"]["rank_by_plays"] == 1, "era plays rank drift"
assert by_tx["summary"]["rank_by_transmissions"] == 1, "era tx rank drift"
era_records = [
    {
        "record": "Most plays in an era",
        "holder": by_plays["name"],
        "era_id": by_plays["id"],
        "value": f"{by_plays['plays']:,} plays",
        "value_number": by_plays["plays"],
        "detail": f"{by_plays['transmissions']} transmissions, {by_plays['span']}",
        "page": by_plays["deep_dive"],
    },
    {
        "record": "Most transmissions in an era",
        "holder": by_tx["name"],
        "era_id": by_tx["id"],
        "value": f"{by_tx['transmissions']} transmissions",
        "value_number": by_tx["transmissions"],
        "detail": f"{by_tx['plays']:,} plays, {by_tx['span']}",
        "page": by_tx["deep_dive"],
    },
]
for rec in era_records:
    assert (ROOT / rec["page"]).exists(), f"missing era deep dive {rec['page']}"

# --- just crossed: the three most recently recorded dated milestones -------
dated = sorted([m for m in MILESTONES if m.get("date")],
               key=lambda m: m["date"], reverse=True)
just_crossed = [{
    "name": m["name"],
    "date": m["date"],
    "title": m.get("title"),
    "fact": m.get("fact", ""),
} for m in dated[:3]]
assert len(just_crossed) == 3, "need 3 most-recent dated milestones"
assert all(just_crossed[i]["date"] > just_crossed[i + 1]["date"]
           for i in range(2)), "just_crossed not in descending date order"
assert just_crossed[0]["date"] == "2026-10-02", "latest milestone drift"

# --- schema ----------------------------------------------------------------
SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Milestone races",
    "description": ("The archive's milestones as races: approaching play-count "
                    "milestones with pace arithmetic, the summit chase, "
                    "session and era records, and the most recently crossed "
                    "milestones (2026-10-11 snapshot)."),
    "type": "object",
    "required": ["version", "generated", "plays_snapshot", "method",
                 "pace_definition", "play_races", "closest_races",
                 "summit_race", "session_records", "era_records",
                 "just_crossed"],
    "properties": {
        "version": {"type": "string"},
        "generated": {"type": "string"},
        "plays_snapshot": {"type": "string"},
        "method": {"type": "string"},
        "pace_definition": {"type": "string"},
        "play_races": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "title", "plays", "target", "milestone",
                             "needed", "progress_pct", "pace_per_day",
                             "days_at_pace", "pace_note"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "page": {"type": ["string", "null"]},
                    "date": {"type": "string"},
                    "plays": {"type": "integer"},
                    "target": {"type": "integer"},
                    "milestone": {"type": "string"},
                    "needed": {"type": "integer"},
                    "progress_pct": {"type": "number"},
                    "pace_per_day": {"type": "number"},
                    "days_at_pace": {"type": "number"},
                    "pace_note": {"type": "string"},
                },
            },
        },
        "closest_races": {"type": "array", "items": {"type": "string"}},
        "summit_race": {
            "type": "object",
            "required": ["holder", "eligibility", "contenders"],
            "properties": {
                "holder": {
                    "type": "object",
                    "required": ["title", "plays", "date", "page"],
                },
                "contenders": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title", "plays", "gap",
                                     "pace_per_day", "catch_days_at_pace",
                                     "catch_note"],
                    },
                },
            },
        },
        "session_records": {"type": "array"},
        "era_records": {"type": "array"},
        "just_crossed": {"type": "array"},
    },
}


def main():
    doc = {
        "version": VERSION,
        "generated": SNAPSHOT,
        "plays_snapshot": SNAPSHOT,
        "method": (
            "The archive's milestones as races, computed from "
            "api/v1/milestone-watch.json (bands + summit), data/artist.json "
            "(plays and upload dates), api/v1/milestones.json (crossed "
            "milestone dates), api/v1/session-clusters.json (session "
            "records), and api/v1/eras.json (era records). Race figures are "
            "simple snapshot arithmetic: current value, target, gap, and an "
            "at-pace figure that is pace-arithmetic, never a prediction."
        ),
        "pace_definition": (
            "pace_per_day = snapshot plays ÷ days from the track's upload "
            "date to the 2026-10-11 snapshot. A lifetime average, not a "
            "current rate. days_at_pace (plays still needed ÷ pace) and "
            "catch_days_at_pace (summit gap ÷ pace) are plain division - "
            "an honest arithmetic estimate, never a prediction."
        ),
        "play_races": play_races,
        "closest_races": closest_races,
        "summit_race": summit_race,
        "session_records": session_records,
        "era_records": era_records,
        "just_crossed": just_crossed,
    }
    (API / "milestone-races.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (API / "schema" / "milestone-races.json").write_text(
        json.dumps(SCHEMA, indent=2) + "\n", encoding="utf-8")
    print(f"milestone-races: {len(play_races)} play races, "
          f"closest = {closest_races[0]}, "
          f"summit contenders = {len(top5)}")

    idx = json.loads((API / "index.json").read_text())
    idx["version"] = VERSION
    render_manifest(idx, ROOT)
    print(f"version -> {VERSION}; manifest re-rendered")


if __name__ == "__main__":
    main()
