#!/usr/bin/env python3
"""Pinned-fixture tests for the codex-network pure logic
(scripts/build_codex_network.py): producer parsing, graph assembly,
family overlap, BFS degrees, shortest-path.

Run: python3 scripts/test_codex_network.py  (exit 0 = all pass)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from build_codex_network import (  # noqa: E402
    bfs_distances,
    build_graph,
    fig_id_for,
    parse_producers,
    shortest_path,
)

PASS, FAIL = 0, 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


# --- parse_producers: pinned fixtures ---
check("plain prod.", parse_producers("Soul Shaking (prod. Fish Narc)")
      == ["Fish Narc"])
check("x-split + hashtag",
      parse_producers("3 Points Pre Game prod. doublemulti x pinkcat #NITEMODE")
      == ["doublemulti", "pinkcat"])
check("extension strip",
      parse_producers("nitemode2019 w/ Max+Vetty prod. NaXi.wav") == ["NaXi"])
check("comma/amp split",
      parse_producers("big litemode (prod runawway, ilyagargod & k3nik)")
      == ["runawway", "ilyagargod", "k3nik"])
check("leading plus", parse_producers("(prod +fiftyzeros)") == ["fiftyzeros"])
check("prodby glued", parse_producers("P1aced a Ward (prodbygus)") == ["bygus"])
check("produced by",
      parse_producers("For Brian (Neck Deep) outro [produced by AWFL]")
      == ["AWFL"])
check("decorative dollars",
      parse_producers("Lucid Boi (prod. $ T.N.C $)") == ["T.N.C"])
check("no prod fragment",
      parse_producers("NIGHT MODE ft. MAX FERRARI x YUNG VETTA x JAX") == [])
check("multiword producer kept whole",
      parse_producers("Soul Shines ~ [prod Josh the Samurai]")
      == ["Josh the Samurai"])
check("dedupe case-insensitive",
      parse_producers("X (prod. DIX2) [prod. dix2]") == ["DIX2"])
check("and-split", parse_producers("Y (prod. a and b)") == ["a", "b"])

# --- fig ids ---
check("fig id slug", fig_id_for("Josh the Samurai") == "fig-p-josh-the-samurai")
check("fig id dots", fig_id_for("T.N.C") == "fig-p-t-n-c")

# --- tiny pinned graph: 3 families, 4 figures ---
# fam-a: fig-x (collab), fig-p1 (producer)
# fam-b: fig-x (collab), fig-y (collab)
# fam-c: fig-z (producer) -- isolated in the overlap graph
FAMS = [
    {"slug": "a", "name": "Fam A", "page": "codex/a.html",
     "track_count": 4, "total_plays": 400, "words": ["w1"],
     "decoded_status": "stated"},
    {"slug": "b", "name": "Fam B", "page": "codex/b.html",
     "track_count": 2, "total_plays": 100, "words": ["w2"],
     "decoded_status": "unknown"},
    {"slug": "c", "name": "Fam C", "page": "codex/c.html",
     "track_count": 1, "total_plays": 50, "words": ["w3"],
     "decoded_status": "stated"},
]
FIGS = {
    "fig-x": {"name": "Fig X", "kind": "collaborator", "page": "circle/x.html",
              "links": {"a": ["T1", "T2"], "b": ["T3"]}},
    "fig-y": {"name": "Fig Y", "kind": "collaborator", "page": "circle/y.html",
              "links": {"b": ["T3"]}},
    "fig-p-p1": {"name": "P1", "kind": "producer", "page": None,
                 "links": {"a": ["T1"]}},
    "fig-p-pz": {"name": "Pz", "kind": "producer", "page": None,
                 "links": {"c": ["T9"]}},
}
CO = [("fig-x", "fig-y", ["T3"])]  # co-credit edge

g = build_graph(FAMS, FIGS, CO)

# nodes: 1 aster + 3 families + 4 figures
check("node count", len(g["nodes"]) == 8)
check("node ids",
      {n["id"] for n in g["nodes"]}
      == {"aster", "fam-a", "fam-b", "fam-c",
          "fig-x", "fig-y", "fig-p-p1", "fig-p-pz"})
# edges: 3 aster-family + 5 family-figure + 1 co-credit
check("edge count", len(g["edges"]) == 9)
check("aster-family edges",
      len([e for e in g["edges"] if e["kind"] == "aster-family"]) == 3)
check("co-credit kept", any(e["kind"] == "co-credit" for e in g["edges"]))
check("edge weight = titles",
      all(e["weight"] == len(e["titles"]) or e["kind"] == "aster-family"
          for e in g["edges"]))

# family overlap: only a<->b via fig-x
check("one overlap pair", len(g["family_overlap"]) == 1)
o = g["family_overlap"][0]
check("overlap pair ids", (o["a_id"], o["b_id"]) == ("fam-a", "fam-b"))
check("overlap weight 1", o["weight"] == 1)
check("overlap shared fig",
      o["shared_figures"] == [{"id": "fig-x", "name": "Fig X",
                               "kind": "collaborator"}])

# degrees: families 1, figures 2
deg = {d["id"]: d["degrees"] for d in g["degrees"]}
check("fam degrees 1",
      deg["fam-a"] == deg["fam-b"] == deg["fam-c"] == 1)
check("fig degrees 2",
      deg["fig-x"] == deg["fig-y"] == deg["fig-p-p1"] == deg["fig-p-pz"] == 2)
check("via families",
      next(d["via"] for d in g["degrees"] if d["id"] == "fig-x")
      == ["fam-a", "fam-b"])

# insights
ins = g["insights"]
check("most-connected family",
      ins["most_connected_family"]["slug"] == "a"
      and ins["most_connected_family"]["figure_count"] == 2)
check("most-connected figure",
      ins["most_connected_figure"]["id"] == "fig-x"
      and ins["most_connected_figure"]["family_count"] == 2)
check("isolated", ins["isolated_families"] == ["c"])
check("largest bridge",
      ins["largest_bridge"]["a_slug"] == "a"
      and ins["largest_bridge"]["weight"] == 1)
check("counts", ins["node_count"] == 8 and ins["edge_count"] == 9
      and ins["figure_count"] == 4 and ins["overlap_pairs"] == 1)

# --- BFS / shortest path on the raw adjacency ---
adj = g["adj"]
check("bfs distances",
      bfs_distances(adj, "aster")["fig-p-pz"] == 2)
check("path direct", shortest_path(adj, "aster", "fam-a") == ["aster", "fam-a"])
check("path via family",
      shortest_path(adj, "fig-p-p1", "fig-y")
      == ["fig-p-p1", "fam-a", "fig-x", "fig-y"])
check("path via aster",
      shortest_path(adj, "fig-p-pz", "fig-y")
      == ["fig-p-pz", "fam-c", "aster", "fam-b", "fig-y"])
check("codex-only no path",
      shortest_path(adj, "fig-p-pz", "fig-y", forbid={"aster"}) is None)
check("codex-only path survives",
      shortest_path(adj, "fig-p-p1", "fig-y", forbid={"aster"})
      == ["fig-p-p1", "fam-a", "fig-x", "fig-y"])
check("self path", shortest_path(adj, "fam-a", "fam-a") == ["fam-a"])
check("unreachable",
      shortest_path({"x": set()}, "x", "y") is None)

# --- layout determinism: rebuild, compare coordinates ---
g2 = build_graph(FAMS, FIGS, CO)
check("layout stable",
      [(n["id"], n["x"], n["y"], n["r"]) for n in g["nodes"]]
      == [(n["id"], n["x"], n["y"], n["r"]) for n in g2["nodes"]])

print(f"test_codex_network: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
