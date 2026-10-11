#!/usr/bin/env python3
"""Build the Vocabulary Codex from the verified discography.

Reads data/artist.json (219 titles), counts recurring ritual vocabulary
across titles, and emits data/codex.json + api/v1/codex.json.

Also generates:
  codex/<slug>.html  - one page per vocabulary family (16)
  codex/index.html    - the codex index

Per family: full track list (dates/plays, linked to release pages),
matched words, and family stats (total plays, span of years).

Method: titles are lowercased and leet-normalized (1->l, 0->o, 3->e,
4->a, 5->s, 7->t) for MATCHING ONLY; single-word keywords match on word
boundaries, multi-word keywords match as phrases. Every claim the codex
makes is a count - no meanings are invented.

Also bumps data version to 0.8.0 and mirrors to api/v1/.
"""
import json
import re
import shutil
import sys
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_releases import slugify  # noqa: E402  (single source of truth)

DATA = ROOT / "data" / "artist.json"
CODEX_OUT = ROOT / "data" / "codex.json"
API_OUT = ROOT / "api" / "v1" / "codex.json"
API_ARTIST = ROOT / "api" / "v1" / "artist.json"
API_INDEX = ROOT / "api" / "v1" / "index.json"
CODEX_PAGES = ROOT / "codex"
NEW_VERSION = "0.8.0"

LEET = str.maketrans({"1": "l", "0": "o", "3": "e", "4": "a", "5": "s", "7": "t"})


def norm(title):
    return title.lower().translate(LEET)


def tokens(title):
    return set(re.findall(r"[a-z']+", norm(title)))


# (arcane name, ritual epithet (counting claim only), keywords)
FAMILIES = [
    ("The Modes",
     "The mode-words. Five transmissions carry them - lite, nite, and night.",
     ["litemode", "nitemode", "night mode"]),
    ("The Castings",
     "Five transmissions bear the word cast - the central verb of the catalog.",
     ["cast"]),
    ("Keys",
     "Three transmissions turn on a key.",
     ["key"]),
    ("Vessels",
     "Two transmissions name a vessel to drink from - an urn, a cup.",
     ["urn", "cup"]),
    ("Wards & the Spirit",
     "A ward placed. A spirit at peace. Two transmissions of protection.",
     ["ward", "spirit"]),
    ("The Rites",
     "The ceremonial forms: ritual, solstice, freestyle, anthem, intro, outro, interlude.",
     ["ritual", "solstice", "freestyle", "anthem", "intro", "outro", "interlude"]),
    ("Light",
     "Lightning, white fire, sun, gold, and things that shine.",
     ["lightning", "white", "sun", "gold", "shine", "shines"]),
    ("Dark",
     "The night and the dark, named twice over.",
     ["dark", "night"]),
    ("Journeys",
     "Trips taken and a walk offered - the road vocabulary.",
     ["trip", "trips", "walk"]),
    ("The Cold",
     "Four transmissions about the world getting colder - a series unto itself.",
     ["cold", "colder"]),
    ("Power",
     "Power claimed, power denied, power gone.",
     ["power"]),
    ("The Pack",
     "Two transmissions for the dogs.",
     ["dog", "dogs"]),
    ("Lucid States",
     "A lucid boy and a dreamed-of you - the dream vocabulary.",
     ["lucid", "dream", "dreamed"]),
    ("Time",
     "Time to grow. Time, defied.",
     ["time"]),
    ("Soul",
     "Two transmissions carry the soul - one shaking, one shining.",
     ["soul"]),
    ("Fire & Water",
     "White fire. Water and sun. The elements, named once each.",
     ["fire", "water"]),
]


def matches(title, keyword):
    n = norm(title)
    if " " in keyword:
        return keyword in n
    return keyword in tokens(title)


NAV = """<nav class="site-nav" aria-label="Primary">
        <a href="../#discography">Discography</a>
        <a href="../releases/">Releases</a>
        <a href="../years/">Years</a>
        <a href="./">Codex</a>
        <a href="../timeline.html">Timeline</a>
        <a href="../network.html">Network</a>
        <a href="../method.html">Method</a>
        <a href="../trilogy.html">Trilogy</a>
        <a href="../press-kit.html">Press kit</a>
      </nav>"""

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Aster da Master</title>
  <meta name="description" content="{desc}">
  <link rel="stylesheet" href="../assets/css/tokens.css">
  <link rel="stylesheet" href="../assets/css/base.css">
  <link rel="stylesheet" href="../assets/css/layout.css">
  <link rel="stylesheet" href="../assets/css/components.css">
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
        <a href="./">Codex</a>
        <a href="../timeline.html">Timeline</a>
        <a href="../network.html">Network</a>
        <a href="../method.html">Method</a>
        <a href="../trilogy.html">Trilogy</a>
        <a href="../press-kit.html">Press kit</a>
      </nav>
    </div>
  </footer>
</body>
</html>
"""


def fmt(n):
    return f"{n:,}"


def year_span(tracks):
    yrs = sorted({t["date"][:4] for t in tracks if t.get("date")})
    if not yrs:
        return "dates unknown"
    return yrs[0] if len(yrs) == 1 else f"{yrs[0]}–{yrs[-1]}"


def family_page(fam, slug, slug_of, prev_s, next_s):
    tracks = fam["tracks"]
    total_plays = sum(t.get("plays") or 0 for t in tracks)
    rows = "".join(
        f'<li><a href="../releases/{slug_of[(t["title"], t.get("date"))]}.html">{escape(t["title"])}</a>'
        f' <span class="dim">{escape(t.get("date") or "date unknown")}'
        + (f" &middot; {fmt(t['plays'])} plays" if t.get("plays") else "")
        + f" &middot; {escape(t.get('type', 'Release'))}</span></li>"
        for t in tracks
    )
    prev_link = (
        f'<a class="btn btn-sm" href="{prev_s}.html" rel="prev">&larr; Prev</a>'
        if prev_s else '<span class="btn btn-sm" aria-disabled="true">&larr;</span>'
    )
    next_link = (
        f'<a class="btn btn-sm" href="{next_s}.html" rel="next">Next &rarr;</a>'
        if next_s else '<span class="btn btn-sm" aria-disabled="true">&rarr;</span>'
    )
    body = f"""
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../">Home</a> / <a href="../#codex">Codex</a> / <a href="./">Families</a> / <span aria-current="page">{escape(fam["name"])}</span>
      </nav>
      <section class="section" aria-labelledby="cf-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The codex</span>
        <h2 id="cf-h">{escape(fam["name"])}</h2>
        <p class="codex-epithet">{escape(fam["epithet"])}</p>
        <p class="codex-words">Matched words: {escape(" · ".join(fam["words"]))}</p>
        <div class="stat-grid">
          <div class="stat"><div class="stat-value">{fam["track_count"]}</div><div class="stat-label">Transmissions</div></div>
          <div class="stat"><div class="stat-value">{fmt(total_plays)}</div><div class="stat-label">Combined plays</div></div>
          <div class="stat"><div class="stat-value">{escape(year_span(tracks))}</div><div class="stat-label">Span of years</div></div>
        </div>
        <p class="chart-sub">Every claim here is a count &mdash; no meanings invented. Play counts are the 2026-10-11 vault snapshot.</p>
      </section>

      <section class="section" aria-labelledby="ct-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The family record</span>
        <h3 id="ct-h">Every {escape(fam["name"]).lower()} transmission, in order</h3>
        <ol class="year-list">{rows}</ol>
      </section>

      <nav class="year-pager" aria-label="Family navigation">
        {prev_link}
        <a class="btn btn-sm" href="./">All families</a>
        {next_link}
      </nav>
"""
    return HEAD.format(
        title=f'{fam["name"]} — codex family',
        desc=f'{fam["name"]}: {fam["track_count"]} transmissions, {fmt(total_plays)} plays.',
    ) + body + FOOT


def index_page(families):
    cards = "".join(
        f'<a class="year-card" href="{f["slug"]}.html">'
        f'<span class="year-card-y">{escape(f["name"])}</span>'
        f'<span class="year-card-n">{f["track_count"]} transmissions &middot; {fmt(f["plays"])} plays</span>'
        f'<span class="year-card-e">{escape(f["words_s"])}</span>'
        f"</a>"
        for f in families
    )
    body = f"""
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../">Home</a> / <span aria-current="page">Codex</span>
      </nav>
      <section class="section" aria-labelledby="cx-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The codex</span>
        <h2 id="cx-h">Sixteen families of ritual words</h2>
        <p>His titles run on ritual vocabulary. Each family is a tally of titles that carry its words — counts, never meanings.</p>
        <div class="year-grid">{cards}</div>
      </section>
"""
    return HEAD.format(
        title="The codex — vocabulary families",
        desc="Sixteen families of Aster da Master's ritual title vocabulary, each with its full track record.",
    ) + body + FOOT


def main():
    data = json.loads(DATA.read_text())
    releases = data["discography"]

    families = []
    for name, epithet, keywords in FAMILIES:
        matched_words = []
        tracks = []
        seen = set()
        for kw in keywords:
            hits = [r for r in releases if matches(r["title"], kw)]
            if hits:
                matched_words.append(kw)
                for r in hits:
                    key = (r["title"], r.get("date"))
                    if key not in seen:
                        seen.add(key)
                        tracks.append({
                            "title": r["title"],
                            "date": r.get("date"),
                            "plays": r.get("plays"),
                            "type": r.get("type", "Release"),
                        })
        if not tracks:
            continue
        tracks.sort(key=lambda t: (t["date"] or "9999", t["title"]))
        families.append({
            "name": name,
            "epithet": epithet,
            "words": matched_words,
            "track_count": len(tracks),
            "tracks": tracks,
        })

    codex = {
        "version": NEW_VERSION,
        "generated": date.today().isoformat(),
        "method": ("Word-boundary matching over lowercased, leet-normalized titles "
                   "(1->l, 0->o, 3->e, 4->a, 5->s, 7->t); multi-word phrases matched "
                   "as phrases. Counts are of titles containing the word. No meanings invented."),
        "families": families,
    }

    CODEX_OUT.write_text(json.dumps(codex, indent=2, ensure_ascii=False) + "\n")
    API_OUT.write_text(json.dumps(codex, indent=2, ensure_ascii=False) + "\n")
    print(f"codex: {len(families)} families, "
          f"{sum(f['track_count'] for f in families)} family-track links")

    # --- Family detail pages ---
    # Release slugs: identical algorithm to build_search_index.py.
    used, rslugs = set(), []
    for r in releases:
        s = slugify(r["title"])
        base, n = s, 1
        while s in used:
            n += 1
            s = f"{base}-{n}"
        used.add(s)
        rslugs.append(s)
    assert len(set(rslugs)) == len(releases), "release slug collision"
    slug_of = {(r["title"], r.get("date")): s for r, s in zip(releases, rslugs)}

    fams = []
    fused = set()
    for fam in families:
        s = slugify(fam["name"])
        base, n = s, 1
        while s in fused:
            n += 1
            s = f"{base}-{n}"
        fused.add(s)
        plays = sum(t.get("plays") or 0 for t in fam["tracks"])
        fams.append({
            "name": fam["name"], "slug": s, "plays": plays,
            "track_count": fam["track_count"],
            "words_s": " · ".join(fam["words"]),
        })

    CODEX_PAGES.mkdir(exist_ok=True)
    for i, fam in enumerate(families):
        prev_s = fams[i - 1]["slug"] if i > 0 else None
        next_s = fams[i + 1]["slug"] if i < len(families) - 1 else None
        (CODEX_PAGES / f'{fams[i]["slug"]}.html').write_text(
            family_page(fam, fams[i]["slug"], slug_of, prev_s, next_s),
            encoding="utf-8",
        )
    (CODEX_PAGES / "index.html").write_text(index_page(fams), encoding="utf-8")
    print(f"codex pages: {len(families)} family pages + index")

    # Bump version + mirror artist.json
    data["version"] = NEW_VERSION
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    shutil.copyfile(DATA, API_ARTIST)
    idx = json.loads(API_INDEX.read_text())
    idx["version"] = NEW_VERSION
    endpoints = idx.setdefault("endpoints", {})
    if isinstance(endpoints, dict):
        endpoints.setdefault("codex", "api/v1/codex.json")
    API_INDEX.write_text(json.dumps(idx, indent=2, ensure_ascii=False) + "\n")
    print(f"version -> {NEW_VERSION}; api/v1 mirrored")


if __name__ == "__main__":
    main()
