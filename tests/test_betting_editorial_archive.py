from __future__ import annotations

import unittest

from scripts.build_betting_editorial_archive import (
    build_archive,
    is_durable_editorial,
    stories_from_report,
)


def story(*, price: str = "-120", summary: str | None = None) -> dict:
    return {
        "league": "MLB",
        "headline": "Away Club at Home Club - 7:10 PM ET",
        "snapshot": summary
        or (
            f"Moneyline sets the win-probability baseline: Away Club +105 / Home Club {price}. "
            "Spread frames the expected margin and the total frames the scoring environment."
        ),
        "story_type": "market_context",
        "key_data": [f"Home Club moneyline {price}"],
        "why_it_matters": ["Pitching confirmations and weather can move totals quickly."],
        "what_to_watch": ["Starting pitcher confirmations before first pitch."],
        "url": "https://www.globalbettingreport.com",
    }


def report(date: str, time: str, card: dict | None = None) -> dict:
    return {
        "updated_at": f"{date} 07:00:00 PM ET",
        "generated_utc": f"{date}T{time}+00:00",
        "homepage_cards": [card or story()],
    }


class BettingEditorialArchiveTests(unittest.TestCase):
    def test_bare_odds_rows_are_not_editorial(self):
        self.assertFalse(
            is_durable_editorial(
                {
                    "headline": "Away Club at Home Club",
                    "snapshot": "Away Club +105 / Home Club -120",
                    "url": "https://example.com/odds",
                }
            )
        )

    def test_contextual_matchup_gets_a_dated_permanent_slug(self):
        stories = stories_from_report(report("2026-08-17", "23:00:00"))
        self.assertEqual(1, len(stories))
        self.assertEqual("2026-08-17-away-club-at-home-club", stories[0]["slug"])
        self.assertTrue(stories[0]["whyItMatters"])
        self.assertTrue(stories[0]["whatToWatch"])

    def test_hourly_price_changes_do_not_create_thin_duplicate_pages(self):
        early = report("2026-08-17", "20:00:00", story(price="-120"))
        late = report("2026-08-17", "23:00:00", story(price="-135"))
        next_day = report("2026-08-18", "23:00:00", story(price="-110"))

        stories = build_archive([early, late, next_day])

        self.assertEqual(2, len(stories))
        latest_same_day = next(item for item in stories if item["reportDate"] == "2026-08-17")
        self.assertIn("-135", " ".join(latest_same_day["market"]))


if __name__ == "__main__":
    unittest.main()
