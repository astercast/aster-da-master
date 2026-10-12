"""Canonical api/v1/index.json manifest writer (wave 17).

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
    ("transmission",
     "The guided journey: six eras with stats, top tracks, key sessions, collaborators, milestones, and computed signal lines.",
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
]

DOCUMENTS = {
    "AGENT.md": "Agent operator's manual: base URL pattern, key endpoints with example requests, end-to-end workflows, rate/expectation notes.",
    "agents.html": "Human + agent surface: 16-endpoint table, llms files, skills, search-index usage, rates & expectations, worked workflows.",
    "API.md": "Human-readable API reference incl. the shared cross-site conventions block.",
    "llms.txt": "Short agent brief: catalog shape, method, API map, key verified facts, ops.",
    "llms-full.txt": "Full agent brief: per-era detail, collaborator research notes, unknowns register, page map, generator order.",
}


def render_manifest(idx, root):
    """Rebuild the manifest's endpoints/meta/skills/documents blocks
    canonically around the caller's idx dict (which carries
    name/version/observed/repository/for_agents/provenance). Writes
    api/v1/index.json byte-deterministically."""
    root = Path(root)
    api = root / "api" / "v1"
    ver = idx.get("version", "0.12.0")

    endpoints = {}
    for key, desc, schema, notes, counter in ENDPOINT_ORDER:
        endpoints[key] = {
            "path": "api/v1/%s.json" % key,
            "description": desc,
            "schema": "api/v1/schema/%s" % schema,
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
            "base": "api/v1/",
            "auth": "none - static files; no keys, no rate limits",
        },
        "repository": idx.get("repository", "https://github.com/astercast/aster-da-master"),
        "for_agents": idx.get("for_agents",
                              "Start at api/v1/index.json. The artist record is the source of truth; data/artist.json feeds the site renderer."),
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
    api = root / "api" / "v1"
    idx = json.loads((api / "index.json").read_text())
    if version is not None:
        idx["version"] = version
    render_manifest(idx, root)


if __name__ == "__main__":
    write_manifest(Path(__file__).resolve().parent.parent)
    print("index.json rebuilt canonically")
