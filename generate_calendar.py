#!/usr/bin/env python3
"""Fetch NBA scoreboard data and write a head-to-head .ics calendar."""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from ics import Calendar, Event
from ics.grammar.parse import ContentLine

TARGET_TEAMS = {
    "Oklahoma City Thunder",
    "San Antonio Spurs",
    "New York Knicks",
    "Philadelphia 76ers",
    "Boston Celtics",
    "Miami Heat",
    "Denver Nuggets",
    "Minnesota Timberwolves",
    "Toronto Raptors",
}

SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
)
OUTPUT_PATH = Path(__file__).resolve().parent / "nba_head_to_head.ics"
USER_AGENT = (
    "nba-h2h-calendar/1.0 (+https://github.com; ESPN public scoreboard client)"
)
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1.5


def current_season_range(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    if today.month >= 10:
        start = date(today.year, 10, 1)
        end = date(today.year + 1, 5, 31)
    else:
        start = date(today.year - 1, 10, 1)
        end = date(today.year, 5, 31)
    return start, end


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def fetch_scoreboard(day: date) -> dict[str, Any]:
    params = {"dates": day.strftime("%Y%m%d")}
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                SCOREBOARD_URL, params=params, headers=headers, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise RuntimeError(f"Failed to fetch scoreboard for {day}: {last_error}") from last_error


def parse_utc(timestamp: str) -> datetime:
    normalized = timestamp.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def extract_matchup(event: dict[str, Any]) -> tuple[str, str, str] | None:
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    competition = competitions[0]
    home_name = None
    away_name = None
    for competitor in competition.get("competitors") or []:
        name = (competitor.get("team") or {}).get("displayName")
        home_away = competitor.get("homeAway")
        if home_away == "home":
            home_name = name
        elif home_away == "away":
            away_name = name
    if not home_name or not away_name:
        return None
    venue = ((competition.get("venue") or {}).get("fullName")) or ""
    return away_name, home_name, venue


def build_calendar(events_by_id: dict[str, dict[str, Any]]) -> Calendar:
    calendar = Calendar()
    calendar.extra.append(ContentLine(name="X-WR-CALNAME", value="NBA Head-to-Head"))
    for game_id, payload in sorted(events_by_id.items(), key=lambda item: item[1]["begin"]):
        event = Event()
        event.uid = f"{game_id}@nba-h2h-calendar"
        event.name = payload["title"]
        event.begin = payload["begin"]
        event.description = payload["description"]
        if payload["location"]:
            event.location = payload["location"]
        calendar.events.add(event)
    return calendar


def collect_games() -> dict[str, dict[str, Any]]:
    start, end = current_season_range()
    matched: dict[str, dict[str, Any]] = {}
    print(f"Fetching NBA scoreboard {start.isoformat()} through {end.isoformat()}...")
    for day in daterange(start, end):
        data = fetch_scoreboard(day)
        for event in data.get("events") or []:
            game_id = str(event.get("id") or "")
            if not game_id or game_id in matched:
                continue
            matchup = extract_matchup(event)
            if not matchup:
                continue
            away_name, home_name, venue = matchup
            if away_name not in TARGET_TEAMS or home_name not in TARGET_TEAMS:
                continue
            tip_off = event.get("date")
            if not tip_off:
                continue
            matched[game_id] = {
                "title": f"🏀 {away_name} @ {home_name}",
                "begin": parse_utc(tip_off),
                "location": venue,
                "description": (
                    f"Head-to-Head Contender Matchup: {away_name} vs {home_name}"
                ),
            }
    return matched


def main() -> None:
    matched = collect_games()
    calendar = build_calendar(matched)
    OUTPUT_PATH.write_text(calendar.serialize(), encoding="utf-8")
    print(f"Wrote {len(matched)} games to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
