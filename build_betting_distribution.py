from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"

REPORT_FILE = BASE_DIR / "betting_odds_report.txt"
OUTPUT_JSON = PUBLIC_DIR / "latest_report.json"
OUTPUT_TXT = PUBLIC_DIR / "latest_report.txt"


def now_et() -> datetime:
    return datetime.now(ET)


def stamp() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


def first_real_line(text: str) -> str:
    skip = {
        "GLOBAL SNAPSHOT",
        "BETTING MARKET NOTE",
        "TOP BOARD",
        "NBA",
        "MLB",
        "NHL",
        "NFL",
    }

    for line in text.splitlines():
        line = line.strip(" -\t")
        if not line:
            continue
        if "|" in line:
            continue
        if line.upper() in skip:
            continue
        if len(line) > 30:
            return line

    return "Global Betting Report is tracking the current odds board."


def split_sections(text: str) -> list[dict]:
    league_titles = {"NBA", "MLB", "NHL", "NFL"}
    cards = []

    lines = text.splitlines()
    current_title = None
    current_lines: list[str] = []

    def flush():
        nonlocal current_title, current_lines

        if not current_title:
            return

        body = "\n".join(current_lines).strip()
        if not body:
            body = f"No current {current_title} betting board data was available during this report window."

        cards.append(
            {
                "title": f"{current_title} Betting Board",
                "headline": first_real_line(body),
                "snapshot": body,
                "source": "betting_odds_report.txt",
                "updated_at": stamp(),
            }
        )

    for raw in lines:
        line = raw.strip()

        if line in league_titles:
            flush()
            current_title = line
            current_lines = []
            continue

        if current_title:
            current_lines.append(raw)

    flush()

    return cards


def build_support_cards(text: str, current_stamp: str) -> list[dict]:
    headline = first_real_line(text)

    return [
        {
            "title": "Market Watch",
            "headline": headline,
            "snapshot": (
                "Moneylines, spreads, totals, board depth, and sportsbook pricing are being monitored "
                "for betting-market movement."
            ),
            "source": "betting_odds_report.txt",
            "updated_at": current_stamp,
        },
        {
            "title": "Betting Context",
            "headline": "What bettors should monitor today",
            "snapshot": (
                "Track line movement, injury news, starting lineup changes, pitching confirmations, "
                "weather, rest advantages, and late market steam before making any betting decision."
            ),
            "source": "GSR betting desk",
            "updated_at": current_stamp,
        },
    ]


def build_homepage_cards(sections: list[dict]) -> list[dict]:
    cards = []

    for section in sections[:8]:
        cards.append(
            {
                "league": section.get("title", "Betting"),
                "headline": section.get("headline", "Global Betting Report market update"),
                "url": "https://www.globalbettingreport.com",
            }
        )

    return cards


def build_payload(text: str) -> dict:
    current_stamp = stamp()
    headline = first_real_line(text)

    sections = split_sections(text)
    sections.extend(build_support_cards(text, current_stamp))

    if not sections:
        sections = [
            {
                "title": "Betting Odds",
                "headline": headline,
                "snapshot": text,
                "source": "betting_odds_report.txt",
                "updated_at": current_stamp,
            }
        ]

    return {
        "site": "Global Betting Report",
        "site_name": "Global Betting Report",
        "vertical": "Betting",
        "title": "Global Betting Report",
        "headline": headline,
        "snapshot": (
            "Odds, implied probability, line movement, market context, and what bettors "
            "should monitor across the sports world."
        ),
        "updated_at": current_stamp,
        "generated_at": current_stamp,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_mode": "multi-card odds report distribution",
        "homepage_cards": build_homepage_cards(sections),
        "sections": sections,
    }


def main() -> int:
    print(f"[{stamp()}] BETTING BUILD STARTED")

    if not REPORT_FILE.exists():
        print(f"[ERROR] Missing source report: {REPORT_FILE}")
        return 1

    text = REPORT_FILE.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        print(f"[ERROR] Empty source report: {REPORT_FILE}")
        return 1

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_payload(text)

    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUTPUT_TXT.write_text(text + "\n", encoding="utf-8")

    print(f"[OK] Wrote {OUTPUT_JSON}")
    print(f"[OK] Wrote {OUTPUT_TXT}")
    print(f"[CHECK] Betting sections: {len(payload.get('sections', []))}")
    print(f"[CHECK] Homepage cards: {len(payload.get('homepage_cards', []))}")
    print(f"[{stamp()}] BETTING BUILD COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())