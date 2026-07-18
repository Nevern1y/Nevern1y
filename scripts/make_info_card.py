#!/usr/bin/env python3
"""Generate a one-shot animated neofetch-style profile card."""

from __future__ import annotations

import html
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "info-card.svg"
ROWS = [
    ("name", "Islam Kusainov"),
    ("role", "AI / ML builder"),
    ("focus", "LLM safety + GeoAI"),
    ("stack", "Python / TypeScript"),
    ("tools", "Streamlit / React / Docker"),
    ("now", "GemmaJudge + Aral Saxaul AI"),
    ("mode", "research -> production"),
]


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def build_svg(static: bool = False) -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 370" role="img" aria-labelledby="title description">',
        '<title id="title">Islam Kusainov profile card</title>',
        '<desc id="description">A terminal-style card showing current AI and software engineering interests.</desc>',
        """<defs>
  <linearGradient id="card" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#0b1118"/>
    <stop offset="1" stop-color="#101c25"/>
  </linearGradient>
  <pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse">
    <path d="M22 0H0V22" fill="none" stroke="#7dd3fc" stroke-opacity=".035"/>
  </pattern>
</defs>
<style>
  text { font-family: "Cascadia Code", "JetBrains Mono", Consolas, monospace; }
  @media (prefers-reduced-motion: reduce) { .motion { opacity: 1 !important; transform: none !important; } .cursor { opacity: 1 !important; } }
</style>""",
        '<rect x="1" y="1" width="498" height="368" rx="18" fill="url(#card)" stroke="#263746" stroke-width="2"/>',
        '<rect x="1" y="1" width="498" height="368" rx="18" fill="url(#grid)"/>',
        '<path d="M1 47H499" stroke="#22313e"/>',
        '<circle cx="23" cy="24" r="5" fill="#ff6b6b"/><circle cx="41" cy="24" r="5" fill="#ffd166"/><circle cx="59" cy="24" r="5" fill="#2be3a7"/>',
        '<text x="82" y="29" fill="#d8e5ed" font-size="14" font-weight="600">identity.sh</text>',
        '<text x="467" y="29" fill="#708596" font-size="12" text-anchor="end">01</text>',
        '<text x="28" y="76" fill="#2be3a7" font-size="13">$ neofetch --compact</text>',
    ]

    for index, (key, value) in enumerate(ROWS):
        y = 111 + index * 32
        delay = 0.28 + index * 0.11
        motion = ""
        attributes = ""
        if not static:
            attributes = ' class="motion"'
            motion = (
                '<set attributeName="opacity" to="0" begin="0s" fill="freeze"/>'
                f'<animate attributeName="opacity" from="0" to="1" dur=".38s" begin="{delay:.2f}s" fill="freeze"/>'
                f'<animateTransform attributeName="transform" type="translate" from="-10 0" to="0 0" dur=".38s" begin="{delay:.2f}s" fill="freeze"/>'
            )
        parts.append(
            f'<g{attributes}>{motion}<text x="29" y="{y}" fill="#7dd3fc" '
            f'font-size="14" font-weight="700">{esc(key)}</text>'
            f'<text x="124" y="{y}" fill="#6b7f90" font-size="14">::</text>'
            f'<text x="153" y="{y}" fill="#d8e5ed" font-size="14">{esc(value)}</text></g>'
        )

    footer_attributes = "" if static else ' class="motion"'
    footer_motion = (
        ""
        if static
        else (
            '<set attributeName="opacity" to="0" begin="0s" fill="freeze"/>'
            '<animate attributeName="opacity" from="0" to="1" dur=".38s" begin="1.12s" fill="freeze"/>'
            '<animateTransform attributeName="transform" type="translate" from="-10 0" to="0 0" dur=".38s" begin="1.12s" fill="freeze"/>'
        )
    )
    cursor_motion = (
        ""
        if static
        else (
            '<animate attributeName="opacity" values="1;0;1" dur=".85s" begin="1.45s" repeatCount="4" fill="freeze"/>'
        )
    )
    parts.extend(
        [
            '<path d="M28 328H472" stroke="#22313e"/>',
            f'<g{footer_attributes}>{footer_motion}<text x="28" y="352" fill="#2be3a7" font-size="13">nevern1y@github</text><text x="164" y="352" fill="#708596" font-size="13">:~$</text><rect class="cursor" x="198" y="341" width="8" height="14" rx="1" fill="#8fffd4">{cursor_motion}</rect></g>',
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def main() -> None:
    static = os.environ.get("STATIC") == "1"
    OUTPUT.write_text(build_svg(static=static), encoding="utf-8")
    print(f"Rendered profile card to {OUTPUT}")


if __name__ == "__main__":
    main()
