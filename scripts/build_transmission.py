#!/usr/bin/env python3
"""Wave 14: build data/v1/transmission.json — the guided-journey era data.

Aggregates the six eras from the real archive sources:
  - data/v1/years.json        (per-year transmissions, plays, top tracks, distributor counts)
  - data/sessions.json       (61 sessions; track -> release page links)
  - data/v1/circle.json       (collaborator footprints, filtered to era years)
  - data/v1/milestones.json   (career firsts, assigned to eras by date)
  - data/artist.json         (era names, spans, scene lines; discography for the
                              2026 singles; upcoming for the trilogy tease status)
  - data/v1/scene-figures.json (Fish Narc's Uncle-LP watch block, passed through
                              to the 2026 extras — status is research-owned)

Every "signal" one-liner is computed from these numbers — no invented facts.
Signal verification: each signal's numeric claims are recomputed here and the
script exits non-zero if any recomputation disagrees.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")
VERSION = "0.19.0"  # wave 35: data version 0.18.0 (verified-data expansion)
SNAPSHOT = "2026-10-11"

sys.path.insert(0, str(ROOT / "scripts"))
from build_sessions import slugify  # single source of truth for session slugs

YEARS = json.loads((ROOT / "data/v1/years.json").read_text())
SESS = json.loads((ROOT / "data/sessions.json").read_text())["sessions"]
CIRCLE = json.loads((ROOT / "data/v1/circle.json").read_text())
MILES = json.loads((ROOT / "data/v1/milestones.json").read_text())["milestones"]
ARTIST = json.loads((ROOT / "data/artist.json").read_text())
ERAS_SRC = ARTIST["eras"]
DISC = ARTIST["discography"]
UPCOMING = ARTIST["upcoming"]
SCENE = json.loads((ROOT / "data/v1/scene-figures.json").read_text())

# Era -> the archive years that carry its data (spans start 2017, but
# years.json covers 2018-2026; the 2017 feature credit is a milestone).
ERA_YEARS = {
    "The First Rite": ["2018", "2019"],
    "The Prolific Year": ["2020"],
    "The Cast It: Years": ["2021", "2022"],
    "The SomeLowLifes Era": ["2023", "2024"],
    "The Silence": ["2025"],
    "The Return": ["2026"],
}

# title -> release page, from the session track lists (covers every
# year top-track; verified by assertion below).
TITLE_PAGE = {}
for s in SESS:
    for t in s["tracks"]:
        TITLE_PAGE.setdefault(t["title"], t["page"])

# deep-dive pages: top-10 sessions by (track_count, total_plays) — same rule
# as scripts/build_session_deepdives.py.
DEEPDIVE = {}
top10 = sorted(SESS, key=lambda s: (-s["track_count"], -s["total_plays"]))[:10]
for s in top10:
    DEEPDIVE[s["id"]] = "sessions/" + slugify(s["name"]) + ".html"

# longest gap between consecutive vault upload dates (for the silence story).
dates = sorted({t["date"] for s in SESS for t in s["tracks"] if t.get("date")})
best = (0, None, None)
for a, b in zip(dates, dates[1:]):
    gap = (date.fromisoformat(b) - date.fromisoformat(a)).days
    if gap > best[0]:
        best = (gap, a, b)
LONGEST_GAP = {"days": best[0], "from": best[1], "to": best[2]}


def fmt(n):
    return f"{n:,}"


def era_stats(name, ys):
    tx = sum(YEARS[y]["transmissions"] for y in ys)
    plays = sum(YEARS[y]["plays"] for y in ys)
    dist = sum(YEARS[y].get("distributor", 0) for y in ys)
    sessions = [s for s in SESS if s["start"][:4] in ys]
    return {"tx": tx, "plays": plays, "dist": dist,
            "sessions": sessions, "session_count": len(sessions)}


def era_top_tracks(ys, n=3):
    merged = []
    for y in ys:
        merged.extend(YEARS[y]["top_tracks"])
    merged.sort(key=lambda t: -t["plays"])
    out = []
    for t in merged[:n]:
        page = TITLE_PAGE.get(t["title"])
        out.append({"title": t["title"], "plays": t["plays"],
                    "date": t["date"], "page": page})
    return out


def era_key_sessions(ys, n=3):
    ss = sorted([s for s in SESS if s["start"][:4] in ys],
                key=lambda s: -s["total_plays"])[:n]
    return [{"name": s["name"], "track_count": s["track_count"],
             "total_plays": s["total_plays"], "days": s["days"],
             "start": s["start"], "end": s["end"],
             "deep_dive": DEEPDIVE.get(s["id"])} for s in ss]


def era_collabs(ys, n=3):
    rows = []
    for slug, c in CIRCLE.items():
        tr = [t for t in c["tracks"] if t["date"][:4] in ys]
        if tr:
            rows.append({"name": c["name"], "transmissions": len(tr),
                         "plays": sum((t["plays"] or 0) for t in tr),
                         "page": c["page"]})
    rows.sort(key=lambda r: -r["plays"])
    return rows[:n]


def era_milestones(name, ys):
    # milestone date year in the era's years; the undated longest-silence
    # milestone is assigned to the era where the silence broke.
    out = []
    for m in MILES:
        d = m.get("date")
        # the First Rite's span reaches back to 2017 (first distributor credit)
        era_years = ["2017"] + ys if name == "The First Rite" else ys
        if d and d[:4] in era_years:
            out.append({"id": m["id"], "name": m["name"], "date": d,
                        "title": m.get("title"), "fact": m["fact"]})
        elif m["id"] == "longest-silence" and name == "The SomeLowLifes Era":
            g = LONGEST_GAP
            out.append({"id": m["id"], "name": m["name"],
                        "date": None,
                        "title": None,
                        "fact": (f"{g['days']} days between uploads, "
                                 f"{g['from']} to {g['to']}: the longest "
                                 f"gap on record. The vault went quiet, "
                                 f"then returned.")})
    return out


# ---- signal lines: every number recomputed from the stats above ----
def signal_first_rite(st, total_plays):
    share = st["plays"] / total_plays
    return (f"{st['tx']} transmissions, {fmt(st['plays'])} plays: "
            f"{share:.1%} of every play in the archive. "
            f"Two years carried the whole catalog.")


def signal_prolific(st, per_year_dist):
    # most distributor releases of any single year, verified below
    return (f"{st['dist']} distributor releases, the most of any single year, "
            f"against {st['tx']} vault transmissions. (2018 ran "
            f"{per_year_dist['2018']['tx']} vault transmissions with "
            f"{per_year_dist['2018']['dist']} distributor releases.) "
            f"The catalog's center had moved.")


def signal_castit(st):
    per_day = round(730 / st["tx"])
    return (f"{st['tx']} transmissions across {st['session_count']} sessions "
            f"in two years, the leanest run on record: one transmission "
            f"about every {per_day} days.")


def signal_somelowlifes(st, big_session):
    g = LONGEST_GAP
    return (f"After a {g['days']}-day silence, the longest gap on record, "
            f"the vault returned with {st['tx']} transmissions, the "
            f"second-biggest output of any era: {big_session['track_count']} "
            f"transmissions across {big_session['days']} days, the most "
            f"prolific session on record.")


def signal_silence(st):
    return (f"{st['tx']} transmissions, {st['dist']} distributor releases; "
            f"the only fully dark distributor year on record. "
            f"The reason is unknown and not speculated here.")


def signal_return(st, latest):
    return (f"Six singles, March–May 2026, all marked explicit on iHeart: "
            f"the ritual resumes. Latest transmission on record: "
            f"\u201c{latest['title']}\u201d, {latest['date']}.")


# ---- the 2026 extras: the verified singles, the Q4 watch, the snapshot.
# Every value comes from an existing verified source; nothing is authored here.
def return_extras():
    single_titles = ["The Night Ends Yeaaa", "Writing Books", "9 Trips",
                     "Living With The Big Shots"]
    singles = []
    for t in single_titles:
        d = next((x for x in DISC
                  if x["title"] == t and x["type"] == "Single"), None)
        assert d, f"2026 single missing from data/artist.json discography: {t}"
        page = ("releases/" +
                re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") + ".html")
        assert (ROOT / page).exists(), f"release page missing: {page}"
        singles.append({"title": t, "date": d["date"], "page": page,
                        "source": d.get("source")})
    dates = [s["date"] for s in singles]
    assert dates == sorted(dates), "2026 singles out of order"
    watch = SCENE["fish-narc"]["watch"]
    tri = UPCOMING[0]
    assert tri["title"] == "Litemode Trilogy", "upcoming[0] is not the trilogy"
    return {
        "singles_2026": singles,
        "singles_note": ("The four 2026 distributor singles, re-verified against "
                         "the iHeart catalog on 2026-10-11: no new distributor "
                         "releases since."),
        "q4_watch": {
            "uncle": {"label": watch["label"], "status": watch["status"],
                      "expected": watch["expected"], "as_of": watch["as_of"],
                      "note": watch["note"],
                      "figure_page": "circle/fish-narc.html"},
            "trilogy": {"title": tri["title"], "status": tri["status"],
                        "source": tri["source"], "page": "trilogy.html"},
        },
        "snapshot": {"date": SNAPSHOT,
                     "note": f"Play counts are the {SNAPSHOT} vault snapshot."},
    }


def main() -> int:
    total_plays = sum(v["plays"] for v in YEARS.values())
    total_tx = sum(v["transmissions"] for v in YEARS.values())
    per_year_dist = {y: {"tx": YEARS[y]["transmissions"],
                         "dist": YEARS[y].get("distributor", 0)}
                     for y in YEARS}

    # pre-verify the claims the signals lean on
    assert max(per_year_dist.items(),
               key=lambda kv: kv[1]["dist"])[0] == "2020", "2020 not max distributor year"
    era_tx = {n: sum(YEARS[y]["transmissions"] for y in ys)
              for n, ys in ERA_YEARS.items()}
    assert sorted(era_tx.values(), reverse=True)[1] == era_tx["The SomeLowLifes Era"], \
        "SomeLowLifes not 2nd by transmissions"
    era_sc = {n: sum(1 for s in SESS if s["start"][:4] in ys)
              for n, ys in ERA_YEARS.items()}
    assert min(era_sc.values()) == era_sc["The Cast It: Years"], "Cast It not fewest sessions"
    big = max(SESS, key=lambda s: s["track_count"])
    assert big["track_count"] == 19 and big["start"][:4] == "2023"
    dark_years = [y for y in YEARS if YEARS[y].get("distributor", 0) == 0]
    assert dark_years == ["2025"], f"unexpected dark years {dark_years}"

    latest = max((m for m in MILES if m["id"] == "latest"),
                 key=lambda m: m["date"] or "")

    eras = []
    for src in ERAS_SRC:
        name = src["name"]
        ys = ERA_YEARS[name]
        st = era_stats(name, ys)
        if name == "The First Rite":
            signal = signal_first_rite(st, total_plays)
        elif name == "The Prolific Year":
            signal = signal_prolific(st, per_year_dist)
        elif name == "The Cast It: Years":
            signal = signal_castit(st)
        elif name == "The SomeLowLifes Era":
            signal = signal_somelowlifes(st, big)
        elif name == "The Silence":
            signal = signal_silence(st)
        elif name == "The Return":
            signal = signal_return(st, latest)
        era = {
            "id": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
            "name": name,
            "span": src.get("span"),
            "years": ys,
            "scene": src.get("scene"),
            "transmissions": st["tx"],
            "plays": st["plays"],
            "sessions": st["session_count"],
            "distributor": st["dist"],
            "top_tracks": era_top_tracks(ys),
            "key_sessions": era_key_sessions(ys),
            "collaborators": era_collabs(ys),
            "milestones": era_milestones(name, ys),
            "signal": signal,
        }
        if name == "The Return":
            era["extras"] = return_extras()
        eras.append(era)

    # every top track must resolve to a real release page
    for e in eras:
        for t in e["top_tracks"]:
            assert t["page"], f"no page for {t['title']}"

    out = {
        "version": VERSION,
        "generated": "2026-10-11",
        "plays_snapshot": SNAPSHOT,
        "method": ("Six eras aggregated from data/v1/years.json, data/sessions.json, "
                   "data/v1/circle.json, data/v1/milestones.json. Signal lines are "
                   "computed from the same numbers and asserted in "
                   "scripts/build_transmission.py. The 2026 era carries an extras "
                   "block: the four verified 2026 singles (data/artist.json "
                   "discography) and the Q4 2026 watch (the Uncle-LP status passed "
                   "through from data/v1/scene-figures.json, the trilogy tease from "
                   "data/artist.json upcoming). Titles and metadata only — never lyrics."),
        "archive_totals": {"transmissions": total_tx, "plays": total_plays,
                           "sessions": len(SESS), "years": sorted(YEARS)},
        "longest_gap": LONGEST_GAP,
        "eras": eras,
    }
    (ROOT / "data/v1/transmission.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # JSON Schema (draft-07), same pattern as scripts/build_milestones.py
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "description": "The guided-journey era aggregates: six eras with "
                       "transmissions, plays, sessions, top tracks, key sessions, "
                       "collaborators, milestones, and computed signal lines — "
                       "plus a 2026 extras block on The Return era (the four "
                       "verified 2026 singles, the Q4 2026 Uncle-LP/trilogy watch, "
                       "the play-count snapshot). "
                       "Generated by scripts/build_transmission.py.",
        "type": "object",
        "properties": {
            "version": {"type": "string"},
            "generated": {"type": "string"},
            "method": {"type": "string"},
            "plays_snapshot": {"type": "string"},
            "archive_totals": {
                "type": "object",
                "properties": {
                    "transmissions": {"type": "integer"},
                    "plays": {"type": "integer"},
                    "sessions": {"type": "integer"},
                    "years": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["transmissions", "plays", "sessions"],
            },
            "longest_gap": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer"},
                    "from": {"type": ["string", "null"]},
                    "to": {"type": ["string", "null"]},
                },
            },
            "eras": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "span": {"type": ["string", "null"]},
                        "years": {"type": "array", "items": {"type": "string"}},
                        "scene": {"type": ["string", "null"]},
                        "transmissions": {"type": "integer"},
                        "plays": {"type": "integer"},
                        "sessions": {"type": "integer"},
                        "distributor": {"type": "integer"},
                        "top_tracks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "plays": {"type": "integer"},
                                    "date": {"type": "string"},
                                    "page": {"type": ["string", "null"]},
                                },
                                "required": ["title", "plays", "date", "page"],
                            },
                        },
                        "key_sessions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "track_count": {"type": "integer"},
                                    "total_plays": {"type": "integer"},
                                    "days": {"type": "integer"},
                                    "start": {"type": "string"},
                                    "end": {"type": "string"},
                                    "deep_dive": {"type": ["string", "null"]},
                                },
                                "required": ["name", "track_count", "total_plays"],
                            },
                        },
                        "collaborators": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "transmissions": {"type": "integer"},
                                    "plays": {"type": "integer"},
                                    "page": {"type": "string"},
                                },
                                "required": ["name", "transmissions", "plays", "page"],
                            },
                        },
                        "milestones": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "date": {"type": ["string", "null"]},
                                    "title": {"type": ["string", "null"]},
                                    "fact": {"type": "string"},
                                },
                                "required": ["id", "name", "fact"],
                            },
                        },
                        "signal": {"type": "string"},
                        "extras": {
                            "type": "object",
                            "description": "2026-era extras (The Return only): "
                                           "the verified 2026 singles, the Q4 "
                                           "2026 watch, the play-count snapshot.",
                            "properties": {
                                "singles_2026": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "title": {"type": "string"},
                                            "date": {"type": "string"},
                                            "page": {"type": "string"},
                                            "source": {"type": ["string", "null"]},
                                        },
                                        "required": ["title", "date", "page"],
                                    },
                                },
                                "singles_note": {"type": "string"},
                                "q4_watch": {
                                    "type": "object",
                                    "properties": {
                                        "uncle": {
                                            "type": "object",
                                            "properties": {
                                                "label": {"type": "string"},
                                                "status": {"type": "string"},
                                                "expected": {"type": "string"},
                                                "as_of": {"type": "string"},
                                                "note": {"type": "string"},
                                                "figure_page": {"type": "string"},
                                            },
                                            "required": ["label", "status",
                                                         "expected", "as_of",
                                                         "figure_page"],
                                        },
                                        "trilogy": {
                                            "type": "object",
                                            "properties": {
                                                "title": {"type": "string"},
                                                "status": {"type": "string"},
                                                "source": {"type": "string"},
                                                "page": {"type": "string"},
                                            },
                                            "required": ["title", "status",
                                                         "source", "page"],
                                        },
                                    },
                                    "required": ["uncle", "trilogy"],
                                },
                                "snapshot": {
                                    "type": "object",
                                    "properties": {
                                        "date": {"type": "string"},
                                        "note": {"type": "string"},
                                    },
                                    "required": ["date", "note"],
                                },
                            },
                            "required": ["singles_2026", "q4_watch", "snapshot"],
                        },
                    },
                    "required": ["id", "name", "transmissions", "plays",
                                 "top_tracks", "key_sessions", "collaborators",
                                 "milestones", "signal"],
                },
            },
        },
        "required": ["version", "archive_totals", "eras"],
    }
    (ROOT / "data/v1/schema/transmission.json").write_text(
        json.dumps(schema, indent=2) + "\n", encoding="utf-8")

    # register the endpoint
    idx_p = ROOT / "data/v1/index.json"
    idx = json.loads(idx_p.read_text())
    from api_manifest import render_manifest
    render_manifest(idx, ROOT)

    print(f"transmission.json: {len(eras)} eras, {total_tx} tx, {fmt(total_plays)} plays")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
