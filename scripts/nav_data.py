#!/usr/bin/env python3
"""scripts/nav_data.py — canonical navigation data for Aster da Master.

THE single source of truth for every nav surface on the site. Imported by:
  - scripts/update_nav.py     (rebuilds / checks the Primary, Mobile and
                               Footer nav blocks on every page)
  - the page generators       (build_circle, build_codex, build_eras,
                               build_years, build_session_deepdives,
                               build_glance, build_releases,
                               build_changelog, build_sessions and
                               build_scene_atlas — Rotation 14 completed
                               the set — and, through build_codex's
                               HEAD/FOOT, the producer deep dives render
                               their nav from here)

Never redefine these lists anywhere else. Adding a page to the nav is a
one-line data edit here — never a new script. This module retires the nine
one-off fork scripts (update_nav_wave10/11/13/14/22/30/33/34/35.py, 645
lines) that each inserted one link after one anchor and hand-patched the
generators' NAV constants so rebuilds kept it.

Canonical pattern: fleet-commons `patterns/nav-injection` v1.0.0,
generalized from marvel-legends-chronicle. Aster's nav is not one list:
a decade of sections accreted per-section variants (the releases pages
carry a compact nav, three root pages lead with homepage anchors, the
homepage and press kit are bespoke). Those variants are DATA below —
named, explicit, and asserted — not per-wave code.

Href tokens (resolved by `_resolve` against the page's depth prefix):
  "#frag"   a homepage anchor: "./#frag" at the root, "../#frag" below it
  "@self"   the section's own index: "./"
  "@home"   the site root: "./" at the root, "../" below it
  anything else is site-root-relative and takes the depth prefix.

Canonical order note: the `agents` and `ledger` variants preserve the
link orders those page families have actually shipped with (Years after
Agents on the agent-facing pages; Sessions/Changelog ahead of Method on
the ledger pages). They are recorded as data so the next nav change is
one edit, made on purpose — not a tenth fork.
"""
from html import escape

# The full archive registry, in the canonical (standard-variant) order.
NAV = [
    ("#discography", "Discography"),
    ("releases/", "Releases"),
    ("years/", "Years"),
    ("circle/", "Circle"),
    ("scene/", "Scene"),
    ("timeline.html", "Timeline"),
    ("chronicle.html", "Chronicle"),
    ("transmission.html", "Transmission"),
    ("tuner.html", "Tuner"),
    ("scene-atlas.html", "Atlas"),
    ("network.html", "Network"),
    ("milestone-race.html", "Race"),
    ("decoder.html", "Decoder"),
    ("api-playground.html", "API"),
    ("agents.html", "Agents"),
    ("method.html", "Method"),
    ("trilogy.html", "Trilogy"),
    ("sessions.html", "Sessions"),
    ("changelog.html", "Changelog"),
    ("glance.html", "Glance"),
    ("press-kit.html", "Press kit"),
]

# The front-desk doors: the few links a first-time visitor reads at a
# glance (the homepage renders its own short form of these — see
# HOME_NAV). Must be a subset of NAV (asserted below).
PRIMARY_NAV = [
    ("transmission.html", "Transmission"),
    ("tuner.html", "Tuner"),
    ("scene-atlas.html", "Atlas"),
    ("releases/", "Releases"),
    ("scene/", "Scene"),
]

# No grouped directory surface on this site; the canonical pattern's
# directory template is not used.
GROUPS = []


def _by_label(entries):
    return {label: href for href, label in entries}


_STD = _by_label(NAV)


def _seq(*labels, **kw):
    """Build an entry list from NAV labels, with optional substitutions
    given as label=(href, label) pairs."""
    out = []
    for lab in labels:
        if lab in kw:
            out.append(kw[lab])
        else:
            out.append((_STD[lab], lab))
    return out


# --- Primary-nav variants (exact shipped orders, as data) -----------------

# Root standard pages (method, trilogy, tuner, scene-atlas) and the two
# scene pages that carry the full boat (scene/index, uncle-release-week).
# The root form files no Circle door; the scene form adds it back (the
# scene variant table in update_nav.py assigns the subdir pages).
STANDARD = _seq(
    "Discography", "Releases", "Years", "Scene", "Timeline", "Chronicle",
    "Transmission", "Tuner", "Atlas", "Network", "Race", "Decoder",
    "API", "Agents", "Method", "Trilogy", "Sessions", "Changelog",
    "Glance", "Press kit",
)
STANDARD_SCENE = _seq(
    "Discography", "Releases", "Years", "Circle", "Scene", "Timeline",
    "Chronicle", "Transmission", "Tuner", "Atlas", "Network", "Race",
    "Decoder", "API", "Agents", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance", "Press kit",
)

# Agent-facing root pages (agents, api-playground, decoder, transmission):
# Years filed after Agents, no Circle entry.
AGENTS = _seq(
    "Discography", "Releases", "Scene", "Timeline", "Chronicle",
    "Transmission", "Tuner", "Atlas", "Network", "Race", "Decoder",
    "API", "Agents", "Years", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance", "Press kit",
)

# Ledger root pages (changelog, chronicle, glance, milestone-race,
# sessions, sessions-explorer): Sessions/Changelog ahead of Method.
LEDGER = _seq(
    "Discography", "Releases", "Years", "Scene", "Timeline", "Chronicle",
    "Transmission", "Tuner", "Atlas", "Network", "Race", "Decoder",
    "API", "Agents", "Sessions", "Changelog", "Method", "Trilogy",
    "Glance", "Press kit",
)

# Section variants: the section's own door replaces its registry slot.
CIRCLE = _seq(
    "Discography", "Releases", "Years", "Circle", "Scene", "Timeline",
    "Chronicle", "Transmission", "Tuner", "Atlas", "Network", "Race",
    "Decoder", "API", "Agents", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance", "Press kit",
    Circle=("@self", "Circle"),
)
CODEX = _seq(
    "Discography", "Releases", "Years", "Circle", "Scene", "Timeline",
    "Chronicle", "Transmission", "Tuner", "Atlas", "Network", "Race",
    "Decoder", "API", "Agents", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance", "Press kit",
    Circle=("@self", "Codex"),
)
# Producer deep dives used to inherit the codex variant whole — their
# "Codex" door pointed at "./", the producers index. The canonical data
# gives the door its real target. (Rotation 13 fix; see WAVELOG.)
PRODUCERS = _seq(
    "Discography", "Releases", "Years", "Circle", "Scene", "Timeline",
    "Chronicle", "Transmission", "Tuner", "Atlas", "Network", "Race",
    "Decoder", "API", "Agents", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance", "Press kit",
    Circle=("codex/", "Codex"),
)
YEARS = _seq(
    "Discography", "Releases", "Years", "Scene", "Timeline", "Chronicle",
    "Transmission", "Tuner", "Atlas", "Network", "Race", "Decoder",
    "API", "Agents", "Method", "Trilogy", "Sessions", "Changelog",
    "Glance", "Press kit",
    Years=("@self", "Years"),
)

# Era deep dives and session deep dives share one curation: Sessions
# filed with the archive doors, Glance ahead of Changelog, no Circle.
ERAS = _seq(
    "Discography", "Releases", "Years", "Sessions", "Scene", "Timeline",
    "Chronicle", "Transmission", "Tuner", "Atlas", "Network", "Race",
    "Decoder", "API", "Agents", "Method", "Trilogy", "Glance",
    "Changelog", "Press kit",
)

# Scene subpages and the Signal board: the full boat minus the Scene
# door itself (the reader is already inside the section's pages).
SCENE = _seq(
    "Discography", "Releases", "Years", "Circle", "Timeline",
    "Chronicle", "Transmission", "Tuner", "Atlas", "Network", "Race",
    "Decoder", "API", "Agents", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance", "Press kit",
)

# Anchored root pages (codex-network, network, timeline): a prelude of
# homepage section anchors, then the archive tail.
ANCHORED_PRELUDE = [
    ("#latest", "Latest"),
    ("#discography", "Discography"),
    ("releases/", "Releases"),
    ("#listen", "Listen"),
    ("#circle", "Circle"),
    ("#about", "About"),
    ("#connect", "Connect"),
    ("#eras", "Eras"),
    ("#numbers", "Numbers"),
    ("#codex", "Codex"),
]
ANCHORED_TAIL = _seq(
    "Scene", "Timeline", "Chronicle", "Transmission", "Tuner", "Atlas",
    "Network", "Race", "Decoder", "API", "Agents", "Years", "Method",
    "Trilogy", "Sessions", "Changelog", "Glance", "Press kit",
)
ANCHORED = ANCHORED_PRELUDE + ANCHORED_TAIL

# Release pages: the compact nav (220 pages).
COMPACT = [
    ("#discography", "Discography"),
    ("@self", "All releases"),
    ("years/", "Years"),
    ("decoder.html", "Decoder"),
    ("api-playground.html", "API"),
    ("scene/", "Scene"),
    ("chronicle.html", "Chronicle"),
    ("transmission.html", "Transmission"),
    ("tuner.html", "Tuner"),
    ("scene-atlas.html", "Atlas"),
    ("milestone-race.html", "Race"),
    ("agents.html", "Agents"),
    ("method.html", "Method"),
    ("trilogy.html", "Trilogy"),
    ("sessions.html", "Sessions"),
    ("changelog.html", "Changelog"),
    ("glance.html", "Glance"),
    ("press-kit.html", "Press kit"),
]
COMPACT_FOOTER = [
    ("@home", "Home"),
    ("@self", "All releases"),
    ("years/", "Years"),
    ("method.html", "Method"),
    ("trilogy.html", "Trilogy"),
    ("sessions.html", "Sessions"),
    ("changelog.html", "Changelog"),
    ("glance.html", "Glance"),
    ("press-kit.html", "Press kit"),
]

# Bespoke pages: registered and sequence-verified by update_nav.py,
# never rewritten by it (their markup carries page furniture the
# renderers do not own).
HOME_NAV = [
    ("transmission.html", "Transmission"),
    ("tuner.html", "Tuner"),
    ("scene-atlas.html", "Atlas"),
    ("releases/", "Archive"),
    ("scene/", "Scene"),
    ("#rooms", "Rooms"),
]
HOME_MOBILE_EXTRA = [("#log", "Station log")]
HOME_FOOTER = [
    ("#top", "Top"),
    ("transmission.html", "Transmission"),
    ("tuner.html", "Tuner"),
    ("scene-atlas.html", "Atlas"),
    ("releases/", "Releases"),
    ("glance.html", "Glance"),
    ("chronicle.html", "Chronicle"),
    ("timeline.html", "Timeline"),
    ("circle/", "Circle"),
    ("scene/", "Scene"),
    ("producers/", "Producers"),
    ("codex/", "Codex"),
    ("codex-network.html", "Codex network"),
    ("network.html", "Network"),
    ("milestone-race.html", "Race"),
    ("decoder.html", "Decoder"),
    ("api-playground.html", "API"),
    ("agents.html", "Agents"),
    ("press-kit.html", "Press kit"),
    ("trilogy.html", "Trilogy"),
    ("method.html", "Method"),
    ("changelog.html", "Changelog"),
]
PRESSKIT_NAV = _seq(
    "Discography", "Releases", "Scene", "Timeline", "Chronicle",
    "Transmission", "Tuner", "Atlas", "Network", "Race", "Decoder",
    "API", "Agents", "Years", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance",
)
# the Home door sits mid-list in the shipped press-kit nav, after
# Trilogy and before Sessions:
PRESSKIT_NAV = (PRESSKIT_NAV[:16] + [("@home", "Home")]
                + PRESSKIT_NAV[16:])
PRESSKIT_FOOTER = [
    ("@home", "Home"),
    ("years/", "Years"),
    ("method.html", "Method"),
    ("trilogy.html", "Trilogy"),
    ("decoder.html", "Decoder"),
    ("api-playground.html", "API"),
    ("sessions.html", "Sessions"),
    ("changelog.html", "Changelog"),
    ("glance.html", "Glance"),
]

VARIANTS = {
    "standard": STANDARD,
    "standard-scene": STANDARD_SCENE,
    "agents": AGENTS,
    "ledger": LEDGER,
    "circle": CIRCLE,
    "codex": CODEX,
    "producers": PRODUCERS,
    "years": YEARS,
    "eras": ERAS,
    "scene": SCENE,
    "anchored": ANCHORED,
    "compact": COMPACT,
}

# Footer derivation: the footer is the primary list with a Home door in
# front, minus the doors named per variant (subdirectory footers drop
# the homepage's Discography anchor; the scene footer also drops the
# Scene door). Named exceptions live here, as data.
_FOOTER_DROP = {
    "standard": (),
    "standard-scene": (),  # per-page drops tabled in update_nav.py
    "agents": (),
    "ledger": (),
    "anchored": ("#latest", "#about"),
    "circle": ("#discography",),
    "codex": ("#discography",),
    "producers": ("#discography",),
    "years": ("#discography",),
    "eras": ("#discography",),
    "scene": ("#discography", "scene/"),
}
_FOOTER_OVERRIDE = {
    "compact": COMPACT_FOOTER,
}

# --- Assertions: coverage is proven at import, not hoped for. ---
_NAV_HREFS = [href for href, _ in NAV]
assert len(_NAV_HREFS) == len(set(_NAV_HREFS)), "duplicate href in NAV"
assert {h for h, _ in PRIMARY_NAV} <= set(_NAV_HREFS), \
    "PRIMARY_NAV not a subset of NAV"
_MASTER = set(_NAV_HREFS) | {"codex/", "producers/", "codex-network.html",
                             "@self", "@home",
                             "#latest", "#listen", "#circle", "#about",
                             "#connect", "#eras", "#numbers", "#codex",
                             "#rooms", "#log", "#top"}
for _name, _entries in list(VARIANTS.items()) + [
        ("home", HOME_NAV), ("home_footer", HOME_FOOTER),
        ("presskit", PRESSKIT_NAV), ("presskit_footer", PRESSKIT_FOOTER),
        ("compact_footer", COMPACT_FOOTER)]:
    _hrefs = [h for h, _ in _entries]
    assert len(_hrefs) == len(set(_hrefs)), f"duplicate href in {_name}"
    assert set(_hrefs) <= _MASTER, f"{_name} has hrefs outside the registry"


def _resolve(href, prefix):
    home = "./" if prefix == "" else prefix
    if href == "@self":
        return "./"
    if href == "@home":
        return home
    if href.startswith("#"):
        return home + href
    return prefix + href


def _render(entries, prefix, current, indent):
    lines = []
    for href, label in entries:
        resolved = _resolve(href, prefix)
        cur = ' aria-current="page"' if current and href == current else ""
        lines.append(
            f'{indent}<a href="{escape(resolved, quote=True)}"{cur}>'
            f"{escape(label)}</a>")
    return "\n".join(lines)


def primary_entries(variant):
    return VARIANTS[variant]


def footer_entries(variant, drop_extra=()):
    if variant in _FOOTER_OVERRIDE:
        return list(_FOOTER_OVERRIDE[variant])
    drop = set(_FOOTER_DROP[variant]) | set(drop_extra)
    return [("@home", "Home")] + [
        e for e in VARIANTS[variant] if e[0] not in drop]


def primary_nav_html(current, prefix="", variant="standard"):
    """The primary nav's inner HTML. `current` is the page's own logical
    href (e.g. "transmission.html") or None; `prefix` is "../" per
    directory depth."""
    return _render(VARIANTS[variant], prefix, current, "        ")


def footer_nav_html(current="", prefix="", variant="standard",
                    drop_extra=()):
    """The footer nav's inner HTML for the variant."""
    return _render(footer_entries(variant, drop_extra), prefix,
                   current, "        ")


def nav_chunk(prefix="", variant="standard", current=None):
    """The full header chunk the generators embed: primary nav plus the
    mobile details panel, in the site's canonical framing (no stray
    blank line before the mobile close — the framing the fork-era
    constants carried is normalized here, once)."""
    items = primary_nav_html(current, prefix, variant)
    return (
        '<nav class="site-nav" aria-label="Primary">\n'
        + items + "\n"
        + "      </nav>\n"
        + '      <details class="mnav">\n'
        + '        <summary><span class="bars" aria-hidden="true">'
        + "<i></i><i></i><i></i></span>Menu</summary>\n"
        + '        <nav class="mnav-panel" aria-label="Mobile">\n'
        + items + "\n"
        + "        </nav>\n"
        + "      </details>"
    )


def footer_block(prefix="", variant="standard", current=None,
                 drop_extra=()):
    """The footer <nav> block, for generator FOOT templates."""
    return (
        '<nav aria-label="Footer">\n'
        + footer_nav_html(current or "", prefix, variant, drop_extra)
        + "\n      </nav>"
    )
