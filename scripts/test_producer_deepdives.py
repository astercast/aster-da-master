#!/usr/bin/env python3
"""Pinned-fixture tests for the wave-27 producer deep-dives.

Covers the pure logic in scripts/build_producer_deepdives.py plus the
data assertions the wave brief demands: every producer credit resolves to
a real release page and a real session id, every explorer producer node
resolves to a deep-dive page, and the explorer JS slug construction lands
on a real producers/<slug>.html for all 113 producers.

Usage: python3 scripts/test_producer_deepdives.py   (exit 0 = all pass)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_producer_deepdives import (  # noqa: E402
    parse_producers, producer_slug, producer_page, network_fig_id,
    canonical_producers)

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name} {detail}")


# --- parse_producers: canonical rule, pinned cases --------------------------
check("prod. single",
      parse_producers("Soul Shaking (prod. Fish Narc)") == ["Fish Narc"])
check("prod x split",
      parse_producers("getting colder w/ capoxxo (prod. pvscale x asa41)")
      == ["pvscale", "asa41"])
check("dollar-strip",
      parse_producers("Lucid Boi (prod. $ T.N.C $)") == ["T.N.C"])
check("no-prod",
      parse_producers("NIGHT MODE ft. MAX FERRARI x YUNG VETTA x JAX") == [])
check("amp-split",
      parse_producers("That's a Lie (prod. Xtravulous x WhyLoner)")
      == ["Xtravulous", "WhyLoner"])
check("comma-split",
      parse_producers("big litemode (prod runawway, ilyagargod & k3nik)")
      == ["runawway", "ilyagargod", "k3nik"])
check("produced-by",
      parse_producers("For Brian (Neck Deep) outro [produced by AWFL]")
      == ["AWFL"])
check("wav-ext",
      parse_producers("nitemode2019 w/ Max+Vetty prod. NaXi.wav") == ["NaXi"])
check("plus-prefix",
      parse_producers("the peace of the spirit urn (prod +fiftyzeros)")
      == ["fiftyzeros"])
check("nospace-prod",
      parse_producers("P1aced a Ward (prodbygus)") == ["bygus"])
check("feat-not-producer",
      "Lil Wintr" not in parse_producers(
          "master key ft. Lil Wintr x Marcelo (prod. ginseng)"))
check("single-credit-ginseng",
      parse_producers("master key ft. Lil Wintr x Marcelo (prod. ginseng)")
      == ["ginseng"])
check("aster-excluded",
      parse_producers("x (prod. Aster da Master)") == [])

# --- producer_slug -----------------------------------------------------------
check("slug-basic", producer_slug("Fish Narc") == "fish-narc")
check("slug-case", producer_slug("DeepHartt") == "deephartt")
check("slug-underscore", producer_slug("astral_hp") == "astral-hp")
check("slug-dots", producer_slug("T.N.C") == "t-n-c")
check("slug-nospace", producer_slug("YungSkah") == "yungskah")
check("slug-jp", producer_slug("itami リネン") == "itami")

# --- network_fig_id: mirrors build_codex_network.py's node-id rule -----------
CBN = {"pvscale": {"slug": "pvscale"}, "keyblayde808": {"slug": "keyblayde808"}}
check("fig-fish-narc", network_fig_id("Fish Narc", CBN) == "fig-fish-narc")
check("fig-circle-member",
      network_fig_id("pvscale", CBN) == "fig-pvscale")
check("fig-plain", network_fig_id("asa41", CBN) == "fig-p-asa41")

# --- canonical_producers: merge rule on a pinned fixture ---------------------
FIX = [
    {"id": "session-01", "name": "S1", "tracks": [
        {"title": "a (prod. deephartt)", "page": "releases/a.html"},
        {"title": "b prod. DeepHartt", "page": "releases/b.html"},
    ]},
    {"id": "session-02", "name": "S2", "tracks": [
        {"title": "c (prod. astral_hp)", "page": "releases/c.html"},
        {"title": "d (prod astral hp)", "page": "releases/d.html"},
        {"title": "e (prod. asa41)", "page": "releases/e.html"},
    ]},
]
prods = canonical_producers(FIX)
by_slug = {p["slug"]: p for p in prods}
check("merge-count", len(prods) == 3, f"got {len(prods)}")
check("merge-deephartt",
      len(by_slug["deephartt"]["credits"]) == 2)
check("merge-deephartt-alias",
      by_slug["deephartt"]["aliases"] == ["DeepHartt"],
      str(by_slug["deephartt"]["aliases"]))
check("merge-astral",
      len(by_slug["astral-hp"]["credits"]) == 2
      and by_slug["astral-hp"]["aliases"] == ["astral hp"])
check("merge-conserves",
      sum(len(p["credits"]) for p in prods) == 5)
check("merge-slug-unique",
      len({p["slug"] for p in prods}) == len(prods))

# --- live data assertions ----------------------------------------------------
DOC = json.loads((ROOT / "data" / "v1" / "producer-deepdives.json").read_text())
SESSIONS = {s["id"]: s for s in
            json.loads((ROOT / "data" / "sessions.json").read_text())["sessions"]}
NET = json.loads((ROOT / "data" / "v1" / "codex-network.json").read_text())
NET_NODES = {n["id"]: n for n in NET["nodes"]}
FAMS = {f["slug"]: f for f in
        json.loads((ROOT / "data" / "v1" / "codex-families.json").read_text())["families"]}

check("doc-producer-count", DOC["producer_count"] == len(DOC["producers"]) == 113,
      str(DOC["producer_count"]))
check("doc-version", DOC["version"] == "0.18.0")

missing_pages, missing_sessions = [], []
for p in DOC["producers"]:
    for pr in p["productions"]:
        if not (ROOT / pr["release_page"]).exists():
            missing_pages.append(pr["release_page"])
        if pr["session_id"] not in SESSIONS:
            missing_sessions.append(pr["session_id"])
    if not (ROOT / p["page"]).exists():
        missing_pages.append(p["page"])
    for f in p["codex_families"]:
        if f["family_slug"] not in FAMS:
            missing_pages.append("family:" + f["family_slug"])
        if not (ROOT / f["family_page"]).exists():
            missing_pages.append(f["family_page"])
    if p["circle_page"] and not (ROOT / p["circle_page"]).exists():
        missing_pages.append(p["circle_page"])
check("every-credit-resolves-to-real-release-page", not missing_pages,
      str(missing_pages[:5]))
check("every-credit-resolves-to-real-session-id", not missing_sessions,
      str(missing_sessions[:5]))

# every network producer/both node -> a real deep-dive page
node_gaps = []
for nid, n in NET_NODES.items():
    if n["kind"] in ("producer", "both"):
        js_slug = re.sub(r"^fig-", "", re.sub(r"^fig-p-", "", nid))
        pg = ROOT / producer_page(js_slug)
        if not pg.exists():
            node_gaps.append((nid, str(pg)))
check("every-explorer-producer-node-resolves", not node_gaps,
      str(node_gaps[:5]))

# the explorer JS slug construction lands on a real page for ALL producers
circle = json.loads((ROOT / "data" / "v1" / "circle.json").read_text())
cbn = {c["name"].lower(): {"slug": c["page"].split("/")[-1].replace(".html", "")}
       for c in circle.values()}
js_gaps = []
for p in DOC["producers"]:
    fid = network_fig_id(p["name"], cbn)
    js_slug = re.sub(r"^fig-", "", re.sub(r"^fig-p-", "", fid))
    if js_slug != p["slug"]:
        js_gaps.append((p["name"], fid, js_slug, p["slug"]))
check("js-slug-construction-matches-pages", not js_gaps, str(js_gaps[:5]))

# research file assertions
RES = json.loads((ROOT / "data" / "producer-research.json").read_text())
res_gaps = []
slugs = {p["slug"] for p in DOC["producers"]}
for rslug, r in RES["producers"].items():
    if rslug not in slugs:
        res_gaps.append("orphan:" + rslug)
    if not r.get("facts"):
        res_gaps.append("empty-facts:" + rslug)
    for src in r.get("sources", []):
        if not (src.get("label") and str(src.get("url", "")).startswith("http")):
            res_gaps.append("bad-source:" + rslug)
check("research-file-valid", not res_gaps, str(res_gaps[:5]))
check("research-coverage", DOC["insights"]["researched_count"] == 5,
      str(DOC["insights"]["researched_count"]))

# pinned spotlight producers
pv = next(p for p in DOC["producers"] if p["slug"] == "pvscale")
check("pvscale-credits", pv["production_count"] == 2)
check("pvscale-research", pv["research"] is not None)
gs = next(p for p in DOC["producers"] if p["slug"] == "ginseng")
check("ginseng-credit",
      gs["productions"][0]["title"]
      == "master key ft. Lil Wintr x Marcelo (prod. ginseng)")
check("ginseng-research", gs["research"] is not None)
ek = next(p for p in DOC["producers"] if p["slug"] == "em-klebold")
check("em-klebold-credit",
      ek["productions"][0]["title"] == "Take Me (prod. Em Klebold)")
check("excluded-have-no-pages",
      all((ROOT / producer_page(s)).exists() is False
          for s in ("capoxxo", "lil-koi", "lil-yu")),
      "exclusion rule violated")

print(f"\ntest_producer_deepdives: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
