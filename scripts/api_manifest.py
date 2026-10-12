"""Canonical data/v1/index.json manifest writer (wave 17).

Every build_*.py generator that touches the manifest keeps its own
version/provenance logic, then calls render_manifest(idx, ROOT) instead of
hand-editing the endpoints map. The endpoints/meta/skills/documents blocks are
fully rebuilt from this module's canonical table on every call, so the
generator chain is byte-stable no matter which generator runs last.

Manifest contract (the cross-site gold standard):
- endpoints.<key> = {path, description, schema, updated, records, notes}
- meta.version mirrors the top-level version (breaking changes get v2/, never
  a silent shape change)
- updated is the pinned snapshot timestamp "2026-10-11T00:00:00Z" (never
  date.today() - see wave-15 lesson on generator drift)
- record counts are computed from the real payload files on disk
"""
import json
from pathlib import Path

SNAPSHOT = "2026-10-11"
UPDATED = "2026-10-11T00:00:00Z"


def _doc(api, name):
    return json.loads((api / name).read_text())


# key, description, schema file, notes, records counter
ENDPOINT_ORDER = [
    ("index",
     "Manifest: every endpoint with description, schema URL, updated timestamp, record counts, and deprecation notes. Start here.",
     "index.json", "meta.version mirrors the top-level version field.",
     lambda api: len(ENDPOINT_ORDER)),
    ("artist",
     "The source of truth: artist record - bio, facts, discography (219 entries), platforms, eras, vault, upcoming. data/artist.json feeds the site renderer and mirrors it.",
     "artist.json", "",
     lambda api: len(_doc(api, "artist.json")["discography"])),
    ("codex",
     "The vocabulary codex: 16 word families with per-family track lists.",
     "codex.json", "",
     lambda api: len(_doc(api, "codex.json")["families"])),
    ("release-slugs",
     "Slug index for the generated release pages: ordinal string -> slug.",
     "release-slugs.json", "",
     lambda api: len(_doc(api, "release-slugs.json"))),
    ("on-this-day",
     "Calendar index: transmissions keyed by MM-DD upload date.",
     "on-this-day.json", "",
     lambda api: len(_doc(api, "on-this-day.json"))),
    ("years",
     "Year-in-review archive: per-year stats and highlights, 2018-2026.",
     "years.json", "",
     lambda api: len(_doc(api, "years.json"))),
    ("circle",
     "The collaborators: 21 voices parsed from title credits.",
     "circle.json", "Title-credit only; producers live in scene-figures.json.",
     lambda api: len(_doc(api, "circle.json"))),
    ("milestones",
     "Career firsts computed from the verified discography: firsts, records, silences.",
     "milestones.json", "",
     lambda api: len(_doc(api, "milestones.json")["milestones"])),
    ("sessions",
     "Upload sessions: 61 studio sessions clustered from vault upload dates (7-day gap rule).",
     "sessions.json", "Computed clusters, not artist-named studio sessions.",
     lambda api: len(_doc(api, "sessions.json")["sessions"])),
    ("changelog",
     "Site construction history, generated from the git log.",
     "changelog.json", "A changelog built from git log cannot record its own sync commit (wave-15 convention, WAVELOG.md).",
     lambda api: _doc(api, "changelog.json")["entry_count"]),
    ("first-last",
     "Per year 2018-2026: the opening and closing transmissions.",
     "first-last.json", "",
     lambda api: len(_doc(api, "first-last.json")["years"])),
    ("milestone-watch",
     "Milestone watch: vault tracks near round-number play counts.",
     "milestone-watch.json", "Play counts are a 2026-10-11 snapshot; they drift.",
     lambda api: len(_doc(api, "milestone-watch.json").get("bands", []))),
    ("scene-figures",
     "Scene figures: producer credits and scene research outside the 21 (e.g. Fish Narc).",
     "scene-figures.json", "",
     lambda api: len(_doc(api, "scene-figures.json"))),
    ("signal-watch",
     "The Signal 2.0 watch file: the latest SoundCloud capture diffed against the previous one - new uploads, play-count movers, milestone crossings, the next-up board, and the capture history. Written by the daily Signal cron (lib/signal-watch.js) and seeded from the two 2026-10-11 captures by scripts/build_signal_watch.py. Records = tracks watched.",
     "signal-watch.json", "Captures, not a live feed; per_day is null when two captures sit under 24 hours apart - a rate is never invented.",
     lambda api: _doc(api, "signal-watch.json")["summary"]["tracks_watched"]),
    ("live-dates",
     "The live-date verification board: scene events (Fish Narc's 'Uncle' release week, capoxxo's October 2026 support dates) each hand-checked against the web on the stated checked_at date, with a verified / single-source / unconfirmed status, sources, and discrepancies kept on the record. Records = dated events + unconfirmed leads.",
     "live-dates.json", "Research, not a scrape: re-swept by hand, never auto-updated; statuses are as of checked_at.",
     lambda api: len(_doc(api, "live-dates.json")["events"]) + len(_doc(api, "live-dates.json")["unconfirmed"])),
    ("transmission",
     "The guided journey: 13 stops — six eras with stats, top tracks, key sessions, collaborators, milestones, and computed signal lines, plus seven live data chapters (The Race, The Record Book, The Codex, The Architects, The Seasons, The Deep Cuts, The Horizon) — plus a 2026 extras block on The Return era (the four verified 2026 singles, the Q4 2026 Uncle-LP/trilogy watch, the play-count snapshot).",
     "transmission.json", "",
     lambda api: len(_doc(api, "transmission.json")["eras"])),
    ("network",
     "Collaboration network: artist-centered nodes (21 title-credited collaborators + producer scene figures), track-weighted edges, co-credit links, computed insights.",
     "network.json", "23 nodes / 27 edges; no producer-collaborator edges exist on record.",
     lambda api: len(_doc(api, "network.json")["nodes"])),
    ("eras",
     "Era deep-dives: six eras with full transmission lists (every track + plays), ALL in-era collaborators, active codex families, milestones, computed signal lines and summaries. Data source for the eras/<id>.html deep-dive pages.",
     "eras.json", "collaborators[] holds every in-era voice; transmission.json keeps only the top 3.",
     lambda api: len(_doc(api, "eras.json")["eras"])),
    ("session-clusters",
     "Session archaeology, interactive: the 61 upload sessions as an explorable timeline - per-session enrichment (era, loudest + deepest-cut tracks, title-credited collaborators, deep-dive/era/journey cross-links), the 60 inter-session gaps, activity seasons, and asserted insights. Data source for sessions-explorer.html.",
     "session-clusters.json", "Seasons are a computed browsing convention (silence > 90 days opens a new season), not artist-named eras.",
     lambda api: len(_doc(api, "session-clusters.json")["clusters"])),
    ("codex-families",
     "Codex family deep-dives: the 16 vocabulary families with decoded readings (traced verbatim to codex.json epithets; unknown where the archive assigns no meaning), era-by-era evolution, key sessions, and title-credited collaborators. Data source for the codex/<slug>.html deep-dive pages.",
     "codex-families.json", "",
     lambda api: len(_doc(api, "codex-families.json")["families"])),
    ("milestone-races",
     "The milestone race: approaching play-count milestones as races (current value, target, gap, and pace-arithmetic estimates - never predictions), the 30,088-play summit chase, session and era record book, and the most recently crossed milestones. Data source for milestone-race.html.",
     "milestone-races.json", "Pace figures are arithmetic on the 2026-10-11 snapshot, not predictions.",
     lambda api: len(_doc(api, "milestone-races.json")["play_races"])),
    ("session-tools",
     "Session explorer 2.0 tooling: per-session compare profiles (stats, loudest + deepest-cut tracks, collaborators, play profiles, family/session/era/journey cross-links), the honest snapshot-history state (one 2026-10-11 snapshot - no play trajectories exist), and the deepest-sessions editorial ranking (lowest average plays per transmission, min 2 transmissions, formula stated). Data source for sessions-explorer.html's compare / deepest-cuts / timeline-scrubber sections.",
     "session-tools.json", "The deepest-cuts ranking is editorial (formula stated in the payload), not an artist fact.",
     lambda api: len(_doc(api, "session-tools.json")["sessions"])),
    ("codex-network",
     "The codex network: 16 word families as nodes, shared title-credited collaborators and title-parsed producers as edges, BFS degrees of separation from Aster, the family-overlap graph, and the connect-the-dots shortest-path data. Data source for codex-network.html.",
     "codex-network.json", "Producer credits are parsed from titles (as credited, verbatim); degrees are BFS distances on this graph, not a social claim.",
     lambda api: len(_doc(api, "codex-network.json")["nodes"])),
    ("producer-deepdives",
     "Producer deep-dives: every as-credited producer in the archive (title prod./produced-by fragments, verbatim) with credited productions (release/session links, co-producers, title-credited voices), codex family ties, a computed production fingerprint, and sourced research where a research pass exists. Data source for producers/<slug>.html.",
     "producer-deepdives.json", "Fingerprints are computed from the archive's credits, not biographies; research blocks carry their evidence flag.",
     lambda api: len(_doc(api, "producer-deepdives.json")["producers"])),
    ("chronicle",
     "The Chronicle: one merged chronological stream - all 61 upload sessions, all 9 dated milestones (the 553-day longest silence as a span), and all 44 title-credited collaboration appearances, each with era assignment, cross-links (release / circle / session pages), and collaborator tags. Data source for chronicle.html.",
     "chronicle.json", "Same-date order is milestone -> session -> collaboration (a stated presentation rule); the 2017 feature credit predates the eras.",
     lambda api: len(_doc(api, "chronicle.json")["events"])),
]

DOCUMENTS = {
    "AGENT.md": "Agent operator's manual: base URL pattern, key endpoints with example requests, end-to-end workflows, rate/expectation notes.",
    "agents.html": "Human + agent surface: 23-endpoint table, llms files, skills, search-index usage, rates & expectations, worked workflows.",
    "API.md": "Human-readable API reference incl. the shared cross-site conventions block.",
    "llms.txt": "Short agent brief: catalog shape, method, API map, key verified facts, ops.",
    "llms-full.txt": "Full agent brief: per-era detail, collaborator research notes, unknowns register, page map, generator order.",
}


def render_manifest(idx, root):
    """Rebuild the manifest's endpoints/meta/skills/documents blocks
    canonically around the caller's idx dict (which carries
    name/version/observed/repository/for_agents/provenance). Writes
    data/v1/index.json byte-deterministically."""
    root = Path(root)
    api = root / "data" / "v1"
    ver = idx.get("version", "0.13.0")

    endpoints = {}
    for key, desc, schema, notes, counter in ENDPOINT_ORDER:
        endpoints[key] = {
            "path": "data/v1/%s.json" % key,
            "description": desc,
            "schema": "data/v1/schema/%s" % schema,
            "updated": UPDATED,
            "records": counter(api),
            "notes": notes,
        }

    skills = sorted((root / "skills").glob("*.md"))
    out = {
        "name": idx.get("name", "Aster da Master API"),
        "version": ver,
        "observed": idx.get("observed", SNAPSHOT),
        "meta": {
            "version": ver,
            "generated": UPDATED,
            "base": "data/v1/",
            "auth": "none - static files; no keys, no rate limits",
        },
        "repository": idx.get("repository", "https://github.com/astercast/aster-da-master"),
        "for_agents": idx.get("for_agents",
                              "Start at data/v1/index.json. The artist record is the source of truth; data/artist.json feeds the site renderer."),
        "provenance": idx.get("provenance", ""),
        "skills": {
            "registry": "skills/index.json",
            "count": len(skills),
            "note": "Hand-maintained markdown playbooks; not generated by scripts/build_*.py.",
        },
        "endpoints": endpoints,
        "documents": DOCUMENTS,
    }
    (api / "index.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def write_manifest(root, version=None):
    """Read the current manifest, optionally bump version, re-render."""
    root = Path(root)
    api = root / "data" / "v1"
    idx = json.loads((api / "index.json").read_text())
    if version is not None:
        idx["version"] = version
    render_manifest(idx, root)


if __name__ == "__main__":
    write_manifest(Path(__file__).resolve().parent.parent)
    print("index.json rebuilt canonically")
