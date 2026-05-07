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
    for line in text.splitlines():
        line = line.strip(" -\t")
        if len(line) > 30 and "|" not in line:
            return line
    return "Global Betting Report is tracking the current odds board."


def build_payload(text: str) -> dict:
    current_stamp = stamp()
    headline = first_real_line(text)

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
        "source_mode": "odds report text distribution",
        "sections": [
            {
                "title": "Betting Odds",
                "headline": headline,
                "snapshot": text,
                "source": "betting_odds_report.txt",
                "updated_at": current_stamp,
            }
        ],
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
    print(f"[{stamp()}] BETTING BUILD COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
