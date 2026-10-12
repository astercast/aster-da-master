#!/usr/bin/env python3
"""Build the codex family deep-dives (wave 21).

17th generator, LAST in the chain. Gives the 16 codex families the
era-deep-dive treatment.

Reads:
  api/v1/codex.json            (families: epithet, words, track lists)
  api/v1/eras.json             (the six eras: years, deep_dive, journey links)
  data/sessions.json           (session -> track lists)
  api/v1/session-clusters.json (session deep_dive links)
  api/v1/circle.json           (collaborator -> track lists)
  api/v1/release-slugs.json    (ordinal -> release page slug)
  data/artist.json             (discography ordinals)

Emits:
  api/v1/codex-families.json       (endpoint #18)
  api/v1/schema/codex-families.json (draft-07 schema #18)
  codex/<slug>.html x16            (family deep-dive pages - this generator
                                   OWNS them; build_codex.py no longer does)
  api/v1/index.json                (endpoint registered via render_manifest())

Per family, every figure recomputed and asserted:
  - every transmission carrying its markers, with plays + release links
  - the decoded reading: traced VERBATIM to codex.json's epithet (status
    "stated"), or status "unknown" where the archive assigns no meaning
    (the litemode/nitemode words - method.html unknowns register,
    re-checked 2026-10-11). NO NEW MEANINGS ARE INVENTED - the generator
    audits every reading against codex.json and fails otherwise.
  - era evolution: first appearance -> latest, per-era rows with deep-dive
    + transmission-journey links
  - key sessions (upload sessions carrying family tracks; session
    deep-dive links where one exists)
  - collaborators named on family tracks (circle page links)

Byte-stable: pinned SNAPSHOT, deterministic ordering, json indent=2.

VERSION is a mirror-only constant: wave 21 adds no new source data
(everything is derived from existing endpoints plus honest unknowns),
so the data version stays 0.13.0.
"""
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_releases import slugify  # noqa: E402  (single source of truth)
from api_manifest import render_manifest  # noqa: E402

API = ROOT / "api" / "v1"
CODEX = json.loads((API / "codex.json").read_text())["families"]
ERAS = json.loads((API / "eras.json").read_text())["eras"]
SESSIONS = json.loads((ROOT / "data" / "sessions.json").read_text())["sessions"]
CLUSTERS = {s["id"]: s for s in
            json.loads((API / "session-clusters.json").read_text())["sessions"]}
CIRCLE = json.loads((API / "circle.json").read_text())
RSLUGS = json.loads((API / "release-slugs.json").read_text())
DISC = json.loads((ROOT / "data" / "artist.json").read_text())["discography"]

VERSION = "0.13.0"  # mirror only - no source data changed in wave 21
SNAPSHOT = "2026-10-11"

CODEX_PAGES = ROOT / "codex"
API_OUT = API / "codex-families.json"
SCHEMA_OUT = API / "schema" / "codex-families.json"


def fmt(n):
    return f"{n:,}"


def release_page(i):
    p = "releases/" + RSLUGS[str(i)] + ".html"
    assert (ROOT / p).exists(), f"missing release page {p}"
    return p


# --- family slugs: identical rule to scripts/build_codex.py ---
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
assert len(FAMSLUG) == 16, "codex family slug drift"

ORDINAL_OF = {(r["title"], r.get("date")): i for i, r in enumerate(DISC)}
SESS_OF = {}
for s in SESSIONS:
    for t in s["tracks"]:
        SESS_OF[(t["title"], t["date"])] = s
YEAR_ERA = {}
for e in ERAS:
    for y in e["years"]:
        YEAR_ERA[y] = e


def family_release_pages(fam):
    """Release page per family track; asserts every track is in the discography."""
    pages = {}
    for t in fam["tracks"]:
        key = (t["title"], t.get("date"))
        assert key in ORDINAL_OF, f"family track not in discography: {key}"
        pages[key] = release_page(ORDINAL_OF[key])
    return pages


# --- decoded readings: the ONLY meanings this wave may state ---------------
# Every "stated" reading is the family's epithet VERBATIM from codex.json.
# The Modes words have no assigned meaning per the unknowns register, so
# their status is "unknown" and the generator says so honestly.
UNKNOWN_WORDS_NOTE = (
    "The archive assigns no meaning to the mode-words. litemode / nitemode "
    "appear in titles, but no index source defines them for this artist or "
    "collective - tallied, never translated. "
    "(method.html unknowns register, re-checked 2026-10-11.)"
)
UNKNOWN_FAMILY = "The Modes"


def decoded(fam):
    if fam["name"] == UNKNOWN_FAMILY:
        return {"reading": UNKNOWN_WORDS_NOTE, "status": "unknown",
                "source": "method.html unknowns register (2026-10-11)"}
    return {"reading": fam["epithet"], "status": "stated",
            "source": ("codex.json epithet - the archive's own reading of "
                       "this word family (site framing of title vocabulary, "
                       "not an artist statement)")}


def family_eras(fam, pages):
    """Era evolution rows in era order; asserts every track lands in an era."""
    rows = []
    for e in ERAS:
        et = [t for t in fam["tracks"] if t.get("date") and
              t["date"][:4] in e["years"]]
        if not et:
            continue
        assert e["deep_dive"] and (ROOT / e["deep_dive"]).exists(), \
            f"missing era deep dive {e['deep_dive']}"
        loud = max(et, key=lambda t: t.get("plays") or 0)
        key = (loud["title"], loud.get("date"))
        rows.append({
            "id": e["id"], "name": e["name"], "span": e["span"],
            "transmissions": len(et),
            "plays": sum(t.get("plays") or 0 for t in et),
            "loudest": {"title": loud["title"], "date": loud.get("date"),
                        "plays": loud.get("plays"), "page": pages[key]},
            "deep_dive": e["deep_dive"],
            "journey": e["journey"],
        })
        assert (ROOT / e["journey"].split("#")[0]).exists(), \
            f"missing journey page for {e['id']}"
    assert sum(r["transmissions"] for r in rows) == fam["track_count"], \
        f"{fam['name']}: era rows don't cover all tracks"
    return rows


def family_sessions(fam, pages):
    """Key upload sessions carrying family tracks (distributor releases excluded)."""
    per = {}
    for t in fam["tracks"]:
        key = (t["title"], t.get("date"))
        s = SESS_OF.get(key)
        if not s:
            continue
        per.setdefault(s["id"], {"session": s, "tracks": []})
        per[s["id"]]["tracks"].append(t)
    rows = []
    for sid, pack in per.items():
        s = pack["session"]
        cl = CLUSTERS.get(sid, {})
        dd = cl.get("deep_dive")
        if dd:
            assert (ROOT / dd).exists(), f"missing session deep dive {dd}"
            page = dd
        else:
            page = "sessions.html"
        rows.append({
            "id": sid, "name": s["name"], "start": s["start"], "end": s["end"],
            "family_transmissions": len(pack["tracks"]),
            "family_plays": sum(t.get("plays") or 0 for t in pack["tracks"]),
            "deep_dive": dd, "page": page,
        })
    rows.sort(key=lambda r: (-r["family_transmissions"], -r["family_plays"],
                             r["start"]))
    return rows


def family_collaborators(fam):
    """Title-credited collaborators named on family tracks (circle links)."""
    keys = {(t["title"], t.get("date")) for t in fam["tracks"]}
    rows = []
    for slug, c in CIRCLE.items():
        tr = [t for t in c["tracks"] if (t["title"], t["date"]) in keys]
        if tr:
            assert (ROOT / c["page"]).exists(), f"missing circle page {c['page']}"
            rows.append({"slug": slug, "name": c["name"], "page": c["page"],
                         "transmissions": len(tr),
                         "plays": sum(t.get("plays") or 0 for t in tr)})
    rows.sort(key=lambda r: (-r["plays"], r["name"]))
    return rows


def build_family(fam):
    pages = family_release_pages(fam)
    by_date = sorted(fam["tracks"],
                     key=lambda t: (t.get("date") or "9999", t["title"]))
    first, last = by_date[0], by_date[-1]
    tx = [{"title": t["title"], "date": t.get("date"),
           "plays": t.get("plays"), "type": t.get("type", "Release"),
           "page": pages[(t["title"], t.get("date"))]} for t in by_date]
    total_plays = sum(t.get("plays") or 0 for t in fam["tracks"])
    dec = decoded(fam)
    # MEANING AUDIT: the only meanings allowed are the epithet verbatim
    # or the honest unknown statement. Anything else fails the build.
    assert dec["status"] == "unknown" or dec["reading"] == fam["epithet"], \
        f"{fam['name']}: reading drifted from codex.json epithet"
    eras = family_eras(fam, pages)
    out = {
        "name": fam["name"],
        "slug": FAMSLUG[fam["name"]],
        "epithet": fam["epithet"],
        "words": fam["words"],
        "page": "codex/" + FAMSLUG[fam["name"]] + ".html",
        "track_count": fam["track_count"],
        "total_plays": total_plays,
        "decoded": dec,
        "first_appearance": {
            "title": first["title"], "date": first.get("date"),
            "plays": first.get("plays"),
            "page": pages[(first["title"], first.get("date"))]},
        "latest": {
            "title": last["title"], "date": last.get("date"),
            "plays": last.get("plays"),
            "page": pages[(last["title"], last.get("date"))]},
        "eras": eras,
        "transmissions": tx,
        "key_sessions": family_sessions(fam, pages),
        "collaborators": family_collaborators(fam),
    }
    assert out["track_count"] == len(tx) == len(fam["tracks"])
    assert out["total_plays"] == sum(t["plays"] or 0 for t in tx)
    return out


# --- page template (era-deep-dive treatment, codex-sized) --------------------
from build_codex import HEAD, FOOT  # noqa: E402


def family_page(d, prev_s, next_s):
    parts = []

    # hero
    words = " · ".join(d["words"])
    years = sorted({t["date"][:4] for t in d["transmissions"] if t.get("date")})
    span = years[0] if len(years) == 1 else f"{years[0]}–{years[-1]}"
    parts.append(f"""
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../">Home</a> / <a href="../#codex">Codex</a> / <a href="./">Families</a> / <span aria-current="page">{escape(d['name'])}</span>
      </nav>
      <section class="section" aria-labelledby="cf-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The codex &middot; family deep dive</span>
        <h2 id="cf-h">{escape(d['name'])}</h2>
        <p class="codex-epithet">{escape(d['epithet'])}</p>
        <p class="codex-words">Matched words: {escape(words)}</p>
        <div class="stat-grid">
          <div class="stat"><div class="stat-value">{d['track_count']}</div><div class="stat-label">Transmissions</div></div>
          <div class="stat"><div class="stat-value">{fmt(d['total_plays'])}</div><div class="stat-label">Combined plays</div></div>
          <div class="stat"><div class="stat-value">{len(d['eras'])}</div><div class="stat-label">Eras active</div></div>
          <div class="stat"><div class="stat-value">{escape(span)}</div><div class="stat-label">Span of years</div></div>
        </div>
        <p class="chart-sub">Every claim here is a count &mdash; no meanings invented. Play counts are the {SNAPSHOT} vault snapshot. Upload dates are upload dates, not recording dates.</p>
      </section>
""")

    # the reading - decoded meaning, traced or honestly unknown
    dec = d["decoded"]
    if dec["status"] == "unknown":
        read_body = (f"<p>{escape(dec['reading'])}</p>"
                     f"<p class=\"chart-sub\">Source: {escape(dec['source'])}</p>")
    else:
        read_body = (f"<blockquote class=\"quote\"><span class=\"sig-lab\">"
                     f"The reading</span>{escape(dec['reading'])}</blockquote>"
                     f"<p class=\"chart-sub\">Source: {escape(dec['source'])}</p>")
    parts.append(f"""
      <section class="section" aria-labelledby="rd-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The cipher</span>
        <h3 id="rd-h">The reading</h3>
        {read_body}
      </section>
""")

    # era evolution
    fa = d["first_appearance"]
    la = d["latest"]
    evo_intro = (
        f"First heard <a href=\"../{fa['page']}\">&ldquo;{escape(fa['title'])}</a>&rdquo; "
        f"({escape(fa['date'] or 'date unknown')}); latest "
        f"<a href=\"../{la['page']}\">&ldquo;{escape(la['title'])}</a>&rdquo; "
        f"({escape(la['date'] or 'date unknown')}).")
    erows = "".join(
        f"<li><a href=\"../{r['deep_dive']}\">{escape(r['name'])}</a> "
        f"<span class=\"dim\">{escape(r['span'])} &middot; &times;{r['transmissions']} &middot; "
        f"{fmt(r['plays'])} plays</span>"
        f"<p class=\"m-fact\">Loudest: &ldquo;<a href=\"../{r['loudest']['page']}\">"
        f"{escape(r['loudest']['title'])}</a>&rdquo; "
        f"({fmt(r['loudest']['plays'] or 0)} plays) &middot; "
        f"<a href=\"../{r['journey']}\">journey</a></p></li>"
        for r in d["eras"])
    parts.append(f"""
      <section class="section" aria-labelledby="ev-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The eras</span>
        <h3 id="ev-h">Evolution across the eras ({len(d['eras'])})</h3>
        <p>{evo_intro}</p>
        <ul class="story-list">{erows}</ul>
      </section>
""")

    # every transmission
    rows = "".join(
        f"<li><a href=\"../{t['page']}\">{escape(t['title'])}</a> "
        f"<span class=\"dim\">{escape(t['date'] or 'date unknown')} &middot; "
        + (f"{fmt(t['plays'])} plays" if t.get("plays") is not None
           else "plays uncounted")
        + f" &middot; {escape(t['type'])}</span></li>"
        for t in d["transmissions"])
    parts.append(f"""
      <section class="section" aria-labelledby="all-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The record</span>
        <h3 id="all-h">Every transmission ({len(d['transmissions'])})</h3>
        <ol class="year-list">{rows}</ol>
        <p class="chart-sub">Distributor releases carry no vault play count &mdash; only SoundCloud uploads do.</p>
      </section>
""")

    # key sessions
    if d["key_sessions"]:
        ss = "".join(
            f"<li><a href=\"../{s['page']}\">{escape(s['name'])}</a> "
            f"<span class=\"dim\">{escape(s['start'])} to {escape(s['end'])} &middot; "
            f"&times;{s['family_transmissions']} family transmission"
            f"{'s' if s['family_transmissions'] != 1 else ''} &middot; "
            f"{fmt(s['family_plays'])} plays</span></li>"
            for s in d["key_sessions"])
        sess_html = f"<ul class=\"year-list\">{ss}</ul>"
    else:
        sess_html = ("<p class=\"tx-empty\">No upload session carries this "
                     "family's words &mdash; every transmission is a "
                     "distributor release.</p>")
    parts.append(f"""
      <section class="section" aria-labelledby="ks-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The sessions</span>
        <h3 id="ks-h">Key sessions ({len(d['key_sessions'])})</h3>
        {sess_html}
        <p class="chart-sub">Distributor releases are not upload sessions &mdash; they carry no session record.</p>
      </section>
""")

    # voices
    if d["collaborators"]:
        co = "".join(
            f"<li><a href=\"../{c['page']}\">{escape(c['name'])}</a> "
            f"<span class=\"dim\">&times;{c['transmissions']} &middot; {fmt(c['plays'])} plays</span></li>"
            for c in d["collaborators"])
        collab_html = f"<ol class=\"top-list\">{co}</ol>"
    else:
        collab_html = ("<p class=\"tx-empty\">No title-credited collaborator "
                       "on this family's transmissions &mdash; every "
                       "transmission stands alone.</p>")
    parts.append(f"""
      <section class="section" aria-labelledby="co-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The voices</span>
        <h3 id="co-h">Voices on this family's transmissions ({len(d['collaborators'])})</h3>
        {collab_html}
        <p class="chart-sub">Credits parsed from <em>w/</em> and <em>ft.</em> fragments in titles &mdash; as credited, verbatim; producers excluded. Public profiles for some voices could not be verified (see the <a href="../method.html#m-unknowns">unknowns register</a>) &mdash; nothing more is claimed.</p>
      </section>
""")

    # keep digging + pager
    era_links = " ".join(
        f"<li><a href=\"../{r['deep_dive']}\">{escape(r['name'])}</a> &mdash; "
        f"<a href=\"../{r['journey']}\">journey node</a></li>"
        for r in d["eras"])
    prev_link = (f'<a class="btn btn-sm" href="{prev_s}.html" rel="prev">&larr; Prev</a>'
                 if prev_s else '<span class="btn btn-sm" aria-disabled="true">&larr;</span>')
    next_link = (f'<a class="btn btn-sm" href="{next_s}.html" rel="next">Next &rarr;</a>'
                 if next_s else '<span class="btn btn-sm" aria-disabled="true">&rarr;</span>')
    parts.append(f"""
      <section class="section" aria-labelledby="keep-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Keep digging</span>
        <h3 id="keep-h">The journey continues</h3>
        <nav class="year-pager" aria-label="Family navigation">
          {prev_link}
          <a class="btn btn-sm" href="./">All families</a>
          {next_link}
        </nav>
        <ul class="story-list">
          <li><a href="../decoder.html">The decoder</a> &mdash; speak a word; the archive answers.</li>
          {era_links}
          <li><a href="../sessions-explorer.html">Sessions explorer</a> &mdash; the 61 upload sessions on one timeline.</li>
          <li><a href="../codex/">Codex</a> &mdash; the 16 vocabulary families.</li>
        </ul>
      </section>
""")

    title = f"{d['name']} — codex family deep dive"
    desc = (f"{d['name']}: {d['track_count']} transmissions, "
            f"{fmt(d['total_plays'])} plays, {len(d['eras'])} eras active. "
            f"The codex family deep dive, from the archive.")
    return HEAD.format(title=escape(title), desc=escape(desc)
                       ) + "".join(parts) + FOOT


SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "codex-families",
    "description": ("Codex family deep-dives: the 16 vocabulary families "
                    "with decoded readings, era-by-era evolution, key "
                    "sessions, and title-credited collaborators. "
                    "Generated by scripts/build_codex_pages.py."),
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "generated": {"type": "string"},
        "plays_snapshot": {"type": "string"},
        "method": {"type": "string"},
        "family_count": {"type": "integer"},
        "families": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "slug": {"type": "string"},
                    "epithet": {"type": "string"},
                    "words": {"type": "array", "items": {"type": "string"}},
                    "page": {"type": "string"},
                    "track_count": {"type": "integer"},
                    "total_plays": {"type": "integer"},
                    "decoded": {
                        "type": "object",
                        "properties": {
                            "reading": {"type": "string"},
                            "status": {"type": "string",
                                       "enum": ["stated", "unknown"]},
                            "source": {"type": "string"},
                        },
                        "required": ["reading", "status", "source"],
                    },
                    "first_appearance": {"$ref": "#/definitions/tx"},
                    "latest": {"$ref": "#/definitions/tx"},
                    "eras": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "span": {"type": "string"},
                                "transmissions": {"type": "integer"},
                                "plays": {"type": "integer"},
                                "loudest": {"$ref": "#/definitions/tx"},
                                "deep_dive": {"type": "string"},
                                "journey": {"type": "string"},
                            },
                            "required": ["id", "name", "span",
                                         "transmissions", "plays", "loudest",
                                         "deep_dive", "journey"],
                        },
                    },
                    "transmissions": {"type": "array",
                                      "items": {"$ref": "#/definitions/txfull"}},
                    "key_sessions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "start": {"type": "string"},
                                "end": {"type": "string"},
                                "family_transmissions": {"type": "integer"},
                                "family_plays": {"type": "integer"},
                                "deep_dive": {"type": ["string", "null"]},
                                "page": {"type": "string"},
                            },
                            "required": ["id", "name", "start", "end",
                                         "family_transmissions",
                                         "family_plays", "page"],
                        },
                    },
                    "collaborators": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "slug": {"type": "string"},
                                "name": {"type": "string"},
                                "page": {"type": "string"},
                                "transmissions": {"type": "integer"},
                                "plays": {"type": "integer"},
                            },
                            "required": ["slug", "name", "page",
                                         "transmissions", "plays"],
                        },
                    },
                },
                "required": ["name", "slug", "epithet", "words", "page",
                             "track_count", "total_plays", "decoded",
                             "first_appearance", "latest", "eras",
                             "transmissions", "key_sessions",
                             "collaborators"],
            },
        },
    },
    "definitions": {
        "tx": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "date": {"type": ["string", "null"]},
                "plays": {"type": ["integer", "null"]},
                "page": {"type": "string"},
            },
            "required": ["title", "date", "plays", "page"],
        },
        "txfull": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "date": {"type": ["string", "null"]},
                "plays": {"type": ["integer", "null"]},
                "type": {"type": "string"},
                "page": {"type": "string"},
            },
            "required": ["title", "date", "plays", "type", "page"],
        },
    },
    "required": ["version", "generated", "plays_snapshot", "method",
                 "family_count", "families"],
}


def main():
    families = [build_family(f) for f in CODEX]
    assert len(families) == 16, "codex family drift"
    assert len({f["slug"] for f in families}) == 16, "family slug collision"

    doc = {
        "version": VERSION,
        "generated": SNAPSHOT,
        "plays_snapshot": SNAPSHOT,
        "method": (
            "Per-family deep dives computed from api/v1/codex.json against "
            "api/v1/eras.json, data/sessions.json, api/v1/session-clusters.json, "
            "api/v1/circle.json, and api/v1/release-slugs.json. Decoded "
            "readings are traced verbatim to codex.json's epithets; where the "
            "archive assigns no meaning (the litemode/nitemode words) the "
            "reading is stated as unknown. No meanings invented."),
        "family_count": len(families),
        "families": families,
    }
    API_OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    SCHEMA_OUT.write_text(json.dumps(SCHEMA, indent=2) + "\n")
    print(f"codex-families: {len(families)} families, "
          f"{sum(f['track_count'] for f in families)} family-track links")

    CODEX_PAGES.mkdir(exist_ok=True)
    for i, d in enumerate(families):
        prev_s = families[i - 1]["slug"] if i > 0 else None
        next_s = families[i + 1]["slug"] if i < len(families) - 1 else None
        (CODEX_PAGES / f'{d["slug"]}.html').write_text(
            family_page(d, prev_s, next_s), encoding="utf-8")
    print(f"codex pages: {len(families)} family deep-dives")

    idx = json.loads((API / "index.json").read_text())
    idx["version"] = VERSION
    render_manifest(idx, ROOT)
    print(f"version -> {VERSION}; manifest re-rendered")


if __name__ == "__main__":
    main()
