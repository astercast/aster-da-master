---
name: era-briefing
description: Summarize one archive era — its span, releases, numbers, and story — for a writeup, from the eras array and the year-in-review endpoint.
---

# Brief an era

## Use when

An agent must write about a period of the catalog: an era chapter, a "the 2020 run" post, a press-kit section, or a timeline annotation. Produces a self-contained, citation-ready summary.

## Inputs

- An era name from `data/v1/artist.json` → `eras[]` (six eras: The First Rite, The Prolific Year, The Cast It: Years, The SomeLowLifes Era, The Silence, The Return)
- A target length (default ~250 words)

## Procedure

1. Fetch `data/v1/artist.json`, read `eras[]`. Find your era; capture `name`, `span`, `scene`, `releases`, and `note`.
2. Fetch `data/v1/years.json`. For each year inside the era's span, pull: transmissions, plays, distributor/vault split, and `top_tracks` (title, plays, date). These are the era's hard numbers.
3. Gather the era's key releases: distributor entries from `data/v1/artist.json` → `discography` (type, date, label, links) matching the titles in `releases[]`; vault standouts from the year's `top_tracks`.
4. Check who was around: scan the era's top tracks for collaborator credits, then `data/v1/circle.json` for their footprint.
5. Write the briefing in three moves: **the span** (dates + what the era is called and why), **the numbers** (transmissions, plays, top tracks — sourced), **the story** (the `scene`/`note` facts, collaborators, what distinguishes it). Every factual sentence must trace to an endpoint.
6. Close with the archive's own framing where the era has one (e.g. "The Silence" — no releases found in 2025; the reason is unknown and not speculated here).

## Worked example

**The First Rite** (2017–2019) — ~120 words:

The First Rite opens the archive: the earliest trace is a 2017 feature credit on another artist's single, and the WoT seal gets pressed onto *Master Key* (album, 2019-12-23, label "WoT", genre Hip-Hop/Rap). 2018 alone holds 39 vault transmissions and 104,479 plays, topped by "Take Me (prod. Em Klebold)" (30,088) and "Soul Shaking (prod. Fish Narc)" (12,944). Collaborators already circling: capoxxo on "candy" and "getting colder" (both 2019), Max Ferrari, Yung Vetta, and JAX on "NIGHT MODE" (2019-07-09). The era ends with the *Master Key* distributor run and the title track's own upload-cluster nearby.

## API references

- `data/v1/eras.json` — the deep-dive endpoint: pick the era by `id`; `summary` (ranks, archive-play share, busiest year, loudest/deepest transmissions, top codex family — all recomputed and asserted), full `tracks[]`, every in-era `collaborators[]`, `codex_families[]`, `key_sessions[]`, `milestones[]`. Start here.
- `data/v1/artist.json` — `eras[]` (name, span, scene, releases, note); `discography` (34 distributor releases with dates/labels/links)
- `data/v1/years.json` — per-year stats and `top_tracks`, 2018–2026
- `data/v1/circle.json` — collaborator footprints within the era
- `data/v1/milestones.json` — career firsts that may fall inside the era

## Pitfalls

- **Never invent biography.** The eras' `scene` and `note` fields are the entire sanctioned story; "The Silence" explicitly records that 2025's reason is unknown and not speculated.
- Era spans are ranges, not upload clusters — a track dated inside a span belongs to the era even if it was uploaded between sessions.
- Don't present year stats as era stats without adding the years up (or saying you didn't).
- If a "key release" you expect isn't in `discography`, check whether it's SoundCloud-only — the distributor list is 34 entries, not 219.
