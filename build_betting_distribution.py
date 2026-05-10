from __future__ import annotations

import json
import re
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


def clean_team_artifacts(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "__TEAM_76 ERS__": "76ers",
        "__TEAM_76ERS__": "76ers",
        "__TEAM_49 ERS__": "49ers",
        "__TEAM_49ERS__": "49ers",
        "_TEAM_76 ERS_": "76ers",
        "_TEAM_49 ERS_": "49ers",
        "Philadelphia __TEAM_76 ERS__": "Philadelphia 76ers",
        "Philadelphia __TEAM_76ERS__": "Philadelphia 76ers",
        "San Francisco __TEAM_49 ERS__": "San Francisco 49ers",
        "San Francisco __TEAM_49ERS__": "San Francisco 49ers",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = re.sub(r"__TEAM_76\s*ERS__", "76ers", text)
    text = re.sub(r"__TEAM_49\s*ERS__", "49ers", text)

    return text.strip()


def normalize_bookmaker(text: str) -> str:
    text = text.replace("Fan Duel", "FanDuel")
    text = text.replace("Draft Kings", "DraftKings")
    return text


def clean_line(text: str) -> str:
    text = str(text or "").strip()
    text = clean_team_artifacts(text)
    text = normalize_bookmaker(text)
    text = text.replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def first_moneyline_price(moneyline: str) -> str:
    match = re.search(r"(?<!\w)([+-]\d{3,4})(?!\w)", clean_line(moneyline))
    return match.group(1) if match else ""


def implied_probability_from_price(price: str) -> str:
    if not price:
        return ""
    try:
        value = int(price)
    except ValueError:
        return ""
    if value < 0:
        probability = abs(value) / (abs(value) + 100)
    else:
        probability = 100 / (value + 100)
    return f"{probability * 100:.1f}%"


def market_snapshot(game: str, moneyline: str, spread: str, total: str, implied_probability: str) -> str:
    price = first_moneyline_price(moneyline)
    implied = implied_probability or (
        f"First listed moneyline implies roughly {implied_probability_from_price(price)} win probability"
        if implied_probability_from_price(price)
        else ""
    )
    parts: list[str] = []
    if moneyline:
        parts.append(f"Moneyline sets the win-probability baseline: {moneyline}.")
    if spread:
        parts.append(f"Spread frames the expected margin: {spread}.")
    if total:
        parts.append(f"Total frames the scoring environment: {total}.")
    if implied:
        parts.append(implied.rstrip(".") + ".")
    if not parts:
        return f"{game} is on the betting board; the useful read is how price, availability and matchup context line up before game time."
    return " ".join(parts[:4])


def event_key_data(game: str, bookmaker: str, moneyline: str, spread: str, total: str, implied_probability: str) -> list[str]:
    data: list[str] = [f"Game: {game}"]
    if bookmaker:
        data.append(f"Market source: {bookmaker}")
    if moneyline:
        data.append(f"Moneyline: {moneyline}")
    if spread:
        data.append(f"Spread: {spread}")
    if total:
        data.append(f"Total: {total}")
    if implied_probability:
        data.append(implied_probability)
    return data[:5]


def market_label(title: str) -> str:
    if "Fantasy" in title:
        return "Fantasy market read"
    if "Context" in title or "Watch" in title:
        return "Market context"
    return "Betting market read"


def first_real_line(text: str) -> str:
    skip = {
        "GLOBAL SNAPSHOT",
        "BETTING MARKET NOTE",
        "TOP BOARD",
        "NBA",
        "MLB",
        "NHL",
        "NFL",
        "DISCLAIMER",
    }

    for raw in text.splitlines():
        line = clean_line(raw).strip(" -\t")
        if not line:
            continue
        if "|" in line:
            continue
        if line.upper() in skip:
            continue
        if line.lower().startswith(("bookmaker:", "moneyline:", "spread:", "total:")):
            continue
        if line.lower().startswith(("this report", "generated:", "editorial safety note")):
            continue
        if len(line) > 20:
            return line

    return "Global Betting Report is tracking the current odds board."


def split_event_blocks(body: str) -> list[list[str]]:
    lines = [clean_line(line) for line in body.splitlines() if clean_line(line)]
    lines = [line for line in lines if line.upper() != "TOP BOARD"]

    blocks: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        is_matchup = bool(re.search(r"\bat\b", line, flags=re.I)) and bool(
            re.search(r"\d{1,2}:\d{2}\s*[AP]M\s*ET", line, flags=re.I)
        )

        if is_matchup and current:
            blocks.append(current)
            current = [line]
        else:
            current.append(line)

    if current:
        blocks.append(current)

    return blocks[:5]


def extract_market_read(block: list[str]) -> list[str]:
    items: list[str] = []
    in_market_read = False

    for raw in block:
        line = clean_line(raw).strip(" -")
        if not line:
            continue

        if line.lower() == "market read:":
            in_market_read = True
            continue

        if in_market_read:
            if line.lower().startswith(("bookmaker:", "moneyline:", "spread:", "total:")):
                continue
            items.append(line)

    return items[:3]


def parse_event_card(block: list[str], league: str, current_stamp: str) -> dict | None:
    if not block:
        return None

    joined = " ".join(clean_line(line) for line in block if clean_line(line))
    joined = re.sub(r"\s+", " ", joined).strip()

    game = clean_line(block[0])

    bookmaker_match = re.search(
        r"Bookmaker:\s*([^:]+?)(?=\s+Moneyline:|\s+Spread:|\s+Total:|\s+Market read:|$)",
        joined,
        flags=re.I,
    )
    moneyline_match = re.search(
        r"Moneyline:\s*(.*?)(?=\s+Spread:|\s+Total:|\s+Market read:|$)",
        joined,
        flags=re.I,
    )
    spread_match = re.search(
        r"Spread:\s*(.*?)(?=\s+Total:|\s+Market read:|$)",
        joined,
        flags=re.I,
    )
    total_match = re.search(
        r"Total:\s*(.*?)(?=\s+Market read:|\s+Bookmaker:|\s+BETTING MARKET NOTE|\s+Generated:|$)",
        joined,
        flags=re.I,
    )

    bookmaker = clean_line(bookmaker_match.group(1)) if bookmaker_match else ""
    moneyline = clean_line(moneyline_match.group(1)) if moneyline_match else ""
    spread = clean_line(spread_match.group(1)) if spread_match else ""
    total = clean_line(total_match.group(1)) if total_match else ""

    market_read = extract_market_read(block)
    implied_probability = next(
        (item for item in market_read if "implied win probability" in item.lower()),
        "",
    )

    market_lines = [
        f"Bookmaker: {bookmaker}" if bookmaker else "",
        f"Moneyline: {moneyline}" if moneyline else "",
        f"Spread: {spread}" if spread else "",
        f"Total: {total}" if total else "",
    ]
    market = " | ".join(line for line in market_lines if line)

    if not game or not market:
        return None

    why = [item for item in market_read if item != implied_probability] or build_odds_meaning(f"{league} Betting Board")[:2]
    snapshot = market_snapshot(game, moneyline, spread, total, implied_probability)

    return {
        "title": f"{league} Betting Board",
        "league": f"{league} Betting Board",
        "headline": game,
        "game": game,
        "market": market,
        "bookmaker": bookmaker,
        "moneyline": moneyline,
        "spread": spread,
        "total": total,
        "implied_probability": implied_probability,
        "snapshot": snapshot,
        "key_data": event_key_data(game, bookmaker, moneyline, spread, total, implied_probability),
        "why_it_matters": why,
        "what_the_odds_mean": why,
        "what_to_watch": build_watch_items(f"{league} Betting Board"),
        "source_label": "Betting market read",
        "story_type": "market_context",
        "source": "betting_odds_report.txt",
        "updated_at": current_stamp,
    }


def compress_event_block(block: list[str]) -> list[str]:
    if not block:
        return []

    joined = " ".join(clean_line(line) for line in block if clean_line(line))
    joined = re.sub(r"\s+", " ", joined).strip()

    lines: list[str] = []

    first = clean_line(block[0])
    if first:
        lines.append(f"Matchup: {first}")

    bookmaker = re.search(r"Bookmaker:\s*([^:]+?)(?=\s+Moneyline:|\s+Spread:|\s+Total:|$)", joined, flags=re.I)
    if bookmaker:
        lines.append(f"Bookmaker: {clean_line(bookmaker.group(1))}")

    moneyline = re.search(r"Moneyline:\s*(.*?)(?=\s+Spread:|\s+Total:|$)", joined, flags=re.I)
    if moneyline:
        lines.append(f"Moneyline: {clean_line(moneyline.group(1))}")

    spread = re.search(r"Spread:\s*(.*?)(?=\s+Total:|$)", joined, flags=re.I)
    if spread:
        lines.append(f"Spread: {clean_line(spread.group(1))}")

    total = re.search(r"Total:\s*(.*?)(?=\s+Bookmaker:|\s+BETTING MARKET NOTE|\s+EDITORIAL SAFETY NOTE|\s+Generated:|$)", joined, flags=re.I)
    if total:
        lines.append(f"Total: {clean_line(total.group(1))}")

    return lines[:5]


def build_clean_snapshot(body: str) -> str:
    blocks = split_event_blocks(body)
    clean_lines: list[str] = []

    for block in blocks[:3]:
        clean_lines.extend(compress_event_block(block))
        clean_lines.append("")

    if not clean_lines:
        return first_real_line(body)

    return "\n".join(clean_lines).strip()


def build_key_data(headline: str, snapshot: str) -> list[str]:
    data: list[str] = []

    if headline:
        data.append(f"Lead market: {clean_line(headline)}")

    moneyline = re.search(r"Moneyline:\s*(.+)", snapshot)
    spread = re.search(r"Spread:\s*(.+)", snapshot)
    total = re.search(r"Total:\s*(.+)", snapshot)

    if moneyline:
        data.append(f"Moneyline context: {clean_line(moneyline.group(1))}")
    if spread:
        data.append(f"Spread context: {clean_line(spread.group(1))}")
    if total:
        data.append(f"Total context: {clean_line(total.group(1))}")

    return data[:4] or ["Current betting board is being read for market position, risk and late movement."]


def build_odds_meaning(title: str) -> list[str]:
    if "MLB" in title:
        return [
            "Pitching confirmations and weather can move MLB totals quickly.",
            "Moneyline gaps show market confidence, but late lineup news still matters.",
            "Check whether the favorite is becoming more expensive before first pitch.",
        ]
    if "NBA" in title:
        return [
            "Injury reports, rest spots, and rotation news can reshape NBA spreads.",
            "A short favorite price suggests a tighter market than the matchup name may imply.",
            "Watch late movement near tipoff for sharper market signals.",
        ]
    if "NHL" in title:
        return [
            "Goalie confirmations can materially change NHL moneylines and totals.",
            "Low totals make puck-line risk more important than raw favorite price.",
            "Special teams and back-to-back scheduling can affect late movement.",
        ]
    if "NFL" in title:
        return [
            "NFL spreads often reflect quarterback, injury, and rest information quickly.",
            "Prime-time markets can move late as public money arrives.",
            "Compare the spread and moneyline together before reading market confidence.",
        ]

    return [
        "Betting readers need more than the number; they need market context.",
        "Track whether price, injuries, matchup edges, public money, or weather may be driving the line.",
    ]


def build_watch_items(title: str) -> list[str]:
    base = [
        "Line movement before game time.",
        "Injury and lineup confirmations.",
        "Late sportsbook adjustment across moneyline, spread, and total.",
    ]

    if "MLB" in title:
        return [
            "Starting pitcher confirmations.",
            "Weather, wind, humidity, and postponement risk.",
            "Bullpen usage and lineup scratches before first pitch.",
        ]

    if "NBA" in title:
        return [
            "Official injury report updates.",
            "Rest and back-to-back spots.",
            "Rotation news and late movement near tipoff.",
        ]

    if "NHL" in title:
        return [
            "Confirmed starting goalies.",
            "Back-to-back scheduling and travel spots.",
            "Totals movement after goalie news.",
        ]

    if "NFL" in title:
        return [
            "Quarterback and injury report movement.",
            "Weather for outdoor games.",
            "Prime-time public money and late spread movement.",
        ]

    return base


def interleave_league_cards(cards: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    order: list[str] = []

    for card in cards:
        title = str(card.get("title") or "Betting")
        if title not in grouped:
            grouped[title] = []
            order.append(title)
        grouped[title].append(card)

    interleaved: list[dict] = []
    max_group_size = max((len(items) for items in grouped.values()), default=0)

    for index in range(max_group_size):
        for title in order:
            if index < len(grouped[title]):
                interleaved.append(grouped[title][index])

    return interleaved


def split_sections(text: str) -> list[dict]:
    league_titles = {"NBA", "MLB", "NHL", "NFL"}
    cards: list[dict] = []
    current_stamp = stamp()

    lines = text.splitlines()
    current_title = None
    current_lines: list[str] = []

    def flush():
        nonlocal current_title, current_lines

        if not current_title:
            return

        body = "\n".join(current_lines).strip()
        if not body:
            return

        for block in split_event_blocks(clean_team_artifacts(body)):
            card = parse_event_card(block, current_title, current_stamp)
            if card:
                cards.append(card)

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

    return interleave_league_cards(cards)


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
            "key_data": ["Market board is active across available leagues."],
            "what_the_odds_mean": [
                "Line movement matters most when it connects to injuries, weather, roster news, or sportsbook adjustment."
            ],
            "what_to_watch": [
                "Track favorites getting more expensive or underdogs drawing late money.",
                "Watch totals in weather-sensitive games.",
                "Compare sportsbook movement before treating one number as the full market.",
            ],
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
            "key_data": ["Betting context requires line movement plus supporting news."],
            "what_the_odds_mean": [
                "A number alone is not a recommendation. Context explains why the market may be moving."
            ],
            "what_to_watch": [
                "Injuries, pitching confirmations, weather, public money, and late sportsbook adjustment."
            ],
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
                "snapshot": section.get("snapshot", ""),
                "source_label": section.get("source_label") or market_label(str(section.get("title", "Betting"))),
                "story_type": section.get("story_type", "market_context"),
                "key_data": section.get("key_data", [])[:4],
                "why_it_matters": (section.get("why_it_matters") or section.get("what_the_odds_mean", []))[:3],
                "what_to_watch": section.get("what_to_watch", [])[:3],
                "url": "https://www.globalbettingreport.com",
            }
        )

    return cards


def build_payload(text: str) -> dict:
    current_stamp = stamp()
    text = clean_team_artifacts(text)
    headline = first_real_line(text)

    sections = split_sections(text)
    sections.extend(build_support_cards(text, current_stamp))

    if not sections:
        sections = [
            {
                "title": "Betting Odds",
                "headline": headline,
                "snapshot": build_clean_snapshot(text),
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
        "source_mode": "public_betting_market_report",
        "homepage_cards": build_homepage_cards(sections),
        "live_newsroom": build_homepage_cards(sections),
        "editor_signals": [
            section.get("headline", "")
            for section in sections[:5]
            if section.get("headline")
        ],
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
    OUTPUT_TXT.write_text(clean_team_artifacts(text) + "\n", encoding="utf-8")

    print(f"[OK] Wrote {OUTPUT_JSON}")
    print(f"[OK] Wrote {OUTPUT_TXT}")
    print(f"[CHECK] Betting sections: {len(payload.get('sections', []))}")
    print(f"[CHECK] Homepage cards: {len(payload.get('homepage_cards', []))}")
    print(f"[{stamp()}] BETTING BUILD COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
