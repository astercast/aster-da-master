#!/usr/bin/env python3
"""Build the producer deep-dives (wave 27).

22nd generator, LAST in the chain. Gives every as-credited producer in the
archive their own deep-dive page, the way the codex families got theirs.

Reads:
  data/sessions.json           (all tracks; producer credits parsed from the
                                titles' own prod./produced-by fragments,
                                as credited verbatim - nothing invented)
  data/producer-research.json  (hand-maintained research pass 2026-10-11;
                                asserted, never silently extended)
  data/v1/codex-network.json    (family-figure edges -> codex family ties)
  data/v1/codex-families.json   (family names + pages)
  data/v1/circle.json           (title-credited voices -> circle pages)
  data/v1/scene-figures.json    (scene-figure pages, e.g. fish-narc)

Emits:
  data/v1/producer-deepdives.json        (endpoint #22)
  data/v1/schema/producer-deepdives.json (draft-07 schema #22)
  producers/<slug>.html                 (one per producer - this generator
                                         OWNS the producers/ directory)
  producers/index.html
  data/v1/index.json                     (endpoint registered via render_manifest())

Per producer, every credit recomputed and asserted:
  - every as-credited production, with plays + release page + session page
  - co-producers credited on the same title (as-credited, verbatim)
  - title-credited voices on their productions (circle page links)
  - codex families carrying their productions (from codex-network.json)
  - the fingerprint: DERIVED stats only (counts, spans, rates) - labeled as
    computed from the archive's credits, never a biography
  - research: only from data/producer-research.json, each block carrying its
    evidence flag (verified / single-source / archive-only)

Slug rule: identical to the codex network's fig_id_for, minus the "fig-p-"
prefix, so the explorer's producer-node deep links (producers/<slug>.html,
built from the node id client-side) resolve 1:1. Spelling variants that
slug identically (deephartt/DeepHartt, astral_hp/astral hp) merge into one
producer, canonical name = most credits (tie: first seen), aliases recorded.
Total credit count is conserved across the merge - asserted.

Byte-stable: pinned SNAPSHOT, deterministic ordering, json indent=2.

VERSION is a mirror-only constant: wave 27 adds no new source data
(everything is derived from data/sessions.json plus the hand-maintained
research input), so the data version stays 0.14.0.

Pure logic lives at module top level (import-safe: build_codex_pages.py and
build_circle.py import parse_producers / producer_slug from here).
Everything that touches disk runs under main().
"""
import json
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_releases import slugify  # noqa: E402  (single source of truth)
from build_codex import HEAD, FOOT  # noqa: E402

import nav_data  # noqa: E402  (canonical nav data — scripts/nav_data.py)
# Producer pages inherit build_codex's HEAD/FOOT; swap its codex nav
# chunk for the producers variant from the canonical data (whose Codex
# door points at ../codex/ — the inherited chunk's "./" door resolved
# to the producers index).
HEAD = HEAD.replace(nav_data.nav_chunk("../", "codex"),
                    nav_data.nav_chunk("../", "producers"))
FOOT = FOOT.replace(nav_data.footer_block("../", "codex"),
                    nav_data.footer_block("../", "producers"))
from api_manifest import render_manifest  # noqa: E402

API = ROOT / "data" / "v1"
SESSIONS = ROOT / "data" / "sessions.json"

VERSION = "0.19.0"  # wave 35: data version 0.18.0 (verified-data expansion)
SNAPSHOT = "2026-10-11"
GENERATED = "2026-10-11T00:00:00Z"

PROD_DIR = ROOT / "producers"
API_OUT = API / "producer-deepdives.json"
SCHEMA_OUT = API / "schema" / "producer-deepdives.json"


def fmt(n):
    return f"{n:,}"


# --- pure logic (import-safe; imported by build_codex_pages.py) ------------


def parse_producers(title):
    """Producer credits from the title's own prod./produced-by fragment.

    Canonical copy: identical rule to the codex network's parse_producers
    (wave 26) - as credited, verbatim; nothing invented. Splits multi-producer
    credits on x / & / + / comma / slash / "and". Returns a list of producer
    names.
    """
    m = re.search(r"prod(?:\.|uced\s+by)?\s*", title, re.I)
    if not m:
        return []
    rest = title[m.end():]
    # the credit lives inside one bracket/paren group; cut at its close
    rest = re.split(r"[)\]\[]", rest)[0]
    # drop trailing hashtags like #NITEMODE
    rest = re.sub(r"#\w+", "", rest)
    names = []
    for p in re.split(r"\s+[xX]\s+|\s*&\s*|\+|,|\s*/\s*|\s+and\s+", rest):
        p = p.strip()
        p = re.sub(r"^[\s.$~!\"'(\[]+|[\s.$~!\"')\]]+$", "", p)
        p = re.sub(r"\.(wav|mp3|flac)$", "", p, flags=re.I)
        p = p.strip()
        if (p and len(p) <= 30
                and not re.search(r"aster\s*da\s*master", p, re.I)):
            names.append(p)
    # dedupe case-insensitively, keep the first-seen spelling
    seen, out = set(), []
    for n in names:
        k = n.lower()
        if k not in seen:
            seen.add(k)
            out.append(n)
    return out


def producer_slug(name):
    """URL slug for a producer name. Identical rule to the codex network's
    fig_id_for, minus the 'fig-p-' prefix."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def producer_page(slug):
    return f"producers/{slug}.html"


def network_fig_id(name, circle_by_name):
    """The codex network's figure-node id rule for producers (wave 26,
    build_codex_network.py): 'fish narc' -> fig-fish-narc; a producer name
    matching a circle member -> fig-<circle slug>; else fig-p-<slug>.
    circle_by_name: {name.lower(): {"slug": ..., ...}}."""
    low = name.lower()
    if low == "fish narc":
        return "fig-fish-narc"
    if low in circle_by_name:
        return "fig-" + circle_by_name[low]["slug"]
    return "fig-p-" + producer_slug(name)


def canonical_producers(sessions):
    """Merge all as-credited producer names into canonical producers.

    sessions: the data/sessions.json sessions list. Returns a list of dicts
    {name, slug, aliases, credits} where each credit is (title, session_id,
    session_name, track). Spelling variants that slug identically merge;
    canonical name = most credits, tie broken by first-seen order. Credit
    totals are conserved (asserted by the caller).
    """
    raw = {}  # name -> [credits]
    order = []
    for s in sessions:
        for t in s["tracks"]:
            for p in parse_producers(t["title"]):
                if p not in raw:
                    raw[p] = []
                    order.append(p)
                raw[p].append((t["title"], s["id"], s["name"], t))
    by_slug = {}
    for name in order:
        slug = producer_slug(name)
        by_slug.setdefault(slug, []).append(name)
    out = []
    for slug in sorted(by_slug):
        names = sorted(by_slug[slug],
                       key=lambda n: (-len(raw[n]), order.index(n)))
        canonical = names[0]
        credits = []
        for n in names:
            credits.extend(raw[n])
        out.append({"name": canonical, "slug": slug,
                    "aliases": [n for n in names[1:]],
                    "credits": credits})
    return out


# --- page templates ---------------------------------------------------------

def breadcrumb(name):
    return (f'<nav class="crumbs" aria-label="Breadcrumb">'
            f'<a href="../">Home</a> / '
            f'<a href="./">Producers</a> / '
            f'<span aria-current="page">{escape(name)}</span></nav>')


def producer_page_html(p, racing=()):
    """Deep-dive page for one producer.

    racing: slugs of producers with a track in an active milestone race -
    they get a race-watch keep-digging link (wave 28).
    """
    parts = [breadcrumb(p["name"])]
    parts.append(f"""
      <p class="kicker"><span class="numeral">&#10022;</span>Producer deep dive</p>
      <h1 class="page-title">{escape(p["name"])}</h1>
      <p class="chart-sub">{"Also credited as " + ", ".join(escape(a) for a in p["aliases"]) + ". " if p["aliases"] else ""}"""
               f"""Every production below is as credited in the archive's own titles &mdash; nothing invented, nothing added.</p>
      <div class="stat-grid">
        <div class="stat-cell"><span class="stat-n">{p["production_count"]}</span><span class="stat-l">Productions</span></div>
        <div class="stat-cell"><span class="stat-n">{fmt(p["total_plays"])}</span><span class="stat-l">Total plays</span></div>
        <div class="stat-cell"><span class="stat-n">{escape(p["years_active"])}</span><span class="stat-l">Years active</span></div>
        <div class="stat-cell"><span class="stat-n">{len(p["codex_families"])}</span><span class="stat-l">Codex families</span></div>
      </div>
""")
    if p["research"]:
        r = p["research"]
        facts = "".join(f"<li>{escape(f)}</li>" for f in r["facts"])
        srcs = "".join(
            f'<li><a href="{escape(s["url"])}" rel="noopener">{escape(s["label"])}</a></li>'
            for s in r["sources"])
        parts.append(f"""
      <section class="section" aria-labelledby="res-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Research</span>
        <h2 id="res-h">Scene context</h2>
        <p class="chart-sub">Evidence: {escape(r["evidence"])}</p>
        <ul class="story-list">{facts}</ul>
        <p class="chart-sub">Sources:</p>
        <ul class="src-list">{srcs}</ul>
      </section>
""")
    rows = []
    for pr in p["productions"]:
        co = "".join(
            f' <a href="{escape(c["page"].split("/")[-1])}">{escape(c["name"])}</a>'
            for c in pr["co_producers"])
        co_html = f"<br>co-produced with:{co}" if co else ""
        voices = "".join(
            f' <a href="../{escape(v["page"])}">{escape(v["name"])}</a>'
            for v in pr["voices"])
        voices_html = f"<br>voices:{voices}" if voices else ""
        rows.append(
            f'<tr><th scope="row"><a href="../{escape(pr["release_page"])}">{escape(pr["title"])}</a></th>'
            f'<td>{escape(pr["date"] or "date unknown")}</td>'
            f'<td class="num">{fmt(pr["plays"])}</td>'
            f'<td><a href="../{escape(pr["session_page"])}">{escape(pr["session_name"])}</a>{co_html}{voices_html}</td></tr>')
    parts.append(f"""
      <section class="section" aria-labelledby="prod-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Credited productions</span>
        <h2 id="prod-h">Where to hear them</h2>
        <div class="table-wrap"><table class="data-table">
          <caption class="visually-hidden">Every as-credited {escape(p["name"])} production, with plays, session, co-producers, and voices</caption>
          <thead><tr><th scope="col">Transmission</th><th scope="col">Date</th><th scope="col">Plays</th><th scope="col">Session &amp; credits</th></tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table></div>
      </section>
""")
    if p["codex_families"]:
        fam_rows = "".join(
            f'<li><a href="../{escape(f["family_page"])}">{escape(f["family_name"])}</a> '
            f'&mdash; &times;{f["transmissions"]}: {escape("; ".join(f["titles"]))}</li>'
            for f in p["codex_families"])
        parts.append(f"""
      <section class="section" aria-labelledby="fam-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Codex ties</span>
        <h2 id="fam-h">Carrying families</h2>
        <ul class="story-list">{fam_rows}</ul>
      </section>
""")
    fp = p["fingerprint"]
    fp_rows = [
        ("Most-played production",
         f'{fp["top_production"]["title"]} ({fmt(fp["top_production"]["plays"])} plays)'),
        ("Solo-credit rate",
         f'{fp["solo_rate_pct"]}% of productions credit them alone'),
        ("Frequent co-producers",
         ", ".join(f'{c["name"]} (×{c["shared"]})' for c in fp["co_producers"][:3]) or "none"),
        ("Most frequent voice on their productions",
         fp["top_voice"] or "none title-credited"),
        ("First production", f'{fp["first"]["title"]} ({fp["first"]["date"]})'),
        ("Latest production", f'{fp["last"]["title"]} ({fp["last"]["date"]})'),
    ]
    fp_html = "".join(
        f"<dt>{escape(k)}</dt><dd>{escape(v)}</dd>" for k, v in fp_rows)
    parts.append(f"""
      <section class="section" aria-labelledby="fp-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Fingerprint</span>
        <h2 id="fp-h">The archive's read</h2>
        <p class="chart-sub">Computed from the archive's own credits &mdash; a production fingerprint, not a biography. No style claims the titles don't make.</p>
        <dl class="fact-list">{fp_html}</dl>
      </section>
""")
    keep = [f'<li><a href="./">All producers</a> &mdash; the full index of as-credited producers.</li>']
    if p["slug"] in racing:
        keep.append(
            '<li><a href="../milestone-race.html#watch">Milestone race &mdash; race to watch</a> '
            '&mdash; a track produced by this producer is in an active '
            'play-count race.</li>')
    if p["explorer_deep_link"]:
        keep.append(
            f'<li><a href="../codex-network.html#{escape(p["explorer_deep_link"])}">Codex network</a> '
            f'&mdash; this producer on the family graph, with degrees of separation from Aster.</li>')
    for f in p["codex_families"]:
        keep.append(
            f'<li><a href="../{escape(f["family_page"])}">{escape(f["family_name"])}</a> '
            f'&mdash; the codex family carrying this producer.</li>')
    keep.append('<li><a href="../sessions-explorer.html">Sessions explorer</a> &mdash; the 61 upload sessions on one timeline.</li>')
    parts.append(f"""
      <section class="section" aria-labelledby="keep-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Keep digging</span>
        <h3 id="keep-h">The journey continues</h3>
        <ul class="story-list">{"".join(keep)}</ul>
      </section>
""")
    title = f"{p['name']} — producer deep dive"
    desc = (f"{p['name']}: {p['production_count']} as-credited productions, "
            f"{fmt(p['total_plays'])} plays. The producer deep dive, from the archive.")
    return HEAD.format(title=escape(title), desc=escape(desc), canonical=f"/{producer_page(p['slug'])}") + "".join(parts) + FOOT


def index_page_html(producers, insights):
    letters = sorted({p["name"][0].upper() for p in producers if p["name"]})
    jump = " ".join(f'<a href="#letter-{l}">{l}</a>' for l in letters)
    rows = []
    # The table is ordered by plays (see the caption), NOT alphabetically,
    # so a letter recurs in separated runs down the page. The jump anchor
    # belongs on the FIRST row carrying each letter only — the row a
    # browser already lands on, since a duplicated id resolves to its
    # first match. Tracking only the previous row's letter (the old rule)
    # re-stamped the id on every later run: 110 letter ids for 31 letters
    # on the shipped page, 79 of them duplicates. Rotation 18.
    seen_letters = set()
    for p in producers:
        letter = p["name"][0].upper()
        anchor = f' id="letter-{letter}"' if letter not in seen_letters else ""
        seen_letters.add(letter)
        res = "yes" if p["research"] else "—"
        rows.append(
            f'<tr{anchor}><th scope="row"><a href="{escape(p["slug"])}.html">{escape(p["name"])}</a></th>'
            f'<td class="num">{p["production_count"]}</td>'
            f'<td class="num">{fmt(p["total_plays"])}</td>'
            f'<td>{escape(p["years_active"])}</td>'
            f'<td class="num">{len(p["codex_families"])}</td>'
            f'<td>{res}</td></tr>')
    lede = (f'{insights["producer_count"]} producers, as credited in the archive\'s own titles. '
            'Every credit is verbatim from a prod./produced-by fragment &mdash; the archive\'s rule, kept. '
            f'{insights["researched_count"]} carry researched scene context; the rest are credits-only, nothing more claimed.')
    body = f"""
      <p class="kicker"><span class="numeral">&#10022;</span>The architects</p>
      <h1 class="page-title">Producer deep dives</h1>
      <p class="chart-sub">{lede}</p>
      <nav class="alpha-nav" aria-label="Alphabetical index">{jump}</nav>
      <div class="table-wrap"><table class="data-table">
        <caption class="visually-hidden">All as-credited producers, by plays</caption>
        <thead><tr><th scope="col">Producer</th><th scope="col">Productions</th><th scope="col">Plays</th><th scope="col">Years</th><th scope="col">Families</th><th scope="col">Researched</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table></div>
      <section class="section" aria-labelledby="keep-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Keep digging</span>
        <h3 id="keep-h">The journey continues</h3>
        <ul class="story-list">
          <li><a href="../codex-network.html">Codex network</a> &mdash; producers as nodes on the family graph, with a connect-the-dots pathfinder.</li>
          <li><a href="../sessions-explorer.html">Sessions explorer</a> &mdash; the 61 upload sessions on one timeline.</li>
          <li><a href="../codex/">Codex</a> &mdash; the 16 vocabulary families.</li>
        </ul>
      </section>
"""
    title = "Producer deep dives"
    desc = (f"{insights['producer_count']} as-credited producers behind the Aster da Master sound, "
            "every credit verbatim from the archive's titles.")
    page = HEAD.format(title=escape(title), desc=escape(desc), canonical="/producers/index.html") + body + FOOT
    # A duplicated id is invalid HTML and makes the alphabet jump land
    # wherever the parser feels like — unshippable from this generator.
    all_ids = re.findall(r'\bid="([^"]+)"', page)
    assert len(all_ids) == len(set(all_ids)), (
        f"producers/index.html would carry duplicate id attributes: "
        f"{sorted({i for i in all_ids if all_ids.count(i) > 1})}")
    letter_ids = [i for i in all_ids if i.startswith("letter-")]
    assert sorted(i[len("letter-"):] for i in letter_ids) == letters, (
        "letter anchors must cover each jump-nav letter exactly once")
    return page


# --- main -------------------------------------------------------------------

SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "producer-deepdives",
    "description": "Producer deep-dives: every as-credited producer in the archive with credited productions (release/session links), codex family ties, title-credited voices, a computed production fingerprint, and sourced research where a research pass exists.",
    "type": "object",
    "required": ["version", "generated", "plays_snapshot", "method",
                 "research_pass", "producer_count", "producers", "insights"],
    "properties": {
        "version": {"type": "string"},
        "generated": {"type": "string"},
        "plays_snapshot": {"type": "string"},
        "method": {"type": "string"},
        "research_pass": {"type": "string"},
        "producer_count": {"type": "integer"},
        "producers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "slug", "page", "aliases",
                             "production_count", "total_plays", "years_active",
                             "first", "last", "productions", "co_producers",
                             "codex_families", "fingerprint",
                             "circle_page", "research", "explorer_deep_link"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "slug": {"type": "string"},
                    "page": {"type": "string"},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "production_count": {"type": "integer"},
                    "total_plays": {"type": "integer"},
                    "years_active": {"type": "string"},
                    "first": {"type": "object"},
                    "last": {"type": "object"},
                    "productions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["title", "date", "plays",
                                         "release_page", "session_id",
                                         "session_name", "session_page",
                                         "co_producers", "voices"],
                            "properties": {
                                "title": {"type": "string"},
                                "date": {"type": ["string", "null"]},
                                "plays": {"type": "integer"},
                                "release_page": {"type": "string"},
                                "session_id": {"type": "string"},
                                "session_name": {"type": "string"},
                                "session_page": {"type": "string"},
                                "co_producers": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["name", "page"],
                                        "properties": {
                                            "name": {"type": "string"},
                                            "page": {"type": "string"}}}},
                                "voices": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["name", "page"],
                                        "properties": {
                                            "name": {"type": "string"},
                                            "page": {"type": "string"}}}},
                            },
                        },
                    },
                    "co_producers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "page", "shared"],
                            "properties": {
                                "name": {"type": "string"},
                                "page": {"type": "string"},
                                "shared": {"type": "integer"}}}},
                    "codex_families": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["family_slug", "family_name",
                                         "family_page", "transmissions",
                                         "titles"],
                            "properties": {
                                "family_slug": {"type": "string"},
                                "family_name": {"type": "string"},
                                "family_page": {"type": "string"},
                                "transmissions": {"type": "integer"},
                                "titles": {"type": "array",
                                           "items": {"type": "string"}}}}},
                    "fingerprint": {"type": "object"},
                    "circle_page": {"type": ["string", "null"]},
                    "research": {"type": ["object", "null"]},
                    "explorer_deep_link": {"type": ["string", "null"]},
                },
            },
        },
        "insights": {"type": "object"},
    },
}


def main():
    sessions = json.loads(SESSIONS.read_text())["sessions"]
    research = json.loads((ROOT / "data" / "producer-research.json").read_text())
    network = json.loads((API / "codex-network.json").read_text())
    families = {f["slug"]: f for f in
                json.loads((API / "codex-families.json").read_text())["families"]}
    circle = json.loads((API / "circle.json").read_text())
    scene = json.loads((API / "scene-figures.json").read_text())

    producers = canonical_producers(sessions)
    assert len({p["slug"] for p in producers}) == len(producers), \
        "producer slug collision survived the merge"
    total_credits = sum(len(p["credits"]) for p in producers)

    # family ties from the codex network's family-figure edges
    fam_nodes = {n["id"]: n for n in network["nodes"] if n["kind"] == "family"}
    net_figs = {n["id"]: n for n in network["nodes"]
                if n["kind"] in ("producer", "both")}
    circle_by_name = {c["name"].lower():
                      {"slug": c["page"].split("/")[-1].replace(".html", ""),
                       **c}
                      for c in circle.values()}
    fig_to_slug = {}
    for p in producers:
        fid = network_fig_id(p["name"], circle_by_name)
        fig_to_slug[fid] = p["slug"]
        for a in p["aliases"]:
            fig_to_slug.setdefault(network_fig_id(a, circle_by_name),
                                   p["slug"])
    # every network producer/both node must resolve to a deep-dive producer
    for fid in net_figs:
        assert fid in fig_to_slug, \
            f"network figure {fid} has no producer deep dive"
    fam_ties = {p["slug"]: [] for p in producers}
    for e in network["edges"]:
        if e["kind"] != "family-figure":
            continue
        fam_id = e["a"] if e["a"] in fam_nodes else e["b"]
        fig_id = e["b"] if e["a"] in fam_nodes else e["a"]
        if fig_id in fig_to_slug:
            slug = fig_to_slug[fig_id]
            fam = fam_nodes[fam_id]
            fam_ties[slug].append({
                "family_slug": fam["id"][len("fam-"):],
                "family_name": fam["name"],
                "family_page": fam["page"],
                "transmissions": len(e["titles"]),
                "titles": sorted(set(e["titles"])),
            })

    # circle voices keyed by (title) -> voice pages
    voice_by_title = {}
    for cslug, c in circle.items():
        for t in c["tracks"]:
            voice_by_title.setdefault(t["title"], []).append(
                {"name": c["name"], "page": c["page"]})
    # circle_by_name (with slug) is defined above, beside fig_to_slug
    scene_by_slug = {}
    for sslug, s in scene.items():
        scene_by_slug[sslug] = s

    # research input assertions
    for rslug, r in research["producers"].items():
        assert any(p["slug"] == rslug for p in producers), \
            f"research slug {rslug} has no archive producer"
        assert r["facts"], f"research {rslug}: empty facts"
        for src in r["sources"]:
            assert src.get("label") and src.get("url", "").startswith("http"), \
                f"research {rslug}: bad source {src}"

    slug_to_page = {p["slug"]: producer_page(p["slug"]) for p in producers}
    out_producers = []
    for p in producers:
        prods = []
        co_counts = {}
        voice_counts = {}
        total_plays = 0
        solo = 0
        for title, sid, sname, t in p["credits"]:
            names = parse_producers(title)
            others = [n for n in names if n != p["name"]
                      and n not in p["aliases"]]
            if not others:
                solo += 1
            co = [{"name": n, "page": slug_to_page[producer_slug(n)]}
                  for n in others]
            for c in co:
                co_counts[c["name"]] = co_counts.get(c["name"], 0) + 1
            voices = voice_by_title.get(title, [])
            for v in voices:
                voice_counts[v["name"]] = voice_counts.get(v["name"], 0) + 1
            rel_page = t.get("page")
            assert rel_page, f"track missing page: {title}"
            assert (ROOT / rel_page).exists(), f"missing release page {rel_page}"
            dd = ROOT / "sessions" / (slugify(sname) + ".html")
            sess_page = ("sessions/" + dd.name) if dd.exists() \
                else f"sessions.html#{sid}"
            prods.append({
                "title": title, "date": t.get("date"),
                "plays": t.get("plays") or 0,
                "release_page": rel_page,
                "session_id": sid, "session_name": sname,
                "session_page": sess_page,
                "co_producers": co,
                "voices": voices,
            })
            total_plays += t.get("plays") or 0
        # assert the credit count survived the alias merge
        prods.sort(key=lambda pr: (pr["date"] or "9999", pr["title"]))
        co_list = sorted(
            ({"name": n, "page": slug_to_page[producer_slug(n)], "shared": c}
             for n, c in co_counts.items()),
            key=lambda d: (-d["shared"], d["name"]))
        dates = [pr["date"] for pr in prods if pr["date"]]
        years = sorted({d[:4] for d in dates})
        years_active = (years[0] if len(years) == 1 else
                        f"{years[0]}–{years[-1]}") if years else "dates unknown"
        top = max(prods, key=lambda pr: pr["plays"])
        fams = sorted(fam_ties[p["slug"]], key=lambda f: f["family_name"])
        for f in fams:
            assert (ROOT / f["family_page"]).exists(), \
                f"missing family page {f['family_page']}"
        cpage = circle_by_name.get(p["name"].lower(), {}).get("page")
        if cpage is None and p["slug"] in scene_by_slug:
            cpage = scene_by_slug[p["slug"]]["page"]
        if cpage:
            assert (ROOT / cpage).exists(), f"missing circle page {cpage}"
        explorer_link = None
        fid = network_fig_id(p["name"], circle_by_name)
        if fid in net_figs:
            explorer_link = "figure-" + fid[len("fig-"):]
        fp = {
            "top_production": {"title": top["title"], "plays": top["plays"]},
            "solo_rate_pct": round(100 * solo / len(prods)),
            "co_producers": co_list,
            "top_voice": (max(voice_counts.items(),
                              key=lambda kv: (kv[1], kv[0]))[0]
                          if voice_counts else None),
            "first": {"title": prods[0]["title"], "date": prods[0]["date"]},
            "last": {"title": prods[-1]["title"], "date": prods[-1]["date"]},
        }
        r = research["producers"].get(p["slug"])
        out_producers.append({
            "id": network_fig_id(p["name"], circle_by_name),
            "name": p["name"], "slug": p["slug"],
            "page": slug_to_page[p["slug"]],
            "aliases": p["aliases"],
            "production_count": len(prods),
            "total_plays": total_plays,
            "years_active": years_active,
            "first": fp["first"], "last": fp["last"],
            "productions": prods,
            "co_producers": co_list,
            "codex_families": fams,
            "fingerprint": fp,
            "circle_page": cpage,
            "research": ({"facts": r["facts"], "sources": r["sources"],
                          "evidence": r["evidence"]} if r else None),
            "explorer_deep_link": explorer_link,
        })

    out_producers.sort(key=lambda p: (-p["total_plays"], -p["production_count"],
                                      p["name"]))
    researched = [p for p in out_producers if p["research"]]
    insights = {
        "producer_count": len(out_producers),
        "researched_count": len(researched),
        "total_credits": total_credits,
        "most_prolific": {"name": max(out_producers,
                                      key=lambda p: p["production_count"])["name"],
                          "productions": max(p["production_count"]
                                             for p in out_producers)},
        "most_plays": {"name": out_producers[0]["name"],
                       "plays": out_producers[0]["total_plays"]},
        "solo_only_producers": sum(1 for p in out_producers
                                   if p["fingerprint"]["solo_rate_pct"] == 100),
        "note": ("Credits are parsed from the titles' own prod./produced-by "
                 "fragments, as credited verbatim. Fingerprints are computed "
                 "from those credits, not biographies."),
    }

    payload = {
        "version": VERSION,
        "generated": GENERATED,
        "plays_snapshot": SNAPSHOT,
        "method": ("Every producer credit is parsed from the archive titles' "
                   "own prod./produced-by fragments (as credited, verbatim); "
                   "spelling variants that slug identically merge with aliases "
                   "recorded. Research is hand-maintained in "
                   "data/producer-research.json (pass 2026-10-11) and asserted, "
                   "never extended silently."),
        "research_pass": research["research_pass"],
        "producer_count": len(out_producers),
        "producers": out_producers,
        "insights": insights,
    }
    API_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    SCHEMA_OUT.write_text(json.dumps(SCHEMA, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")

    # pages (this generator OWNS producers/)
    PROD_DIR.mkdir(exist_ok=True)
    # racing producers: their tracks are in an active milestone race
    # (wave 28 cross-link; milestone_races runs before this generator)
    races_doc = json.loads((API / "milestone-races.json").read_text())
    racing = set()
    for r in races_doc["play_races"]:
        for name in parse_producers(r["title"]):
            racing.add(producer_slug(name))
    assert racing, "no racing producers found"
    slug_set = {p["slug"] for p in out_producers}
    assert racing <= slug_set, \
        f"racing slug has no producer page: {racing - slug_set}"
    for f in PROD_DIR.glob("*.html"):
        f.unlink()
    for p in out_producers:
        (PROD_DIR / (p["slug"] + ".html")).write_text(
            producer_page_html(p, racing=racing), encoding="utf-8")
        assert (ROOT / p["page"]).exists()
    (PROD_DIR / "index.html").write_text(
        index_page_html(out_producers, insights), encoding="utf-8")

    idx = json.loads((API / "index.json").read_text())
    idx["version"] = VERSION
    render_manifest(idx, ROOT)
    print(f"producer-deepdives: {len(out_producers)} producers, "
          f"{total_credits} credits, {len(researched)} researched; "
          f"pages + data/v1/producer-deepdives.json + schema #22; "
          f"version -> {VERSION}")


if __name__ == "__main__":
    main()
