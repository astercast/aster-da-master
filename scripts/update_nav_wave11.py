#!/usr/bin/env python3
"""One-off: insert the Glance link into every <nav> block (primary + footer).

Run once after wave 11. Generator NAV constants are updated separately
so future regenerations keep the link.
"""
import re
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")
SUBDIRS = ("releases", "years", "circle", "codex", "sessions")

NAV_RE = re.compile(r"<nav\b[^>]*>.*?</nav>", re.DOTALL)


def prefix_for(path: Path) -> str:
    rel = path.relative_to(ROOT).parts
    return "../" if rel and rel[0] in SUBDIRS else ""


def insert_link(nav_html: str, prefix: str) -> str:
    if "glance.html" in nav_html:
        return nav_html  # already done
    link = f'<a href="{prefix}glance.html">Glance</a>'
    anchor = f'<a href="{prefix}press-kit.html">Press kit</a>'
    if anchor in nav_html:
        return nav_html.replace(anchor, f"{link}\n        {anchor}", 1)
    return nav_html.replace("</nav>", f"        {link}\n      </nav>", 1)


def main():
    changed = 0
    for html in sorted(ROOT.rglob("*.html")):
        if "__pycache__" in html.parts:
            continue
        text = html.read_text(encoding="utf-8")
        prefix = prefix_for(html)

        def repl(m):
            return insert_link(m.group(0), prefix)

        new, n = NAV_RE.subn(repl, text)
        if n and new != text:
            html.write_text(new, encoding="utf-8")
            changed += 1
    print(f"nav updated in {changed} files")


if __name__ == "__main__":
    main()
