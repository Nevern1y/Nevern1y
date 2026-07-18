#!/usr/bin/env python3
"""Fetch public GitHub contribution data without an API token."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from http.client import HTTPException, HTTPSConnection
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "contributions.json"
DEFAULT_USERNAME = "Nevern1y"
COUNT_RE = re.compile(r"\b([\d,]+)\s+contributions?\b", re.IGNORECASE)
USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


class ContributionsHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cells: list[dict[str, str]] = []
        self.tooltips: dict[str, str] = {}
        self._tooltip_for: str | None = None
        self._tooltip_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        classes = attributes.get("class", "").split()
        if (
            "ContributionCalendar-day" in classes
            and attributes.get("data-date")
            and attributes.get("data-level") is not None
        ):
            self.cells.append(attributes)
        if tag == "tool-tip" and attributes.get("for"):
            self._tooltip_for = attributes["for"]
            self._tooltip_text = []

    def handle_data(self, data: str) -> None:
        if self._tooltip_for is not None:
            self._tooltip_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tool-tip" and self._tooltip_for is not None:
            self.tooltips[self._tooltip_for] = " ".join(
                "".join(self._tooltip_text).split()
            )
            self._tooltip_for = None
            self._tooltip_text = []


def parse_contributions(html: str) -> list[dict[str, Any]]:
    """Extract dated contribution cells from GitHub's public calendar HTML."""
    parser = ContributionsHTMLParser()
    parser.feed(html)
    parser.close()
    by_date: dict[str, dict[str, Any]] = {}

    for cell in parser.cells:
        day = cell.get("data-date", "")
        try:
            date.fromisoformat(day)
            level = int(cell.get("data-level", "0"))
        except (TypeError, ValueError):
            continue

        raw_count = cell.get("data-count")
        if raw_count is not None:
            count = int(raw_count)
        else:
            label = parser.tooltips.get(cell.get("id", ""), "")
            match = COUNT_RE.search(label)
            if match:
                count = int(match.group(1).replace(",", ""))
            elif label.lower().startswith("no contributions"):
                count = 0
            else:
                raise RuntimeError(f"Could not read contribution count for {day}")

        by_date[day] = {
            "date": day,
            "count": count,
            "level": max(0, min(level, 4)),
        }

    return [by_date[key] for key in sorted(by_date)]


def validate_calendar(days: list[dict[str, Any]], expected_end: date) -> None:
    if not 365 <= len(days) <= 371:
        raise RuntimeError(
            f"Expected 365-371 calendar days, but GitHub returned {len(days)}"
        )

    parsed_dates = [date.fromisoformat(item["date"]) for item in days]
    for previous, current in zip(parsed_dates, parsed_dates[1:]):
        if current - previous != timedelta(days=1):
            raise RuntimeError(
                f"Contribution calendar has a gap between {previous} and {current}"
            )

    actual_end = parsed_dates[-1]
    if actual_end > expected_end or actual_end < expected_end - timedelta(days=1):
        raise RuntimeError(
            f"Contribution calendar ends on {actual_end}, expected {expected_end}"
        )


def calculate_stats(days: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate stable summary statistics from sorted contribution days."""
    if not days:
        raise ValueError("Contribution calendar is empty")

    ordered = sorted(days, key=lambda item: item["date"])
    longest = 0
    running = 0
    previous_date: date | None = None
    previous_active = False
    for item in ordered:
        current_date = date.fromisoformat(item["date"])
        if item["count"] > 0:
            consecutive = (
                previous_date is not None
                and current_date - previous_date == timedelta(days=1)
                and previous_active
            )
            running = running + 1 if consecutive else 1
            longest = max(longest, running)
        else:
            running = 0
        previous_date = current_date
        previous_active = item["count"] > 0

    end = len(ordered) - 1
    if ordered[end]["count"] == 0:
        end -= 1
    current = 0
    expected_date: date | None = None
    while end >= 0 and ordered[end]["count"] > 0:
        current_date = date.fromisoformat(ordered[end]["date"])
        if expected_date is not None and expected_date - current_date != timedelta(
            days=1
        ):
            break
        current += 1
        expected_date = current_date
        end -= 1

    best = max(ordered, key=lambda item: (item["count"], item["date"]))
    monthly: defaultdict[str, int] = defaultdict(int)
    for item in ordered:
        monthly[item["date"][:7]] += item["count"]

    return {
        "total": sum(item["count"] for item in ordered),
        "active_days": sum(item["count"] > 0 for item in ordered),
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly_totals": dict(sorted(monthly.items())),
    }


def fetch_calendar(username: str) -> str:
    if not USERNAME_RE.fullmatch(username):
        raise ValueError(f"Invalid GitHub username: {username!r}")

    path = f"/users/{username}/contributions"
    headers = {
        "Accept": "text/html",
        "User-Agent": f"{username}-profile-readme/1.0",
    }
    last_error: Exception | None = None
    for attempt in range(3):
        connection = HTTPSConnection("github.com", timeout=30)
        try:
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            body = response.read()
            if response.status == 200:
                charset = response.headers.get_content_charset() or "utf-8"
                return body.decode(charset)
            if response.status not in {429, 500, 502, 503, 504}:
                raise RuntimeError(
                    f"GitHub contribution request returned HTTP {response.status}"
                )
            last_error = RuntimeError(f"GitHub returned HTTP {response.status}")
        except (TimeoutError, OSError, HTTPException) as error:
            last_error = error
        finally:
            connection.close()

        if attempt < 2:
            time.sleep(2**attempt)

    raise RuntimeError(
        "GitHub contribution request failed after 3 attempts"
    ) from last_error


def build_payload(username: str, html: str) -> dict[str, Any]:
    days = parse_contributions(html)
    validate_calendar(days, expected_end=datetime.now(timezone.utc).date())

    return {
        "username": username,
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "range": {"from": days[0]["date"], "to": days[-1]["date"]},
        "days": days,
        "stats": calculate_stats(days),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--username",
        default=os.environ.get("GITHUB_USERNAME", DEFAULT_USERNAME),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--html", type=Path, help="Parse a saved HTML response")
    args = parser.parse_args()

    html = (
        args.html.read_text(encoding="utf-8")
        if args.html
        else fetch_calendar(args.username)
    )
    payload = build_payload(args.username, html)
    if args.output.exists():
        try:
            existing = json.loads(args.output.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}
        comparable_keys = ("username", "range", "days", "stats")
        if all(existing.get(key) == payload.get(key) for key in comparable_keys):
            payload["generated_at"] = existing.get(
                "generated_at", payload["generated_at"]
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Saved {len(payload['days'])} days and "
        f"{payload['stats']['total']} contributions to {args.output}"
    )


if __name__ == "__main__":
    main()
