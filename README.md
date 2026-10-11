# Aster da Master

The all-in-one site for **Aster da Master** — *he transcends music.*

A single-page, insanely designed, professionally composed artist site: minimal cyberpunk meets ancient aesthetic. Bone white on marble black, antique gold, one jade-neon accent. Roman numerals, monumental type, terminal micro-labels.

## Status

✅ **Research complete (2026-10-11)** — identity resolved: two distributor profiles for one artist (main Apple Music catalog, Hip-Hop/Rap, 34 releases; alt-spelling Alternative duplicate), SomeLowLifes collective, WoT 2019 era, quiet 2025, 2026 comeback. `data/artist.json` is populated from verified facts only (34-release discography, 9 platforms, 22 collaborators, 10 facts). The Spotify "Aster" profile is identity-**unverified** and is not merged — shown only with "possible profile" framing. Real name, age, hometown: unknown, never invented. Source report: `~/workspace/research_notes/aster-da-master-20261011/report.md`.

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
