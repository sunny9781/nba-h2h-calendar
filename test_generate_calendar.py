from datetime import date, datetime, timezone
from unittest import TestCase
from unittest.mock import call, patch

import generate_calendar


class CurrentSeasonRangeTests(TestCase):
    def test_includes_finals_month_for_current_season(self):
        self.assertEqual(
            generate_calendar.current_season_range(date(2026, 10, 5)),
            (date(2026, 10, 1), date(2027, 6, 30)),
        )
        self.assertEqual(
            generate_calendar.current_season_range(date(2027, 6, 15)),
            (date(2026, 10, 1), date(2027, 6, 30)),
        )

    def test_july_selects_the_upcoming_season(self):
        self.assertEqual(
            generate_calendar.current_season_range(date(2027, 7, 1)),
            (date(2027, 10, 1), date(2028, 6, 30)),
        )


class CollectGamesTests(TestCase):
    def test_fetches_all_schedule_types_per_target_team(self):
        start = date(2026, 10, 1)
        end = date(2027, 6, 30)
        with (
            patch.object(
                generate_calendar, "current_season_range", return_value=(start, end)
            ),
            patch.object(
                generate_calendar, "fetch_team_schedule", return_value={"events": []}
            ) as fetch,
        ):
            generate_calendar.collect_games()

        self.assertEqual(
            fetch.call_args_list,
            [
                call(abbreviation, 2027, season_type)
                for abbreviation in generate_calendar.TARGET_TEAM_ABBREVIATIONS.values()
                for season_type in generate_calendar.SCHEDULE_TYPES
            ],
        )

    def test_calendar_events_omit_location(self):
        calendar = generate_calendar.build_calendar(
            {
                "game-1": {
                    "title": "Thunder @ Spurs",
                    "begin": datetime(2026, 10, 21, tzinfo=timezone.utc),
                    "description": "Head-to-Head Contender Matchup",
                }
            }
        )

        self.assertNotIn("LOCATION", calendar.serialize())
