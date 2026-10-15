#!/usr/bin/env python3
"""Generate per-release pages + a filterable release index from data/artist.json.

Output: releases/<slug>.html (one per release), releases/index.html.
Each release page carries: cover art, title, type, date, label, track count,
credits as listed in the title (parsed, never invented), platform links, and a
provenance block. Titles only - no lyrics anywhere.

Idempotent: regenerates cleanly; slugs asserted unique.
"""
import json
import re
from html import escape
from pathlib import Path

import nav_data  # noqa: E402  (canonical nav data — scripts/nav_data.py)
ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "artist.json").read_text())
OUT = ROOT / "releases"

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} · Aster da Master</title>
  <meta name="description" content="{desc}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{title} · Aster da Master">
  <meta property="og:description" content="{desc}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:image" content="../assets/og-card.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} · Aster da Master">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="../assets/og-card.png">
  <link rel="preload" href="../assets/fonts/anton-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="../assets/css/fonts.css">
  <link rel="stylesheet" href="../assets/css/aster.css">
  {ldjson}
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="container header-bar">
      <a class="brand" href="../" aria-label="Aster da Master home">
        <span class="brand-mark" aria-hidden="true">A&#10022;</span>
        <span>ASTER DA MASTER</span>
      </a>
      {navchunk}
    </div>
  </header>
  <main id="main">
    <div class="container">
"""

FOOT = """    </div>
  </main>
  <footer class="site-footer">
    <div class="container footer-grid">
      <p>&copy; 2026 ASTER DA MASTER</p>
      """ + nav_data.footer_block("../", "compact") + """
    </div>
  </footer>
  <script src="../assets/js/identity.js"></script>
</body>
</html>
"""

def slugify(title: str) -> str:
    s = title.lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "release"

def credits_from_title(title: str):
    """Extract credit fragments verbatim from the title (parens/brackets).
    Nothing is invented - the raw fragments are shown as listed in the title."""
    frags = re.findall(r"\(([^)]*)\)", title) + re.findall(r"\[([^\]]*)\]", title)
    keep = [f.strip() for f in frags if re.search(r"(?i)feat|ft\.|prod|w/|with", f)]
    return keep


RELEASE_TYPE_MAP = {"Album": "AlbumRelease", "EP": "EPRelease", "Single": "SingleRelease"}


# --- Rotation 22 (Aster identity pass, ASTER-STUDY §8.3 + AZ-4) -------------
# The catalog mark, minted from the archive's own record: ADM + the entry's
# position in the archive order (this array's order, the same order the
# index prints as ItemList positions), zero-padded to four. Numbering is
# added structure only; no slug, URL or title changes.
def catalog_mark(i):
    return f"ADM {i + 1:04d}"


def ld_script(obj):
    payload = json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")
    return '<script type="application/ld+json">' + payload + "</script>"


def release_ld(r, slug):
    """Honest JSON-LD for one release page: only fields the catalog record
    itself carries (title/type/date/track count/artwork). No ratings, no
    offers, no play counts. SoundCloud-only entries are single tracks, so
    they type as MusicRecording, never MusicAlbum."""
    if r.get("type") == "SoundCloud-only":
        rec = {
            "@context": "https://schema.org",
            "@type": "MusicRecording",
            "name": r["title"],
            "byArtist": {"@type": "MusicGroup", "name": "Aster da Master"},
            "url": f"/releases/{slug}.html",
        }
        if r.get("date"):
            rec["datePublished"] = r["date"]
        return ld_script(rec)
    ld = {
        "@context": "https://schema.org",
        "@type": "MusicAlbum",
        "name": r["title"],
        "byArtist": {"@type": "MusicGroup", "name": "Aster da Master"},
        "url": f"/releases/{slug}.html",
    }
    rt = RELEASE_TYPE_MAP.get(r.get("type"))
    if rt:
        ld["albumReleaseType"] = rt
    if r.get("date"):
        ld["datePublished"] = r["date"]
    if r.get("tracks"):
        ld["numTracks"] = r["tracks"]
    if r.get("artwork"):
        ld["image"] = r["artwork"]
    return ld_script(ld)


def index_ld(releases, slug_list):
    items = [
        {"@type": "ListItem", "position": i + 1, "name": r["title"],
         "url": f"/releases/{s}.html"}
        for i, (r, s) in enumerate(zip(releases, slug_list))
    ]
    return ld_script({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "numberOfItems": len(items),
        "itemListElement": items,
    })

def build():
    releases = DATA["discography"]
    used_slugs = set()
    slug_list = []
    for r in releases:
        s = slugify(r["title"])
        base, n = s, 1
        while s in used_slugs:
            n += 1
            s = f"{base}-{n}"
        used_slugs.add(s)
        slug_list.append(s)
    assert len(set(slug_list)) == len(releases), "slug collision"

    # Page titles must be unique site-wide: two different releases can share
    # a catalog title (e.g. "9 Trips", a 2023 SoundCloud-only track and a
    # 2026 Single). A shared title gets its year as a qualifier in the page
    # title only — the record's own title (h1, JSON-LD name) stays untouched.
    title_counts = {}
    for r in releases:
        title_counts[r["title"]] = title_counts.get(r["title"], 0) + 1
    page_titles = []
    for r in releases:
        if title_counts[r["title"]] > 1:
            year = (r.get("date") or "")[:4] or "undated"
            page_titles.append(f'{r["title"]} ({year})')
        else:
            page_titles.append(r["title"])
    if len(set(page_titles)) != len(page_titles):
        # Same title AND same year: fall back to the record's type.
        page_titles = [
            f'{r["title"]} ({r["type"]}, {(r.get("date") or "")[:4] or "undated"})'
            if title_counts[r["title"]] > 1 else r["title"]
            for r in releases
        ]
    assert len(set(page_titles)) == len(page_titles), "page title collision"

    OUT.mkdir(exist_ok=True)

    for i, r in enumerate(releases):
        slug = slug_list[i]
        art = ""
        if r.get("artwork"):
            art = (
                f'<img src="{escape(r["artwork"])}" alt="{escape(r["title"])} cover art" loading="lazy">'
            )
        else:
            art = f'<div class="disco-art disco-mono" aria-hidden="true">{escape((r["title"] or "?")[0])}</div>'

        credits = credits_from_title(r["title"])
        credit_html = ""
        if credits:
            credit_html = (
                '<dt>As credited in the title</dt><dd>'
                + "; ".join(escape(c) for c in credits)
                + "</dd>"
            )

        links = "".join(
            f'<a class="btn btn-sm" href="{escape(l["url"])}" target="_blank" rel="noopener">{escape(l["label"])}</a>'
            for l in (r.get("links") or [])
        )
        citations = "".join(
            f'<li><a href="{escape(c["url"])}" target="_blank" rel="noopener">{escape(c["label"])}</a></li>'
            for c in (r.get("citations") or [])
        )
        prev_link = next_link = ""
        if i > 0:
            p = releases[i - 1]
            prev_link = f'<a class="btn" href="{slug_list[i - 1]}.html">&larr; {escape(p["title"])}</a>'
        if i < len(releases) - 1:
            n = releases[i + 1]
            next_link = f'<a class="btn" href="{slug_list[i + 1]}.html">{escape(n["title"])} &rarr;</a>'

        # Poster form: title at poster size, one plain metadata line
        # (type, date, label, track count, catalog mark closing), the
        # tracklist, the exits, then provenance as the record.
        # Sleek-minimal rework (2026-10-15): the state word and the play
        # count leave the metadata line. Play numbers are off the
        # presented site entirely by the user's direct order; the counts
        # stay in the data layer, unshown.
        is_vault = r["type"] == "SoundCloud-only"
        meta_bits = [
            escape(r["type"]),
            f'{"Uploaded" if is_vault else "Released"} {escape(r["date"]) if r.get("date") else "date unknown"}',
        ]
        if r.get("label"):
            meta_bits.append(escape(r["label"]))
        if r.get("tracks"):
            meta_bits.append(f'{r["tracks"]} tracks')
        meta_line = " &middot; ".join(meta_bits) + f' &middot; <span class="cat-mark">{catalog_mark(i)}</span>'

        # The tracklist prints what the record carries. Single-track
        # records: the one track, numbered, its timing slot honest (the
        # catalog carries no durations anywhere). Multi-track records:
        # titles were never captured, so the position carries the count
        # and says so. Nothing is invented to fill the form.
        if r.get("tracks") and isinstance(r.get("tracks"), int) and r["tracks"] > 1:
            tracklist = (
                f'<p class="tracks-note">{r["tracks"]} tracks. Track titles are not in the '
                'verified record; the catalog carries the count from the distributor listing.</p>'
            )
        else:
            tracklist = (
                f'<ol class="tracks"><li><span class="t-title">{escape(r["title"])}</span>'
                '<span class="t-time">timing unrecorded</span></li></ol>'
            )

        # Simplification steer (2026-10-14): the provenance record closes
        # the poster folded, one tap from the surface. Nothing is removed:
        # the full record (source, confidence, research line, title credits,
        # cited indexes, note) stands inside the fold, in the same order.
        prov = f"""
        <details class="provenance-fold">
          <summary>Provenance</summary>
          <dl class="release-meta">
            <dt>Source</dt><dd>{escape(r.get("source", "Not recorded"))}</dd>
            <dt>Confidence</dt><dd>{escape(r.get("confidence", "verified"))}</dd>
            <dt>Research</dt><dd>2026-10-11 artist research pass; titles and credits only; no lyrics reproduced.</dd>
            {credit_html}
          </dl>
          {"<p>Cited indexes:</p><ul>" + citations + "</ul>" if citations else ""}
          {f'<p>{escape(r["note"])}</p>' if r.get("note") else ""}
        </details>"""

        body = f"""
      <article class="poster" aria-labelledby="rel-title">
        <h1 class="poster-title" id="rel-title">{escape(r["title"])}</h1>
        <p class="poster-meta">{meta_line}</p>
        <div class="poster-art">{art}</div>
        <section class="tracklist" aria-labelledby="tl-h">
          <h2 id="tl-h">Tracklist</h2>
          {tracklist}
        </section>
        <div class="btn-row">{links or '<p class="chart-sub">No distributor platform links on record for this entry.</p>'}</div>
      </article>
      {prov}
      <nav class="release-nav" aria-label="More releases">{prev_link}{next_link}</nav>
"""
        (OUT / f"{slug}.html").write_text(
            HEAD.format(title=escape(page_titles[i]), desc=escape(f'{r["title"]} · {r["type"]} by Aster da Master'), canonical=f"/releases/{slug}.html", ldjson=release_ld(r, slug), navchunk=nav_data.nav_chunk("../", "compact"))
            + body
            + FOOT,
            encoding="utf-8",
        )

    # Index page: the whole catalogue as one quiet list (sleek-minimal
    # rework, 2026-10-15). Rows are static HTML, so the full list reads
    # with no script at all; the small inline script only filters what
    # is already on the page (title search + year + type). No play
    # counts anywhere: numbers are off the presented site.
    n_vault = sum(1 for r in releases if r["type"] == "SoundCloud-only")
    n_dist = len(releases) - n_vault
    years = sorted({(r["date"] or "")[:4] for r in releases if r.get("date")},
                   reverse=True)
    types = sorted({r["type"] for r in releases})

    def opts(vals):
        return "".join(f'<option value="{escape(v)}">{escape(v)}</option>' for v in vals)

    rows = []
    for i, r in enumerate(releases):
        year = (r["date"] or "")[:4] if r.get("date") else "Unknown"
        search_text = (r["title"] + " " + " ".join(credits_from_title(r["title"]))).lower()
        meta = escape(r["type"]) + " &middot; " + escape(r["date"] or "date unknown")
        if r.get("label"):
            meta += " &middot; " + escape(r["label"])
        rows.append(
            f'<li class="row" data-search="{escape(search_text, quote=True)}" '
            f'data-year="{escape(year, quote=True)}" data-type="{escape(r["type"], quote=True)}">'
            f'<span class="mark">{catalog_mark(i)}</span>'
            f'<span class="t"><a href="{slug_list[i]}.html">{escape(r["title"])}</a>'
            f'<span class="meta">{meta}</span></span></li>'
        )
    rows_html = "\n          ".join(rows)

    index_body = f"""
      <div class="page-head">
        <p class="kicker"><span class="numeral">&#10022;</span>The complete catalogue</p>
        <h1 class="page-title" id="idx-h">Releases</h1>
        <p class="lede">Every release on record: {n_dist} through distributors and {n_vault} from the SoundCloud vault, in the archive's order.</p>
      </div>
      <section aria-label="Catalogue">
        <div class="filters" role="group" aria-label="Filter releases">
          <label>Search titles <input type="search" id="f-text" placeholder="Type a title or a name" autocomplete="off"></label>
          <label>Year <select id="f-year"><option value="">All years</option>{opts(years)}</select></label>
          <label>Type <select id="f-type"><option value="">All types</option>{opts(types)}</select></label>
        </div>
        <p class="count-note" id="rl-count">{len(releases)} releases</p>
        <ul class="rows" id="release-list">
          {rows_html}
        </ul>
        <p class="count-note" id="rl-none" hidden>No releases match. Clear the search to see the whole catalogue.</p>
      </section>
      <script>
      (function () {{
        var rows = Array.prototype.slice.call(document.querySelectorAll("#release-list .row"));
        var ft = document.getElementById("f-text"), fy = document.getElementById("f-year"), fv = document.getElementById("f-type");
        var count = document.getElementById("rl-count"), none = document.getElementById("rl-none");
        function apply() {{
          var q = ft.value.trim().toLowerCase(), y = fy.value, t = fv.value, shown = 0;
          rows.forEach(function (row) {{
            var ok = (!q || row.getAttribute("data-search").indexOf(q) !== -1)
              && (!y || row.getAttribute("data-year") === y)
              && (!t || row.getAttribute("data-type") === t);
            row.hidden = !ok;
            if (ok) shown++;
          }});
          count.textContent = shown + (shown === 1 ? " release" : " releases");
          none.hidden = shown !== 0;
        }}
        ft.addEventListener("input", apply);
        fy.addEventListener("change", apply);
        fv.addEventListener("change", apply);
      }})();
      </script>
"""
    (OUT / "index.html").write_text(
        HEAD.format(title="Releases", desc="The complete Aster da Master release archive", canonical="/releases/index.html", ldjson=index_ld(releases, slug_list), navchunk=nav_data.nav_chunk("../", "compact")) + index_body + FOOT,
        encoding="utf-8",
    )
    print(f"Built {len(releases)} release pages + index in {OUT}/")

if __name__ == "__main__":
    build()
