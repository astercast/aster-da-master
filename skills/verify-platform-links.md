---
name: verify-platform-links
description: Audit every platform and social link on the Aster da Master site — resolve each URL, flag dead or redirected links.
---

# Verify platform links

Use when links may have rotted, or before any push that touches `data/artist.json`.

## Inputs

- `data/artist.json` (platforms, socials, discography link lists)

## Procedure

1. Extract every URL from `data/artist.json`.
2. Fetch each with a HEAD/GET (follow redirects). Record: status code, final URL, load time.
3. Flag: dead (4xx/5xx/timeout), redirected-to-different-artist (identity drift — critical), slow (>5s).
4. For discography links, confirm the page actually names the release (title match), not just the artist page.
5. Write findings to a dated report under `hidden_files/`; fix `data/artist.json` only for confirmed-correct replacements.

## Pitfalls

- "Fixing" a dead link by guessing a new URL — only replace with a verified platform search result.
- Identity drift: a platform reassigning an artist URL to a different artist. Treat as a research escalation, not a link edit.
