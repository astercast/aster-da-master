#!/usr/bin/env python3
"""Wave 33: The Chronicle - one merged chronological stream.

New scripts/build_chronicle.py (22nd generator, LAST in the chain) merges
three real archive sources into a single filterable timeline:
api/v1/chronicle.json (endpoint #23, registered in index.json via
render_manifest(), draft-07 schema #23):

  - 61 upload sessions      <- data/sessions.json + api/v1/session-clusters.json
  - 9 dated milestones      <- api/v1/milestones.json (the longest silence is
                               a span: dated at its start, end_date carried)
  - 44 collaboration appearances <- api/v1/circle.json (one event per
                               title-credited appearance, release page
                               resolved by exact title+date join)

Every figure is recomputed here and the script exits non-zero on any
disagreement. Same-date ordering is milestone -> session -> collaboration
(a stated presentation rule, not an artist fact). Era assignment is by
calendar year via api/v1/eras.json; the 2017 feature credit predates the
eras and is honestly labeled "Before the vault".

Titles and metadata only - never lyrics, never invented bio facts.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "api" / "v1"
NEW_VERSION = "0.17.0"  # wave 33: new chronicle explorer endpoint
SNAPSHOT = "2026-10-11"

sys.path.insert(0, str(ROOT / "scripts"))
from api_manifest import render_manifest  # noqa: E402

SESS = json.loads((ROOT / "data" / "sessions.json").read_text())["sessions"]
CL = json.loads((API / "session-clusters.json").read_text())["sessions"]
MILES = json.loads((API / "milestones.json").read_text())["milestones"]
CIRCLE = json.loads((API / "circle.json").read_text())
ERAS = json.loads((API / "eras.json").read_text())["eras"]

KIND_ORDER = {"milestone": 0, "session": 1, "collaboration": 2}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def event_sort_key(e):
    """Chronological sort: date, then milestone -> session -> collaboration
    (stated presentation rule), then title. Pure logic, pinned by tests."""
    return (e["date"], KIND_ORDER[e["kind"]], e["title"])

# milestone -> hand-picked contextual link (documented, all verified on disk)
MILESTONE_LINKS = {
    "first-distributor": [("Release page",
                            "releases/lost-memories-feat-aster-da-master.html")],
    "first-collab": [("Circle page", "circle/jo-e-dripp.html")],
    "prolific-day": [("Session deep dive",
                      "sessions/the-november-3rd-12th-session.html")],
    "longest-silence": [("Gap visualization", "sessions-explorer.html")],
    "plays-250k": [("Milestone race", "milestone-race.html")],
}


def era_for_year(year):
    """Calendar year -> era id via eras.json years arrays; 2017 -> None."""
    for e in ERAS:
        if str(year) in e["years"]:
            return e["id"], e["name"]
    return None, "Before the vault"


def check_date(d, what):
    assert DATE_RE.match(d or ""), f"{what}: bad date {d!r}"
    date.fromisoformat(d)  # real calendar date, not just the shape


def main() -> int:
    assert len(SESS) == 61, f"session count drift: {len(SESS)}"
    assert len(CIRCLE) == 21, f"circle drift: {len(CIRCLE)}"
    cl_by_id = {s["id"]: s for s in CL}
    assert len(cl_by_id) == 61, "session-clusters drift"

    # (title, date) -> release page, for exact joins. Vault tracks first
    # (asserted pages from data/sessions.json); distributor singles fall
    # back to the discography ordinal -> releases/<slug>.html.
    page_by_track = {}
    for s in SESS:
        for t in s["tracks"]:
            page_by_track[(t["title"], t["date"])] = t["page"]
    DISC = json.loads((ROOT / "data" / "artist.json").read_text())["discography"]
    SLUGS = json.loads((API / "release-slugs.json").read_text())
    for i, e in enumerate(DISC):
        page_by_track.setdefault((e["title"], e["date"]),
                                 f"releases/{SLUGS[str(i)]}.html")
    sess_of_track = {}
    for s in SESS:
        for t in s["tracks"]:
            sess_of_track[(t["title"], t["date"])] = s["id"]

    era_list = [{"id": e["id"], "name": e["name"], "years": e["years"]}
                for e in ERAS]

    events = []

    # --- sessions ---
    for raw in SESS:
        enr = cl_by_id[raw["id"]]
        check_date(raw["start"], raw["id"])
        href = enr["deep_dive"] or f"sessions-explorer.html#card-{raw['id']}"
        events.append({
            "id": raw["id"],
            "date": raw["start"],
            "kind": "session",
            "era_id": enr["era_id"],
            "era_name": enr["era_name"],
            "title": raw["name"],
            "detail": (f"{raw['track_count']} transmissions, "
                       f"{raw['total_plays']:,} plays"),
            "plays": raw["total_plays"],
            "links": [{"label": "Deep dive" if enr["deep_dive"] else "Session card",
                       "href": href}],
            "collaborators": enr["collaborators"],
        })

    # --- milestones (8 dated + the longest silence as a span) ---
    for m in MILES:
        if m["date"] is None:
            assert m["id"] == "longest-silence", \
                f"unexpected undated milestone: {m['id']}"
            start, end = m["from"], m["to"]
            check_date(start, m["id"]), check_date(end, m["id"])
            links = [{"label": lab, "href": href}
                     for lab, href in MILESTONE_LINKS[m["id"]]]
            events.append({
                "id": m["id"],
                "date": start,
                "end_date": end,
                "kind": "milestone",
                "era_id": era_for_year(int(start[:4]))[0],
                "era_name": "The Silence",
                "title": m["name"],
                "detail": (f"{m['fact']} ({m['days']} days, "
                           f"{start} to {end})"),
                "plays": None,
                "links": links,
                "collaborators": [],
            })
            continue
        check_date(m["date"], m["id"])
        era_id, era_name = era_for_year(int(m["date"][:4]))
        links = [{"label": lab, "href": href}
                 for lab, href in MILESTONE_LINKS.get(m["id"], [])]
        if m.get("title"):
            key = (m["title"], m["date"])
            if key in page_by_track:
                links.insert(0, {"label": "Release page",
                                 "href": page_by_track[key]})
        # the first-collaboration milestone is about JO$E DRIPP: tag it so
        # the chronicle's voice filter can find it (verified: circle slug
        # jo-e-dripp, "Mistakes Ft. JO$E DRIPP", 2018-04-28)
        collab_slug = "jo-e-dripp" if m["id"] == "first-collab" else None
        collabs = ["JO$E DRIPP"] if collab_slug else []
        events.append({
            "id": m["id"],
            "date": m["date"],
            "kind": "milestone",
            "era_id": era_id,
            "era_name": era_name,
            "title": m["name"],
            "detail": m["fact"] + (f" \u2014 \u201c{m['title']}\u201d"
                                   if m.get("title") else ""),
            "plays": m.get("plays"),
            "links": links,
            "collaborators": collabs,
            "collab_slug": collab_slug,
        })

    # --- collaboration appearances (one event per title-credited track) ---
    collab_rows = []
    for slug, c in CIRCLE.items():
        for t in c["tracks"]:
            check_date(t["date"], f"{slug}/{t['title']}")
            key = (t["title"], t["date"])
            assert key in page_by_track, \
                f"circle track not in discography: {t['title']!r} ({t['date']})"
            page = page_by_track[key]
            assert (ROOT / page).exists(), \
                f"circle track page missing: {page}"
            sess_id = sess_of_track.get(key)  # None for distributor singles
            era_id, era_name = era_for_year(int(t["date"][:4]))
            collab_rows.append({
                "slug": slug, "name": c["name"], "page": c["page"],
                "title": t["title"], "date": t["date"], "plays": t["plays"],
                "release_page": page, "session_id": sess_id,
                "era_id": era_id, "era_name": era_name,
            })
    collab_rows.sort(key=lambda r: (r["date"], r["slug"], r["title"]))
    per_slug_n = {}
    for r in collab_rows:
        per_slug_n[r["slug"]] = per_slug_n.get(r["slug"], 0) + 1
        n = per_slug_n[r["slug"]]
        links = [{"label": "Release page", "href": r["release_page"]},
                 {"label": "Circle page", "href": r["page"]}]
        if r["session_id"]:
            links.append({"label": "Session",
                          "href": f"sessions-explorer.html#card-{r['session_id']}"})
        plays_txt = f"{r['plays']:,} plays" if r["plays"] is not None \
            else "distributor single \u2014 no vault plays on record"
        events.append({
            "id": f"collab-{r['slug']}-{n}",
            "date": r["date"],
            "kind": "collaboration",
            "era_id": r["era_id"],
            "era_name": r["era_name"],
            "title": r["title"],
            "detail": f"{r['name']} on the record \u2014 {plays_txt}",
            "plays": r["plays"],
            "links": links,
            "collaborators": [r["name"]],
            "collab_slug": r["slug"],
        })

    # --- order + assert ---
    events.sort(key=event_sort_key)
    by_kind = {"milestone": 0, "session": 0, "collaboration": 0}
    for e in events:
        by_kind[e["kind"]] += 1
    assert by_kind == {"milestone": 9, "session": 61, "collaboration": 44}, \
        f"event counts drift: {by_kind}"
    keys = [(e["date"], KIND_ORDER[e["kind"]], e["title"]) for e in events]
    assert keys == sorted(keys), "chronicle not in chronological order"
    assert len({e["id"] for e in events}) == len(events), "duplicate event ids"
    for e in events:
        for link in e["links"]:
            assert (ROOT / link["href"].split("#")[0]).exists(), \
                f"chronicle link dead: {e['id']} -> {link['href']}"
    # era coverage: every event year maps; only 2017 is pre-era
    years = {e["date"][:4] for e in events}
    assert years <= {"2017", "2018", "2019", "2020", "2021", "2022",
                     "2023", "2024", "2025", "2026"}, f"year drift: {years}"
    pre = [e for e in events if e["era_id"] is None]
    assert len(pre) == 1 and pre[0]["id"] == "first-distributor", \
        f"pre-era events drift: {[e['id'] for e in pre]}"

    collaborators = [{"slug": slug, "name": c["name"], "page": c["page"],
                      "appearances": per_slug_n.get(slug, 0)}
                     for slug, c in CIRCLE.items()]
    collaborators.sort(key=lambda c: (-c["appearances"], c["name"]))

    by_year = {}
    for e in events:
        by_year[e["date"][:4]] = by_year.get(e["date"][:4], 0) + 1
    busiest = max(sorted(by_year), key=lambda y: by_year[y])

    doc = {
        "version": NEW_VERSION,
        "generated": SNAPSHOT,
        "plays_snapshot": SNAPSHOT,
        "method": (
            "The Chronicle: sessions (data/sessions.json, enriched by "
            "api/v1/session-clusters.json), dated milestones "
            "(api/v1/milestones.json - the longest silence is a span, "
            "dated at its start with end_date carried), and one event per "
            "title-credited collaboration appearance (api/v1/circle.json, "
            "release page resolved by exact title+date join against "
            "data/sessions.json and data/artist.json). Merged and "
            "sorted chronologically; "
            "same-date order is milestone -> session -> collaboration (a "
            "stated presentation rule). Era by calendar year via "
            "api/v1/eras.json; the 2017 feature credit predates the eras "
            "('Before the vault'). Powers chronicle.html."
        ),
        "kinds": ["milestone", "session", "collaboration"],
        "same_date_order": ["milestone", "session", "collaboration"],
        "eras": era_list,
        "collaborators": collaborators,
        "events": events,
        "insights": {
            "event_count": len(events),
            "by_kind": by_kind,
            "first_date": events[0]["date"],
            "last_date": events[-1]["date"],
            "busiest_year": {"year": busiest, "events": by_year[busiest]},
            "first_event": {"id": events[0]["id"], "title": events[0]["title"],
                            "date": events[0]["date"]},
            "last_event": {"id": events[-1]["id"],
                           "title": events[-1]["title"],
                           "date": events[-1]["date"]},
            "note": "one merged stream: every session, every dated "
                    "milestone, every title-credited collaboration "
                    "appearance, in order",
        },
    }
    (API / "chronicle.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # draft-07 schema for the new endpoint
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "chronicle",
        "type": "object",
        "required": ["version", "generated", "plays_snapshot", "method",
                     "kinds", "same_date_order", "eras", "collaborators",
                     "events", "insights"],
        "properties": {
            "version": {"type": "string"},
            "generated": {"type": "string"},
            "plays_snapshot": {"type": "string"},
            "method": {"type": "string"},
            "kinds": {"type": "array", "items": {"type": "string"}},
            "same_date_order": {"type": "array",
                                "items": {"type": "string"}},
            "eras": {"type": "array"},
            "collaborators": {"type": "array"},
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "date", "kind", "era_id", "era_name",
                                 "title", "detail", "plays", "links",
                                 "collaborators"],
                    "properties": {
                        "id": {"type": "string"},
                        "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                        "end_date": {"type": "string",
                                     "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                        "kind": {"enum": ["milestone", "session",
                                          "collaboration"]},
                        "era_id": {"type": ["string", "null"]},
                        "era_name": {"type": "string"},
                        "title": {"type": "string"},
                        "detail": {"type": "string"},
                        "plays": {"type": ["integer", "null"]},
                        "links": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["label", "href"],
                                "properties": {
                                    "label": {"type": "string"},
                                    "href": {"type": "string"},
                                },
                            },
                        },
                        "collaborators": {"type": "array",
                                          "items": {"type": "string"}},
                        "collab_slug": {"type": ["string", "null"]},
                    },
                },
            },
            "insights": {"type": "object"},
        },
    }
    (API / "schema" / "chronicle.json").write_text(
        json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"chronicle: {len(events)} events "
          f"({by_kind['session']} sessions, {by_kind['milestone']} milestones, "
          f"{by_kind['collaboration']} collaborations), "
          f"{events[0]['date']} -> {events[-1]['date']}")

    idx = json.loads((API / "index.json").read_text())
    idx["version"] = NEW_VERSION
    render_manifest(idx, ROOT)
    print(f"version -> {NEW_VERSION}; manifest re-rendered")


if __name__ == "__main__":
    raise SystemExit(main())
