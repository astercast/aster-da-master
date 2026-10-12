#!/usr/bin/env python3
"""Wave 18: era deep-dives.

Expands the Transmission journey's six eras (2018->2026) into full browsable
deep-dive pages, plus a new data/v1/eras.json (endpoint #16):

  - data/v1/eras.json        - per era: everything data/v1/transmission.json
                              carries (stats, top tracks, key sessions,
                              milestones, computed signal line) PLUS the
                              full era transmission list (every entry, with
                              plays + release-page link), ALL in-era
                              collaborators (transmission.json keeps only
                              the top 3), the codex families active in the
                              era, and a computed "summary" of the era's
                              signal (ranks, shares, busiest year, loudest
                              and quietest transmissions, top family)
  - data/v1/schema/eras.json - draft-07 schema (#16)
  - eras/<id>.html           - one deep-dive page per era, linking back to
                              the Transmission journey at the matching era
                              node (transmission.html#era-<id>) and forward
                              to glance/timeline

Sources (all real archive data):
  - data/v1/transmission.json  (era aggregates, built by build_transmission.py)
  - data/v1/years.json         (per-year transmissions/plays, for re-verifying)
  - data/sessions.json        (61 sessions, for re-verifying session counts)
  - data/artist.json          (the 219-entry discography -> full era track
                              lists; era scene/note/releases text)
  - data/v1/release-slugs.json (ordinal -> slug, for release-page links)
  - data/v1/circle.json        (full in-era collaborator footprints)
  - data/v1/codex.json         (family track dates -> families active per era)

Every number is recomputed here and the script exits non-zero on any
disagreement. No payload shape changes to any existing endpoint; data
version stays 0.13.0 (no source data changed).

Runs LAST in the validate.sh generator chain (after build_network).
Titles and metadata only - never lyrics, never invented bio facts.
"""
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "data" / "v1"
OUT = ROOT / "eras"
NEW_VERSION = "0.18.0"  # wave 35: data version 0.18.0 (verified-data expansion)
SNAPSHOT = "2026-10-11"

sys.path.insert(0, str(ROOT / "scripts"))
from build_releases import slugify  # noqa: E402 (single source of truth)
from build_transmission import (  # noqa: E402 (reuse its verified mappings)
    ERA_YEARS, DEEPDIVE, LONGEST_GAP)

TX = json.loads((API / "transmission.json").read_text())
YEARS = json.loads((API / "years.json").read_text())
SESS = json.loads((ROOT / "data/sessions.json").read_text())["sessions"]
ARTIST = json.loads((ROOT / "data/artist.json").read_text())
DISC = ARTIST["discography"]
ERAS_SRC = {e["name"]: e for e in ARTIST["eras"]}
CIRCLE = json.loads((API / "circle.json").read_text())
CODEX = json.loads((API / "codex.json").read_text())["families"]
RSLUGS = json.loads((API / "release-slugs.json").read_text())

def fmt(n):
    return f"{n:,}"

# --- release pages: ordinal -> root-relative page; assert every one exists ---
def release_page(i):
    p = "releases/" + RSLUGS[str(i)] + ".html"
    assert (ROOT / p).exists(), f"missing release page {p}"
    return p

# --- codex family slugs: identical rule to scripts/build_codex.py ---
FAMSLUG = {}
_fused = set()
for fam in CODEX:
    s = slugify(fam["name"])
    base, n = s, 1
    while s in _fused:
        n += 1
        s = f"{base}-{n}"
    _fused.add(s)
    FAMSLUG[fam["name"]] = s
    assert (ROOT / "codex" / (s + ".html")).exists(), f"missing codex page {s}"
assert len(FAMSLUG) == 16, "codex family slug drift"

def era_entries(ys):
    """All discography entries in the era's years, with ordinal + page."""
    out = []
    for i, x in enumerate(DISC):
        if x["date"][:4] in ys:
            out.append({"ordinal": i, "title": x["title"], "date": x["date"],
                        "type": x["type"],
                        "plays": x.get("plays"),
                        "page": release_page(i)})
    return out

def era_all_collabs(ys):
    """Every title-credited collaborator with tracks in the era's years."""
    rows = []
    for slug, c in CIRCLE.items():
        tr = [t for t in c["tracks"] if t["date"][:4] in ys]
        if tr:
            rows.append({"name": c["name"],
                         "transmissions": len(tr),
                         "plays": sum((t["plays"] or 0) for t in tr),
                         "page": c["page"]})
            assert (ROOT / c["page"]).exists(), f"missing circle page {c['page']}"
    rows.sort(key=lambda r: (-r["plays"], r["name"]))
    return rows

def era_families(ys):
    """Codex families with tracks in the era's years, by plays desc."""
    rows = []
    for fam in CODEX:
        tr = [t for t in fam["tracks"] if t.get("date", "")[:4] in ys]
        if tr:
            tr = sorted(tr, key=lambda t: -(t.get("plays") or 0))
            rows.append({"name": fam["name"], "words": fam["words"],
                         "transmissions": len(tr),
                         "plays": sum(t.get("plays") or 0 for t in tr),
                         "page": "codex/" + FAMSLUG[fam["name"]] + ".html",
                         "top_tracks": [{"title": t["title"],
                                         "date": t["date"],
                                         "plays": t.get("plays")}
                                        for t in tr[:3]]})
    rows.sort(key=lambda r: (-r["plays"], r["name"]))
    return rows

def era_summary(e, tx_eras, ys, entries, collabs, families):
    """Computed signal summary; every figure recomputed + asserted by caller."""
    total_plays = sum(o["plays"] for o in tx_eras)
    rank_plays = 1 + sum(1 for o in tx_eras if o["plays"] > e["plays"])
    rank_tx = 1 + sum(1 for o in tx_eras
                      if o["transmissions"] > e["transmissions"])
    busiest = max(ys, key=lambda y: YEARS[y]["transmissions"])
    sc = [x for x in entries if x["type"] == "SoundCloud-only"]
    loudest = max(sc, key=lambda x: x["plays"])
    deepest = min(sc, key=lambda x: x["plays"])
    collab_plays = sum(c["plays"] for c in collabs)
    top_family = families[0] if families else None
    return {
        "rank_by_plays": rank_plays,
        "rank_by_transmissions": rank_tx,
        "eras_total": len(tx_eras),
        "archive_plays_share": round(e["plays"] / total_plays, 4),
        "busiest_year": {"year": busiest,
                         "transmissions": YEARS[busiest]["transmissions"],
                         "plays": YEARS[busiest]["plays"]},
        "loudest_transmission": {"title": loudest["title"],
                                 "plays": loudest["plays"],
                                 "page": loudest["page"]},
        "deepest_cut": {"title": deepest["title"],
                        "plays": deepest["plays"],
                        "page": deepest["page"]},
        "collaborators_count": len(collabs),
        "collab_plays": collab_plays,
        "collab_plays_share": (round(collab_plays / e["plays"], 4)
                               if e["plays"] else 0.0),
        "top_family": ({"name": top_family["name"],
                        "transmissions": top_family["transmissions"],
                        "plays": top_family["plays"],
                        "page": top_family["page"]}
                       if top_family else None),
        "milestones_count": len(e["milestones"]),
    }

def verify(e, ys, entries, collabs, families, summary):
    """Recompute everything the page/JSON claims about this era."""
    assert len(entries) == e["transmissions"], \
        f"{e['name']}: {len(entries)} entries != {e['transmissions']} tx"
    sc_plays = sum(x["plays"] or 0 for x in entries
                   if x["type"] == "SoundCloud-only")
    assert sc_plays == e["plays"], f"{e['name']}: plays {sc_plays} != {e['plays']}"
    dist = [x for x in entries if x["type"] != "SoundCloud-only"]
    assert len(dist) == e["distributor"], f"{e['name']}: distributor drift"
    assert len([s for s in SESS if s["start"][:4] in ys]) == e["sessions"], \
        f"{e['name']}: session count drift"
    # loudest transmission must be the journey's #1 defining track
    assert summary["loudest_transmission"]["title"] == e["top_tracks"][0]["title"], \
        f"{e['name']}: loudest != top track"
    assert summary["loudest_transmission"]["plays"] == e["top_tracks"][0]["plays"]
    # full collaborator list must agree with the journey's top-3 head
    for want, got in zip(e["collaborators"], collabs):
        assert want["name"] == got["name"] and want["plays"] == got["plays"], \
            f"{e['name']}: collab head drift on {want['name']}"
    # every session deep-dive link must be a real file
    for s in e["key_sessions"]:
        if s["deep_dive"]:
            assert (ROOT / s["deep_dive"]).exists(), s["deep_dive"]
    # ranks recomputed independently
    plays_sorted = sorted(TX["eras"], key=lambda o: -o["plays"])
    assert plays_sorted[summary["rank_by_plays"] - 1]["name"] == e["name"]
    tx_sorted = sorted(TX["eras"], key=lambda o: -o["transmissions"])
    assert tx_sorted[summary["rank_by_transmissions"] - 1]["name"] == e["name"]
    # busiest year recomputed independently
    assert max(ys, key=lambda y: YEARS[y]["transmissions"]) == \
        summary["busiest_year"]["year"]
    # deepest cut really is the minimum
    sc = [x for x in entries if x["type"] == "SoundCloud-only"]
    assert summary["deepest_cut"]["plays"] == min(x["plays"] for x in sc)
    # top family really is the max
    if families:
        assert summary["top_family"]["name"] == families[0]["name"]
    # every page link in the era payload resolves
    for t in e["top_tracks"]:
        assert (ROOT / t["page"]).exists(), t["page"]
    for t in entries:
        assert (ROOT / t["page"]).exists(), t["page"]
    for f in families:
        assert (ROOT / f["page"]).exists(), f["page"]

NAV = """<nav class="site-nav" aria-label="Primary">
        <a href="../#discography">Discography</a>
        <a href="../releases/">Releases</a>
        <a href="../years/">Years</a>
        <a href="../sessions.html">Sessions</a>
        <a href="../scene/">Scene</a>
        <a href="../timeline.html">Timeline</a>
        <a href="../chronicle.html">Chronicle</a>
        <a href="../transmission.html">Transmission</a>
        <a href="../network.html">Network</a>
        <a href="../milestone-race.html">Race</a>
        <a href="../decoder.html">Decoder</a>
        <a href="../api-playground.html">API</a>
        <a href="../agents.html">Agents</a>
        <a href="../method.html">Method</a>
        <a href="../trilogy.html">Trilogy</a>
        <a href="../glance.html">Glance</a>
        <a href="../changelog.html">Changelog</a>
        <a href="../press-kit.html">Press kit</a>
      </nav>
      <details class="mnav">
        <summary><span class="bars" aria-hidden="true"><i></i><i></i><i></i></span>Menu</summary>
        <nav class="mnav-panel" aria-label="Mobile">
        <a href="../#discography">Discography</a>
        <a href="../releases/">Releases</a>
        <a href="../years/">Years</a>
        <a href="../sessions.html">Sessions</a>
        <a href="../scene/">Scene</a>
        <a href="../timeline.html">Timeline</a>
        <a href="../chronicle.html">Chronicle</a>
        <a href="../transmission.html">Transmission</a>
        <a href="../network.html">Network</a>
        <a href="../milestone-race.html">Race</a>
        <a href="../decoder.html">Decoder</a>
        <a href="../api-playground.html">API</a>
        <a href="../agents.html">Agents</a>
        <a href="../method.html">Method</a>
        <a href="../trilogy.html">Trilogy</a>
        <a href="../glance.html">Glance</a>
        <a href="../changelog.html">Changelog</a>
        <a href="../press-kit.html">Press kit</a>
      
        </nav>
      </details>"""

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — era deep dive — Aster da Master</title>
  <meta name="description" content="{desc}">
  <link rel="preload" href="../assets/fonts/anton-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="../assets/css/fonts.css">

  <link rel="stylesheet" href="../assets/css/tokens.css">
  <link rel="stylesheet" href="../assets/css/base.css">
  <link rel="stylesheet" href="../assets/css/layout.css">
  <link rel="stylesheet" href="../assets/css/components.css">
  <link rel="stylesheet" href="../assets/css/motifs.css">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="container header-bar">
      <a class="brand" href="../" aria-label="Aster da Master home">
        <span class="brand-mark" aria-hidden="true">A&#10022;</span>
        <span>ASTER DA MASTER</span>
      </a>
      """ + NAV + """
    </div>
  </header>
  <main id="main">
    <div class="container">
"""

FOOT = """    </div>
  </main>
  <footer class="site-footer">
    <div class="container footer-grid">
      <p>&copy; 2026 ASTER DA MASTER &mdash; ALL SIGNALS RESERVED</p>
      <nav aria-label="Footer">
        <a href="../">Home</a>
        <a href="../releases/">Releases</a>
        <a href="../years/">Years</a>
        <a href="../sessions.html">Sessions</a>
        <a href="../scene/">Scene</a>
        <a href="../timeline.html">Timeline</a>
        <a href="../chronicle.html">Chronicle</a>
        <a href="../transmission.html">Transmission</a>
        <a href="../network.html">Network</a>
        <a href="../milestone-race.html">Race</a>
        <a href="../decoder.html">Decoder</a>
        <a href="../api-playground.html">API</a>
        <a href="../agents.html">Agents</a>
        <a href="../method.html">Method</a>
        <a href="../trilogy.html">Trilogy</a>
        <a href="../glance.html">Glance</a>
        <a href="../changelog.html">Changelog</a>
        <a href="../press-kit.html">Press kit</a>
      </nav>
    </div>
  </footer>
  <script src="../assets/js/identity.js"></script>
</body>
</html>
"""

def ordinal_word(n):
    return {1: "first", 2: "second", 3: "third", 4: "fourth",
            5: "fifth", 6: "sixth"}.get(n, str(n) + "th")

def era_page(e, idx, n_eras, entries, collabs, families, summary):
    ys = ", ".join(e["years"])
    src = ERAS_SRC[e["name"]]
    eid = e["id"]
    parts = []

    # hero
    parts.append(f"""
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../">Home</a> / <a href="../transmission.html#era-{eid}">Transmission</a> / <span aria-current="page">{escape(e['name'])}</span>
      </nav>
      <section class="section" aria-labelledby="era-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Era deep dive &middot; era {idx + 1} of {n_eras}</span>
        <h2 id="era-h">{escape(e['name'])}</h2>
        <p class="lede">{escape(e['span'])} &middot; {escape(e['scene'] or '')}</p>
        <div class="stat-grid">
          <div class="stat"><div class="stat-value">{fmt(e['transmissions'])}</div><div class="stat-label">Transmissions</div></div>
          <div class="stat"><div class="stat-value">{fmt(e['plays'])}</div><div class="stat-label">Plays</div></div>
          <div class="stat"><div class="stat-value">{e['sessions']}</div><div class="stat-label">Sessions</div></div>
          <div class="stat"><div class="stat-value">{e['distributor']}</div><div class="stat-label">Distributor releases</div></div>
        </div>
        <p class="chart-sub">Play counts are the {SNAPSHOT} vault snapshot. Upload dates are upload dates, not recording dates.</p>
      </section>
""")

    # the signal, decoded
    sig_items = [
        f"Rank <strong>#{summary['rank_by_plays']}</strong> of {summary['eras_total']} eras by plays — "
        f"<strong>{summary['archive_plays_share']:.1%}</strong> of every play in the archive.",
        f"Rank <strong>#{summary['rank_by_transmissions']}</strong> of {summary['eras_total']} by transmissions.",
        f"Busiest year: <strong>{summary['busiest_year']['year']}</strong> — "
        f"{fmt(summary['busiest_year']['transmissions'])} transmissions, {fmt(summary['busiest_year']['plays'])} plays.",
        f"Loudest transmission: &ldquo;<a href=\"../{summary['loudest_transmission']['page']}\">{escape(summary['loudest_transmission']['title'])}</a>&rdquo; "
        f"at {fmt(summary['loudest_transmission']['plays'])} plays.",
        f"Deepest cut: &ldquo;<a href=\"../{summary['deepest_cut']['page']}\">{escape(summary['deepest_cut']['title'])}</a>&rdquo; "
        f"at {fmt(summary['deepest_cut']['plays'])} plays.",
    ]
    if summary["collaborators_count"]:
        sig_items.append(
            f"{summary['collaborators_count']} summoned voices carry "
            f"<strong>{summary['collab_plays_share']:.1%}</strong> of the era's plays.")
    if summary["top_family"]:
        tf = summary["top_family"]
        sig_items.append(
            f"Most-played codex family: <a href=\"../{tf['page']}\">{escape(tf['name'])}</a> — "
            f"{tf['transmissions']} transmissions, {fmt(tf['plays'])} plays.")
    sig_items.append(
        f"{summary['milestones_count']} milestones filed in this era.")
    parts.append(f"""
      <section class="section" aria-labelledby="sig-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The signal</span>
        <h3 id="sig-h">The signal, decoded</h3>
        <blockquote class="quote"><span class="sig-lab">The signal</span>{escape(e['signal'])}</blockquote>
        <ul class="story-list">
          {''.join('<li>' + i + '</li>' for i in sig_items)}
        </ul>
      </section>
""")

    # defining tracks
    tt = "".join(
        f"<li><a href=\"../{t['page']}\">{escape(t['title'])}</a> "
        f"<span class=\"dim\">{escape(t['date'])} &middot; {fmt(t['plays'])} plays</span></li>"
        for t in e["top_tracks"])
    parts.append(f"""
      <section class="section" aria-labelledby="dt-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The canon</span>
        <h3 id="dt-h">Defining tracks</h3>
        <ol class="year-list">{tt}</ol>
      </section>
""")

    # every transmission
    rows = []
    for x in sorted(entries, key=lambda x: (x["date"], x["title"])):
        if x["type"] == "SoundCloud-only":
            meta = f"{escape(x['date'])} &middot; {fmt(x['plays'])} plays"
        else:
            meta = f"{escape(x['date'])} &middot; {escape(x['type'])} &middot; distributor release"
        rows.append(
            f"<li><a href=\"../{x['page']}\">{escape(x['title'])}</a> "
            f"<span class=\"dim\">{meta}</span></li>")
    parts.append(f"""
      <section class="section" aria-labelledby="all-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The record</span>
        <h3 id="all-h">Every transmission in this era ({len(rows)})</h3>
        <ol class="year-list">{''.join(rows)}</ol>
        <p class="chart-sub">Distributor releases carry no vault play count — only SoundCloud uploads do.</p>
      </section>
""")

    # key sessions
    ss = []
    for s in e["key_sessions"]:
        name = escape(s["name"])
        if s["deep_dive"]:
            name = f"<a href=\"../{s['deep_dive']}\">{name}</a>"
        ss.append(
            f"<li>{name} <span class=\"dim\">{s['track_count']} transmissions &middot; "
            f"{fmt(s['total_plays'])} plays &middot; {escape(s['start'])} to {escape(s['end'])}</span></li>")
    parts.append(f"""
      <section class="section" aria-labelledby="ks-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The sessions</span>
        <h3 id="ks-h">Key sessions</h3>
        <ul class="year-list">{''.join(ss)}</ul>
      </section>
""")

    # collaborators (all)
    if collabs:
        co = "".join(
            f"<li><a href=\"../{c['page']}\">{escape(c['name'])}</a> "
            f"<span class=\"dim\">&times;{c['transmissions']} &middot; {fmt(c['plays'])} plays</span></li>"
            for c in collabs)
        collab_html = f"<ol class=\"top-list\">{co}</ol>"
    else:
        collab_html = ("<p class=\"tx-empty\">No title-credited collaborators this era "
                       "&mdash; every transmission stands alone.</p>")
    parts.append(f"""
      <section class="section" aria-labelledby="co-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The summoned</span>
        <h3 id="co-h">Every voice in this era ({len(collabs)})</h3>
        {collab_html}
        <p class="chart-sub">Credits parsed from <em>w/</em> and <em>ft.</em> fragments in titles &mdash; as credited, verbatim; producers excluded.</p>
      </section>
""")

    # milestones
    if e["milestones"]:
        ms = "".join(
            f"<li><span class=\"m-name\">{escape(m['name'])}</span>"
            + (f" <span class=\"dim\">{escape(m['date'])}</span>" if m["date"] else "")
            + f"<p class=\"m-fact\">{escape(m['fact'])}</p></li>"
            for m in e["milestones"])
        mile_html = f"<ul class=\"story-list\">{ms}</ul>"
    else:
        mile_html = "<p class=\"tx-empty\">No milestones filed for this era. The numbers speak.</p>"
    parts.append(f"""
      <section class="section" aria-labelledby="mi-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The marks</span>
        <h3 id="mi-h">Milestones ({len(e['milestones'])})</h3>
        {mile_html}
      </section>
""")

    # codex families
    if families:
        fa = "".join(
            f"<li><a href=\"../{f['page']}\">{escape(f['name'])}</a> "
            f"<span class=\"dim\">&times;{f['transmissions']} &middot; {fmt(f['plays'])} plays</span>"
            f"<p class=\"m-fact\">Words: {escape(' · '.join(f['words']))}. "
            f"Top: &ldquo;{escape(f['top_tracks'][0]['title'])}&rdquo;</p></li>"
            for f in families)
        fam_html = f"<ul class=\"story-list\">{fa}</ul>"
    else:
        fam_html = "<p class=\"tx-empty\">No codex family carries transmissions in this era.</p>"
    parts.append(f"""
      <section class="section" aria-labelledby="fa-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The language</span>
        <h3 id="fa-h">Codex families active in this era ({len(families)})</h3>
        {fam_html}
      </section>
""")

    # pager + keep digging
    prev_e = TX["eras"][idx - 1] if idx > 0 else None
    next_e = TX["eras"][idx + 1] if idx + 1 < n_eras else None
    pager = []
    if prev_e:
        pager.append(f"<a href=\"{prev_e['id']}.html\">&larr; {escape(prev_e['name'])}</a>")
    pager.append(f"<a href=\"../transmission.html#era-{eid}\">Transmission journey &middot; this era</a>")
    if next_e:
        pager.append(f"<a href=\"{next_e['id']}.html\">{escape(next_e['name'])} &rarr;</a>")
    parts.append(f"""
      <section class="section" aria-labelledby="keep-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Keep digging</span>
        <h3 id="keep-h">The journey continues</h3>
        <nav class="year-pager" aria-label="Era navigation">
          {' '.join(pager)}
        </nav>
        <ul class="story-list">
          <li><a href="../glance.html">The vault at a glance</a> — all 219 entries in one frame.</li>
          <li><a href="../timeline.html">Timeline</a> — the career as a single scroll.</li>
          <li><a href="../network.html">Network</a> — the collaboration universe as a graph.</li>
          <li><a href="../codex/">Codex</a> — the 16 vocabulary families.</li>
          <li><a href="../sessions.html">Sessions</a> — all 61 upload sessions.</li>
          <li><a href="../sessions-explorer.html#era-{eid}">Sessions explorer</a> — this era's sessions on the explorable timeline.</li>
          <li><a href="../milestone-race.html">Milestone race</a> — approaching play-count milestones as races, plus the summit chase.</li>
        </ul>
      </section>
""")

    title = f"{e['name']} — era deep dive"
    desc = (f"{e['name']} ({e['span']}): {e['transmissions']} transmissions, "
            f"{fmt(e['plays'])} plays. The era deep dive, from the archive.")
    return (HEAD.format(title=escape(title), desc=escape(desc))
            + "".join(parts) + FOOT)

SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "eras",
    "description": ("Era deep-dives: six eras with full transmission lists, "
                    "all in-era collaborators, active codex families, "
                    "milestones, computed signal lines and summaries. "
                    "Generated by scripts/build_eras.py."),
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "generated": {"type": "string"},
        "plays_snapshot": {"type": "string"},
        "method": {"type": "string"},
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
                    "note": {"type": ["string", "null"]},
                    "era_releases": {"type": "array",
                                     "items": {"type": "string"}},
                    "transmissions": {"type": "integer"},
                    "plays": {"type": "integer"},
                    "sessions": {"type": "integer"},
                    "distributor": {"type": "integer"},
                    "top_tracks": {"type": "array"},
                    "key_sessions": {"type": "array"},
                    "collaborators": {"type": "array"},
                    "milestones": {"type": "array"},
                    "signal": {"type": "string"},
                    "tracks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ordinal": {"type": "integer"},
                                "title": {"type": "string"},
                                "date": {"type": "string"},
                                "type": {"type": "string"},
                                "plays": {"type": ["integer", "null"]},
                                "page": {"type": "string"},
                            },
                            "required": ["ordinal", "title", "date",
                                         "type", "plays", "page"],
                        },
                    },
                    "codex_families": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "words": {"type": "array",
                                          "items": {"type": "string"}},
                                "transmissions": {"type": "integer"},
                                "plays": {"type": "integer"},
                                "page": {"type": "string"},
                                "top_tracks": {"type": "array"},
                            },
                            "required": ["name", "transmissions", "plays",
                                         "page"],
                        },
                    },
                    "summary": {
                        "type": "object",
                        "properties": {
                            "rank_by_plays": {"type": "integer"},
                            "rank_by_transmissions": {"type": "integer"},
                            "eras_total": {"type": "integer"},
                            "archive_plays_share": {"type": "number"},
                            "busiest_year": {"type": "object"},
                            "loudest_transmission": {"type": "object"},
                            "deepest_cut": {"type": "object"},
                            "collaborators_count": {"type": "integer"},
                            "collab_plays": {"type": "integer"},
                            "collab_plays_share": {"type": "number"},
                            "top_family": {"type": ["object", "null"]},
                            "milestones_count": {"type": "integer"},
                        },
                        "required": ["rank_by_plays", "rank_by_transmissions",
                                     "eras_total", "archive_plays_share",
                                     "busiest_year", "loudest_transmission",
                                     "deepest_cut", "collaborators_count",
                                     "collab_plays_share", "milestones_count"],
                    },
                    "deep_dive": {"type": "string"},
                    "journey": {"type": "string"},
                },
                "required": ["id", "name", "transmissions", "plays",
                             "top_tracks", "key_sessions", "collaborators",
                             "milestones", "signal", "tracks",
                             "codex_families", "summary", "deep_dive",
                             "journey"],
            },
        },
    },
    "required": ["version", "archive_totals", "eras"],
}

def main() -> int:
    tx_eras = TX["eras"]
    assert len(tx_eras) == 6, "era count drift"
    assert [e["id"] for e in tx_eras] == [
        "the-first-rite", "the-prolific-year", "the-cast-it-years",
        "the-somelowlifes-era", "the-silence", "the-return"], "era id drift"
    # the 553-day silence record is cited on the SomeLowLifes deep dive
    assert LONGEST_GAP["days"] == 553 and LONGEST_GAP["from"] == "2022-02-22" \
        and LONGEST_GAP["to"] == "2023-08-29", "longest-gap drift"

    eras_out = []
    OUT.mkdir(exist_ok=True)
    for idx, e in enumerate(tx_eras):
        ys = ERA_YEARS[e["name"]]
        src = ERAS_SRC[e["name"]]
        entries = era_entries(ys)
        collabs = era_all_collabs(ys)
        families = era_families(ys)
        summary = era_summary(e, tx_eras, ys, entries, collabs, families)
        verify(e, ys, entries, collabs, families, summary)

        eras_out.append({
            "id": e["id"], "name": e["name"], "span": e["span"],
            "years": ys, "scene": e["scene"],
            "note": src.get("note"), "era_releases": src.get("releases", []),
            "transmissions": e["transmissions"], "plays": e["plays"],
            "sessions": e["sessions"], "distributor": e["distributor"],
            "top_tracks": e["top_tracks"], "key_sessions": e["key_sessions"],
            "collaborators": collabs, "milestones": e["milestones"],
            "signal": e["signal"], "tracks": entries,
            "codex_families": families, "summary": summary,
            "deep_dive": f"eras/{e['id']}.html",
            "journey": f"transmission.html#era-{e['id']}",
        })
        (OUT / f"{e['id']}.html").write_text(
            era_page(e, idx, len(tx_eras), entries, collabs, families,
                     summary),
            encoding="utf-8")

    # every discography entry lands in exactly one era page (except entries
    # dated before 2018, which predate the journey's data years - on record
    # that is only the 2017 "lost memories" feature credit)
    listed = [t["ordinal"] for e in eras_out for t in e["tracks"]]
    assert len(listed) == len(set(listed)) == TX["archive_totals"]["transmissions"], \
        "era track lists overlap or miss entries"
    unlisted = sorted(set(range(len(DISC))) - set(listed))
    assert all(DISC[i]["date"] < "2018" for i in unlisted) and unlisted, \
        f"unexpected unlisted discography entries: {unlisted}"
    assert sum(1 for i in unlisted) == sum(1 for x in DISC if x["date"] < "2018"), \
        "pre-2018 entries missing from era track lists"

    doc = {
        "version": NEW_VERSION,
        "generated": SNAPSHOT,
        "plays_snapshot": SNAPSHOT,
        "method": ("Era deep-dives expanded from data/v1/transmission.json "
                   "against data/artist.json (discography), data/v1/years.json, "
                   "data/sessions.json, data/v1/circle.json, and "
                   "data/v1/codex.json. collaborators[] holds EVERY in-era "
                   "collaborator (transmission.json keeps only the top 3). "
                   "summary figures are recomputed and asserted in "
                   "scripts/build_eras.py. Titles and metadata only - "
                   "never lyrics, never invented bio facts."),
        "archive_totals": TX["archive_totals"],
        "eras": eras_out,
    }
    (API / "eras.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (API / "schema" / "eras.json").write_text(
        json.dumps(SCHEMA, indent=2) + "\n", encoding="utf-8")

    # register the endpoint (same convention as build_network.py)
    idx_p = API / "index.json"
    idx = json.loads(idx_p.read_text())
    idx["version"] = NEW_VERSION
    from api_manifest import render_manifest
    render_manifest(idx, ROOT)

    print(f"eras.json: {len(eras_out)} eras, "
          f"{sum(len(e['tracks']) for e in eras_out)} tracks, "
          f"{sum(len(e['collaborators']) for e in eras_out)} collab slots, "
          f"{sum(len(e['codex_families']) for e in eras_out)} family slots")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
