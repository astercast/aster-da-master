#!/usr/bin/env python3
"""One-off: insert the "Scene" link into every site <nav> block
(primary + mobile + footer).

Run once after the wave-30 merge. Also updates the NAV/FOOTNAV constants inside
scripts/build_*.py so future regenerations keep the link.

Rule: a "Timeline" link alone on its line is a site nav entry (breadcrumbs
keep anchors on one line with " / " separators and are skipped). The Scene
link goes immediately before the Timeline link -- i.e. after 'Circle',
before 'Timeline' -- keeping the scene section with the town map.

Release pages use a compact nav with no Timeline link: follow the wave-13/14
rule and place Scene after the API link instead.

Idempotent: files already carrying the Scene link are skipped.
"""
import re
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")
SUBDIRS = ("releases", "years", "circle", "codex", "sessions",
           "scene", "producers", "eras")

TIMELINE_RE = re.compile(
    r'^(?P<indent>[ \t]*)<a href="(?P<prefix>(?:\.\./)?)timeline\.html"[^>]*>Timeline</a>\n',
    re.MULTILINE,
)
API_RE = re.compile(
    r'^(?P<indent>[ \t]*)<a href="(?P<prefix>(?:\.\./)?)api-playground\.html"[^>]*>API</a>\n',
    re.MULTILINE,
)
GUARD = ">Scene</a>"


def prefix_for(path: Path) -> str:
    rel = path.relative_to(ROOT).parts
    return "../" if rel and rel[0] in SUBDIRS else ""


def insert_before_timeline(text: str, prefix: str) -> str:
    def repl(m):
        if m.group("prefix") != prefix:
            return m.group(0)
        indent = m.group("indent")
        return f'{indent}<a href="{prefix}scene/">Scene</a>\n' + m.group(0)
    return TIMELINE_RE.sub(repl, text)


def insert_after_api(text: str, prefix: str) -> str:
    def repl(m):
        if m.group("prefix") != prefix:
            return m.group(0)
        indent = m.group("indent")
        return m.group(0) + f'{indent}<a href="{prefix}scene/">Scene</a>\n'
    return API_RE.sub(repl, text)


def main():
    changed = 0
    targets = (sorted(ROOT.rglob("*.html"))
               + sorted((ROOT / "scripts").glob("build_*.py")))
    for path in targets:
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if GUARD in text:
            continue  # already ships the Scene link
        if path.suffix == ".html":
            prefix = prefix_for(path)
            new = insert_before_timeline(text, prefix)
            # compact nav (no Timeline link): fall back to after-API rule
            if new == text:
                new = insert_after_api(text, prefix)
        else:
            # .py generators carry both "" and "../" variants; apply both
            new = insert_before_timeline(text, "")
            new = insert_before_timeline(new, "../")
            # compact nav fallback (build_releases), both variants
            if new == text:
                new = insert_after_api(text, "")
                new = insert_after_api(new, "../")
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print("updated", path.relative_to(ROOT))
    print(f"{changed} files updated")


if __name__ == "__main__":
    main()
