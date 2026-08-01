from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env", override=False)

UNSUPPORTED_SPORT_KEYS = frozenset({"tennis_atp", "tennis_wta"})
STANDARD_MARKETS = "h2h,spreads,totals"
GOLF_KEY = "golf_pga_championship_winner"
GOLF_MARKETS = "outrights"


def filter_supported_sports(
    sports: Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    return [item for item in sports if item[0] not in UNSUPPORTED_SPORT_KEYS]

def supports_game_card_input(league_label: str, game: dict[str, Any]) -> bool:
    if league_label != "Golf":
        return True
    return bool(game.get("home_team") and game.get("away_team"))




def main() -> int:
    engine_path = Path(sys.argv[1] if len(sys.argv) > 1 else "betting_report.py").resolve()
    if not engine_path.is_file():
        raise SystemExit(f"Betting engine not found: {engine_path}")

    sys.path.insert(0, str(engine_path.parent))
    spec = importlib.util.spec_from_file_location("gsr_betting_report", engine_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load Betting engine: {engine_path}")

    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)

    if engine.MARKETS != STANDARD_MARKETS:
        raise SystemExit(f"Unexpected standard markets: {engine.MARKETS}")
    if engine.SPORT_MARKETS.get(GOLF_KEY) != GOLF_MARKETS:
        raise SystemExit("Golf winner requests must use markets=outrights")

    configured = list(engine.SPORTS_TO_QUERY)
    engine.SPORTS_TO_QUERY = filter_supported_sports(configured)
    removed = [key for key, _ in configured if key in UNSUPPORTED_SPORT_KEYS]
    print(f"[GBR] Disabled unsupported Odds API sport keys: {','.join(removed) or 'none'}")
    original_build_game_card = engine.build_game_card

    def build_game_card(game: dict[str, Any], league_label: str):
        if not supports_game_card_input(league_label, game):
            return None
        return original_build_game_card(game, league_label)

    engine.build_game_card = build_game_card
    return int(engine.main())


if __name__ == "__main__":
    raise SystemExit(main())
