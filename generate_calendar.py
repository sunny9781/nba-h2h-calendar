#!/usr/bin/env python3
"""Fetch NBA scoreboard data and write a head-to-head .ics calendar."""

from __future__ import annotations

import time
from datetime import date, datetime, timezone
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
TARGET_TEAM_ABBREVIATIONS = {
    "Oklahoma City Thunder": "okc",
    "San Antonio Spurs": "sas",
    "New York Knicks": "nyk",
    "Philadelphia 76ers": "phi",
    "Boston Celtics": "bos",
    "Miami Heat": "mia",
    "Denver Nuggets": "den",
    "Minnesota Timberwolves": "min",
    "Toronto Raptors": "tor",
}

TEAM_SCHEDULE_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"
)
OUTPUT_PATH = Path(__file__).resolve().parent / "nba_head_to_head.ics"
USER_AGENT = (
    "nba-h2h-calendar/1.0 (+https://github.com; ESPN public scoreboard client)"
)
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1.5
SCHEDULE_TYPES = (1, 2, 3)


def current_season_range(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    if today.month >= 7:
        season_start_year = today.year
    else:
        season_start_year = today.year - 1
    start = date(season_start_year, 10, 1)
    end = date(season_start_year + 1, 6, 30)
    return start, end


def fetch_team_schedule(
    team_abbreviation: str, season: int, season_type: int
) -> dict[str, Any]:
    params = {"season": season, "seasontype": season_type}
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                f"{TEAM_SCHEDULE_URL}/{team_abbreviation}/schedule",
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise RuntimeError(
        f"Failed to fetch season type {season_type} schedule for "
        f"{team_abbreviation} in {season}: {last_error}"
    ) from last_error


def parse_utc(timestamp: str) -> datetime:
    normalized = timestamp.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def extract_matchup(event: dict[str, Any]) -> tuple[str, str] | None:
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
    return away_name, home_name


def build_calendar(events_by_id: dict[str, dict[str, Any]]) -> Calendar:
    calendar = Calendar()
    calendar.extra.append(ContentLine(name="X-WR-CALNAME", value="NBA Head-to-Head"))
    for game_id, payload in sorted(events_by_id.items(), key=lambda item: item[1]["begin"]):
        event = Event()
        event.uid = f"{game_id}@nba-h2h-calendar"
        event.name = payload["title"]
        event.begin = payload["begin"]
        event.description = payload["description"]
        calendar.events.add(event)
    return calendar


def collect_games() -> dict[str, dict[str, Any]]:
    _, end = current_season_range()
    season = end.year
    matched: dict[str, dict[str, Any]] = {}
    print(
        f"Fetching {season - 1}-{str(season)[-2:]} NBA team schedules "
        f"for {len(TARGET_TEAM_ABBREVIATIONS)} teams..."
    )
    for team_abbreviation in TARGET_TEAM_ABBREVIATIONS.values():
        for season_type in SCHEDULE_TYPES:
            data = fetch_team_schedule(team_abbreviation, season, season_type)
            for event in data.get("events") or []:
                game_id = str(event.get("id") or "")
                if not game_id or game_id in matched:
                    continue
                matchup = extract_matchup(event)
                if not matchup:
                    continue
                away_name, home_name = matchup
                if away_name not in TARGET_TEAMS or home_name not in TARGET_TEAMS:
                    continue
                tip_off = event.get("date")
                if not tip_off:
                    continue
                matched[game_id] = {
                    "title": f"🏀 {away_name} @ {home_name}",
                    "begin": parse_utc(tip_off),
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
