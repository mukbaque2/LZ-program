"""Generate lz.ico: two intertwined helical strands.

Run from the project root:
    python tools/make_icon.py

Kept as a script rather than a committed binary blob nobody can edit, so the
icon can be changed by changing the drawing instead of by finding whatever
tool produced it.

Drawn at 8x and downsampled, because PIL's ImageDraw has no antialiasing;
supersampling is the usual way around that and costs nothing at this size.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

SIZES = [16, 24, 32, 48, 64, 128, 256]
SUPERSAMPLE = 8

# Two strands, distinguishable in both light and dark title bars.
STRAND_A = (38, 132, 143, 255)    # teal
STRAND_B = (214, 137, 16, 255)    # amber
BACKGROUND = (0, 0, 0, 0)         # transparent


def _strand(draw: ImageDraw.ImageDraw, size: int, phase: float,
            colour: tuple[int, int, int, int], width: int) -> None:
    """One strand of the coil, as a sine wave running down the canvas."""
    amplitude = size * 0.26
    centre = size / 2
    margin = size * 0.10
    turns = 2.25

    points = []
    steps = 240
    for i in range(steps + 1):
        t = i / steps
        y = margin + t * (size - 2 * margin)
        x = centre + amplitude * math.sin(2 * math.pi * turns * t + phase)
        points.append((x, y))

    draw.line(points, fill=colour, width=width, joint="curve")

    # Round the ends: `joint="curve"` smooths corners but leaves flat caps.
    r = width / 2
    for x, y in (points[0], points[-1]):
        draw.ellipse([x - r, y - r, x + r, y + r], fill=colour)


def render(size: int) -> Image.Image:
    big = size * SUPERSAMPLE
    img = Image.new("RGBA", (big, big), BACKGROUND)
    draw = ImageDraw.Draw(img)

    width = max(2, int(big * 0.085))
    # Draw the back strand first so the front one overlaps it, which reads as
    # a coil rather than as two separate squiggles.
    _strand(draw, big, math.pi, STRAND_B, width)
    _strand(draw, big, 0.0, STRAND_A, width)

    return img.resize((size, size), Image.LANCZOS)


def main() -> int:
    out = Path(__file__).resolve().parent.parent / "lz.ico"
    frames = [render(s) for s in SIZES]
    frames[-1].save(out, format="ICO",
                    sizes=[(s, s) for s in SIZES],
                    append_images=frames[:-1])
    print(f"wrote {out} ({', '.join(f'{s}x{s}' for s in SIZES)})")

    preview = out.with_name("lz-icon-preview.png")
    render(256).save(preview)
    print(f"wrote {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
