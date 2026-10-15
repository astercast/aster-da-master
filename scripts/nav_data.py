#!/usr/bin/env python3
"""scripts/nav_data.py — canonical navigation data for Aster da Master.

THE single source of truth for every nav surface on the site. Imported by:
  - scripts/update_nav.py     (rebuilds / checks the Primary, Mobile and
                               Footer nav blocks on every page)
  - the page generators       (build_circle, build_codex, build_eras,
                               build_years, build_session_deepdives,
                               build_glance, build_releases,
                               build_changelog, build_sessions and
                               build_scene_atlas — and, through
                               build_codex's HEAD/FOOT, the producer
                               deep dives render their nav from here)

Never redefine these lists anywhere else. Adding a page to the nav is a
one-line data edit here — never a new script. This module retires the nine
one-off fork scripts (update_nav_wave10/11/13/14/22/30/33/34/35.py, 645
lines) that each inserted one link after one anchor and hand-patched the
generators' NAV constants so rebuilds kept it.

Sleek-minimal rework (2026-10-15, the user's direct order): the presented
site is four doors — Releases, Story, About, Press kit — over a Home
route. The 23-door archive registry and the five front-desk doors are
retired as lists; the archive's depth now lives in the data layer
(data/v1/), which this rework does not touch. The footer map is Home +
the same four doors on every page.

Rotation 30 (VP-0039): ONE chrome generation. A decade of sections had
accreted per-section footer variants (ten distinct 19–26-item footer
label sets, and an anchored variant whose home-section anchors repeated
the home destination seven times on one page). The variants are retired
as label sets: every page now carries the SAME primary nav (the five
front-desk doors) and the SAME footer map (Home + the full registry
below, in this order). The old variant names survive only as accepted
routing tags in the render functions' signatures, so generator call
sites did not need to change; they no longer select anything. The
homepage's #discography anchor is not a registry entry: it is a section
of the home page itself and duplicates the Home destination, so the
catalogue's one name — Releases — is carried by the releases/ door and
by the home page's own drawer heading, not by a second footer label.

Href tokens (resolved by `_resolve` against the page's depth prefix):
  "#frag"   a homepage anchor: "./#frag" at the root, "../#frag" below it
  "@self"   the section's own index: "./"
  "@home"   the site root: "./" at the root, "../" below it
  anything else is site-root-relative and takes the depth prefix.
"""
from html import escape

# The full archive registry, in canonical order. This order is the
# footer map's order (after Home) on every page of the site.
NAV = [
    ("releases/", "Releases"),
    ("story.html", "Story"),
    ("about.html", "About"),
    ("press-kit.html", "Press kit"),
]

# The front-desk doors: the few links a first-time visitor reads at a
# glance. Rotation 21: these five are THE primary nav on every page —
# primary_nav_html renders this list. The full registry survives intact
# as the FOOTER map on every page (FOOTER below), so no destination is
# delisted: every door removed from the header remains reachable by a
# labelled path in the footer, and the homepage's station-index dialog
# keeps its own full grouping.
# Must be a subset of NAV (asserted below).
PRIMARY_NAV = [
    ("releases/", "Releases"),
    ("story.html", "Story"),
    ("about.html", "About"),
    ("press-kit.html", "Press kit"),
]

# Rotation 30 (VP-0039): plain-language glosses for the primary labels
# that are insider words. Each renders as the link's title attribute —
# the gloss a first-time visitor meets at first encounter with the
# label, in the desktop nav and the mobile panel alike — at zero
# geometry cost: the label text and the link boxes do not change.
# "Releases" is already plain language and carries no gloss.
GLOSSES = {
    "story.html": "His career in six eras, 2017 to today",
    "about.html": "Who he is, and where to listen",
}

# The ONE footer map: a Home-labelled route first, then the full
# registry in canonical order. Identical on every page; only the depth
# prefix and the aria-current marker vary.
FOOTER = [("@home", "Home")] + NAV

# Legacy variant names (rotation 30): accepted by the render functions
# and by update_nav's page tables for call compatibility, but they no
# longer select a label set — every variant resolves to the one FOOTER.
_VARIANT_NAMES = (
    "standard", "standard-scene", "agents", "ledger", "circle", "codex",
    "producers", "eras", "scene", "anchored", "compact",
)
VARIANTS = {name: FOOTER for name in _VARIANT_NAMES}

# Bespoke pages: registered and sequence-verified by update_nav.py,
# never rewritten by it (their markup carries page furniture the
# renderers do not own). Their sequences are the same canonical lists:
# the home page and the press kit carry the same primary five and the
# same footer map as every other page.
HOME_NAV = list(PRIMARY_NAV)
# Rotation 21: the mobile panel mirrors the primary five exactly —
# no extra doors in the small viewport.
HOME_MOBILE_EXTRA = []
HOME_FOOTER = None  # resolved below, after _resolve is defined
PRESSKIT_NAV = list(PRIMARY_NAV)
PRESSKIT_FOOTER = None  # resolved below, after _resolve is defined

# --- Assertions: coverage is proven at import, not hoped for. ---
_NAV_HREFS = [href for href, _ in NAV]
assert len(_NAV_HREFS) == len(set(_NAV_HREFS)), "duplicate href in NAV"
assert {h for h, _ in PRIMARY_NAV} <= set(_NAV_HREFS), \
    "PRIMARY_NAV not a subset of NAV"
assert set(GLOSSES) <= {h for h, _ in PRIMARY_NAV}, \
    "GLOSSES keys must be primary-nav hrefs"
_FOOTER_HREFS = [h for h, _ in FOOTER]
assert len(_FOOTER_HREFS) == len(set(_FOOTER_HREFS)), \
    "duplicate href in FOOTER"
assert FOOTER[0] == ("@home", "Home"), "footer must open with the Home route"
assert FOOTER[1:] == NAV, "footer must be Home + the registry, in order"


def _resolve(href, prefix):
    home = "./" if prefix == "" else prefix
    if href == "@self":
        return "./"
    if href == "@home":
        return home
    if href.startswith("#"):
        return home + href
    return prefix + href


# The bespoke pages' footer sequences, in resolved root form (the form
# update_nav.py's bespoke check compares against the written markup).
HOME_FOOTER = [(_resolve(h, ""), label) for h, label in FOOTER]
PRESSKIT_FOOTER = [(_resolve(h, ""), label) for h, label in FOOTER]


def _render(entries, prefix, current, indent):
    lines = []
    for href, label in entries:
        resolved = _resolve(href, prefix)
        cur = ' aria-current="page"' if current and href == current else ""
        lines.append(
            f'{indent}<a href="{escape(resolved, quote=True)}"{cur}>'
            f"{escape(label)}</a>")
    return "\n".join(lines)


def primary_entries(variant=None):
    return list(PRIMARY_NAV)


def footer_entries(variant=None, drop_extra=()):
    """The one footer map. `variant` and `drop_extra` are legacy
    routing tags (rotation 30): accepted, and deliberately without
    effect — the map is the same on every page."""
    return list(FOOTER)


def _render_primary(entries, prefix, current):
    """Rotation 22 (AZ-6, filed form): the primary nav as ONE LINE of
    single words, punctuated as a sentence — the doors joined by
    semicolons and closed by a full stop. Same five destinations, same
    link count as the list form it replaces; the punctuation is text,
    not chrome, and no destination is added or removed. Rotation 30:
    the insider labels carry their plain-language gloss as the link's
    title (see GLOSSES); label text and geometry are unchanged."""
    parts = []
    for href, label in entries:
        resolved = _resolve(href, prefix)
        cur = ' aria-current="page"' if current and href == current else ""
        gloss = GLOSSES.get(href)
        ttl = f' title="{escape(gloss, quote=True)}"' if gloss else ""
        parts.append(
            f'<a href="{escape(resolved, quote=True)}"{cur}{ttl}>'
            f"{escape(label)}</a>")
    return ('<span class="nav-sep" aria-hidden="true">; </span>'.join(parts)
            + '<span class="nav-sep" aria-hidden="true">.</span>')


def primary_nav_html(current, prefix="", variant=None):
    """The primary nav's inner HTML: the five front-desk doors
    (PRIMARY_NAV) on every page. `current` is the page's own logical
    href (e.g. "tuner.html") or None; `prefix` is "../" per directory
    depth. `variant` is a legacy routing tag and selects nothing."""
    return _render_primary(PRIMARY_NAV, prefix, current)


def footer_nav_html(current="", prefix="", variant=None,
                    drop_extra=()):
    """The footer nav's inner HTML: the one footer map (FOOTER)."""
    return _render(FOOTER, prefix, current, "        ")


def nav_chunk(prefix="", variant=None, current=None):
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


def footer_block(prefix="", variant=None, current=None,
                 drop_extra=()):
    """The footer <nav> block, for generator FOOT templates."""
    return (
        '<nav aria-label="Footer">\n'
        + footer_nav_html(current or "", prefix, variant, drop_extra)
        + "\n      </nav>"
    )
