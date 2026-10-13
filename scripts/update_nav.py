#!/usr/bin/env python3
"""Rebuild the nav blocks on every page from scripts/nav_data.py.

Canonical pattern: fleet-commons `patterns/nav-injection` v1.0.0,
generalized from marvel-legends-chronicle's update_nav.py. This script
retires the nine one-off forks (update_nav_wave10/11/13/14/22/30/33/34/
35.py): there is exactly one injector now, and nav links live in
exactly one data file.

The contract:
  - nav_data.py is the ONLY place nav links are listed.
  - Each page's Primary, Mobile and Footer nav blocks are located by
    their stable aria-label anchors and REPLACED wholesale — never
    patched, never inserted-into. Rebuilding is what makes a run
    idempotent. The replacement normalizes the whitespace after the
    opening tag (the renderer owns the layout); the whitespace before
    the closing tag is the page's own framing and is kept verbatim.
  - Which variant a page carries is site configuration — the tables
    below, adjusted ONCE here, never per wave.
  - index.html and press-kit.html are bespoke (registered in nav_data
    as HOME_* / PRESSKIT_*): their link sequences are verified, their
    markup is never rewritten. 404.html carries no nav and is skipped.
  - Generator-owned pages are rebuilt here too, and every generator
    that embeds nav markup renders it from the same nav_data, so a
    rebuild and a regeneration agree. (Rotation 14 completed the
    rewiring: build_changelog, build_sessions and build_scene_atlas
    joined the set; the remaining generators in the chain are
    data-only and own no nav markup — their pages are hand pages
    whose blocks this injector rebuilds and --check verifies.)

Usage:
  python3 scripts/update_nav.py           rewrite stale pages in place
  python3 scripts/update_nav.py --check   exit 1 listing stale pages,
                                          write nothing (wave checks)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import nav_data  # noqa: E402

PRIMARY_RE = re.compile(
    r'(<nav class="site-nav" aria-label="Primary">\s*)(.*?)(\s*</nav>)',
    re.S)
MOBILE_RE = re.compile(
    r'(<nav class="mnav-panel" aria-label="Mobile">\s*)(.*?)(\s*</nav>)',
    re.S)
FOOTER_RE = re.compile(
    r'(<nav aria-label="Footer">\s*)(.*?)(\s*</nav>)', re.S)
LINK_RE = re.compile(r'<a href="([^"]+)"[^>]*>([^<]+)</a>')

# Root pages by variant. Directories are tabled in DIR_VARIANTS.
ROOT_VARIANTS = {
    "agents.html": "agents",
    "api-playground.html": "agents",
    "decoder.html": "agents",
    "transmission.html": "agents",
    "changelog.html": "ledger",
    "chronicle.html": "ledger",
    "glance.html": "ledger",
    "milestone-race.html": "ledger",
    "sessions.html": "ledger",
    "sessions-explorer.html": "ledger",
    "codex-network.html": "anchored",
    "network.html": "anchored",
    "timeline.html": "anchored",
    "method.html": "standard",
    "scene-atlas.html": "standard",
    "trilogy.html": "standard",
    "tuner.html": "standard",
    "signal.html": "scene",
}
DIR_VARIANTS = {
    "releases": "compact",
    "circle": "circle",
    "codex": "codex",
    "producers": "producers",
    "eras": "eras",
    "sessions": "eras",
    "years": "years",
    "scene": "scene",
}
# Scene pages carrying the full standard nav instead of the scene cut.
SCENE_STANDARD = {"index.html", "uncle-release-week.html"}
# Bespoke pages: sequence-verified, never rewritten.
CHECK_ONLY = {"index.html", "press-kit.html"}
# Root pages whose aria-current marker names another page's href.
CURRENT_OVERRIDE = {"sessions-explorer.html": "sessions.html"}
# Footer doors dropped beyond the variant's own rule, per page.
FOOTER_DROP_EXTRA = {
    "scene/index.html": ("#discography",),
    "scene/uncle-release-week.html": ("#discography", "scene/"),
}


def page_config(path):
    """(variant, prefix, current, check_only) for a page, or None to
    skip it entirely (404.html — no nav blocks)."""
    rel = path.relative_to(ROOT)
    name = path.name
    if len(rel.parts) == 1:
        if name == "404.html":
            return None
        if name in CHECK_ONLY:
            return ("bespoke", "", None, True)
        variant = ROOT_VARIANTS[name]
        prefix = ""
        # aria-current: root pages mark their own door when it is in
        # the variant (subdir pages never mark).
        hrefs = [h for h, _ in nav_data.VARIANTS[variant]]
        current = CURRENT_OVERRIDE.get(
            name, name if name in hrefs else None)
        return (variant, prefix, current, False)
    prefix = "../" * (len(rel.parts) - 1)
    if rel.parts[0] == "scene" and name in SCENE_STANDARD:
        return ("standard-scene", prefix, None, False)
    return (DIR_VARIANTS[rel.parts[0]], prefix, None, False)


def rebuild(text, current, prefix, variant, drop_extra=()):
    """Return `text` with its Primary/Mobile/Footer navs rebuilt from
    nav_data. Group 1 (opening tag + whitespace) is normalized per the
    canonical pattern; group 3 (framing before the close) is kept."""
    items = nav_data.primary_nav_html(current, prefix, variant)
    new = PRIMARY_RE.sub(
        lambda m: m.group(1).rstrip() + "\n" + items + m.group(3),
        text, count=1)
    new = MOBILE_RE.sub(
        lambda m: m.group(1).rstrip() + "\n" + items + m.group(3),
        new, count=1)
    foot = nav_data.footer_nav_html(current or "", prefix, variant,
                                    drop_extra)
    new = FOOTER_RE.sub(
        lambda m: m.group(1).rstrip() + "\n" + foot + m.group(3),
        new, count=1)
    return new


def _links(block):
    return [(h, label) for h, label in LINK_RE.findall(block)]


def bespoke_ok(text, name):
    """Verify a check-only page's link sequences against nav_data."""
    def block(rx):
        m = rx.search(text)
        return _links(m.group(2)) if m else None
    if name == "index.html":
        exp_primary = nav_data.HOME_NAV
        exp_mobile = nav_data.HOME_NAV + nav_data.HOME_MOBILE_EXTRA
        exp_footer = nav_data.HOME_FOOTER
    else:  # press-kit.html
        exp_primary = [(nav_data._resolve(h, ""), label)
                       for h, label in nav_data.PRESSKIT_NAV]
        exp_mobile = exp_primary
        exp_footer = [(nav_data._resolve(h, ""), label)
                      for h, label in nav_data.PRESSKIT_FOOTER]
        return (block(PRIMARY_RE) == exp_primary
                and block(MOBILE_RE) == exp_mobile
                and block(FOOTER_RE) == exp_footer)
    return (block(PRIMARY_RE) == exp_primary
            and block(MOBILE_RE) == exp_mobile
            and block(FOOTER_RE) == exp_footer)


def pages():
    for path in sorted(ROOT.rglob("*.html")):
        if "__pycache__" in path.parts:
            continue
        yield path


def main():
    check = "--check" in sys.argv
    changed, stale_bespoke, skipped = [], [], 0
    for path in pages():
        cfg = page_config(path)
        if cfg is None:
            skipped += 1
            continue
        variant, prefix, current, check_only = cfg
        text = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(ROOT))
        if check_only:
            if not bespoke_ok(text, path.name):
                stale_bespoke.append(rel)
            continue
        drop_extra = FOOTER_DROP_EXTRA.get(rel, ())
        new = rebuild(text, current, prefix, variant, drop_extra)
        if new != text:
            changed.append(rel)
            if not check:
                path.write_text(new, encoding="utf-8")
    if check:
        bad = changed + stale_bespoke
        if bad:
            print(f"nav STALE on {len(bad)} pages: {', '.join(bad)}")
            return 1
        print(f"nav in sync on all pages ({skipped} skipped: no nav)")
        return 0
    print(f"nav updated on {len(changed)} pages: "
          f"{', '.join(changed) if changed else '(none)'}")
    if stale_bespoke:
        print(f"bespoke sequence drift: {', '.join(stale_bespoke)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
