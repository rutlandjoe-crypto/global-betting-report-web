import json
import sys
from pathlib import Path

REPORT_PATHS = [
    Path("public/latest_report.json"),
    Path("latest_report.json"),
    Path("betting_odds_report.json"),
]

BANNED_PHRASES = [
    "books wait on prices",
    "board takes shape",
    "market takes shape",
    "lines take shape",
    "fallback",
    "generic",
    "placeholder",
]

MIN_CARDS = 8


def load_json(path: Path):
    if not path.exists():
        raise SystemExit(f"BETTING AGENT ALERT: Missing required report file: {path}")

    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        data = json.loads(text)
    except Exception as exc:
        raise SystemExit(f"BETTING AGENT ALERT: Could not parse JSON in {path}: {exc}")

    return data, text


def card_count(data):
    cards = data.get("homepage_cards") or data.get("cards") or []
    return len(cards), cards


def scan_report(path: Path):
    data, text = load_json(path)
    lowered = text.lower()

    headline = data.get("headline") or data.get("title") or ""
    updated_at = data.get("updated_at") or data.get("generated_at") or "UNKNOWN"
    count, cards = card_count(data)

    problems = []

    if count < MIN_CARDS:
        problems.append(f"only {count} cards; minimum is {MIN_CARDS}")

    hits = [phrase for phrase in BANNED_PHRASES if phrase in lowered]
    if hits:
        problems.append("banned fallback phrases found: " + ", ".join(hits))

    return {
        "path": str(path),
        "headline": headline,
        "updated_at": updated_at,
        "card_count": count,
        "problems": problems,
    }


def main():
    print("=== GSR BETTING AGENT QUALITY CHECK ===")

    any_problem = False

    for path in REPORT_PATHS:
        result = scan_report(path)

        print("")
        print(f"FILE: {result['path']}")
        print(f"headline: {result['headline']}")
        print(f"updated_at/generated_at: {result['updated_at']}")
        print(f"card_count: {result['card_count']}")

        if result["problems"]:
            any_problem = True
            print("STATUS: WARNING")
            for problem in result["problems"]:
                print(f"- {problem}")
        else:
            print("STATUS: CLEAR")

    if any_problem:
        raise SystemExit("BETTING AGENT ALERT: Betting report failed quality check.")

    print("")
    print("BETTING AGENT CLEAR: Betting report passed quality check.")


if __name__ == "__main__":
    main()
