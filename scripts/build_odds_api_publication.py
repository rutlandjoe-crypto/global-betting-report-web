from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import betting_odds


PUBLIC_JSON = ROOT / "public" / "latest_report.json"
PUBLIC_TEXT = ROOT / "public" / "latest_report.txt"
ROOT_JSON = ROOT / "betting_odds_report.json"
ROOT_TEXT = ROOT / "betting_odds_report.txt"
MIN_CARDS = 8
MIN_CREDITS_BEFORE_RUN = 20
PROVIDER = "The Odds API v4"


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        Path(temp_name).replace(path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def quota_preflight(api_key: str) -> int:
    response = requests.get(
        "https://api.the-odds-api.com/v4/sports/",
        params={"apiKey": api_key},
        headers=betting_odds.HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    remaining_text = response.headers.get("x-requests-remaining")
    if remaining_text is None:
        raise RuntimeError("Odds API did not return the remaining-credit header")
    remaining = int(remaining_text)
    if remaining < MIN_CREDITS_BEFORE_RUN:
        raise RuntimeError(
            f"Only {remaining} Odds API credits remain; preserving the last verified report"
        )
    print(f"Odds API quota preflight passed: {remaining} credits remain.")
    return remaining


def verified_markets(card: dict) -> list[str]:
    market = card.get("market") or {}
    found = []
    if market.get("moneyline"):
        found.append("moneyline")
    if market.get("spread"):
        found.append("spread")
    if market.get("total"):
        found.append("total")
    return found


def main() -> int:
    api_key = os.getenv("ODDS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ODDS_API_KEY is missing; preserving the last verified report")

    starting_credits = quota_preflight(api_key)
    report_text, draft = betting_odds.build_report()

    genuine_cards = []
    for section in (draft.get("sections") or {}).values():
        for card in section.get("cards") or []:
            markets = verified_markets(card)
            market = card.get("market") or {}
            if (
                card.get("story_type") == "market_signal"
                and market.get("has_pricing") is True
                and markets
            ):
                clean = dict(card)
                clean["source_label"] = PROVIDER
                clean["verified_markets"] = markets
                genuine_cards.append(clean)

    genuine_cards.sort(key=lambda item: item.get("priority_score", 0), reverse=True)
    genuine_cards = genuine_cards[:12]
    if len(genuine_cards) < MIN_CARDS:
        raise RuntimeError(
            f"Odds API returned only {len(genuine_cards)} verified market cards; "
            "preserving the last verified report"
        )

    generated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    homepage_cards = betting_odds.build_homepage_cards(genuine_cards)
    for homepage, full in zip(homepage_cards, genuine_cards):
        homepage["source_label"] = PROVIDER
        homepage["verified_markets"] = full["verified_markets"]
        homepage["bookmaker"] = full.get("bookmaker", "")
        homepage["matchup"] = full.get("matchup", "")
        homepage["start_time"] = full.get("start_time", "")

    by_sport: dict[str, list[dict]] = {}
    for card in genuine_cards:
        by_sport.setdefault(card.get("sport", "Betting"), []).append(card)

    sections = {}
    for label, cards in by_sport.items():
        lead = cards[0]
        sections[label.lower().replace(" ", "_")] = {
            "title": f"{label} Betting Market",
            "headline": lead.get("headline", ""),
            "snapshot": lead.get("snapshot", ""),
            "cards": cards,
            "source_label": PROVIDER,
            "url": lead.get("url", ""),
            "updated_at": generated,
        }

    draft.update(
        {
            "site": "Global Betting Report",
            "site_name": "Global Betting Report",
            "vertical": "Betting",
            "generated_utc": generated,
            "verified_at": generated,
            "source_mode": "the_odds_api_v4_daily",
            "updated_at": generated,
            "generated_at": generated,
            "homepage_cards": homepage_cards,
            "live_newsroom": betting_odds.build_live_newsroom(genuine_cards),
            "sections": sections,
            "verification": {
                "status": "verified",
                "provider": PROVIDER,
                "verified_at": generated,
                "sports": [sport["label"] for sport in betting_odds.SPORTS],
                "markets": ["moneyline", "spread", "total"],
                "region": "us",
                "total_verified_events": len(genuine_cards),
                "credits_before_run": starting_credits,
                "estimated_credits_used": 9,
            },
        }
    )
    draft["freshness"]["source"] = PROVIDER
    draft["freshness"]["total_market_cards"] = len(genuine_cards)

    encoded = json.dumps(draft, ensure_ascii=False, indent=2) + "\n"
    write_atomic(ROOT_JSON, encoded)
    write_atomic(PUBLIC_JSON, encoded)
    write_atomic(ROOT_TEXT, report_text + "\n")
    write_atomic(PUBLIC_TEXT, report_text + "\n")
    print(
        f"Published {len(genuine_cards)} verified cards from {PROVIDER}; "
        "canonical files updated atomically."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"BETTING GENERATION FAILED: {exc}")
        raise SystemExit(1)
