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

## Skills

Task procedures in `skills/`:

- `announce-release` — draft release announcements in the site's voice
- `verify-platform-links` — audit every outbound link; flag dead links and identity drift
- `build-press-kit` — assemble a press kit from verified facts only
