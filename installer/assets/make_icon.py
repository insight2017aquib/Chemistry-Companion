"""Generate multi-size Chemistry Companion application icon (.ico)."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent


def make_icon(size: int) -> Image.Image:
    """Rounded blue badge with a simple 3-atom molecule motif."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    margin = max(1, size // 16)
    radius = max(2, size // 5)
    bg = (3, 102, 214, 255)  # sci-blue
    d.rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=radius,
        fill=bg,
    )

    cx, cy = size / 2, size / 2
    r = max(2, size // 9)
    bond_w = max(1, size // 18)
    radius_orbit = size * 0.22
    pts = []
    for ang in (-90, 30, 150):
        rad = math.radians(ang)
        pts.append((cx + radius_orbit * math.cos(rad), cy + radius_orbit * math.sin(rad)))

    for i in range(3):
        a, b = pts[i], pts[(i + 1) % 3]
        d.line([a, b], fill=(255, 255, 255, 230), width=bond_w)

    for x, y in pts:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 255))

    rc = max(1, r // 2)
    d.ellipse([cx - rc, cy - rc, cx + rc, cy + rc], fill=(200, 230, 255, 255))
    return img


def main() -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [make_icon(s) for s in sizes]
    ico_path = OUT_DIR / "chemistry_companion.ico"
    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    make_icon(256).save(OUT_DIR / "chemistry_companion_256.png")
    make_icon(64).save(OUT_DIR / "chemistry_companion_64.png")
    print(f"Wrote {ico_path} ({ico_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
