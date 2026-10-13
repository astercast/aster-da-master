#!/usr/bin/env python3
"""Generate year-in-review archive pages for the Aster da Master site.

Output:
  years/2018.html ... years/2026.html  - one page per year
  years/index.html                     - the year-archive index
  data/v1/years.json                    - machine-readable per-year stats
                                       (registered in data/v1/index.json)

Per year: transmission count, total plays, top-10 tracks by plays,
key collaborators (parsed from title credits, never invented),
distributor-vs-vault split, the era it belongs to, 3 "defining tracks"
(top by plays - labeled as a data pick, not an editorial one), and the
full chronological transmission list linking to release pages.

Titles only - no lyrics anywhere. Idempotent: regenerates cleanly.
Re-run after any discography change.
"""
import json
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import nav_data  # noqa: E402  (canonical nav data — scripts/nav_data.py)
from build_releases import slugify  # noqa: E402  (single source of truth)

DATA = json.loads((ROOT / "data" / "artist.json").read_text())
YEARS = list(range(2018, 2027))
OUT = ROOT / "years"
API = ROOT / "data" / "v1"

NAV = nav_data.nav_chunk("../", "years")

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Aster da Master</title>
  <meta name="description" content="{desc}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{title} — Aster da Master">
  <meta property="og:description" content="{desc}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:image" content="../assets/og-card.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} — Aster da Master">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="../assets/og-card.png">
  <link rel="preload" href="../assets/fonts/anton-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="../assets/css/fonts.css">

  <link rel="stylesheet" href="../assets/css/tokens.css">
  <link rel="stylesheet" href="../assets/css/base.css">
  <link rel="stylesheet" href="../assets/css/layout.css">
  <link rel="stylesheet" href="../assets/css/components.css">
  <link rel="stylesheet" href="../assets/css/motifs.css">
  <link rel="stylesheet" href="../assets/css/layer2.css">
</head>
<body class="layer2">
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
      """ + nav_data.footer_block("../", "years") + """
    </div>
  </footer>
  <script src="../assets/js/identity.js"></script>
</body>
</html>
"""

def parse_collabs(title):
    """Port of assets/js/common.js parseCollabs: credit names from the
    title's own w//ft./feat. fragments. Nothing invented."""
    names = []
    for m in re.finditer(r"(?:\bw\/\s*|\bft\.?\s+|\bfeat\.?\s+)", title, re.I):
        rest = title[m.end():]
        rest = re.split(r"[(\[]", rest)[0]
        rest = re.split(r"prod\.?", rest, flags=re.I)[0]
        for p in re.split(r"\s+[xX]\s+|\s*&\s*|\s*\+\s*|,|\s*/\s*|\s+and\s+", rest):
            p = re.sub(r"^[ .!~)\"']+|[ .!~)\"']+$", "", p)
            if (
                p
                and len(p) < 30
                and not re.search(r"aster\s*da\s*master", p, re.I)
                and not re.search(r"prod", p, re.I)
            ):
                names.append(p)
    return names

def era_for_year(year, eras):
    for e in eras:
        m = re.search(r"(\d{4})(?:\s*[–—-]\s*(\d{4}))?", str(e.get("span") or ""))
        if not m:
            continue
        start, end = int(m.group(1)), int(m.group(2) or m.group(1))
        if start <= year <= end:
            return e
    return None

def fmt(n):
    return f"{n:,}"

def year_page(year, entries, slug_of, era):
    dist = [r for r in entries if r["type"] != "SoundCloud-only"]
    vault = [r for r in entries if r["type"] == "SoundCloud-only"]
    plays = sum(r.get("plays") or 0 for r in entries)
    by_plays = sorted(entries, key=lambda r: -(r.get("plays") or 0))
    top10 = by_plays[:10]
    defining = by_plays[:3]

    collabs = {}
    for r in entries:
        for c in parse_collabs(r["title"]):
            key = c.lower()
            if key not in collabs:
                collabs[key] = {"name": c, "n": 0}
            collabs[key]["n"] += 1
    top_collabs = sorted(collabs.values(), key=lambda c: -c["n"])[:8]

    def link_for(r):
        return f"../releases/{slug_of[id(r)]}.html"

    rows = []
    for i, r in enumerate(top10, 1):
        rows.append(
            f'<tr><td>{i}</td><td><a href="{link_for(r)}">{escape(r["title"])}</a></td>'
            f'<td class="num">{fmt(r.get("plays") or 0)}</td>'
            f'<td>{escape(r.get("date") or "")}</td></tr>'
        )

    collab_html = (
        "".join(
            f'<li><strong>{escape(c["name"])}</strong> &times;{c["n"]}</li>'
            for c in top_collabs
        )
        or "<li>None credited this year.</li>"
    )

    defining_html = "".join(
        f'<li><a href="{link_for(r)}">{escape(r["title"])}</a>'
        f' <span class="dim">&mdash; {fmt(r.get("plays") or 0)} plays</span></li>'
        for r in defining
    )

    full_list = "".join(
        f'<li><a href="{link_for(r)}">{escape(r["title"])}</a>'
        f' <span class="dim">{escape(r.get("date") or "")}'
        + (f' &middot; {fmt(r.get("plays"))} plays' if r.get("plays") else "")
        + f' &middot; {escape(r["type"])}</span></li>'
        for r in sorted(entries, key=lambda r: r.get("date") or "")
    )

    prev_link = (
        f'<a class="btn btn-sm" href="{year - 1}.html" rel="prev">&larr; {year - 1}</a>'
        if year > YEARS[0]
        else '<span class="btn btn-sm" aria-disabled="true">&larr;</span>'
    )
    next_link = (
        f'<a class="btn btn-sm" href="{year + 1}.html" rel="next">{year + 1} &rarr;</a>'
        if year < YEARS[-1]
        else '<span class="btn btn-sm" aria-disabled="true">&rarr;</span>'
    )

    era_html = ""
    if era:
        era_html = (
            f'<section class="section" aria-labelledby="era-h">'
            f'<span class="kicker"><span class="numeral">&#10022;</span>The era</span>'
            f'<h2 id="era-h">{escape(era["name"])}</h2>'
            f'<p>{escape(era.get("scene", ""))}</p>'
            f'<p class="dim">{escape(era.get("note", ""))} '
            f'<a href="../#eras">All eras &rarr;</a></p></section>'
        )

    body = f"""
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../">Home</a> / <a href="./">Years</a> / <span aria-current="page">{year}</span>
      </nav>
      <section class="section" aria-labelledby="yr-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The yearly archive</span>
        <h1 id="yr-h">{year}</h1>
        <div class="stat-grid">
          <div class="stat"><div class="stat-value">{len(entries)}</div><div class="stat-label">Transmissions</div></div>
          <div class="stat"><div class="stat-value">{fmt(plays)}</div><div class="stat-label">Vault plays</div></div>
          <div class="stat"><div class="stat-value">{len(dist)}</div><div class="stat-label">Distributor releases</div></div>
          <div class="stat"><div class="stat-value">{len(vault)}</div><div class="stat-label">Vault tracks</div></div>
        </div>
        <p class="chart-sub">Play counts cover the SoundCloud vault only (a 2026-10-11 snapshot; counts drift). Distributor releases carry no public play counts.</p>
      </section>

      <section class="section" aria-labelledby="def-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Defining tracks</span>
        <h2 id="def-h">The three highest-play transmissions of {year}</h2>
        <ol class="def-list">{defining_html}</ol>
        <p class="chart-sub">A data pick, not an editorial one &mdash; ranked by play count alone.</p>
      </section>

      <section class="section" aria-labelledby="top-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Top ten</span>
        <h2 id="top-h">Top 10 by plays</h2>
        <div class="table-wrap"><table>
          <thead><tr><th scope="col">#</th><th scope="col">Title</th><th scope="col" class="num">Plays</th><th scope="col">Uploaded</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table></div>
      </section>

      <section class="section" aria-labelledby="col-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The circle that year</span>
        <h2 id="col-h">Key collaborators</h2>
        <ul class="tag-list">{collab_html}</ul>
        <p class="chart-sub">Parsed from w/ and ft. credits in the titles themselves &mdash; nothing inferred.</p>
      </section>

      {era_html}

      <section class="section" aria-labelledby="all-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The full record</span>
        <h2 id="all-h">Every {year} transmission, in order</h2>
        <ol class="year-list">{full_list}</ol>
      </section>

      <nav class="year-pager" aria-label="Year navigation">
        {prev_link}
        <a class="btn btn-sm" href="./">All years</a>
        {next_link}
      </nav>
"""
    return HEAD.format(
        title=f"{year} — Year in review",
        desc=f"Aster da Master in {year}: {len(entries)} transmissions, {fmt(plays)} vault plays, top tracks and collaborators.",
        canonical=f"/years/{year}.html",
    ) + body + FOOT

def index_page(summaries):
    cards = "".join(
        f'<a class="year-card" href="{y}.html">'
        f'<span class="year-card-y">{y}</span>'
        f'<span class="year-card-n">{s["count"]} transmissions &middot; {fmt(s["plays"])} plays</span>'
        f'<span class="year-card-e">{escape(s["era"] or "")}</span>'
        f'<span class="year-card-t">Top: {escape(s["top"] or "&mdash;")}</span>'
        f"</a>"
        for y, s in sorted(summaries.items())
    )
    body = f"""
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../">Home</a> / <span aria-current="page">Years</span>
      </nav>
      <section class="section" aria-labelledby="yi-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The yearly archive</span>
        <h1 id="yi-h">Nine years, one page each</h1>
        <p>Every year on record, distilled: transmissions, plays, defining tracks, collaborators, the era it belongs to.</p>
        <div class="year-grid">{cards}</div>
      </section>
"""
    return HEAD.format(
        title="Year in review — the yearly archive",
        desc="Aster da Master year by year, 2018–2026: transmissions, plays, defining tracks, collaborators.",
        canonical="/years/index.html",
    ) + body + FOOT

def main():
    releases = DATA["discography"]
    eras = DATA.get("eras", [])

    # Slug list identical to build_search_index.py (single source of truth).
    used, slugs = set(), []
    for r in releases:
        s = slugify(r["title"])
        base, n = s, 1
        while s in used:
            n += 1
            s = f"{base}-{n}"
        used.add(s)
        slugs.append(s)
    assert len(set(slugs)) == len(releases), "slug collision"
    slug_of = {id(r): s for r, s in zip(releases, slugs)}

    by_year = {y: [] for y in YEARS}
    for r in releases:
        date = r.get("date") or ""
        m = re.match(r"^(\d{4})-\d{2}-\d{2}$", date)
        if m and int(m.group(1)) in by_year:
            by_year[int(m.group(1))].append(r)

    OUT.mkdir(exist_ok=True)
    summaries = {}
    api_years = {}
    for y in YEARS:
        entries = by_year[y]
        era = era_for_year(y, eras)
        (OUT / f"{y}.html").write_text(
            year_page(y, entries, slug_of, era), encoding="utf-8"
        )
        by_plays = sorted(entries, key=lambda r: -(r.get("plays") or 0))
        summaries[y] = {
            "count": len(entries),
            "plays": sum(r.get("plays") or 0 for r in entries),
            "era": era["name"] if era else "",
            "top": by_plays[0]["title"] if by_plays and (by_plays[0].get("plays") or 0) else "",
        }
        api_years[str(y)] = {
            "page": f"years/{y}.html",
            "transmissions": len(entries),
            "plays": summaries[y]["plays"],
            "distributor": sum(1 for r in entries if r["type"] != "SoundCloud-only"),
            "vault": sum(1 for r in entries if r["type"] == "SoundCloud-only"),
            "era": era["name"] if era else None,
            "top_tracks": [
                {"title": r["title"], "plays": r.get("plays") or 0, "date": r.get("date")}
                for r in by_plays[:10]
            ],
        }

    (OUT / "index.html").write_text(index_page(summaries), encoding="utf-8")
    (API / "years.json").write_text(
        json.dumps(api_years, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"years: {len(YEARS)} pages + index + data/v1/years.json")

if __name__ == "__main__":
    main()
