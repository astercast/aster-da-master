---
name: codex-pathfinder
description: Trace the shortest connection between any two figures (or a family and a figure) through the codex relationship graph — shared collaborators/producers as edges, BFS degrees of separation from Aster, family-overlap pairs — from codex-network.json (drives codex-network.html's connect-the-dots pathfinder).
---

# Connect the dots in the codex

## Use when

An agent (or a human) wants to answer "how is X connected to Y?" inside the
codex — the shortest path between any two figures, between a family and a
figure, or a figure's degrees of separation from Aster — or to list which
families share voices. Feeds the `codex-network.html` graph / pathfinder /
degrees-table sections.

## Inputs

- `api/v1/codex-network.json` — endpoint #21:
  - `families[]` — the 16 families (id `fam-<slug>`, name, page, track
    count, plays, words, `decoded_status`)
  - `figures[]` — every figure named on family transmissions: id
    (`fig-<circle-slug>` for title-credited collaborators, `fig-p-<name>`
    for producers, `fig-fish-narc` for Fish Narc), name, `kind`
    (`collaborator` / `producer` / `both`), `page` (circle page or null),
    `family_count`, and `families[]` (the carrying families with
    transmission counts and titles)
  - `nodes[]` / `edges[]` — the rendered graph (deterministic server-side
    ring layout): `aster-family` edges (Aster speaks every word in the
    family), `family-figure` edges (weight = shared transmissions, with
    `label` + `titles`), `co-credit` figure–figure edges from
    `network.json` title co-occurrences
  - `family_overlap[]` — the 16 families as nodes, shared figures as
    edges (`weight` = shared-figure count), sorted by weight desc
  - `degrees[]` — BFS distance from Aster for every node, with `via`
    (the carrying families for each figure)
  - `insights` — most-connected family / figure, largest bridge,
    isolated families, counts
- Method notes: read `method` first. Collaborator figures follow the
  circle's title-credit rule (parsed from w//ft./feat. fragments, as
  credited verbatim); producer figures are parsed from the titles' own
  prod./produced-by fragments (as credited, verbatim). Degrees are BFS
  distances **on this graph** — not a social claim.

## Procedure

1. Fetch `api/v1/codex-network.json`. Read `method` first.
2. For "how is X connected to Y": run BFS over `edges[]` (undirected)
   from X's node id to Y's node id. Report each hop with the edge's
   `label` (e.g. "JAX × 2 in The Modes"). The archive route may pass
   through Aster (he speaks every family); the codex-only route forbids
   the Aster node.
3. For "degrees of separation from Aster": read `degrees[]` — every
   family is 1 degree, every figure is 2 degrees via the listed carrying
   families. Quote the `via` families; the number alone is not the story.
4. For "which families share voices": read `family_overlap[]` — pairs
   with `weight` and `shared_figures[]`. Four families are isolates
   (`insights.isolated_families`): keys, lucid-states, the-cold, the-pack.
5. Cross-link out: family deep dives (`codex/<slug>.html`), circle pages
   (`figures[].page` where set), `network.html` (the full collaboration
   graph), `transmission.html#chapter-codex` (the journey's Codex chapter),
   `milestone-race.html`.

## Worked example

"Connect JAX to the producer runawway — and is there a codex-only route
from capoxxo to Lil Wintr?"

- `GET api/v1/codex-network.json` → `fig-jax` (collaborator; families:
  the-modes, dark, journeys), `fig-p-runawway` (producer; family:
  the-modes — "big litemode (prod runawway, ilyagargod & k3nik)").
- Shortest path (through the archive): JAX → The Modes ("JAX × 2 in
  The Modes") → runawway ("runawway × 1 in The Modes"). 2 steps.
- capoxxo → Lil Wintr, codex-only: no path found — the-cold shares no
  voices with any other family (isolated), and keys is isolated too. The
  archive reports the gap; it doesn't fill it. Through the archive the
  route exists via Aster (capoxxo → the-cold → Aster → keys → Lil Wintr,
  4 steps).

## API references

- `api/v1/codex-network.json` — the codex relationship graph: 16 family
  nodes, 53 figure nodes, family-overlap pairs, BFS degrees, insights
  (endpoint #21; drives `codex-network.html`)
- `api/v1/codex-families.json` — family deep dives behind the family
  pages (endpoint #18)
- `api/v1/network.json` — the full collaboration graph; source of the
  co-credit edges (endpoint #15)
- `api/v1/circle.json` — the 21 title-credited collaborators (endpoint #7)

## Pitfalls

- **Degrees are graph distances, not social claims.** Every figure is 2
  degrees from Aster *in the codex graph* (via their carrying families)
  — don't present it as a real-world relationship measure.
- Producer spellings are as-credited verbatim: "YungSkah" and "Yung Skah"
  are separate figure nodes, like max/vetty in the circle. Don't merge
  them.
- 41 of the 53 figures have no circle page (`page: null`) — credited as
  named, nothing more claimed. Don't invent bios for them.
- The codex-only pathfinder mode forbids the Aster hub: "no path found"
  is a real, honest answer for isolates — don't route around it.
- Play counts are the 2026-10-11 snapshot; upload dates ≠ recording
  dates. Never quote or reproduce lyrics — titles and metadata only.
