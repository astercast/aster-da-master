---
name: collaborator-tracer
description: Map any collaborator's full footprint across the discography — shared tracks, plays, years active, and verified research notes — via the circle and scene-figures endpoints.
---

# Trace a collaborator's footprint

## Use when

An agent needs everything the archive knows about one person: who they worked with, on what, when, and how it landed. Feeds collaborator profiles, "who is X" answers, network writeups.

## Inputs

- A collaborator slug (the key in `api/v1/circle.json`, e.g. `capoxxo`, `pvscale`, `lil-yu`) or a scene-figure key from `api/v1/scene-figures.json`
- Optional: focus — tracks only, research notes only, network context only

## Procedure

1. Check `api/v1/circle.json` first. If the slug is there, read: `name`, `page`, `shared_transmissions`, `shared_plays`, `years_active`, and the full `tracks[]` list (title, date, plays, type). The 21 keys are title-credited collaborators only.
2. If the slug is **not** in `circle.json`, check `api/v1/scene-figures.json` — producers are excluded from the circle by the title-credit rule, so a producer (e.g. Fish Narc) lives here instead, with `kind`, `standing`, `tracks`, `facts`, and `sources`.
3. Read `verified_notes` (circle entries) — `research_pass` date, `facts`, `sources`. These carry the 2026-10-11 research enrichment (Pitchfork canon mentions, tape credits, production histories). Cite sources when using them.
4. Check `years_active` and map the tracks onto eras (`api/v1/artist.json` → `eras[]`) for the "when in the story" line.
5. Optional network step: for a title-credited collaborator, open their `circle/<slug>.html` page — it lists every shared track linked to its release page, plus era breakdown.
6. Summarize as: **who** (name + standing), **footprint** (N tracks, total plays, years), **the tracks** (chronological, with plays), **the research** (verified facts, cited).

## Worked example

`capoxxo` (circle entry, page `circle/capoxxo.html`):

- Footprint: 2 shared transmissions, 16,174 shared plays, active 2019.
- Tracks: "candy w/ capoxxo(prod. razorwrist)" — 2019-10-04, 11,587 plays; "getting colder w/ capoxxo (prod. pvscale x asa41)" — 2019-12-22, 4,587 plays.
- Research (pass 2026-10-11): named in Pitchfork's "A Deeply Incomplete Canon of Hyperpop-Digicore"; collab tape *Persona* w/ mayh3mp (Cult Love Sound Tapes, 2022; 5 tracks, cassette run of 100).
- Era: both tracks land in "The First Rite" (2017–2019), near the close of that era — just before *Master Key* (2019-12-23).

## API references

- `api/v1/circle.json` — the 21 title-credited collaborators and their per-track footprint
- `api/v1/scene-figures.json` — producer/scene figures outside the 21 (`kind`, `standing`, `facts`, `sources`)
- `api/v1/artist.json` — `eras[]` for era placement; `collaborators` count (22 = 21 circle + scene figures)
- `api/v1/index.json` — registry; circle/ page paths live under `circle/`

## Pitfalls

- The circle is **title-credit only**. A missing producer is not an absent collaborator — check `scene-figures.json` first.
- Watch near-duplicate slugs: `max` and `max-ferrari` are separate circle entries. Match exactly.
- Credits are parsed from `w/` / `ft.` / `feat.` fragments, verbatim as uploaded — inconsistent punctuation is a source fact, not a typo to fix.
- Verified research notes are a 2026-10-11 enrichment of *public* sources; anything not in `verified_notes` or `facts` is unknown — say so, don't fill it.
- Never invent relationship details (how they met, who introduced whom) beyond what the endpoints record.
