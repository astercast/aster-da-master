#!/usr/bin/env python3
"""Wave 26: codex network explorer.

Computes the codex relationship graph from REAL archive data into
data/v1/codex-network.json (endpoint #21):
  - nodes: Aster (the speaker of every family), the 16 codex families,
    and every figure named on family transmissions -- title-credited
    collaborators (the circle's title-credit rule, as credited verbatim)
    and producer credits parsed from the titles' own prod. fragments
  - edges: aster-family (Aster speaks every word in the family),
    family-figure (weight = shared transmissions), figure-figure
    co-credit (from network.json's title co-occurrence edges, both
    endpoints in this graph)
  - family_overlap: the 16 families as nodes, shared figures as edges
  - degrees: BFS distance from Aster for every node, with the carrying
    families listed for each figure
  - insights: most-connected family / figure, largest shared bridge,
    isolated families -- all computed, then asserted

No payload shape changes to any existing endpoint; data version stays
0.14.0 (no source data changed). Titles and metadata only - never lyrics,
never invented bio facts.

Runs LAST in the validate.sh generator chain (after build_session_tools).
"""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "data" / "v1"
NEW_VERSION = "0.19.0"  # wave 35: data version 0.18.0 (verified-data expansion)
SNAPSHOT = "2026-10-11"

sys.path.insert(0, str(ROOT / "scripts"))
from api_manifest import render_manifest  # noqa: E402

CF = json.loads((API / "codex-families.json").read_text())["families"]
CIRCLE = json.loads((API / "circle.json").read_text())
NET = json.loads((API / "network.json").read_text())

W, H, CX, CY = 920, 640, 460, 320

# --- pure logic (imported by scripts/test_codex_network.py) ---


def parse_producers(title):
    """Producer credits from the title's own prod./produced-by fragment.

    Mirrors the spirit of parse_collabs (build_years.py): as credited,
    verbatim; nothing invented. Splits multi-producer credits on x / & /
    + / comma / slash / "and". Returns a list of producer names.
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


def fig_id_for(name):
    """Stable figure node id for a producer name (collaborators keep
    their circle slug, assigned by the caller)."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return "fig-p-" + (slug or "unknown")


def bfs_distances(adj, source):
    """BFS distances from source over an undirected adjacency map
    {node_id: set(node_id)}. Unreached nodes are absent from the result."""
    dist = {source: 0}
    frontier = [source]
    while frontier:
        nxt = []
        for u in frontier:
            for v in adj.get(u, ()):
                if v not in dist:
                    dist[v] = dist[u] + 1
                    nxt.append(v)
        frontier = nxt
    return dist


def shortest_path(adj, start, goal, forbid=frozenset()):
    """Shortest path (list of node ids) from start to goal, or None.
    Nodes in `forbid` are never entered (start/goal exempt)."""
    if start == goal:
        return [start]
    prev = {start: None}
    frontier = [start]
    while frontier:
        nxt = []
        for u in frontier:
            for v in adj.get(u, ()):
                if v in forbid and v != goal:
                    continue
                if v not in prev:
                    prev[v] = u
                    if v == goal:
                        path = [v]
                        while prev[path[-1]] is not None:
                            path.append(prev[path[-1]])
                        return path[::-1]
                    nxt.append(v)
        frontier = nxt
    return None


def build_graph(families, figure_defs, co_credit):
    """Pure graph assembly.

    families: [{slug, name, page, track_count, total_plays}] (16)
    figure_defs: {fig_id: {name, kind, page, links: {fam_slug: [titles]}}}
    co_credit: [(a_id, b_id, [titles])] -- figure-figure edges, real data
    Returns {nodes, edges, family_overlap, degrees, insights} with a
    deterministic server-side layout (rings; stable across re-runs).
    """
    fam_ids = ["fam-" + f["slug"] for f in families]
    fam_by_id = {"fam-" + f["slug"]: f for f in families}

    adj = defaultdict(set)
    edges = []

    def add_edge(a, b, weight, kind, label, titles):
        adj[a].add(b)
        adj[b].add(a)
        edges.append({"a": a, "b": b, "weight": weight, "kind": kind,
                      "label": label, "titles": sorted(titles)})

    for fid in fam_ids:
        f = fam_by_id[fid]
        add_edge("aster", fid, f["track_count"], "aster-family",
                 "Aster speaks every word in this family "
                 "(%d transmissions)" % f["track_count"], [])

    for fig_id in sorted(figure_defs):
        fd = figure_defs[fig_id]
        for fam_slug in sorted(fd["links"]):
            fid = "fam-" + fam_slug
            titles = fd["links"][fam_slug]
            fname = fam_by_id[fid]["name"]
            add_edge(fid, fig_id, len(titles), "family-figure",
                     "%s x %d in %s" % (fd["name"], len(titles), fname),
                     titles)

    for a, b, titles in sorted(co_credit):
        fa, fb = figure_defs[a]["name"], figure_defs[b]["name"]
        add_edge(a, b, len(titles), "co-credit",
                 "%s and %s credited together x %d" % (fa, fb, len(titles)),
                 titles)

    # family overlap: families as nodes, shared figures as edges
    overlap = []
    fig_fams = {fig: set(fd["links"]) for fig, fd in figure_defs.items()}
    for i in range(len(families)):
        for j in range(i + 1, len(families)):
            si, sj = families[i]["slug"], families[j]["slug"]
            shared = sorted(
                fig for fig, fs in fig_fams.items() if si in fs and sj in fs)
            if shared:
                overlap.append({
                    "a_id": "fam-" + si, "b_id": "fam-" + sj,
                    "a_slug": si, "b_slug": sj,
                    "a_name": families[i]["name"],
                    "b_name": families[j]["name"],
                    "a_page": families[i]["page"],
                    "b_page": families[j]["page"],
                    "weight": len(shared),
                    "shared_figures": [
                        {"id": fig, "name": figure_defs[fig]["name"],
                         "kind": figure_defs[fig]["kind"]}
                        for fig in shared],
                })
    overlap.sort(key=lambda o: (-o["weight"], o["a_slug"], o["b_slug"]))

    # degrees of separation from Aster (BFS on the real graph)
    dist = bfs_distances(adj, "aster")
    degrees = []
    for fid in fam_ids:
        degrees.append({"id": fid, "name": fam_by_id[fid]["name"],
                        "kind": "family", "degrees": dist.get(fid),
                        "via": []})
    for fig_id in sorted(figure_defs):
        fd = figure_defs[fig_id]
        via = sorted("fam-" + s for s in fd["links"])
        degrees.append({"id": fig_id, "name": fd["name"], "kind": fd["kind"],
                        "degrees": dist.get(fig_id), "via": via})
    degrees.sort(key=lambda d: (d["degrees"] if d["degrees"] is not None
                                else 999, d["name"].lower()))

    # insights (computed; the caller asserts them)
    fam_fig_n = {fid: sum(1 for fd in figure_defs.values()
                          if fid[4:] in fd["links"]) for fid in fam_ids}
    most_fam = max(fam_ids, key=lambda fid: (fam_fig_n[fid],
                                             fam_by_id[fid]["track_count"],
                                             fam_by_id[fid]["slug"]))
    fig_fam_n = {fig: len(fd["links"]) for fig, fd in figure_defs.items()}
    most_fig = max(sorted(figure_defs),
                   key=lambda fig: (fig_fam_n[fig],
                                    figure_defs[fig]["name"].lower()))
    isolated = sorted(f["slug"] for f in families
                      if not any(o["a_slug"] == f["slug"]
                                 or o["b_slug"] == f["slug"]
                                 for o in overlap))
    kinds = defaultdict(int)
    for fd in figure_defs.values():
        kinds[fd["kind"]] += 1
    insights = {
        "most_connected_family": {
            "id": most_fam, "slug": most_fam[4:],
            "name": fam_by_id[most_fam]["name"],
            "page": fam_by_id[most_fam]["page"],
            "figure_count": fam_fig_n[most_fam]},
        "most_connected_figure": {
            "id": most_fig, "name": figure_defs[most_fig]["name"],
            "kind": figure_defs[most_fig]["kind"],
            "page": figure_defs[most_fig]["page"],
            "family_count": fig_fam_n[most_fig],
            "families": sorted(figure_defs[most_fig]["links"])},
        "largest_bridge": ({
            "a_slug": overlap[0]["a_slug"], "b_slug": overlap[0]["b_slug"],
            "a_name": overlap[0]["a_name"], "b_name": overlap[0]["b_name"],
            "weight": overlap[0]["weight"],
            "shared_figures": [s["name"]
                               for s in overlap[0]["shared_figures"]]}
            if overlap else None),
        "isolated_families": isolated,
        "family_count": len(families),
        "figure_count": len(figure_defs),
        "collaborator_figures": kinds.get("collaborator", 0)
        + kinds.get("both", 0),
        "producer_figures": kinds.get("producer", 0) + kinds.get("both", 0),
        "overlap_pairs": len(overlap),
        "node_count": 1 + len(families) + len(figure_defs),
        "edge_count": len(edges),
    }

    # deterministic layout: families inner ring, figures outer ring
    max_t = max(f["track_count"] for f in families)
    fam_sorted = sorted(families,
                        key=lambda f: (-f["track_count"], f["name"]))
    fam_xy = {}
    for i, f in enumerate(fam_sorted):
        a = -math.pi / 2 + (i / len(fam_sorted)) * 2 * math.pi
        fam_xy["fam-" + f["slug"]] = (
            round(CX + 170 * math.cos(a), 1),
            round(CY + 170 * 0.92 * math.sin(a), 1))
    max_nf = max((len(fd["links"]) for fd in figure_defs.values()),
                 default=1)
    fig_sorted = sorted(figure_defs, key=lambda fid: figure_defs[fid]["name"].lower())
    fig_xy = {}
    for i, fid in enumerate(fig_sorted):
        a = math.pi / 2 + (i / len(fig_sorted)) * 2 * math.pi
        fig_xy[fid] = (round(CX + 268 * math.cos(a), 1),
                       round(CY + 268 * 0.90 * math.sin(a), 1))

    nodes = [{"id": "aster", "kind": "artist", "name": "Aster da Master",
              "page": "index.html", "x": CX, "y": CY, "r": 34,
              "blurb": "The speaker of every family"}]
    for f in families:
        fid = "fam-" + f["slug"]
        nodes.append({"id": fid, "kind": "family", "name": f["name"],
                      "page": f["page"], "x": fam_xy[fid][0],
                      "y": fam_xy[fid][1],
                      "r": round(13 + (f["track_count"] / max_t) * 19, 1),
                      "blurb": "%d transmissions, %s plays"
                      % (f["track_count"], f"{f['total_plays']:,}")})
    for fid in fig_sorted:
        fd = figure_defs[fid]
        nodes.append({"id": fid, "kind": fd["kind"], "name": fd["name"],
                      "page": fd["page"], "x": fig_xy[fid][0],
                      "y": fig_xy[fid][1],
                      "r": round(8 + (len(fd["links"]) / max_nf) * 9, 1),
                      "blurb": "%s in %d %s" % (
                          {"collaborator": "Title-credited",
                           "producer": "Production credit",
                           "both": "Voice + production"}[fd["kind"]],
                          len(fd["links"]),
                          "family" if len(fd["links"]) == 1 else "families")})

    return {"nodes": nodes, "edges": edges, "family_overlap": overlap,
            "degrees": degrees, "insights": insights, "adj": adj}


# --- real-data assembly ---

# --- real-data assembly ---

# pinned producer-parse spot checks against real titles (drift guards)
assert parse_producers("Soul Shaking (prod. Fish Narc)") == ["Fish Narc"]
assert parse_producers(
    "3 Points Pre Game prod. doublemulti x pinkcat #NITEMODE") == \
    ["doublemulti", "pinkcat"]
assert parse_producers("nitemode2019 w/ Max+Vetty prod. NaXi.wav") == ["NaXi"]
assert parse_producers("big litemode (prod runawway, ilyagargod & k3nik)") == \
    ["runawway", "ilyagargod", "k3nik"]
assert parse_producers("the peace of the spirit urn (prod +fiftyzeros)") == \
    ["fiftyzeros"]
assert parse_producers("P1aced a Ward (prodbygus)") == ["bygus"]
assert parse_producers("For Brian (Neck Deep) outro [produced by AWFL]") == \
    ["AWFL"]
assert parse_producers("Lucid Boi (prod. $ T.N.C $)") == ["T.N.C"]
assert parse_producers("NIGHT MODE ft. MAX FERRARI x YUNG VETTA x JAX") == []
assert parse_producers("master key ft. Lil Wintr x Marcelo (prod. ginseng)") \
    == ["ginseng"]

assert len(CF) == 16, f"codex family count drift: {len(CF)}"

families = [{"slug": f["slug"], "name": f["name"], "page": f["page"],
             "track_count": f["track_count"],
             "total_plays": f["total_plays"],
             "words": f["words"],
             "decoded_status": f["decoded"]["status"]}
            for f in CF]
for f in families:
    assert (ROOT / f["page"]).exists(), f"missing family page {f['page']}"
    assert f["track_count"] == len(
        [t for t in CF if t["slug"] == f["slug"]][0]["transmissions"])

# circle name -> (slug, page) for page resolution
CIRCLE_BY_NAME = {c["name"].lower(): (slug, c["page"])
                  for slug, c in CIRCLE.items()}

# scene-figure record for Fish Narc (producer credit on "Soul Shaking").
# Rotation 22: the circle's per-person pages folded into the index;
# the record lives at the fold anchor.
FISH_NARC_PAGE = "circle/index.html#c-fish-narc"
assert (ROOT / FISH_NARC_PAGE.split("#")[0]).exists(), "missing fish-narc page"

# figure_defs: {fig_id: {name, kind, page, links: {fam_slug: [titles]}}}
figure_defs = {}
collab_slugs = set()  # circle slugs title-credited on family tracks


def ensure_figure(fig_id, name, kind, page):
    if fig_id not in figure_defs:
        if page is not None:
            assert (ROOT / page.split("#")[0]).exists(), f"missing figure page {page}"
        figure_defs[fig_id] = {"name": name, "kind": kind, "page": page,
                               "links": defaultdict(list)}
    return figure_defs[fig_id]


for f in CF:
    slug = f["slug"]
    # title-credited collaborators (canonical, from codex-families.json)
    for c in f["collaborators"]:
        collab_slugs.add(c["slug"])
        fd = ensure_figure("fig-" + c["slug"], c["name"], "collaborator",
                           c["page"])
        # re-derive the shared titles from circle.json (same rule as
        # build_codex_pages.family_collaborators)
        circ = CIRCLE[c["slug"]]
        fam_keys = {(t["title"], t.get("date")) for t in f["transmissions"]}
        titles = sorted(t["title"] for t in circ["tracks"]
                        if (t["title"], t.get("date")) in fam_keys)
        assert len(titles) == c["transmissions"], \
            f"{c['slug']} title drift in {slug}"
        fd["links"][slug] = titles
    # producer credits parsed from the family's own transmission titles
    prod_titles = defaultdict(list)  # display name -> [titles]
    prod_seen = {}  # normalized -> display name (first-seen spelling)
    for t in f["transmissions"]:
        for p in parse_producers(t["title"]):
            key = p.lower()
            if key not in prod_seen:
                prod_seen[key] = p
            prod_titles[prod_seen[key]].append(t["title"])
    for disp, titles in prod_titles.items():
        titles = sorted(set(titles))
        low = disp.lower()
        if low == "fish narc":
            fig_id, page = "fig-fish-narc", FISH_NARC_PAGE
        elif low in CIRCLE_BY_NAME:
            cslug, page = CIRCLE_BY_NAME[low]
            fig_id = "fig-" + cslug
        else:
            fig_id, page = fig_id_for(disp), None
        fd = ensure_figure(fig_id, disp, "producer", page)
        if fd["links"][slug]:
            # same producer credited twice on one title edge case guard
            merged = sorted(set(fd["links"][slug]) | set(titles))
            fd["links"][slug] = merged
        else:
            fd["links"][slug] = titles

# kind resolution: a figure can be both a title-credited collaborator
# and a producer inside the codex (e.g. Keyblayde808 on "White Noise")
_prod_ids = set()
for f in CF:
    for t in f["transmissions"]:
        for p in parse_producers(t["title"]):
            low = p.lower()
            if low == "fish narc":
                _prod_ids.add("fig-fish-narc")
            elif low in CIRCLE_BY_NAME:
                _prod_ids.add("fig-" + CIRCLE_BY_NAME[low][0])
            else:
                _prod_ids.add(fig_id_for(p))
for fig_id, fd in figure_defs.items():
    in_collab = fig_id in {"fig-" + s for s in collab_slugs}
    in_prod = fig_id in _prod_ids
    fd["kind"] = ("both" if (in_collab and in_prod)
                  else "collaborator" if in_collab else "producer")

for fd in figure_defs.values():
    fd["links"] = {k: sorted(set(v)) for k, v in fd["links"].items()}

# co-credit figure-figure edges from network.json (title co-occurrence;
# both endpoints must be figures in this graph)
co_credit = []
for e in NET["edges"]:
    if e["kind"] != "co-credit":
        continue
    a, b = "fig-" + e["a"], "fig-" + e["b"]
    if a in figure_defs and b in figure_defs:
        co_credit.append((a, b, e["shared_tracks"]))
assert len(co_credit) == 5, f"co-credit edge drift: {len(co_credit)}"

g = build_graph(families, figure_defs, co_credit)

# --- drift-guard assertions ---
node_ids = {n["id"] for n in g["nodes"]}
assert len(g["nodes"]) == g["insights"]["node_count"]
assert node_ids == ({"aster"} | {"fam-" + f["slug"] for f in families}
                    | set(figure_defs))
for e in g["edges"]:
    assert e["a"] in node_ids and e["b"] in node_ids, e
    assert e["weight"] >= 1, e
    if e["kind"] != "aster-family":
        assert e["weight"] == len(e["titles"]), e
assert len([e for e in g["edges"] if e["kind"] == "aster-family"]) == 16
assert len([e for e in g["edges"] if e["kind"] == "co-credit"]) == 5
for o in g["family_overlap"]:
    assert o["weight"] == len(o["shared_figures"]) >= 1, o
# structural property of the codex graph: Aster speaks every family
# directly, so every family is 1 degree out and every figure is 2
# (via the family/families that carry them) -- computed by BFS, asserted
for d in g["degrees"]:
    if d["kind"] == "family":
        assert d["degrees"] == 1, d
    else:
        assert d["degrees"] == 2, d
        assert d["via"], d
ins = g["insights"]
assert ins["most_connected_family"]["figure_count"] == max(
    sum(1 for fd in figure_defs.values() if f["slug"] in fd["links"])
    for f in families)
assert ins["most_connected_figure"]["family_count"] == max(
    len(fd["links"]) for fd in figure_defs.values())
assert ins["isolated_families"] == sorted(ins["isolated_families"])
for s in ins["isolated_families"]:
    assert not any(o["a_slug"] == s or o["b_slug"] == s
                   for o in g["family_overlap"]), s
# spot-check the headline facts the page will render
assert ins["family_count"] == 16
assert g["degrees"][0]["degrees"] == 1  # sorted: families first

# --- payload ---

METHOD = (
    "The codex relationship graph, computed from real archive data. Nodes: "
    "Aster da Master (the speaker of every family), the 16 codex families "
    "(data/v1/codex-families.json), and every figure named on family "
    "transmissions. Collaborator figures follow the circle's title-credit "
    "rule: parsed from w//ft./feat. fragments in titles, as credited "
    "verbatim (build_years.parse_collabs). Producer figures are parsed "
    "from the titles' own prod./produced-by fragments (as credited, "
    "verbatim; multi-producer credits split on x / & / + / comma). Edges: "
    "aster-family (Aster speaks every word in the family), family-figure "
    "(weight = shared transmissions), figure-figure co-credit from "
    "data/v1/network.json title co-occurrences. Degrees of separation are "
    "BFS distances from Aster on this graph: every family is 1 degree "
    "(Aster speaks every family directly), every figure is 2 degrees (via "
    "the family or families that carry them). The pathfinder's codex-only "
    "mode excludes the Aster hub, so figures in families that share no "
    "voices honestly report no path. Play counts are the single "
    "2026-10-11 snapshot; upload dates are not recording dates. Titles "
    "and metadata only -- never lyrics, never invented bio facts."
)

doc = {
    "version": NEW_VERSION,
    "generated": SNAPSHOT,
    "plays_snapshot": SNAPSHOT,
    "method": METHOD,
    "artist": {"id": "aster", "name": "Aster da Master",
               "page": "index.html"},
    "families": [
        {"id": "fam-" + f["slug"], "slug": f["slug"], "name": f["name"],
         "page": f["page"], "track_count": f["track_count"],
         "total_plays": f["total_plays"], "words": f["words"],
         "decoded_status": f["decoded_status"]}
        for f in families
    ],
    "figures": [
        {"id": fid,
         "name": figure_defs[fid]["name"],
         "kind": figure_defs[fid]["kind"],
         "page": figure_defs[fid]["page"],
         "family_count": len(figure_defs[fid]["links"]),
         "families": [
             {"family_id": "fam-" + s,
              "family_slug": s,
              "family_name": next(f["name"] for f in families
                                  if f["slug"] == s),
              "family_page": next(f["page"] for f in families
                                   if f["slug"] == s),
              "transmissions": len(titles),
              "titles": titles}
             for s, titles in sorted(figure_defs[fid]["links"].items())]}
        for fid in sorted(figure_defs,
                          key=lambda x: figure_defs[x]["name"].lower())
    ],
    "nodes": g["nodes"],
    "edges": g["edges"],
    "family_overlap": g["family_overlap"],
    "degrees": g["degrees"],
    "insights": g["insights"],
}

SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "codex-network",
    "description": ("Codex relationship graph: the 16 word families as "
                    "nodes, shared collaborators/producers as edges, BFS "
                    "degrees of separation from Aster, the family-overlap "
                    "graph, and the connect-the-dots shortest-path data."),
    "type": "object",
    "required": ["version", "generated", "plays_snapshot", "method",
                 "artist", "families", "figures", "nodes", "edges",
                 "family_overlap", "degrees", "insights"],
    "properties": {
        "version": {"type": "string"},
        "generated": {"type": "string"},
        "plays_snapshot": {"type": "string"},
        "method": {"type": "string"},
        "artist": {
            "type": "object",
            "required": ["id", "name", "page"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "page": {"type": "string"},
            },
        },
        "families": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "slug", "name", "page", "track_count",
                             "total_plays", "words", "decoded_status"],
                "properties": {
                    "id": {"type": "string"},
                    "slug": {"type": "string"},
                    "name": {"type": "string"},
                    "page": {"type": "string"},
                    "track_count": {"type": "integer", "minimum": 1},
                    "total_plays": {"type": "integer", "minimum": 0},
                    "words": {"type": "array", "items": {"type": "string"}},
                    "decoded_status": {"enum": ["stated", "unknown"]},
                },
            },
        },
        "figures": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "kind", "page", "family_count",
                             "families"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "kind": {"enum": ["collaborator", "producer", "both"]},
                    "page": {"type": ["string", "null"]},
                    "family_count": {"type": "integer", "minimum": 1},
                    "families": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["family_id", "family_slug",
                                         "family_name", "family_page",
                                         "transmissions", "titles"],
                            "properties": {
                                "family_id": {"type": "string"},
                                "family_slug": {"type": "string"},
                                "family_name": {"type": "string"},
                                "family_page": {"type": "string"},
                                "transmissions": {"type": "integer",
                                                 "minimum": 1},
                                "titles": {"type": "array",
                                           "items": {"type": "string"}},
                            },
                        },
                    },
                },
            },
        },
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "kind", "name", "page", "x", "y", "r",
                             "blurb"],
                "properties": {
                    "id": {"type": "string"},
                    "kind": {"enum": ["artist", "family", "collaborator",
                                      "producer", "both"]},
                    "name": {"type": "string"},
                    "page": {"type": ["string", "null"]},
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "r": {"type": "number"},
                    "blurb": {"type": "string"},
                },
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["a", "b", "weight", "kind", "label", "titles"],
                "properties": {
                    "a": {"type": "string"},
                    "b": {"type": "string"},
                    "weight": {"type": "integer", "minimum": 1},
                    "kind": {"enum": ["aster-family", "family-figure",
                                      "co-credit"]},
                    "label": {"type": "string"},
                    "titles": {"type": "array",
                               "items": {"type": "string"}},
                },
            },
        },
        "family_overlap": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["a_id", "b_id", "a_slug", "b_slug", "a_name",
                             "b_name", "a_page", "b_page", "weight",
                             "shared_figures"],
                "properties": {
                    "a_id": {"type": "string"},
                    "b_id": {"type": "string"},
                    "a_slug": {"type": "string"},
                    "b_slug": {"type": "string"},
                    "a_name": {"type": "string"},
                    "b_name": {"type": "string"},
                    "a_page": {"type": "string"},
                    "b_page": {"type": "string"},
                    "weight": {"type": "integer", "minimum": 1},
                    "shared_figures": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["id", "name", "kind"],
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "kind": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
        "degrees": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "kind", "degrees", "via"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "kind": {"type": "string"},
                    "degrees": {"type": "integer", "minimum": 1},
                    "via": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "insights": {
            "type": "object",
            "required": ["most_connected_family", "most_connected_figure",
                         "largest_bridge", "isolated_families",
                         "family_count", "figure_count",
                         "collaborator_figures", "producer_figures",
                         "overlap_pairs", "node_count", "edge_count"],
            "properties": {
                "most_connected_family": {"type": "object"},
                "most_connected_figure": {"type": "object"},
                "largest_bridge": {"type": ["object", "null"]},
                "isolated_families": {"type": "array",
                                      "items": {"type": "string"}},
                "family_count": {"type": "integer"},
                "figure_count": {"type": "integer"},
                "collaborator_figures": {"type": "integer"},
                "producer_figures": {"type": "integer"},
                "overlap_pairs": {"type": "integer"},
                "node_count": {"type": "integer"},
                "edge_count": {"type": "integer"},
            },
        },
    },
}

(API / "codex-network.json").write_text(
    json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
(API / "schema" / "codex-network.json").write_text(
    json.dumps(SCHEMA, indent=2) + "\n", encoding="utf-8")

# register the endpoint (same convention as the other generators)
idx_p = API / "index.json"
idx = json.loads(idx_p.read_text())
idx["version"] = NEW_VERSION
render_manifest(idx, ROOT)

print(f"codex-network.json: {ins['node_count']} nodes, "
      f"{ins['edge_count']} edges ({ins['overlap_pairs']} family-overlap "
      f"pairs); most-connected family {ins['most_connected_family']['name']} "
      f"x{ins['most_connected_family']['figure_count']} figures; "
      f"most-connected figure {ins['most_connected_figure']['name']} "
      f"x{ins['most_connected_figure']['family_count']} families; "
      f"isolated families: {', '.join(ins['isolated_families']) or 'none'}")
