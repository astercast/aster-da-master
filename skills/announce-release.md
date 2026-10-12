---
name: announce-release
description: Draft a release announcement for Aster da Master in the site's voice — ancient weight, neon signal, zero hype filler.
---

# Announce a release

Use when a new single, EP, album, or video drops and the site + socials need the announcement.

## Inputs

- Release record from `data/artist.json` (title, date, type, platform links)
- One true detail about the release (a verified fact — sound, story, collaborator). Never invent one.

## Procedure

1. Read the release record. Confirm title, date, and at least one platform link exist.
2. Write three variants: 240-character (X/Threads), 2-sentence (Instagram caption lead), and one-line (site hero kicker).
3. Voice rules: monumental, minimal, no exclamation marks, no "fire"/"banger"/"out now!!" filler. Ancient weight + neon signal.
4. Every variant links the platform, never just names it.
5. Update `data/artist.json` `featured_release` and rebuild nothing (the site renders from data).

## Worked example

Release: "Reachhh" (single, 2024-04-08). True detail: Shazam-pop association.
- X: "REACHHH. The signal continues. [link]"
- IG lead: "A transmission from the archive. Reachhh — listen everywhere. [link]"
- Kicker: "Latest transmission — Reachhh"

## Pitfalls

- Announcing before the platform links are live — always verify the link resolves first.
- Inventing chart positions, collaborator quotes, or genre labels. If it's not in `data/v1/artist.json`, it doesn't go in the announcement.
