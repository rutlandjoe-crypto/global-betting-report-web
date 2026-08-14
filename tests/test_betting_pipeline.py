from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import build_betting_distribution as builder
import get_betting_odds_report as generator
from scripts import check_betting_agent
from scripts import promote_betting_report


def market(name: str, outcomes: list[dict]) -> dict:
    return {
        "name": name,
        "books": [{"name": "DraftKings", "removed": False, "outcomes": outcomes}],
    }


def event(index: int, start_time: str) -> dict:
    return {
        "sport_event": {
            "id": f"sr:sport_event:{index}",
            "start_time": start_time,
            "competitors": [
                {"name": f"Away {index}", "qualifier": "away"},
                {"name": f"Home {index}", "qualifier": "home"},
            ],
        },
        "markets": [
            market("2way", [
                {"type": "away", "odds_american": "+120"},
                {"type": "home", "odds_american": "-135"},
            ]),
            market("handicap", [
                {"type": "away", "spread": "+1.5", "odds_american": "-110"},
                {"type": "home", "spread": "-1.5", "odds_american": "-110"},
            ]),
            market("total", [
                {"type": "over", "total": "8.5", "odds_american": "-105"},
                {"type": "under", "total": "8.5", "odds_american": "-115"},
            ]),
        ],
    }


class FakeClient:
    def __init__(self):
        self.calls = 0

    def competition_markets(self, competition_id: str) -> dict:
        now = generator.utc_now()
        offset = self.calls * 2
        self.calls += 1
        return {
            "generated_at": now.isoformat(),
            "sport_event_markets": [
                event(offset + 1, (now + timedelta(hours=offset + 1)).isoformat()),
                event(offset + 2, (now + timedelta(hours=offset + 2)).isoformat()),
            ],
        }


class BettingPipelineTests(unittest.TestCase):
    def test_sportradar_native_decimal_market_shape_is_publishable(self):
        now = generator.utc_now()
        payload = {
            "generated_at": now.isoformat(),
            "sport_event_markets": [
                {
                    "sport_event": {
                        "id": "sr:sport_event:native",
                        "scheduled": (now + timedelta(hours=2)).isoformat(),
                        "competitors": [
                            {"name": "Away Native", "qualifier": "away"},
                            {"name": "Home Native", "qualifier": "home"},
                        ],
                        "markets": [
                            market("2way", [
                                {"type": "away", "odds": "2.20"},
                                {"type": "home", "odds": "1.74"},
                            ]),
                            market("handicap", [
                                {"type": "away", "spread": 1.5, "odds": "1.91"},
                                {"type": "home", "spread": -1.5, "odds": "1.91"},
                            ]),
                            market("total", [
                                {"type": "over", "total": 8.5, "odds": "1.95"},
                                {"type": "under", "total": 8.5, "odds": "1.87"},
                            ]),
                        ],
                    }
                }
            ],
        }

        entries = generator.market_entries(payload)
        self.assertEqual(len(entries), 1)
        lines = generator.event_lines(entries[0], now)
        self.assertIsNotNone(lines)
        rendered = "\n".join(lines or [])
        self.assertIn("Away Native at Home Native", rendered)
        self.assertIn("Away Native +120", rendered)
        self.assertIn("Home Native -135", rendered)

    def test_quality_gate_checks_only_authoritative_public_output(self):
        self.assertEqual(check_betting_agent.REPORT_PATHS, [Path("public/latest_report.json")])

    def test_sourced_report_handoff_and_public_schema(self):
        run_token = "test-current-run-token"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path = root / "betting_odds_report.txt"
            marker_path = root / ".gbr_betting_success.json"
            with (
                patch.object(generator, "REPORT_FILE", report_path),
                patch.object(generator, "SUCCESS_MARKER", marker_path),
                patch.object(generator, "RUN_TOKEN", run_token),
            ):
                report = generator.generate_betting_odds_report(FakeClient())

            self.assertNotIn("fallback", report.lower())
            self.assertNotIn("monitoring window", report.lower())
            marker_data = json.loads(marker_path.read_text(encoding="utf-8"))
            self.assertEqual(marker_data["valid_event_count"], 8)
            self.assertEqual(marker_data["run_token"], run_token)

            public_dir = root / "public"
            output_json = public_dir / "latest_report.json"
            output_txt = public_dir / "latest_report.txt"
            with (
                patch.object(builder, "REPORT_FILE", report_path),
                patch.object(builder, "SUCCESS_MARKER", marker_path),
                patch.object(builder, "PUBLIC_DIR", public_dir),
                patch.object(builder, "OUTPUT_JSON", output_json),
                patch.object(builder, "OUTPUT_TXT", output_txt),
                patch.dict(os.environ, {"GBR_RUN_TOKEN": run_token}),
            ):
                self.assertEqual(builder.main(), 0)

            payload = json.loads(output_json.read_text(encoding="utf-8"))

            self.assertEqual(len(payload["homepage_cards"]), 8)
            self.assertEqual(
                set(payload),
                {
                    "site", "site_name", "vertical", "title", "headline", "snapshot",
                    "updated_at", "generated_at", "generated_utc", "source_mode",
                    "homepage_cards", "live_newsroom", "editor_signals", "sections",
                    "verification",
                },
            )
            self.assertEqual(
                payload["verification"]["provider"],
                "Sportradar Odds Comparison Prematch v2",
            )
            self.assertEqual(promote_betting_report.verified_output_count(payload), 8)

    def test_handoff_rejects_wrong_run_token(self):
        with tempfile.TemporaryDirectory() as directory:
            marker_path = Path(directory) / ".gbr_betting_success.json"
            marker_path.write_text("{}", encoding="utf-8")
            with (
                patch.object(builder, "SUCCESS_MARKER", marker_path),
                patch.dict(os.environ, {"GBR_RUN_TOKEN": "current"}),
            ):
                with self.assertRaisesRegex(ValueError, "run token"):
                    builder.validate_current_run_source("sourced report")

    def test_builder_does_not_create_placeholder_cards(self):
        with self.assertRaisesRegex(ValueError, "valid sourced Betting cards"):
            builder.build_payload("NBA\nMonitoring window only")


if __name__ == "__main__":
    unittest.main()
