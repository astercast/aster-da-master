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
# glance. Rotation 21: these five are now THE primary nav on every
# page — primary_nav_html renders this list, never the full variant
# registry. The full registry survives intact as the FOOTER nav on
# every page (footer_entries derives from VARIANTS below), so no
# destination is delisted: every door removed from the header
# remains reachable by a labelled path in the footer, and the
# homepage's station-index dialog keeps its own full grouping.
# Must be a subset of NAV (asserted below).
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
    "Discography", "Releases", "Scene", "Timeline", "Chronicle",
    "Transmission", "Tuner", "Atlas", "Network", "Race", "Decoder",
    "API", "Agents", "Method", "Trilogy", "Sessions", "Changelog",
    "Glance", "Press kit",
)
STANDARD_SCENE = _seq(
    "Discography", "Releases", "Circle", "Scene", "Timeline",
    "Chronicle", "Transmission", "Tuner", "Atlas", "Network", "Race",
    "Decoder", "API", "Agents", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance", "Press kit",
)

# Agent-facing root pages (agents, api-playground, decoder, transmission):
# Years filed after Agents, no Circle entry.
AGENTS = _seq(
    "Discography", "Releases", "Scene", "Timeline", "Chronicle",
    "Transmission", "Tuner", "Atlas", "Network", "Race", "Decoder",
    "API", "Agents", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance", "Press kit",
)

# Ledger root pages (changelog, chronicle, glance, milestone-race,
# sessions, sessions-explorer): Sessions/Changelog ahead of Method.
LEDGER = _seq(
    "Discography", "Releases", "Scene", "Timeline", "Chronicle",
    "Transmission", "Tuner", "Atlas", "Network", "Race", "Decoder",
    "API", "Agents", "Sessions", "Changelog", "Method", "Trilogy",
    "Glance", "Press kit",
)

# Section variants: the section's own door replaces its registry slot.
CIRCLE = _seq(
    "Discography", "Releases", "Circle", "Scene", "Timeline",
    "Chronicle", "Transmission", "Tuner", "Atlas", "Network", "Race",
    "Decoder", "API", "Agents", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance", "Press kit",
    Circle=("@self", "Circle"),
)
CODEX = _seq(
    "Discography", "Releases", "Circle", "Scene", "Timeline",
    "Chronicle", "Transmission", "Tuner", "Atlas", "Network", "Race",
    "Decoder", "API", "Agents", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance", "Press kit",
    Circle=("@self", "Codex"),
)
# Producer deep dives used to inherit the codex variant whole — their
# "Codex" door pointed at "./", the producers index. The canonical data
# gives the door its real target. (Rotation 13 fix; see WAVELOG.)
PRODUCERS = _seq(
    "Discography", "Releases", "Circle", "Scene", "Timeline",
    "Chronicle", "Transmission", "Tuner", "Atlas", "Network", "Race",
    "Decoder", "API", "Agents", "Method", "Trilogy", "Sessions",
    "Changelog", "Glance", "Press kit",
    Circle=("codex/", "Codex"),
)
# Rotation 22: the YEARS variant is retired with the years/ family
# itself (page consolidation). The year listings live in the Archive
# now; no page resolves to a years variant.

# Era deep dives and session deep dives share one curation: Sessions
# filed with the archive doors, Glance ahead of Changelog, no Circle.
ERAS = _seq(
    "Discography", "Releases", "Sessions", "Scene", "Timeline",
    "Chronicle", "Transmission", "Tuner", "Atlas", "Network", "Race",
    "Decoder", "API", "Agents", "Method", "Trilogy", "Glance",
    "Changelog", "Press kit",
)

# Scene subpages and the Signal board: the full boat minus the Scene
# door itself (the reader is already inside the section's pages).
SCENE = _seq(
    "Discography", "Releases", "Circle", "Timeline",
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
    "Network", "Race", "Decoder", "API", "Agents", "Method",
    "Trilogy", "Sessions", "Changelog", "Glance", "Press kit",
)
ANCHORED = ANCHORED_PRELUDE + ANCHORED_TAIL

# Release pages: the compact nav (220 pages).
COMPACT = [
    ("#discography", "Discography"),
    ("@self", "All releases"),
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
    ("releases/", "Releases"),
    ("scene/", "Scene"),
]
# Rotation 21: the mobile panel mirrors the primary five exactly —
# no extra doors in the small viewport. The Rooms and Station log
# sections themselves stay on the homepage, one scroll away, and
# every header door they carried remains in the footer below.
HOME_MOBILE_EXTRA = []
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
# Rotation 21: the press kit's header carries the same five
# front-desk doors as every other page; its footer (below) keeps
# the kit's own short list, and the full registry stays in the
# footer of every other page.
PRESSKIT_NAV = list(PRIMARY_NAV)
PRESSKIT_FOOTER = [
    ("@home", "Home"),
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


def _render_primary(entries, prefix, current):
    """Rotation 22 (AZ-6, filed form): the primary nav as ONE LINE of
    single words, punctuated as a sentence — the doors joined by
    semicolons and closed by a full stop. Same five destinations, same
    link count as the list form it replaces; the punctuation is text,
    not chrome, and no destination is added or removed."""
    parts = []
    for href, label in entries:
        resolved = _resolve(href, prefix)
        cur = ' aria-current="page"' if current and href == current else ""
        parts.append(
            f'<a href="{escape(resolved, quote=True)}"{cur}>'
            f"{escape(label)}</a>")
    return ('<span class="nav-sep" aria-hidden="true">; </span>'.join(parts)
            + '<span class="nav-sep" aria-hidden="true">.</span>')


def primary_nav_html(current, prefix="", variant="standard"):
    """The primary nav's inner HTML: the five front-desk doors
    (PRIMARY_NAV) on every page, whatever the variant. `current` is
    the page's own logical href (e.g. "tuner.html") or None;
    `prefix` is "../" per directory depth. The variant registry
    still drives the FOOTER (footer_nav_html), where the full set
    of doors remains — header economy, never delisting."""
    return _render_primary(PRIMARY_NAV, prefix, current)


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
