import json
import unittest
from copy import deepcopy
from pathlib import Path

from get_betting_news_report import extract_article_links
from scripts.link_betting_app_report import link_report
from scripts.build_betting_editorial_archive import is_durable_editorial


class BettingAppLinkTests(unittest.TestCase):
    def setUp(self):
        card = {
            "headline": "NFL: Home Club favored vs Away Club (-150)",
            "matchup": "Away Club at Home Club", "story_type": "market_signal",
            "url": "https://www.espn.com/nfl/scoreboard",
            "snapshot": "Home Club is the favorite based on the listed moneyline.",
            "key_data": ["Home Club -150 and Away Club +130 moneylines.", "Spread: Home Club -3 (-110), Away Club +3 (-110).", "Total: 45.5 points (Over -110 / Under -110)."],
            "why_it_matters": ["The spread frames the expected margin."],
            "what_to_watch": ["Injury confirmations before kickoff."],
            "verified_markets": ["moneyline", "spread", "total"],
        }
        self.report = {
            "updated_at": "2026-10-27T18:00:00Z",
            "homepage_cards": [card], "live_newsroom": [deepcopy(card)],
            "sections": {"nfl": {"cards": [deepcopy(card)]}},
            "verification": {"status": "verified", "provider": "The Odds API v4"},
        }

    def test_every_current_market_card_has_a_matching_readable_page(self):
        before = deepcopy(self.report)
        payload, archive = link_report(self.report, [])
        slugs = {story["slug"] for story in archive}
        for collection in ("homepage_cards", "live_newsroom"):
            for card in payload[collection]:
                self.assertIn("/editorial/", card["url"])
                self.assertIn(card["url"].rsplit("/", 1)[-1], slugs)
        self.assertEqual(before, self.report)
        self.assertEqual(before["verification"], payload["verification"])

    def test_news_retains_original_headline_url_and_attribution(self):
        news = {"headline": "Home Club vs Away Club betting analysis", "source": "Action Network", "url": "https://www.actionnetwork.com/nfl/home-club-away-club-analysis"}
        payload, _ = link_report(self.report, [], [news, news])
        self.assertEqual(news["headline"], payload["live_newsroom"][0]["headline"])
        self.assertEqual(news["url"], payload["live_newsroom"][0]["url"])
        self.assertEqual(news["source"], payload["live_newsroom"][0]["source_name"])
        self.assertEqual(len(self.report["live_newsroom"]) + 1, len(payload["live_newsroom"]))

    def test_provider_status_and_bare_odds_are_not_archived(self):
        card = deepcopy(self.report["homepage_cards"][0])
        card.pop("verified_markets", None)
        card["snapshot"] = "Short odds row"
        self.assertFalse(is_durable_editorial(card))

    def test_unreadable_scoreboard_card_blocks_publication(self):
        self.report["homepage_cards"][0]["verified_markets"] = []
        with self.assertRaisesRegex(ValueError, "no readable matchup page"):
            link_report(self.report, [])

    def test_source_navigation_and_off_site_links_are_rejected(self):
        html = '''<a href="/nfl/odds">NFL odds and betting lines</a>
        <a href="https://other.example/a-long-article-slug">A different website betting article</a>
        <a href="/nfl/home-away-betting-analysis">Home &amp; Away betting analysis today</a>'''
        links = extract_article_links(html, "https://www.actionnetwork.com")
        self.assertEqual(1, len(links))
        self.assertEqual("Home & Away betting analysis today", links[0]["headline"])


if __name__ == "__main__":
    unittest.main()
