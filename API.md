# Aster da Master — API

Base: `api/v1/`. Static JSON, versioned. The artist record is the single source
of truth; `data/artist.json` feeds the site renderer and mirrors it.

- `api/v1/index.json` — manifest: version, endpoints, observation date, provenance, agent routing
- `api/v1/artist.json` — the canonical artist record: bio, facts, discography, platforms, socials, featured release, booking
- `api/v1/schema/artist.json` — JSON Schema (draft-07) for the artist record

## Publication rule

`research_status` gates everything. While it reads `PENDING`, no artist facts
are published — the site renders its designed "assembling the archive" state.
Facts enter only from verified public platform pages (Spotify, Apple Music,
SoundCloud, YouTube, etc.). Unverified claims are never published; identity
drift (a platform URL pointing at a different artist) escalates to research.

## Cover art

Discography entries carry an `artwork` URL sourced from the iTunes Search API
(`artworkUrl100`, upgraded to 600×600 via Apple's standard size pattern) and
hotlinked from Apple's CDN (`*.mzstatic.com`). Verified 2026-10-11: all 34
release artworks resolve with `image/*` content types. The site renders them
with `loading="lazy"` and falls back to a monogram tile if a URL ever dies.
Releases with no artwork simply omit the field — no placeholders.

## Skills

Task procedures in `skills/`:

- `announce-release` — draft release announcements in the site's voice
- `verify-platform-links` — audit every outbound link; flag dead links and identity drift
- `build-press-kit` — assemble a press kit from verified facts only
