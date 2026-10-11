# Aster da Master

The all-in-one site for **Aster da Master** — *he transcends music.*

A single-page, insanely designed, professionally composed artist site: minimal cyberpunk meets ancient aesthetic. Bone white on marble black, antique gold, one jade-neon accent. Roman numerals, monumental type, terminal micro-labels.

## Status

🚧 **Research in progress** — discography, platform links, and bio are being gathered across the web (Spotify, Apple Music, SoundCloud, YouTube, and everywhere else). `data/artist.json` carries `research_status: PENDING` until verified. The scaffold is complete; content populates from research, never invented.

## Structure

- `index.html` — the whole site (hero, latest transmission, discography, listen, about, connect)
- `assets/css/` — `tokens.css`, `base.css`, `layout.css`, `components.css` (modular, no frameworks)
- `assets/js/site.js` — renders discography/platforms/socials/bio from `data/artist.json`; reveal-on-scroll
- `data/artist.json` — the single source of truth (populated by research)
- `api/v1/` — machine-readable artist record + schema (`API.md`)
- `skills/` — agent task procedures (announce-release, verify-platform-links, build-press-kit)

## Aesthetic rules

- Minimal: one idea per screen, vast negative space
- Ancient: Cinzel/Trajan display type, gold rules, Roman-numeral sections
- Cyberpunk: single neon accent, mono micro-labels, faint grid — restraint, not overload
- Reduced motion respected everywhere; semantic HTML; keyboard navigable

## Deploy

Private repo. GitHub only — no Vercel, nothing live until the artist says so.
Push via `python3 ~/workspace/skills/github/bin/gh-push.py`.
