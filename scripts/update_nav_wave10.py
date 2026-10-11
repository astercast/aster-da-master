#!/usr/bin/env python3
"""One-off: insert Sessions + Changelog links into every <nav> block.

Run once after wave 10. Generator NAV constants are updated separately
so future regenerations keep the links.
"""
import re
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")
SUBDIRS = ("releases", "years", "circle", "codex")

NAV_RE = re.compile(r"<nav\b[^>]*>.*?</nav>", re.DOTALL)


def prefix_for(path: Path) -> str:
    rel = path.relative_to(ROOT).parts
    return "../" if rel and rel[0] in SUBDIRS else ""


def insert_links(nav_html: str, prefix: str) -> str:
    if "sessions.html" in nav_html:
        return nav_html  # already done
    s_link = f'<a href="{prefix}sessions.html">Sessions</a>'
    c_link = f'<a href="{prefix}changelog.html">Changelog</a>'
    anchor = '<a href="press-kit.html">Press kit</a>'
    anchor2 = f'<a href="{prefix}press-kit.html">Press kit</a>'
    for a in (anchor2, anchor):
        if a in nav_html:
            return nav_html.replace(a, f"{s_link}\n        {c_link}\n        {a}", 1)
    # fallback: before closing tag
    return nav_html.replace("</nav>", f"        {s_link}\n        {c_link}\n      </nav>", 1)


def main():
    changed = 0
    for html in sorted(ROOT.rglob("*.html")):
        if "__pycache__" in html.parts:
            continue
        text = html.read_text(encoding="utf-8")
        prefix = prefix_for(html)

        def repl(m):
            return insert_links(m.group(0), prefix)

        new, n = NAV_RE.subn(repl, text)
        if n and new != text:
            html.write_text(new, encoding="utf-8")
            changed += 1
    print(f"nav updated in {changed} files")


if __name__ == "__main__":
    main()
