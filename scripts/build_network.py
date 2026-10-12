#!/usr/bin/env python3
"""build_network.py — collaboration network graph, wave 16.

Computes the whole collab universe from REAL data into api/v1/network.json:
  - nodes: the artist (center) -> 21 title-credited collaborators from
    api/v1/circle.json -> producer scene figures from api/v1/scene-figures.json
  - edges: artist <-> every node (weight = shared tracks);
    collaborator <-> collaborator edges from title co-occurrence (two circle
    entries sharing the same track title, e.g. "NIGHT MODE ft. MAX FERRARI x
    YUNG VETTA x JAX"); producer <-> collaborator edges from track-title
    overlap with scene-figure track lists (none on record — recorded, not invented)
  - deterministic server-side layout (concentric rings, stable x/y) so every
    re-run is byte-identical; the client only adds drag on top of it
  - insights: most frequent collaborator, producer with most credits,
    year with most collabs, first-ever collaborator — all asserted

Every edge comes from title-credit data. No invented bio facts.
Runs LAST in the validate.sh generator chain (after build_transmission).
"""
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "api" / "v1"
NEW_VERSION = "0.14.0"
SNAPSHOT = "2026-10-11"

W, H, CX, CY = 920, 640, 460, 320

SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "network",
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "generated": {"type": "string"},
        "artist": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
            "required": ["id", "name"],
        },
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "kind": {"enum": ["artist", "collaborator", "producer"]},
                    "track_count": {"type": "integer", "minimum": 0},
                    "first_date": {"type": ["string", "null"]},
                    "last_date": {"type": ["string", "null"]},
                    "page": {"type": "string"},
                    "tracks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "date": {"type": ["string", "null"]},
                                "plays": {"type": ["integer", "null"]},
                            },
                            "required": ["title"],
                        },
                    },
                    "years": {"type": "array", "items": {"type": "integer"}},
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "r": {"type": "number"},
                },
                "required": ["id", "name", "kind", "track_count", "page",
                             "tracks", "years", "x", "y", "r"],
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "a": {"type": "string"},
                    "b": {"type": "string"},
                    "weight": {"type": "integer", "minimum": 1},
                    "kind": {"enum": ["artist", "co-credit"]},
                    "shared_tracks": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["a", "b", "weight", "kind"],
            },
        },
        "insights": {
            "type": "object",
            "properties": {
                "most_frequent_collaborator": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "track_count": {"type": "integer"},
                    },
                    "required": ["name", "track_count"],
                },
                "producer_most_credits": {
                    "type": ["object", "null"],
                    "properties": {
                        "name": {"type": "string"},
                        "track_count": {"type": "integer"},
                    },
                    "required": ["name", "track_count"],
                },
                "year_most_collabs": {
                    "type": "object",
                    "properties": {
                        "year": {"type": "integer"},
                        "collab_tracks": {"type": "integer"},
                    },
                    "required": ["year", "collab_tracks"],
                },
                "first_ever_collaborator": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "date": {"type": "string"},
                        "title": {"type": "string"},
                    },
                    "required": ["name", "date", "title"],
                },
            },
            "required": ["most_frequent_collaborator", "producer_most_credits",
                         "year_most_collabs", "first_ever_collaborator"],
        },
    },
    "required": ["version", "generated", "artist", "nodes", "edges", "insights"],
}


def main():
    circle = json.loads((API / "circle.json").read_text())
    figures = json.loads((API / "scene-figures.json").read_text())

    nodes = []
    title_to_nodes = defaultdict(list)   # normalized title -> [node ids]
    tracks_seen = {}                     # normalized title -> representative track dict

    def norm_title(t):
        return " ".join(t.split()).lower()

    # --- artist (center) ---
    artist = {"id": "aster", "name": "Aster da Master"}

    # --- collaborators from circle.json ---
    for slug in sorted(circle):
        c = circle[slug]
        tracks = sorted(c["tracks"], key=lambda t: t.get("date") or "")
        dates = sorted(t.get("date") for t in tracks if t.get("date"))
        years = sorted({int(d[:4]) for d in dates})
        node = {
            "id": slug, "name": c["name"], "kind": "collaborator",
            "track_count": len(tracks),
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
            "page": c["page"],
            "tracks": [
                {"title": t["title"], "date": t.get("date"), "plays": t.get("plays")}
                for t in tracks
            ],
            "years": years,
        }
        assert node["track_count"] == c["shared_transmissions"], slug
        nodes.append(node)
        for t in tracks:
            nt = norm_title(t["title"])
            title_to_nodes[nt].append(slug)
            tracks_seen.setdefault(nt, t["title"])

    # --- producers from scene-figures.json ---
    for slug in sorted(figures):
        f = figures[slug]
        tracks = sorted(f["tracks"], key=lambda t: t.get("date") or "")
        dates = sorted(t.get("date") for t in tracks if t.get("date"))
        years = sorted({int(d[:4]) for d in dates})
        node = {
            "id": slug, "name": f["name"], "kind": "producer",
            "track_count": len(tracks),
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
            "page": f["page"],
            "tracks": [
                {"title": t["title"], "date": t.get("date"), "plays": t.get("plays")}
                for t in tracks
            ],
            "years": years,
        }
        nodes.append(node)
        for t in tracks:
            nt = norm_title(t["title"])
            title_to_nodes[nt].append(slug)
            tracks_seen.setdefault(nt, t["title"])

    by_id = {n["id"]: n for n in nodes}

    # --- edges ---
    edges = []
    # artist <-> every node, weight = shared track count
    for n in nodes:
        edges.append({"a": "aster", "b": n["id"], "weight": n["track_count"],
                      "kind": "artist"})
    # node <-> node co-credit edges from shared track titles
    pair_titles = defaultdict(list)
    for nt, ids in sorted(title_to_nodes.items()):
        uniq = sorted(set(ids))
        if len(uniq) < 2:
            continue
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                pair_titles[(uniq[i], uniq[j])].append(tracks_seen[nt])
    for (a, b), titles in sorted(pair_titles.items()):
        edges.append({"a": a, "b": b, "weight": len(titles), "kind": "co-credit",
                      "shared_tracks": sorted(titles)})

    # --- insights (all computed, then asserted) ---
    collabs = [n for n in nodes if n["kind"] == "collaborator"]
    prods = [n for n in nodes if n["kind"] == "producer"]
    assert collabs and len(collabs) == len(circle)

    most = max(collabs, key=lambda n: (n["track_count"], n["first_date"] or ""))
    assert most["track_count"] == max(n["track_count"] for n in collabs)

    pm = max(prods, key=lambda n: n["track_count"]) if prods else None
    producer_insight = ({"name": pm["name"], "track_count": pm["track_count"]}
                        if pm else None)

    year_counts = defaultdict(int)
    seen_titles = set()
    for n in nodes:
        for t in n["tracks"]:
            nt = norm_title(t["title"])
            if nt in seen_titles or not t.get("date"):
                continue
            seen_titles.add(nt)
            year_counts[int(t["date"][:4])] += 1
    busiest_year = max(sorted(year_counts), key=lambda y: year_counts[y])
    assert year_counts[busiest_year] == max(year_counts.values())

    first_tracks = [(t["date"], c["name"], t["title"])
                    for c in collabs for t in c["tracks"] if t.get("date")]
    first_date, first_name, first_title = min(first_tracks)
    assert first_date == min(d for d, _, _ in first_tracks)

    insights = {
        "most_frequent_collaborator": {"name": most["name"],
                                       "track_count": most["track_count"]},
        "producer_most_credits": producer_insight,
        "year_most_collabs": {"year": busiest_year,
                              "collab_tracks": year_counts[busiest_year]},
        "first_ever_collaborator": {"name": first_name, "date": first_date,
                                    "title": first_title},
    }

    # --- deterministic layout: rings by track count ---
    collabs_sorted = sorted(collabs, key=lambda n: (-n["track_count"], n["name"]))
    maxc = max(n["track_count"] for n in collabs_sorted)

    def place_ring(ns, radius, y_stretch=1.0):
        for i, n in enumerate(ns):
            a = -math.pi / 2 + (i / len(ns)) * 2 * math.pi
            n["x"] = round(CX + radius * math.cos(a), 1)
            n["y"] = round(CY + radius * y_stretch * math.sin(a), 1)

    inner = collabs_sorted[:8]
    outer = collabs_sorted[8:]
    place_ring(inner, 150)
    place_ring(outer, 240, 0.92)
    for i, p in enumerate(sorted(prods, key=lambda n: n["name"])):
        a = math.pi / 2 + (i / max(len(prods), 1)) * 2 * math.pi
        p["x"] = round(CX + 330 * math.cos(a), 1)
        p["y"] = round(CY + 255 * math.sin(a), 1)

    artist_node = {
        "id": "aster", "name": "Aster da Master", "kind": "artist",
        "track_count": len(seen_titles),
        "first_date": None, "last_date": None, "page": "index.html",
        "tracks": [], "years": sorted(year_counts),
        "x": CX, "y": CY, "r": 40,
    }
    for n in collabs_sorted:
        n["r"] = round(12 + (n["track_count"] / maxc) * 22, 1)
    for n in prods:
        n["r"] = round(12 + (n["track_count"] / maxc) * 22, 1)

    all_nodes = [artist_node] + collabs_sorted + sorted(
        prods, key=lambda n: n["name"])
    ids = {n["id"] for n in all_nodes}
    for e in edges:
        assert e["a"] in ids and e["b"] in ids, e
    artist_edges = [e for e in edges if e["kind"] == "artist"]
    assert len(artist_edges) == len(nodes)
    for e in artist_edges:
        assert e["weight"] == by_id[e["b"]]["track_count"]
    for e in edges:
        if e["kind"] == "co-credit":
            assert e["weight"] == len(e["shared_tracks"]) >= 1

    doc = {
        "version": NEW_VERSION,
        "generated": SNAPSHOT,
        "artist": artist,
        "nodes": all_nodes,
        "edges": edges,
        "insights": insights,
    }

    (API / "network.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (API / "schema" / "network.json").write_text(
        json.dumps(SCHEMA, indent=2) + "\n", encoding="utf-8")

    # register the endpoint (same convention as build_circle.py)
    idx_p = API / "index.json"
    idx = json.loads(idx_p.read_text())
    idx["version"] = NEW_VERSION
    from api_manifest import render_manifest
    render_manifest(idx, ROOT)

    co = len([e for e in edges if e["kind"] == "co-credit"])
    print(f"network.json: {len(all_nodes)} nodes, {len(edges)} edges "
          f"({co} co-credit); insights: {insights['most_frequent_collaborator']['name']} "
          f"x{insights['most_frequent_collaborator']['track_count']}, "
          f"busiest year {insights['year_most_collabs']['year']}, "
          f"first {insights['first_ever_collaborator']['name']} "
          f"({insights['first_ever_collaborator']['date']})")


if __name__ == "__main__":
    raise SystemExit(main())
