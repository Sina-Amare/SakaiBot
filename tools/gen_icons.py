"""Generate the PWA / favicon icon set from the master Aigram logo.

Drop the AI-generated logo at ``src/panel/static/icons/aigram-logo.png`` (a
square PNG, ideally 1024x1024 or larger), then run from the repo root:

    python tools/gen_icons.py

It writes every size the app references (PWA icons, maskable, apple-touch, and
a small favicon) with high-quality resampling. The master logo already carries
its own dark rounded tile + safe padding, so it doubles as the maskable icon.
"""

import sys
from pathlib import Path

from PIL import Image

ICONS = Path(__file__).resolve().parents[1] / "src" / "panel" / "static" / "icons"
MASTER = ICONS / "aigram-logo.png"

# (filename, size). apple-touch must be opaque; the logo tile already is.
TARGETS = [
    ("icon-192.png", 192),
    ("icon-512.png", 512),
    ("icon-maskable-512.png", 512),  # logo tile fills the square -> valid maskable
    ("apple-touch-icon.png", 180),
    ("favicon-32.png", 32),
]


def main() -> int:
    if not MASTER.exists():
        print(f"Master logo not found: {MASTER}\n"
              f"Save the square logo PNG there first, then re-run.")
        return 1
    src = Image.open(MASTER).convert("RGBA")
    if src.width != src.height:
        print(f"Warning: logo is {src.width}x{src.height}, not square — "
              f"it will be resized to a square anyway.")
    for name, size in TARGETS:
        out = src.resize((size, size), Image.LANCZOS)
        dest = ICONS / name
        if name == "apple-touch-icon.png":
            # flatten onto the logo's own dark tile colour (no alpha for iOS)
            bg = Image.new("RGB", (size, size), (7, 11, 12))
            bg.paste(out, (0, 0), out)
            bg.save(dest, "PNG")
        else:
            out.save(dest, "PNG")
        print(f"wrote {dest.relative_to(ICONS.parents[3])} ({size}x{size})")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
