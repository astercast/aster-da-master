#!/usr/bin/env python3
"""Wave 31 (THE PIRATE BROADCAST) identity wiring — idempotent.

For every generator script and hand-maintained page:
  1. Swap the Google Fonts link: Inter + JetBrains Mono -> IBM Plex Mono
     (Anton kept: the call-sign display, unique in the fleet).
  2. Add assets/css/motifs.css after components.css (same path prefix).
  3. Add assets/js/identity.js before </body> (same path prefix).

Re-running is a no-op. After running, re-run the generator chain so the
emitted pages pick up the new heads/feet (stage 6 of validate.sh then
re-runs the chain itself and must stay byte-stable).
"""
import re
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")

GENERATORS = [
    "scripts/build_changelog.py",
    "scripts/build_circle.py",
    "scripts/build_codex.py",
    "scripts/build_eras.py",
    "scripts/build_glance.py",
    "scripts/build_releases.py",
    "scripts/build_session_deepdives.py",
    "scripts/build_sessions.py",
    "scripts/build_years.py",
]

HAND_PAGES = [
    "scene/index.html",
    "scene/fish-narc-uncle.html",
    "scene/capoxxo-2026.html",
    "scene/lil-koi.html",
    "scene/lil-yu.html",
    "scene/pvscale.html",
    "scene/digicore-radar.html",
    "scene/unconfirmed-board.html",
    "agents.html",
    "api-playground.html",
    "codex-network.html",
    "decoder.html",
    "glance.html",
    "index.html",
    "method.html",
    "milestone-race.html",
    "network.html",
    "press-kit.html",
    "sessions.html",
    "sessions-explorer.html",
    "timeline.html",
    "transmission.html",
    "trilogy.html",
]

FONT_OLD = "family=Anton&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700"
FONT_NEW = "family=Anton&family=IBM+Plex+Mono:wght@400;500;600;700"


def edit(path: Path) -> dict:
    # NOTE (wave 31): generator templates carry PLAIN double quotes, not
    # backslash-escaped ones (verified by direct count) — one code path.
    text = path.read_text(encoding="utf-8")
    q = '"'
    stats = {"fonts": 0, "motifs": False, "identity": False}

    # 1. font swap
    if FONT_OLD in text:
        stats["fonts"] = text.count(FONT_OLD)
        text = text.replace(FONT_OLD, FONT_NEW)

    # 2. motifs.css after the components.css link (match the path prefix)
    if "motifs.css" not in text:
        m = re.search(
            r"<link rel=" + q + "stylesheet" + q + r" href=" + q
            + r"([^" + q + r"]*?)assets/css/components\.css" + q + r">",
            text,
        )
        if not m:
            raise SystemExit(f"no components.css link found in {path}")
        prefix = m.group(1)
        bs = ""
        insert = (
            "\n  <link rel=" + bs + '"stylesheet"' + bs + " href=" + bs + '"'
            + prefix + "assets/css/motifs.css" + bs + '">'
        )
        text = text[: m.end()] + insert + text[m.end():]
        stats["motifs"] = True

    # 3. identity.js before </body> (same prefix as the css chain)
    if "identity.js" not in text:
        m = re.search(
            r"<link rel=" + q + "stylesheet" + q + r" href=" + q
            + r"([^" + q + r"]*?)assets/css/components\.css" + q + r">",
            text,
        )
        prefix = m.group(1) if m else ""
        bs = ""
        tag = (
            '  <script src=' + bs + '"' + prefix + 'assets/js/identity.js"'
            + bs + "></script>\n"
        )
        if "</body>" not in text:
            raise SystemExit(f"no </body> found in {path}")
        text = text.replace("</body>", tag + "</body>", 1)
        stats["identity"] = True

    path.write_text(text, encoding="utf-8")
    return stats


def main() -> None:
    total = {"fonts": 0, "motifs": 0, "identity": 0}
    for rel in GENERATORS:
        s = edit(ROOT / rel)
        total["fonts"] += s["fonts"]
        total["motifs"] += s["motifs"]
        total["identity"] += s["identity"]
        print(f"gen  {rel}: fonts={s['fonts']} motifs+={s['motifs']} identity+={s['identity']}")
    for rel in HAND_PAGES:
        s = edit(ROOT / rel)
        total["fonts"] += s["fonts"]
        total["motifs"] += s["motifs"]
        total["identity"] += s["identity"]
        print(f"page {rel}: fonts={s['fonts']} motifs+={s['motifs']} identity+={s['identity']}")
    print(f"TOTAL: {total}")


if __name__ == "__main__":
    main()
