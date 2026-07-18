from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

from scripts.fetch_contributions import (
    calculate_stats,
    parse_contributions,
    validate_calendar,
)
from scripts.make_ascii_svg import build_svg as build_ascii_svg
from scripts.make_info_card import build_svg as build_info_svg
from scripts.render_heatmap_svg import build_svg


ROOT = Path(__file__).resolve().parents[1]


class ContributionDataTests(unittest.TestCase):
    def test_parser_reads_counts_and_levels(self) -> None:
        markup = """
        <table>
          <td id="d1" class="ContributionCalendar-day" data-date="2026-07-16" data-level="2"></td>
          <tool-tip for="d1">7 contributions on July 16th.</tool-tip>
          <td id="d2" class="ContributionCalendar-day" data-date="2026-07-17" data-level="0"></td>
          <tool-tip for="d2">No contributions on July 17th.</tool-tip>
          <td id="d3" class="ContributionCalendar-day" data-date="2026-07-18" data-level="1"></td>
          <tool-tip for="d3">1 contribution on July 18th.</tool-tip>
        </table>
        """
        self.assertEqual(
            parse_contributions(markup),
            [
                {"date": "2026-07-16", "count": 7, "level": 2},
                {"date": "2026-07-17", "count": 0, "level": 0},
                {"date": "2026-07-18", "count": 1, "level": 1},
            ],
        )

    def test_stats_include_streaks_and_best_day(self) -> None:
        days = [
            {"date": "2026-07-13", "count": 2, "level": 1},
            {"date": "2026-07-14", "count": 3, "level": 2},
            {"date": "2026-07-15", "count": 0, "level": 0},
            {"date": "2026-07-16", "count": 5, "level": 3},
            {"date": "2026-07-17", "count": 1, "level": 1},
            {"date": "2026-07-18", "count": 0, "level": 0},
        ]
        stats = calculate_stats(days)
        self.assertEqual(stats["total"], 11)
        self.assertEqual(stats["active_days"], 4)
        self.assertEqual(stats["current_streak"], 2)
        self.assertEqual(stats["longest_streak"], 2)
        self.assertEqual(stats["best_day"], {"date": "2026-07-16", "count": 5})

    def test_calendar_validation_rejects_gaps_and_stale_data(self) -> None:
        start = date(2025, 7, 19)
        days = [
            {
                "date": (start + timedelta(days=offset)).isoformat(),
                "count": 0,
                "level": 0,
            }
            for offset in range(365)
        ]
        validate_calendar(days, expected_end=date.fromisoformat(days[-1]["date"]))

        gapped = (
            days[:180]
            + days[181:]
            + [
                {
                    "date": (start + timedelta(days=365)).isoformat(),
                    "count": 0,
                    "level": 0,
                }
            ]
        )
        with self.assertRaisesRegex(RuntimeError, "gap"):
            validate_calendar(gapped, expected_end=start + timedelta(days=365))
        with self.assertRaisesRegex(RuntimeError, "ends on"):
            validate_calendar(days, expected_end=start + timedelta(days=367))

    def test_renderer_emits_valid_svg(self) -> None:
        days = [
            {"date": "2026-07-12", "count": 0, "level": 0},
            {"date": "2026-07-13", "count": 2, "level": 1},
        ]
        payload = {
            "username": "Nevern1y",
            "days": days,
            "stats": calculate_stats(days),
        }
        root = ET.fromstring(build_svg(payload, static=True))
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")

    def test_animated_art_has_visible_static_fallbacks(self) -> None:
        ascii_svg = build_ascii_svg([" " * 72])
        info_svg = build_info_svg()
        payload = {
            "username": "Nevern1y",
            "days": [
                {"date": "2026-07-12", "count": 0, "level": 0},
                {"date": "2026-07-13", "count": 2, "level": 1},
            ],
        }
        payload["stats"] = calculate_stats(payload["days"])
        heatmap_svg = build_svg(payload)
        self.assertIn('class="reveal-clip"', ascii_svg)
        self.assertIn('width="334"', ascii_svg)
        self.assertIn('<set attributeName="width" to="0"', ascii_svg)
        self.assertNotIn('class="motion" opacity="0"', info_svg)
        self.assertNotIn('class="motion" opacity="0"', heatmap_svg)

    def test_generated_artifacts_are_valid(self) -> None:
        for filename in ("avi-ascii.svg", "info-card.svg", "contrib-heatmap.svg"):
            with self.subTest(filename=filename):
                ET.parse(ROOT / filename)
        payload = json.loads(
            (ROOT / "data" / "contributions.json").read_text(encoding="utf-8")
        )
        validate_calendar(
            payload["days"], expected_end=date.fromisoformat(payload["range"]["to"])
        )


if __name__ == "__main__":
    unittest.main()
