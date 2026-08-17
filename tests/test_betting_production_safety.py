import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import build_betting_distribution
import get_betting_odds_report as odds_report
import master_runner
from scripts.promote_betting_report import promote
from scripts.run_external_betting_engine import (
    GOLF_KEY,
    GOLF_MARKETS,
    STANDARD_MARKETS,
    filter_supported_sports,
    supports_game_card_input,
)


ROOT = Path(__file__).resolve().parents[1]


def fixture_report(generated: datetime, *, verified: bool = True) -> dict:
    cards = []
    for index in range(8):
        cards.append(
            {
                "headline": f"Team {index} at Team {index + 1}",
                "verified_markets": ["h2h"] if verified else [],
            }
        )
    return {
        "site": "Global Betting Report",
        "vertical": "Betting",
        "generated_utc": generated.isoformat(),
        "generated_at": generated.isoformat(),
        "homepage_cards": cards,
        "live_newsroom": cards[:5],
    }


def write_report(path: Path, payload: dict) -> bytes:
    raw = (json.dumps(payload, indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


class FailingClient:
    def competition_markets(self, competition_id):
        raise odds_report.ProviderError("Sportradar returned HTTP 403: Authentication Error")


class EmptyClient:
    def competition_markets(self, competition_id):
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sport_event_markets": [],
        }


class BettingProductionSafetyTests(unittest.TestCase):
    def test_external_engine_filters_only_unsupported_tennis_keys(self):
        configured = [
            ("baseball_mlb", "MLB"),
            ("basketball_nba", "NBA"),
            ("tennis_atp", "Tennis"),
            ("tennis_wta", "Tennis"),
            (GOLF_KEY, "Golf"),
        ]

        self.assertEqual(
            [
                ("baseball_mlb", "MLB"),
                ("basketball_nba", "NBA"),
                (GOLF_KEY, "Golf"),
            ],
            filter_supported_sports(configured),
        )
        self.assertEqual("h2h,spreads,totals", STANDARD_MARKETS)
        self.assertEqual("outrights", GOLF_MARKETS)
        self.assertFalse(
            supports_game_card_input(
                "Golf", {"home_team": None, "away_team": None}
            )
        )
        self.assertTrue(
            supports_game_card_input("MLB", {"home_team": "Home", "away_team": "Away"})
        )

    def test_403_leaves_last_valid_output_byte_for_byte_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = temp / "betting_odds_report.txt"
            marker = temp / ".gbr_betting_success.json"
            canonical = temp / "public" / "latest_report.json"
            old_source = b"last valid verified betting report\n"
            old_canonical = b'{"last":"valid"}\n'
            source.write_bytes(old_source)
            canonical.parent.mkdir()
            canonical.write_bytes(old_canonical)

            with patch.object(odds_report, "REPORT_FILE", source), patch.object(
                odds_report, "SUCCESS_MARKER", marker
            ):
                with self.assertRaisesRegex(odds_report.ProviderError, "HTTP 403"):
                    odds_report.generate_betting_odds_report(FailingClient())

            self.assertEqual(old_source, source.read_bytes())
            self.assertEqual(old_canonical, canonical.read_bytes())
            self.assertFalse(marker.exists())

    def test_zero_provider_events_leave_last_valid_source_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = temp / "betting_odds_report.txt"
            marker = temp / ".gbr_betting_success.json"
            old_source = b"last valid verified betting report\n"
            source.write_bytes(old_source)

            with patch.object(odds_report, "REPORT_FILE", source), patch.object(
                odds_report, "SUCCESS_MARKER", marker
            ):
                with self.assertRaisesRegex(odds_report.ProviderError, "Only 0 valid sourced events"):
                    odds_report.generate_betting_odds_report(EmptyClient())

            self.assertEqual(old_source, source.read_bytes())
            self.assertFalse(marker.exists())

    def test_stale_root_cannot_overwrite_fresher_canonical(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            root = temp / "latest_report.json"
            canonical = temp / "public" / "latest_report.json"
            write_report(root, fixture_report(now - timedelta(hours=2)))
            canonical_bytes = write_report(canonical, fixture_report(now))

            with self.assertRaisesRegex(ValueError, "not newer"):
                promote(root, canonical, now - timedelta(hours=3))

            self.assertEqual(canonical_bytes, canonical.read_bytes())

    def test_authorized_fixture_promotes_only_verified_fresh_output(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = temp / "generated.json"
            canonical = temp / "public" / "latest_report.json"
            compatibility = temp / "latest_report.json"
            expected = write_report(source, fixture_report(now))

            promote(
                source,
                canonical,
                now - timedelta(minutes=1),
                compatibility,
            )

            self.assertEqual(expected, canonical.read_bytes())
            self.assertEqual(expected, compatibility.read_bytes())

    def test_verified_receipt_builds_only_the_canonical_public_report(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = temp / "betting_odds_report.txt"
            source.write_bytes(b"current sourced Sportradar report\n")
            marker = temp / ".gbr_betting_success.json"
            run_token = "current-test-run"
            marker.write_text(
                json.dumps(
                    {
                        "source": "sportradar_oddscomparison_prematch_v2",
                        "source_generated_at": now.isoformat(),
                        "valid_event_count": 8,
                        "valid_market_count": 8,
                        "run_token": run_token,
                        "generated_utc": now.isoformat(),
                        "report_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )
            public = temp / "public"
            canonical = public / "latest_report.json"
            text_output = public / "latest_report.txt"

            with patch.object(
                build_betting_distribution, "REPORT_FILE", source
            ), patch.object(
                build_betting_distribution, "SUCCESS_MARKER", marker
            ), patch.object(
                build_betting_distribution, "PUBLIC_DIR", public
            ), patch.object(
                build_betting_distribution, "OUTPUT_JSON", canonical
            ), patch.object(
                build_betting_distribution, "OUTPUT_TXT", text_output
            ), patch.object(
                build_betting_distribution,
                "build_payload",
                return_value=fixture_report(now),
            ), patch.dict(
                build_betting_distribution.os.environ,
                {"GBR_RUN_TOKEN": run_token},
            ):
                self.assertEqual(0, build_betting_distribution.main())

            payload = json.loads(canonical.read_text(encoding="utf-8"))
            self.assertEqual("verified", payload["verification"]["status"])
            self.assertEqual(
                "Sportradar Odds Comparison Prematch v2",
                payload["verification"]["provider"],
            )
            self.assertGreaterEqual(len(payload["homepage_cards"]), 8)
            self.assertFalse((temp / "latest_report.json").exists())

    def test_zero_verified_output_is_rejected_without_overwrite(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = temp / "generated.json"
            canonical = temp / "public" / "latest_report.json"
            write_report(source, fixture_report(now, verified=False))
            canonical_bytes = write_report(
                canonical, fixture_report(now - timedelta(hours=1))
            )

            with self.assertRaisesRegex(ValueError, "zero verified"):
                promote(source, canonical, now - timedelta(minutes=1))

            self.assertEqual(canonical_bytes, canonical.read_bytes())

    def test_failed_ingestion_blocks_distribution(self):
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory) / "public" / "latest_report.json"
            canonical.parent.mkdir()
            canonical.write_bytes(b"last valid canonical report\n")

            with patch.object(
                master_runner,
                "SCRIPTS",
                [
                    ("get_betting_odds_report.py", 1, True),
                    ("build_betting_distribution.py", 1, True),
                ],
            ), patch.object(
                master_runner, "REQUIRED_OUTPUTS", [canonical]
            ), patch.object(
                master_runner,
                "run_script",
                return_value=("failed", "HTTP 403 Authentication Error", 0.1),
            ) as run_script, patch.object(
                master_runner, "acquire_lock", return_value=True
            ), patch.object(
                master_runner, "release_lock"
            ), patch.object(
                master_runner, "write_last_run_status"
            ), patch.object(
                master_runner, "log"
            ), patch.object(
                master_runner, "log_blank_line"
            ), patch.object(
                master_runner.os, "chdir"
            ):
                self.assertEqual(1, master_runner.main())

            run_script.assert_called_once_with("get_betting_odds_report.py", 1)
            self.assertEqual(b"last valid canonical report\n", canonical.read_bytes())

    def test_workflows_restore_crons_and_validate_before_commit(self):
        hourly = ROOT / ".github/workflows/betting-agent-hourly.yml"
        cloud = (ROOT / ".github/workflows/gsr-cloud-run.yml").read_text()
        self.assertFalse(hourly.exists())
        self.assertIn('cron: "0 * * * *"', cloud)
        self.assertIn("workflow_dispatch:", cloud)
        self.assertIn("SPORTRADAR_API_KEY", cloud)
        self.assertNotIn("ODDS_API_KEY", cloud)
        self.assertNotIn("python betting_report.py", cloud)
        self.assertNotIn("Copy-Item ./latest_report.json ./public/latest_report.json", cloud)
        self.assertLess(
            cloud.index("Validate current canonical Betting report"),
            cloud.index("Commit updated site data if changed"),
        )
        self.assertNotIn("continue-on-error", cloud)
        self.assertIn('BETTING_PUSH_URL="${GSR_PUSH_URL/https:\\/\\/globalbettingreport.com/https:\\/\\/www.globalbettingreport.com}"', cloud)
        self.assertIn("curl -sS --fail --location", cloud)

    def test_active_text_artifacts_do_not_contain_blocked_fallback_copy(self):
        blocked = ("books wait on prices", "board takes shape")
        for relative in ("betting_odds_report.txt", "public/latest_report.txt"):
            path = ROOT / relative
            if path.exists():
                lowered = path.read_text(encoding="utf-8", errors="ignore").lower()
                self.assertFalse([phrase for phrase in blocked if phrase in lowered])

        runner = (ROOT / "master_runner.py").read_text(encoding="utf-8")
        self.assertNotIn("verified Odds API ingestion", runner)


if __name__ == "__main__":
    unittest.main()
