---
name: build-press-kit
description: Assemble a press kit from verified artist facts only — bio, facts, discography, links, contact. Nothing invented, nothing speculative.
---

# Build the press kit

Use when press, playlist editors, or venues ask for materials.

## Inputs

- `api/v1/artist.json` (only verified fields)
- Booking contact (only if the artist has approved its publication)

## Procedure

1. Pull: name, tagline, bio paragraphs, fact list, discography (titles + dates), platform links, booking email.
2. Assemble: one-page bio (150 words max, third person, from verified facts only), fact sheet (bullets), discography table, link block, contact line.
3. Mark every fact with its source platform. Anything without a source is cut.
4. Never include: genre labels not confirmed by the artist, personal background not publicly stated, collaborator claims not credited on a release, private contact details.

## Pitfalls

- Padding a thin bio with adjectives that imply unverified facts ("chart-topping", "viral", "legendary" — cut all of them).
- Publishing the booking email before the artist approves it — the `booking` field in the API is the authority.
