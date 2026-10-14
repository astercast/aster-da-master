#!/usr/bin/env python3
"""Build the milestone race (wave 22; wave 28: race 2.0).

18th generator in the chain. Turns the milestone-watcher skill logic
into a live "race" experience:

  - play_races:   every track approaching a round-number milestone
                  (from data/v1/milestone-watch.json bands), each with
                  current plays, target, gap, an HONEST at-pace figure,
                  and its as-credited producers (wave 28).
  - closest_races: race ids sorted by days_at_pace ascending - the
                  gap-closing ranking.
  - summit_race:  the "Take Me" 30,088 summit record and the five closest
                  contenders by catch-time at lifetime pace.
  - session_records / era_records: the standing records (recomputed and
                  asserted against session-clusters.json / eras.json).
  - just_crossed: the three most recently recorded dated milestones
                  (from milestones.json).
  - head_to_head (wave 28): every pair of active races, raced against
                  each other - gap between projected finish days, and the
                  at-pace projected finisher. Arithmetic, never a
                  prediction.
  - vault_pace (wave 28): the pace database - all 185 vault tracks with
                  lifetime pace, release page, and as-credited producers.
                  Powers the race-any-two-tracks tool and The Climb.
  - the_climb (wave 28): all 182 summit-eligible vault tracks ranked by
                  catch time at lifetime pace - the full leaderboard behind
                  the summit section's top 5.
  - race_history (wave 28): completed races - all dated milestone
                  crossings, threshold winners (1k/10k/20k/30k), and the
                  photo finish (closest dated pair). Crossing dates per
                  track are NOT recorded; the method says so.
  - race_of_the_week (wave 28): the closest active race, computed from
                  the snapshot (not editorial), with a share card.

PACE DISCIPLINE: pace_per_day = snapshot plays / days from upload date to
the 2026-10-11 snapshot - a lifetime average, never a current rate.
days_at_pace / catch_days_at_pace are plain division, labeled estimates,
never predictions. The page and the skill say so out loud.

Reads:
  data/v1/milestone-watch.json  (bands, summit, plays_snapshot)
  data/artist.json             (discography: source of truth for plays/dates)
  data/v1/milestones.json       (crossed milestones + dates)
  data/v1/session-clusters.json (session record insights)
  data/v1/eras.json             (era stats)

Emits:
  data/v1/milestone-races.json          (endpoint #19)
  data/v1/schema/milestone-races.json   (draft-07 schema #19)
  data/v1/index.json                    (endpoint registered via render_manifest())

Every figure is recomputed and asserted; the build fails rather than
carrying a wrong number. Byte-stable: pinned SNAPSHOT, deterministic
ordering, json indent=2.

VERSION is a mirror-only constant: wave 28 adds no new source data
(everything derives from existing endpoints), so the data version stays
0.14.0.
"""
import datetime
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_releases import slugify  # noqa: E402  (single source of truth)
from build_producer_deepdives import parse_producers, producer_slug  # noqa: E402
from api_manifest import render_manifest  # noqa: E402

API = ROOT / "data" / "v1"
WATCH = json.loads((API / "milestone-watch.json").read_text())
SUMMIT = WATCH["summit"]
DISC = json.loads((ROOT / "data" / "artist.json").read_text())["discography"]
MILESTONES = json.loads((API / "milestones.json").read_text())["milestones"]
SC = json.loads((API / "session-clusters.json").read_text())
ERAS = json.loads((API / "eras.json").read_text())["eras"]

VERSION = "0.19.0"  # wave 35: data version 0.18.0 (verified-data expansion)
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


def race_producers(title):
    """As-credited producers of a racing track, each with its record fold."""
    prods = []
    for name in parse_producers(title):
        slug = producer_slug(name)
        page = f"producers/index.html#p-{slug}"
        assert (ROOT / page.split("#")[0]).exists(), f"missing producer page {page}"
        prods.append({"name": name, "slug": slug, "page": page})
    return prods


def project_pair(a, b, target_a, target_b):
    """Race any two vault tracks to their (possibly different) targets.

    a/b are dicts with id/title/plays/pace_per_day/page/producers.
    needed = target - plays; days_at_pace = needed / pace_per_day (plain
    division, rounded to 1). A track already past its line has no race to
    run - the verdict says so instead of projecting. Ties yield
    projected_first None (handled, never silently resolved). Every
    verdict carries the uncertainty label.
    """
    UNCERTAIN = ("Pace is a lifetime average from a single snapshot, not a "
                 "current rate - this is arithmetic, not a forecast.")
    na, nb = target_a - a["plays"], target_b - b["plays"]
    crossed = [x["id"] for x, n in ((a, na), (b, nb)) if n <= 0]
    da = round(na / a["pace_per_day"], 1) if na > 0 else 0.0
    db = round(nb / b["pace_per_day"], 1) if nb > 0 else 0.0
    assert a["pace_per_day"] > 0 and b["pace_per_day"] > 0, \
        "zero pace in pair projection"
    same_target = target_a == target_b
    if len(crossed) == 2:
        first, note = None, ("Both tracks are already past their lines - "
                             "no race to run. " + UNCERTAIN)
    elif len(crossed) == 1:
        winner = a if crossed[0] == a["id"] else b
        wtarget = target_a if crossed[0] == a["id"] else target_b
        first = crossed[0]
        note = (f'"{winner["title"]}" already crossed the '
                f'{wtarget:,} plays line - the race is over. ' + UNCERTAIN)
    else:
        if da < db:
            first = a["id"]
        elif db < da:
            first = b["id"]
        else:
            first = None
        line_note = ("different finish lines - the race is who gets there "
                     "first, not who runs fastest") if not same_target else \
            "the same finish line - the race is purely who closes the gap first"
        first_title = {a["id"]: a["title"], b["id"]: b["title"]}.get(first)
        note = (
            f"At lifetime pace from the 2026-10-11 snapshot, "
            + (f'"{first_title}" crosses first - {line_note}.'
               if first else
               "the pair is tied at lifetime pace - no projected finisher.")
            + " " + UNCERTAIN
        )
    return {
        "a": a["id"],
        "b": b["id"],
        "a_title": a["title"],
        "b_title": b["title"],
        "a_page": a["page"],
        "b_page": b["page"],
        "a_plays": a["plays"],
        "b_plays": b["plays"],
        "a_target": target_a,
        "b_target": target_b,
        "a_needed": na,
        "b_needed": nb,
        "a_milestone": f"{target_a:,} plays",
        "b_milestone": f"{target_b:,} plays",
        "a_pace_per_day": a["pace_per_day"],
        "b_pace_per_day": b["pace_per_day"],
        "a_days_at_pace": da,
        "b_days_at_pace": db,
        "a_producers": a["producers"],
        "b_producers": b["producers"],
        "same_target": same_target,
        "already_crossed": crossed,
        "days_gap": round(abs(da - db), 1),
        "projected_first": first,
        "projected_note": note,
    }


def head_to_head_pair(ra, rb):
    """Race two active races against each other (featured matchups).

    Delegates to project_pair with each race's own band target; active
    races are never already crossed (asserted at build time).
    """
    p = project_pair(ra, rb, ra["target"], rb["target"])
    assert not p["already_crossed"], "active race already crossed its line"
    p["a_progress_pct"] = ra["progress_pct"]
    p["b_progress_pct"] = rb["progress_pct"]
    return p


def photo_finish_pair(dated):
    """The closest pair of dated milestone crossings, by date gap.

    dated: list of {"name", "date", "title"} in any order. Returns
    (a, b, gap_days) with a dated earlier than b.
    """
    assert len(dated) >= 2, "need at least 2 dated milestones"
    best = None
    for x, y in itertools.combinations(sorted(dated, key=lambda m: m["date"]), 2):
        gap = (datetime.date.fromisoformat(y["date"])
               - datetime.date.fromisoformat(x["date"])).days
        assert gap > 0, "two milestones share a date"
        if best is None or gap < best[2]:
            best = (x, y, gap)
    return best


def threshold_winners(vault, thresholds):
    """Winners of the completed threshold races: counts + current leader.

    A track is past a threshold when its snapshot plays reach it. Crossing
    DATES are not recorded - the archive holds one snapshot, so no finish
    order is claimed; the method block says so out loud.
    """
    out = []
    for th in thresholds:
        past = [r for r in vault if (r.get("plays") or 0) >= th]
        leader = max(past, key=lambda r: (r.get("plays") or 0, r["title"]))
        page = f"releases/{slugify(leader['title'])}.html"
        assert (ROOT / page).exists(), f"missing release page {page}"
        out.append({
            "threshold": th,
            "label": f"{th:,} plays",
            "crossed_count": len(past),
            "leader": {
                "title": leader["title"],
                "plays": leader["plays"],
                "date": leader["date"],
                "page": page,
            },
        })
    counts = [t["crossed_count"] for t in out]
    assert all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1)), \
        "threshold counts not monotonic"
    return out


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
            "producers": race_producers(t["title"]),
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

# --- snapshot provenance: independently verified (wave 28) -------------------
# The 2026-10-11 play-count snapshot this race is built on was
# independently re-captured on 2026-10-11 by a read-only live-browser pass
# of the official SoundCloud profile (soundcloud.com/asterdamaster):
# 185/185 tracks matched with zero play-count differences against
# data/artist.json (verified 2026-10-11; see
# ~/workspace/research_notes/aster-soundcloud-20261011/report.md).
# Titles and play counts are factual metadata - no lyrics involved.
# The verification is recorded here as a documented research outcome, not
# a build-time file dependency (the chain must run on a fresh clone).
SNAPSHOT_PROVENANCE = (
    "The 2026-10-11 play-count snapshot was independently re-captured on "
    "2026-10-11 by a read-only live-browser pass of the official "
    "SoundCloud profile (soundcloud.com/asterdamaster): all 185 tracks "
    "matched the archive's snapshot with zero play-count differences. "
    "Titles and play counts are factual metadata."
)

# --- head-to-head: every pair of active races, raced against each other ---
h2h_pairs = [head_to_head_pair(ra, rb)
             for ra, rb in itertools.combinations(play_races, 2)]
assert len(h2h_pairs) == 6, "need all 6 pairs of 4 races"
h2h_pairs.sort(key=lambda p: (p["days_gap"], p["a"], p["b"]))
for p in h2h_pairs:
    # the gap is the arithmetic difference of the two finish estimates
    assert p["days_gap"] == round(abs(p["a_days_at_pace"]
                                     - p["b_days_at_pace"]), 1), \
        f"days_gap arithmetic drift in {p['a']} vs {p['b']}"
    first = (p["a"] if p["a_days_at_pace"] < p["b_days_at_pace"]
             else p["b"] if p["b_days_at_pace"] < p["a_days_at_pace"] else None)
    assert p["projected_first"] == first, \
        f"projected_first drift in {p['a']} vs {p['b']}"
    assert "not a forecast" in p["projected_note"], \
        "uncertainty label missing from projected_note"
assert all(h2h_pairs[i]["days_gap"] <= h2h_pairs[i + 1]["days_gap"]
           for i in range(5)), "head-to-head pairs not sorted by days_gap"
head_to_head = {
    "method": (
        "Any two active play races, raced against each other. The "
        "projected finisher is whoever has the smaller days_at_pace - "
        "plain division on the 2026-10-11 snapshot, with the uncertainty "
        "stated on every pair. Races with different targets have different "
        "finish lines: the race is who gets there first, not who runs "
        "fastest. Pairs are ordered by days_gap ascending - the closest "
        "projected finishes first. The same project_pair arithmetic powers "
        "the page's race-any-two-tracks tool (from vault_pace, client-side)."
    ),
    "pairs": h2h_pairs,
}

# --- vault_pace: the pace database every race is computed from -------------
# Every vault track with its lifetime pace, release page, and as-credited
# producers. Powers the race-any-two-tracks tool and The Climb.
vault_pace = []
for r in VAULT:
    plays = r.get("plays") or 0
    pace = pace_per_day(plays, r["date"])
    assert pace > 0, f"zero pace: {r['title']}"
    vpid = "vp-" + slugify(r["title"])
    page = f"releases/{slugify(r['title'])}.html"
    assert (ROOT / page).exists(), f"missing release page {page}"
    vault_pace.append({
        "id": vpid,
        "title": r["title"],
        "plays": plays,
        "date": r["date"],
        "page": page,
        "pace_per_day": pace,
        "producers": race_producers(r["title"]),
    })
vault_pace.sort(key=lambda v: v["title"].lower())
assert len(vault_pace) == len(VAULT) == 185, "vault pace table drift"
assert len({v["id"] for v in vault_pace}) == len(vault_pace), \
    "vault_pace id collision"
# spot-assert the pace arithmetic against the summit holder
take_me = next(v for v in vault_pace
               if v["title"] == "Take Me (prod. Em Klebold)")
assert take_me["plays"] == 30088 and take_me["pace_per_day"] == round(
    30088 / (SNAP - datetime.date(2018, 2, 4)).days, 2), "Take Me pace drift"

# --- the climb: every eligible track's chase for the summit -----------------
# Same eligibility as the summit contenders (90+ days on record at the
# snapshot; still behind the holder), ranked by catch time at lifetime
# pace. The full leaderboard behind the top-5 the summit section shows.
climb = []
for v in vault_pace:
    if v["date"] >= ELIGIBLE_BEFORE:
        continue
    if v["plays"] >= SUMMIT["plays"]:
        continue
    gap = SUMMIT["plays"] - v["plays"]
    assert gap > 0
    catch = round(gap / v["pace_per_day"], 1)
    climb.append({
        "rank": None,  # filled after sorting
        "title": v["title"],
        "page": v["page"],
        "date": v["date"],
        "plays": v["plays"],
        "gap": gap,
        "pace_per_day": v["pace_per_day"],
        "catch_days_at_pace": catch,
        "catch_note": ("At the lifetime pace from the 2026-10-11 snapshot - "
                       "simple division, not a prediction."),
    })
climb.sort(key=lambda c: (c["catch_days_at_pace"], c["title"]))
for i, c in enumerate(climb, 1):
    c["rank"] = i
    assert round(c["gap"] / c["pace_per_day"], 1) == c["catch_days_at_pace"]
    assert c["date"] < ELIGIBLE_BEFORE
assert len(climb) == 182, f"climb count drift: {len(climb)}"
assert all(climb[i]["catch_days_at_pace"] <= climb[i + 1]["catch_days_at_pace"]
           for i in range(len(climb) - 1)), "climb not sorted by catch time"
# the climb's top 5 must match the summit section's contenders exactly
assert [c["title"] for c in climb[:5]] == \
    [c["title"] for c in summit_race["contenders"]], \
    "climb top 5 drift vs summit contenders"
the_climb = {
    "method": (
        "Every vault track eligible for the summit chase (uploaded before "
        "2026-07-13 - pace needs a track record - and still behind the "
        "30,088-play holder), ranked by catch time at lifetime pace. "
        "catch_days_at_pace is plain division on the 2026-10-11 snapshot: "
        "an honest arithmetic estimate, never a prediction."
    ),
    "holder": summit_race["holder"],
    "count": len(climb),
    "entries": climb,
}

# --- race history: the races that are already decided -----------------------
# Completed play-count races: threshold_winners counts vault tracks whose
# snapshot plays are past 1k/10k/20k/30k. Crossing DATES are not recorded -
# the archive holds a single play-count snapshot (2026-10-11), so no finish
# order or crossing date is claimed. That is stated in the method block and
# on the page; the data never pretends otherwise.
THRESHOLDS = [1000, 10000, 20000, 30000]
th_winners = threshold_winners(VAULT, THRESHOLDS)
# the dated record of crossings, from milestones.json (the "Longest silence"
# entry carries no date and is excluded - recorded here, not silently)
undated = [m["name"] for m in MILESTONES if not m.get("date")]
crossed_all = [{
    "name": m["name"],
    "date": m["date"],
    "title": m.get("title"),
    "fact": m.get("fact", ""),
} for m in sorted([m for m in MILESTONES if m.get("date")],
                  key=lambda m: m["date"], reverse=True)]
assert len(crossed_all) == len(MILESTONES) - len(undated), \
    "crossed_all must cover every dated milestone"
pf_a, pf_b, pf_gap = photo_finish_pair(
    [{"name": m["name"], "date": m["date"], "title": m.get("title")}
     for m in MILESTONES if m.get("date")])
# PHOTO-FINISH ASSERTION: no other dated pair is closer in time.
gaps = [(datetime.date.fromisoformat(y) - datetime.date.fromisoformat(x)).days
        for x, y in itertools.combinations(
            sorted(m["date"] for m in MILESTONES if m.get("date")), 2)]
assert pf_gap == min(gaps) and pf_gap > 0, "photo finish is not the minimum gap"
race_history = {
    "method": (
        "Completed races from the archive's own records. threshold_winners "
        "counts vault tracks past each round-number play threshold and names "
        "the current leader - crossing dates are not recorded: the archive "
        "holds ONE play-count snapshot (2026-10-11), so crossing dates and "
        "finish order for these races cannot be recovered and are not "
        "claimed. completed_crossings are the dated "
        "milestone entries from data/v1/milestones.json (the undated "
        "'Longest silence' entry is excluded, recorded here). The photo "
        "finish is the pair of recorded crossings closest together in time."
    ),
    "undated_excluded": undated,
    "completed_crossings": crossed_all,
    "threshold_winners": th_winners,
    "photo_finish": {
        "a": {"name": pf_a["name"], "date": pf_a["date"],
              "title": pf_a.get("title")},
        "b": {"name": pf_b["name"], "date": pf_b["date"],
              "title": pf_b.get("title")},
        "gap_days": pf_gap,
        "note": (
            "The two recorded milestone crossings closest together in time - "
            "the archive's tightest back-to-back finish, as recorded. These "
            "are catalog milestones, not per-track crossing times."
        ),
    },
}

# --- race of the week: the closest active race, computed not editorial -----
watch_race = next(r for r in play_races if r["id"] == closest_races[0])
race_of_the_week = {
    "race_id": closest_races[0],
    "computed": SNAPSHOT,
    "basis": (
        "The closest active race at the 2026-10-11 snapshot: the shortest "
        "days_at_pace among the play races. Computed from the data, not "
        "chosen by an editor."
    ),
    "share_text": (
        f"Race to watch: \"{watch_race['title']}\" is {watch_race['needed']} "
        f"plays from {watch_race['milestone']} "
        f"({watch_race['plays']:,} of {watch_race['target']:,} plays). "
        f"At lifetime pace, ~{watch_race['days_at_pace']} days to the line - "
        "an estimate, not a prediction. Aster da Master milestone race."
    ),
    "deep_link": "milestone-race.html#watch",
    "caveat": (
        "Play counts are the 2026-10-11 snapshot; pace is a lifetime "
        "average from that single snapshot, not a current rate - the "
        "spotlight is arithmetic, never a prediction."
    ),
}

# --- schema ----------------------------------------------------------------
SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Milestone races",
    "description": ("The archive's milestones as races: approaching play-count "
                    "milestones with pace arithmetic, head-to-head race pairs, "
                    "the summit chase, session and era records, race history, "
                    "and the computed race of the week (2026-10-11 snapshot)."),
    "type": "object",
    "required": ["version", "generated", "plays_snapshot", "method",
                 "pace_definition", "play_races", "closest_races",
                 "summit_race", "session_records", "era_records",
                 "just_crossed", "head_to_head", "vault_pace", "the_climb",
                 "race_history", "race_of_the_week", "snapshot_provenance"],
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
                             "days_at_pace", "pace_note", "producers"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "page": {"type": ["string", "null"]},
                    "date": {"type": "string"},
                    "producers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "slug", "page"],
                            "properties": {
                                "name": {"type": "string"},
                                "slug": {"type": "string"},
                                "page": {"type": "string"},
                            },
                        },
                    },
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
        "head_to_head": {
            "type": "object",
            "required": ["method", "pairs"],
            "properties": {
                "method": {"type": "string"},
                "pairs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["a", "b", "a_title", "b_title",
                                     "a_needed", "b_needed",
                                     "a_days_at_pace", "b_days_at_pace",
                                     "same_target", "already_crossed",
                                     "days_gap", "projected_first",
                                     "projected_note"],
                    },
                },
            },
        },
        "vault_pace": {
            "type": "object",
            "required": ["method", "count", "tracks"],
            "properties": {
                "method": {"type": "string"},
                "count": {"type": "integer"},
                "tracks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "title", "plays", "date", "page",
                                     "pace_per_day", "producers"],
                    },
                },
            },
        },
        "the_climb": {
            "type": "object",
            "required": ["method", "holder", "count", "entries"],
            "properties": {
                "method": {"type": "string"},
                "count": {"type": "integer"},
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["rank", "title", "plays", "gap",
                                     "pace_per_day", "catch_days_at_pace",
                                     "catch_note"],
                    },
                },
            },
        },
        "race_history": {
            "type": "object",
            "required": ["method", "undated_excluded", "completed_crossings",
                         "threshold_winners", "photo_finish"],
        },
        "race_of_the_week": {
            "type": "object",
            "required": ["race_id", "computed", "basis", "share_text",
                         "deep_link", "caveat"],
        },
        "snapshot_provenance": {"type": "string"},
    },
}


def main():
    doc = {
        "version": VERSION,
        "generated": SNAPSHOT,
        "plays_snapshot": SNAPSHOT,
        "method": (
            "The archive's milestones as races, computed from "
            "data/v1/milestone-watch.json (bands + summit), data/artist.json "
            "(plays and upload dates), data/v1/milestones.json (crossed "
            "milestone dates), data/v1/session-clusters.json (session "
            "records), and data/v1/eras.json (era records). Race figures are "
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
        "head_to_head": head_to_head,
        "vault_pace": {
            "method": (
                "All 185 vault tracks with lifetime pace (snapshot plays "
                "divided by days from upload to the 2026-10-11 snapshot), "
                "release page, and as-credited producers. Powers the "
                "race-any-two-tracks tool and The Climb. Pace is a lifetime "
                "average, not a current rate."
            ),
            "count": len(vault_pace),
            "tracks": vault_pace,
        },
        "the_climb": the_climb,
        "race_history": race_history,
        "race_of_the_week": race_of_the_week,
        "snapshot_provenance": SNAPSHOT_PROVENANCE,
    }
    (API / "milestone-races.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (API / "schema" / "milestone-races.json").write_text(
        json.dumps(SCHEMA, indent=2) + "\n", encoding="utf-8")
    print(f"milestone-races: {len(play_races)} play races, "
          f"{len(h2h_pairs)} head-to-head pairs, "
          f"vault_pace = {len(vault_pace)}, climb = {len(climb)}, "
          f"closest = {closest_races[0]}, "
          f"summit contenders = {len(top5)}, "
          f"photo finish = {pf_a['name']} vs {pf_b['name']} ({pf_gap}d), "
          f"race of the week = {race_of_the_week['race_id']}")

    idx = json.loads((API / "index.json").read_text())
    idx["version"] = VERSION
    render_manifest(idx, ROOT)
    print(f"version -> {VERSION}; manifest re-rendered")


if __name__ == "__main__":
    main()
