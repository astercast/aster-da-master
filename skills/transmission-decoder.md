---
name: transmission-decoder
description: Interpret a title word through the codex — which family it belongs to, which tracks carry it, and what the archive's own decoder page says.
---

# Decode a transmission word

## Use when

An agent (or a visitor) types a word — "litemode", "cold", "soul" — and wants to know what it means inside this archive: which vocabulary family claims it, and which transmissions carry it.

## Inputs

- A single word or short phrase (a title fragment, e.g. `nitemode`, `colder`, `ward`)

## Procedure

1. Fetch `data/v1/codex.json`. It holds 16 families, each with `name`, `epithet`, `words[]`, `track_count`, and `tracks[]` (title, date, plays, type).
2. Match the input against each family's `words[]` (case-insensitive; the decoder page also matches title text — see step 4). Note which family claims it and read the family's `epithet` for the archive's own gloss.
3. Pull the family's `tracks[]`: titles, dates, plays. That's the word's full transmission footprint.
4. For the live behavior, mirror `decoder.html` + `assets/js/decoder.js`: it matches the word against family word-lists and returns matching families plus the raw matching tracks. Reuse that logic rather than inventing new matching rules.
5. Present: **the family** (name + epithet), **the words it covers**, **the transmissions** (chronological, with plays), and **the read** — what the distribution says (e.g. a word that only appears in 2019 vs. one that spans 2018–2026).

## Worked example

Input: `nitemode`

- Family: **The Modes** — "The mode-words. Five transmissions carry them - lite, nite, and night." Words: `litemode`, `nitemode`, `night mode`.
- Transmissions (5): "NIGHT MODE ft. MAX FERRARI x YUNG VETTA x JAX" (2019-07-09, plays); "u Not at the Table (Sunsetzer0) #litemode" (2024-04-18); "3 Points Pre Game prod. doublemulti x pinkcat #NITEMODE" (2024-05-28); "nitemode2019 w/ Max+Vetty prod. NaXi.wav" (2024-11-05, plays — the vault's quietest track); "big litemode (prod runawway, ilyagargod & k3nik)" (2025-11-23).
- Read: the mode-words bookend the archive — one cluster in 2019, one in 2024–2025, with the tag spelling shifting from `nitemode2019` to `#litemode`/`#NITEMODE`/`big litemode`. Five transmissions across six years: a recurring signal, not a phase.

## API references

- `data/v1/codex.json` — the 16 families, word lists, per-family track lists
- `decoder.html` + `assets/js/decoder.js` — the reference decoder implementation
- `data/v1/sessions.json` — session context for any decoded track
- `data/v1/index.json` — registry

## Pitfalls

- Matching is title-text only. **Never quote or interpret lyrics** — the codex counts words in titles, nothing else.
- A family membership is a classification fact, not a definition. The archive deliberately leaves words like "litemode / nitemode" undefined (see the unknowns register on `method.html`) — don't supply a meaning the archive doesn't claim.
- Case and spelling variants (`nitemode2019`, `#NITEMODE`) are distinct uploads; list them as uploaded, don't normalize them away.
- If a word matches no family, say so plainly and offer the closest families rather than forcing a match.
