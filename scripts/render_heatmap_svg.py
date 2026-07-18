#!/usr/bin/env python3
"""Render the public contribution calendar as an animated terminal SVG."""

from __future__ import annotations

import argparse
import html
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "contributions.json"
DEFAULT_OUTPUT = ROOT / "contrib-heatmap.svg"
WIDTH = 900
HEIGHT = 250
GRID_X = 60
GRID_Y = 67
CELL = 11
PITCH = 15
PALETTE = ["#17212b", "#123f3a", "#0d6b5d", "#15a57f", "#2be3a7", "#8fffd4"]
MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def _xml(value: object) -> str:
    return html.escape(str(value), quote=True)


def _month_labels(
    days: list[dict[str, Any]], first_sunday: date
) -> list[tuple[int, str]]:
    labels: list[tuple[int, str]] = []
    seen: set[tuple[int, int]] = set()
    last_x = -100
    for item in sorted(days, key=lambda row: row["date"]):
        current = date.fromisoformat(item["date"])
        key = (current.year, current.month)
        if key in seen:
            continue
        seen.add(key)
        week = (current - first_sunday).days // 7
        x = GRID_X + week * PITCH
        if x - last_x >= 34:
            labels.append((x, MONTHS[current.month - 1]))
            last_x = x
    return labels


def build_svg(payload: dict[str, Any], static: bool = False) -> str:
    days = sorted(payload["days"], key=lambda item: item["date"])
    if not days:
        raise ValueError("No contribution days to render")

    first = date.fromisoformat(days[0]["date"])
    first_sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    stats = payload["stats"]
    username = payload.get("username", "GitHub")
    best = stats.get("best_day", {"date": "n/a", "count": 0})
    max_count = max(item["count"] for item in days)

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 250" role="img" aria-labelledby="title description">',
        f'<title id="title">{_xml(username)} contribution activity</title>',
        '<desc id="description">An animated 53-week calendar generated from public GitHub contribution data.</desc>',
        """<defs>
  <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#0b1118"/>
    <stop offset="1" stop-color="#101c25"/>
  </linearGradient>
  <filter id="soft-glow" x="-80%" y="-80%" width="260%" height="260%">
    <feGaussianBlur stdDeviation="2.4" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<style>
  text { font-family: "Cascadia Code", "JetBrains Mono", Consolas, monospace; }
  .muted { fill: #73889a; }
  .label { fill: #91a4b5; font-size: 10px; }
  @media (prefers-reduced-motion: reduce) { .motion { opacity: 1 !important; transform: none !important; } }
</style>""",
        '<rect x="1" y="1" width="898" height="248" rx="18" fill="url(#panel)" stroke="#263746" stroke-width="2"/>',
        '<path d="M1 47H899" stroke="#22313e"/>',
        '<circle cx="23" cy="24" r="5" fill="#ff6b6b"/><circle cx="41" cy="24" r="5" fill="#ffd166"/><circle cx="59" cy="24" r="5" fill="#2be3a7"/>',
    ]

    intro_attributes = "" if static else ' class="motion"'
    intro_motion = (
        ""
        if static
        else (
            '<set attributeName="opacity" to="0" begin="0s" fill="freeze"/>'
            '<animate attributeName="opacity" from="0" to="1" dur=".45s" begin=".08s" fill="freeze"/>'
            '<animateTransform attributeName="transform" type="translate" from="0 5" to="0 0" dur=".45s" begin=".08s" fill="freeze"/>'
        )
    )
    parts.append(
        f'<g{intro_attributes}>{intro_motion}<text x="82" y="29" fill="#d8e5ed" font-size="14" font-weight="600">{_xml(username.lower())}@github:~$ contributions --public</text><text x="849" y="29" fill="#2be3a7" font-size="13">LIVE</text></g>'
    )

    for x, label in _month_labels(days, first_sunday):
        parts.append(f'<text class="label" x="{x}" y="59">{label}</text>')

    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = GRID_Y + row * PITCH + 9
        parts.append(f'<text class="label" x="22" y="{y}">{label}</text>')

    for item in days:
        current = date.fromisoformat(item["date"])
        week = (current - first_sunday).days // 7
        weekday = (current.weekday() + 1) % 7
        x = GRID_X + week * PITCH
        y = GRID_Y + weekday * PITCH
        level = int(item["level"])
        if item["count"] == max_count and max_count > 0:
            level = 5
        delay = 0.12 + (week + weekday) * 0.018
        attributes = "" if static else ' class="motion"'
        motion = (
            ""
            if static
            else (
                '<set attributeName="opacity" to="0" begin="0s" fill="freeze"/>'
                f'<animate attributeName="opacity" from="0" to="1" dur=".42s" begin="{delay:.3f}s" fill="freeze"/>'
                f'<animateTransform attributeName="transform" type="translate" from="0 -13" to="0 0" dur=".42s" begin="{delay:.3f}s" fill="freeze"/>'
            )
        )
        glow = ' filter="url(#soft-glow)"' if level == 5 else ""
        count_label = "contribution" if item["count"] == 1 else "contributions"
        parts.append(
            f'<rect{attributes} x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" '
            f'fill="{PALETTE[level]}" data-count="{item["count"]}"{glow}>{motion}'
            f"<title>{item['date']}: {item['count']} {count_label}</title></rect>"
        )

    footer_y = 207
    footer_attributes = "" if static else ' class="motion"'
    footer_motion = (
        ""
        if static
        else (
            '<set attributeName="opacity" to="0" begin="0s" fill="freeze"/>'
            '<animate attributeName="opacity" from="0" to="1" dur=".45s" begin=".65s" fill="freeze"/>'
            '<animateTransform attributeName="transform" type="translate" from="0 5" to="0 0" dur=".45s" begin=".65s" fill="freeze"/>'
        )
    )
    parts.extend(
        [
            '<path d="M22 184H878" stroke="#22313e"/>',
            f'<g{footer_attributes}>{footer_motion}<text x="24" y="{footer_y}" fill="#d8e5ed" font-size="14" font-weight="700">{stats["total"]:,}</text><text x="24" y="224" class="muted" font-size="10">CONTRIBUTIONS</text></g>',
            f'<g{footer_attributes}>{footer_motion}<text x="190" y="{footer_y}" fill="#d8e5ed" font-size="14" font-weight="700">{stats["active_days"]}</text><text x="190" y="224" class="muted" font-size="10">ACTIVE DAYS</text></g>',
            f'<g{footer_attributes}>{footer_motion}<text x="330" y="{footer_y}" fill="#d8e5ed" font-size="14" font-weight="700">{stats["current_streak"]}d</text><text x="330" y="224" class="muted" font-size="10">CURRENT STREAK</text></g>',
            f'<g{footer_attributes}>{footer_motion}<text x="482" y="{footer_y}" fill="#d8e5ed" font-size="14" font-weight="700">{stats["longest_streak"]}d</text><text x="482" y="224" class="muted" font-size="10">LONGEST STREAK</text></g>',
            f'<g{footer_attributes}>{footer_motion}<text x="634" y="{footer_y}" fill="#d8e5ed" font-size="14" font-weight="700">{best["count"]}</text><text x="634" y="224" class="muted" font-size="10">BEST / {best["date"]}</text></g>',
            '<g transform="translate(772 201)"><text x="-30" y="8" class="muted" font-size="9">LESS</text>',
        ]
    )
    for index, color in enumerate(PALETTE):
        parts.append(
            f'<rect x="{index * 15}" y="0" width="10" height="10" rx="2" fill="{color}"/>'
        )
    parts.extend(
        ['<text x="94" y="8" class="muted" font-size="9">MORE</text></g>', "</svg>"]
    )
    return "\n".join(parts) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    static = args.static or os.environ.get("STATIC") == "1"
    args.output.write_text(build_svg(payload, static=static), encoding="utf-8")
    print(f"Rendered {len(payload['days'])} contribution cells to {args.output}")


if __name__ == "__main__":
    main()
