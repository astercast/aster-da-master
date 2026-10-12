---
name: network-graph-reader
description: Read the collaboration network (network.json) — nodes, track-weighted edges, co-credit links, and computed insights — to answer "who works with whom" questions and map the collab universe.
---

# Read the collaboration network

## Use when

An agent needs the shape of the whole collaboration universe, not one
person's footprint: who the central collaborators are, which collaborators
link to each other (co-credits), which years were the busiest, who came
first. Feeds network writeups, "who works with whom" answers, era-collab
crossover analysis. For a single person's full footprint, use
`collaborator-tracer` first; come here for the graph around them.

## Inputs

- A question about relationships: a collaborator slug, a year, or "the whole graph"
- Optional: focus — insights only, one node's neighborhood, co-credit subgraph

## Procedure

1. Read `api/v1/network.json`. Structure: `artist` (center), `nodes[]`
   (`id`, `name`, `kind` = artist/collaborator/producer, `track_count`,
   `first_date`, `last_date`, `tracks[]`, layout `x`/`y`), `edges[]`
   (`a`, `b`, `weight`, `kind` = artist/co-credit, optional `shared_tracks[]`),
   `insights` (computed, asserted at build time).
2. Start with `insights` — it answers the four canonical questions directly:
   `most_frequent_collaborator`, `producer_most_credits`,
   `year_most_collabs`, `first_ever_collaborator`. Quote these; do not
   recompute them (the builder already asserted them against the data).
3. For one node's neighborhood: filter `edges[]` where `a` or `b` equals the
   node id. `kind: "artist"` edges are artist↔collaborator (weight = shared
   tracks); `kind: "co-credit"` edges link collaborators who share a track
   title (read `shared_tracks[]` for the receipts).
4. Map node ids back to `circle/<slug>.html` pages via the node's `page`
   field (or `circle.json` keys) for per-track detail.
5. Report shapes, not stories: node counts, edge weights, co-credit pairs.
   The graph records that collaborations happened; it says nothing about how
   or why — never invent relationship narratives.

## Worked example

"The collaboration universe at a glance" (verified 2026-10-11):

- 23 nodes: the artist at center, 21 title-credited collaborators
  (`kind: collaborator`, node size = shared tracks), 1 producer scene figure
  (Fish Narc, `kind: producer`, different shape).
- 27 edges: artist↔every node (weight = shared tracks) + 5 co-credit edges
  from real title co-occurrences.
- Insights: most frequent collaborator = **Max Ferrari ×8**; producer with
  most credits = **Fish Narc ×2**; busiest collab year = **2019 (21 tracks)**;
  first-ever collaborator = **JO$E DRIPP** ("Mistakes Ft. JO$E DRIPP",
  2018-04-28).
- Max Ferrari's neighborhood: artist edge weight 8; co-credit edges
  `jax ↔ max-ferrari` (weight 2: "DESTINY (ft. JAX & Max Ferrari)",
  "NIGHT MODE ft. MAX FERRARI x YUNG VETTA x JAX") and
  `max-ferrari ↔ yung-vetta` (weight 1: "NIGHT MODE…").
- Honest absence: no producer↔collaborator edges exist on record — recorded
  as absent, not invented.

## API references

- `api/v1/network.json` — the graph: nodes, edges, insights
  (schema: `api/v1/schema/network.json`)
- `api/v1/circle.json` — per-collaborator track detail behind each node
- `api/v1/scene-figures.json` — producer nodes' research backing
- `api/v1/index.json` — registry; network endpoint `records: 23`

## Pitfalls

- Node ids are slugs (`max-ferrari`), not display names ("Max Ferrari").
  Match exactly — `max` and `vetty` are separate circle entries from
  `max-ferrari` / `yung-vetta`.
- Edge `weight` is a shared-track count, not a play count. For plays, join
  against `circle.json`.
- Co-credit edges come only from title co-occurrences parsed from `w/` /
  `ft.` / `feat.` fragments — a missing edge is not proof two people never
  met, only that no shared title exists.
- `x`/`y` are a deterministic server-side ring layout for the
  `network.html` visualization — stable across re-runs, not geographic or
  semantic.
- Never invent relationship details (how they met, who introduced whom)
  beyond what the endpoints record.
