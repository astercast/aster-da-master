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

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "artist.json").read_text())
OUT = ROOT / "releases"

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
      <nav class="site-nav" aria-label="Primary">
        <a href="../#discography">Discography</a>
        <a href="./">All releases</a>
        <a href="../press-kit.html">Press kit</a>
      </nav>
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
        <a href="./">All releases</a>
        <a href="../press-kit.html">Press kit</a>
      </nav>
    </div>
  </footer>
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

        prov = f"""
        <section class="provenance" aria-labelledby="prov-h">
          <h2 id="prov-h">Provenance</h2>
          <dl class="release-meta">
            <dt>Source</dt><dd>{escape(r.get("source", "Not recorded"))}</dd>
            <dt>Confidence</dt><dd>{escape(r.get("confidence", "verified"))}</dd>
            <dt>Research</dt><dd>2026-10-11 artist research pass; titles and credits only &mdash; no lyrics reproduced.</dd>
          </dl>
          {"<p>Cited indexes:</p><ul>" + citations + "</ul>" if citations else ""}
          {f'<p>{escape(r["note"])}</p>' if r.get("note") else ""}
        </section>"""

        body = f"""
      <article class="release-hero" aria-labelledby="rel-title">
        <div>{art}</div>
        <div>
          <p class="kicker"><span class="numeral">&#10022;</span>{escape(r["type"])}</p>
          <h1 id="rel-title">{escape(r["title"])}</h1>
          <dl class="release-meta">
            <dt>Type</dt><dd>{escape(r["type"])}</dd>
            <dt>{'Uploaded' if r['type'] == 'SoundCloud-only' else 'Released'}</dt><dd>{escape(r["date"]) if r.get("date") else "Unknown"}</dd>
            {f'<dt>Label</dt><dd>{escape(r["label"])}</dd>' if r.get("label") else ""}
            {f'<dt>Tracks</dt><dd>{r["tracks"]}</dd>' if r.get("tracks") else ""}
            {f'<dt>Plays</dt><dd>{r["plays"]:,} <span class="chart-sub">(snapshot 2026-10-11)</span></dd>' if r.get("plays") is not None else ""}
            {credit_html}
          </dl>
          <div class="btn-row">{links or '<p class="chart-sub">No distributor platform links on record for this entry.</p>'}</div>
        </div>
      </article>
      {prov}
      <nav class="release-nav" aria-label="More releases">{prev_link}{next_link}</nav>
"""
        (OUT / f"{slug}.html").write_text(
            HEAD.format(title=escape(r["title"]), desc=escape(f'{r["title"]} — {r["type"]} by Aster da Master'))
            + body
            + FOOT,
            encoding="utf-8",
        )

    # Index page with filters (year / type / label)
    index_items = []
    n_vault = sum(1 for r in releases if r["type"] == "SoundCloud-only")
    n_dist = len(releases) - n_vault
    for i, r in enumerate(releases):
        index_items.append(
            {
                "title": r["title"],
                "slug": slug_list[i],
                "date": r.get("date"),
                "year": (r["date"] or "")[:4] if r.get("date") else "Unknown",
                "type": r["type"],
                "label": r.get("label") or "—",
                "plays": r.get("plays"),
            }
        )
    years = sorted({i["year"] for i in index_items}, reverse=True)
    types = sorted({i["type"] for i in index_items})
    labels = sorted({i["label"] for i in index_items if i["label"] != "—"})

    def opts(vals):
        return "".join(f'<option value="{escape(v)}">{escape(v)}</option>' for v in vals)

    index_body = f"""
      <section class="section" aria-labelledby="idx-h">
        <p class="kicker"><span class="numeral">&#10022;</span>The full archive</p>
        <h1 id="idx-h">Every release</h1>
        <p>{len(releases)} transmissions on record &mdash; {n_dist} distributor releases and {n_vault} from the SoundCloud vault.</p>
        <div class="filter-row" role="group" aria-label="Filter releases">
          <label>Year <select id="f-year"><option value="">All years</option>{opts(years)}</select></label>
          <label>Type <select id="f-type"><option value="">All types</option>{opts(types)}</select></label>
          <label>Label <select id="f-label"><option value="">All labels</option>{opts(labels)}</select></label>
        </div>
        <ul class="release-list" id="release-list"></ul>
      </section>
      <script>
      (function () {{
        var items = {json.dumps(index_items, ensure_ascii=False)};
        var list = document.getElementById("release-list");
        var fy = document.getElementById("f-year"), ft = document.getElementById("f-type"), fl = document.getElementById("f-label");
        function esc(s) {{ return String(s).replace(/[&<>"']/g, function (c) {{
          return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]; }}); }}
        function render() {{
          var y = fy.value, t = ft.value, l = fl.value;
          var rows = items.filter(function (i) {{
            return (!y || i.year === y) && (!t || i.type === t) && (!l || i.label === l);
          }});
          list.innerHTML = rows.map(function (i) {{
            var plays = (i.plays != null)
              ? ' <span class="rl-plays">' + Number(i.plays).toLocaleString("en-US") + " plays</span>"
              : "";
            return '<li><span><a href="' + esc(i.slug) + '.html">' + esc(i.title) + "</a>" +
              '<span class="rl-type">' + esc(i.type) + "</span>" + plays + "</span>" +
              '<span class="rl-date">' + esc(i.date || "date unknown") + "</span></li>";
          }}).join("") || "<li>No releases match those filters.</li>";
        }}
        [fy, ft, fl].forEach(function (s) {{ s.addEventListener("change", render); }});
        render();
      }})();
      </script>
"""
    (OUT / "index.html").write_text(
        HEAD.format(title="Every release", desc="The complete Aster da Master release archive") + index_body + FOOT,
        encoding="utf-8",
    )
    print(f"Built {len(releases)} release pages + index in {OUT}/")


if __name__ == "__main__":
    build()
