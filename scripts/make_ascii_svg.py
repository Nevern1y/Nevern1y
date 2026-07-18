#!/usr/bin/env python3
"""Turn a portrait or the current GitHub avatar into animated ASCII SVG art."""

from __future__ import annotations

import argparse
import html
import os
from io import BytesIO
from http.client import HTTPSConnection
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "avi-ascii.svg"
AVATAR_PATH = "/u/77607229?v=4&size=512"
RAMP = "@%#*+=-:. "
COLS = 72
ROWS = 40


def load_image(source: Path | None) -> Image.Image:
    from PIL import Image

    if source:
        return Image.open(source)
    connection = HTTPSConnection("avatars.githubusercontent.com", timeout=30)
    try:
        connection.request(
            "GET",
            AVATAR_PATH,
            headers={"User-Agent": "Nevern1y-profile-readme/1.0"},
        )
        response = connection.getresponse()
        body = response.read()
        if response.status != 200:
            raise RuntimeError(f"Avatar request returned HTTP {response.status}")
        return Image.open(BytesIO(body))
    finally:
        connection.close()


def prepare_image(image: Image.Image, tight_crop: bool = False) -> Image.Image:
    from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

    image = ImageOps.exif_transpose(image).convert("RGBA")
    side = min(image.size)
    if tight_crop:
        side = int(side * 0.88)
        left = min(image.width - side, int(image.width * 0.10))
        top = min(image.height - side, int(image.height * 0.01))
    else:
        left = (image.width - side) // 2
        top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side))

    background = Image.new("RGBA", image.size, "white")
    background.alpha_composite(image)
    rgb = background.convert("RGB")

    circle = Image.new("L", rgb.size, 0)
    ImageDraw.Draw(circle).ellipse((2, 2, side - 3, side - 3), fill=255)
    isolated = Image.new("RGB", rgb.size, "white")
    isolated.paste(rgb, mask=circle)

    gray = ImageOps.grayscale(isolated)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    edges = gray.filter(ImageFilter.FIND_EDGES).point(lambda value: int(value * 0.45))
    gray = gray.point(
        lambda value: min(255, int(255 * ((value / 255) ** 0.60) * 1.08 + 6))
    )
    gray = ImageChops.subtract(gray, edges)
    gray = ImageEnhance.Contrast(gray).enhance(1.12)
    gray = ImageEnhance.Sharpness(gray).enhance(1.25)
    return gray.resize((COLS, ROWS), Image.Resampling.LANCZOS)


def to_ascii(image: Image.Image) -> list[str]:
    lines: list[str] = []
    for y in range(ROWS):
        chars = []
        for x in range(COLS):
            value = image.getpixel((x, y))
            if value >= 205:
                chars.append(" ")
            else:
                index = min(len(RAMP) - 1, value * len(RAMP) // 256)
                chars.append(RAMP[index])
        lines.append("".join(chars))
    return lines


def build_svg(lines: list[str], static: bool = False) -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 370" role="img" aria-labelledby="title description">',
        '<title id="title">Animated ASCII portrait of Islam Kusainov</title>',
        '<desc id="description">A monochrome portrait typed diagonally one row at a time.</desc>',
        """<defs>
  <linearGradient id="portrait-panel" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#0b1118"/>
    <stop offset="1" stop-color="#101c25"/>
  </linearGradient>
</defs>
<style>
  text { font-family: "Cascadia Mono", "JetBrains Mono", Consolas, monospace; }
  .ascii { fill: #b9cad5; font-size: 7.2px; font-weight: 600; }
  @media (prefers-reduced-motion: reduce) { .reveal-clip { width: 334px !important; } .cursor { display: none; } }
</style>""",
        '<rect x="1" y="1" width="378" height="368" rx="18" fill="url(#portrait-panel)" stroke="#263746" stroke-width="2"/>',
        '<path d="M1 47H379" stroke="#22313e"/>',
        '<circle cx="23" cy="24" r="5" fill="#ff6b6b"/><circle cx="41" cy="24" r="5" fill="#ffd166"/><circle cx="59" cy="24" r="5" fill="#2be3a7"/>',
        '<text x="82" y="29" fill="#d8e5ed" font-size="14" font-weight="600">avatar.txt</text>',
    ]

    x = 23
    text_width = 334
    start_y = 66
    line_height = 7.35
    for index, line in enumerate(lines):
        y = start_y + index * line_height
        begin = 0.22 + index * 0.055
        clip_id = f"row-{index}"
        parts.append(
            f'<clipPath id="{clip_id}"><rect class="reveal-clip" x="{x}" y="{y - 7:.2f}" width="{text_width}" height="9">'
        )
        if not static:
            parts.append(
                '<set attributeName="width" to="0" begin="0s" fill="freeze"/>'
                f'<animate attributeName="width" from="0" to="{text_width}" dur=".42s" begin="{begin:.3f}s" fill="freeze"/>'
            )
        parts.append("</rect></clipPath>")
        parts.append(
            f'<text class="ascii" x="{x}" y="{y:.2f}" textLength="{text_width}" '
            f'lengthAdjust="spacingAndGlyphs" clip-path="url(#{clip_id})" xml:space="preserve">{html.escape(line)}</text>'
        )
        if not static:
            parts.append(
                f'<rect class="cursor" x="{x}" y="{y - 6.8:.2f}" width="4" height="7.7" fill="#8fffd4" opacity="0">'
                f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.04;.9;1" dur=".42s" begin="{begin:.3f}s" fill="freeze"/>'
                f'<animate attributeName="x" from="{x}" to="{x + text_width}" dur=".42s" begin="{begin:.3f}s" fill="freeze"/>'
                "</rect>"
            )

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", type=Path, help="Optional local portrait")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args()

    lines = to_ascii(
        prepare_image(load_image(args.source), tight_crop=args.source is None)
    )
    static = args.static or os.environ.get("STATIC") == "1"
    args.output.write_text(build_svg(lines, static=static), encoding="utf-8")
    print(f"Rendered {COLS}x{ROWS} ASCII portrait to {args.output}")


if __name__ == "__main__":
    main()
