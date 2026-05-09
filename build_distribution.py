#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_betting_distribution.py

Global Betting Report distribution builder.

Editorial Brain v3 update:
- Deepens betting-market interpretation without changing the locked front-end structure
- Adds cleaner card-ready fields: key_data, why_it_matters, what_to_watch
- Adds WNBA-ready hooks so WNBA betting context can appear when data exists
- Builds homepage_cards, live_newsroom, and editor_signals
- Preserves latest_report.json / latest_report.txt public outputs
- Never crashes on missing, partial, list-based, or dict-based inputs

This file is designed as a full replacement.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # type: ignore


# =============================================================================
# PATHS / CONSTANTS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"

TITLE = "GLOBAL BETTING REPORT"
SITE = "Global Betting Report"
VERTICAL = "Betting"
SITE_TZ = "America/New_York"

DEFAULT_X_HANDLE = "@GlobalSportsRp"
DEFAULT_SUBSTACK_URL = "https://globalsportsreport.substack.com/"
DISCLAIMER = (
    "This report is an automated market-context summary intended to support, "
    "not replace, human sports journalism. It is not gambling advice."
)

EDITORIAL_BRAIN_VERSION = "v3-betting-market-context-wnba-ready"

INPUT_JSON_FILES: dict[str, Path] = {
    "betting_odds": BASE_DIR / "betting_odds_report.json",
    "mlb": BASE_DIR / "mlb_report.json",
    "nba": BASE_DIR / "nba_report.json",
    "wnba": BASE_DIR / "wnba_report.json",
    "nhl": BASE_DIR / "nhl_report.json",
    "nfl": BASE_DIR / "nfl_report.json",
    "ncaafb": BASE_DIR / "ncaafb_report.json",
    "soccer": BASE_DIR / "soccer_report.json",
    "fantasy": BASE_DIR / "fantasy_report.json",
}

INPUT_TEXT_FILES: dict[str, Path] = {
    "betting_odds": BASE_DIR / "betting_odds_report.txt",
    "mlb": BASE_DIR / "mlb_report.txt",
    "nba": BASE_DIR / "nba_report.txt",
    "wnba": BASE_DIR / "wnba_report.txt",
    "nhl": BASE_DIR / "nhl_report.txt",
    "nfl": BASE_DIR / "nfl_report.txt",
    "ncaafb": BASE_DIR / "ncaafb_report.txt",
    "soccer": BASE_DIR / "soccer_report.txt",
    "fantasy": BASE_DIR / "fantasy_report.txt",
}

SECTION_ORDER = [
    "betting_odds",
    "mlb",
    "nba",
    "wnba",
    "nhl",
    "nfl",
    "ncaafb",
    "soccer",
    "fantasy",
]

OUTPUT_LATEST_JSON = BASE_DIR / "latest_report.json"
OUTPUT_LATEST_TXT = BASE_DIR / "latest_report.txt"
OUTPUT_FULL_TXT = BASE_DIR / "global_betting_report.txt"

PUBLIC_LATEST_JSON = PUBLIC_DIR / "latest_report.json"
PUBLIC_LATEST_TXT = PUBLIC_DIR / "latest_report.txt"
PUBLIC_FULL_TXT = PUBLIC_DIR / "global_betting_report.txt"

BETTING_TERMS = [
    "odds",
    "moneyline",
    "spread",
    "total",
    "over",
    "under",
    "favorite",
    "underdog",
    "implied probability",
    "market",
    "sportsbook",
    "line",
    "priced",
    "price",
    "handle",
    "tickets",
    "movement",
    "number",
    "prop",
]

VOLATILITY_TERMS = [
    "moved",
    "movement",
    "steam",
    "drift",
    "shortened",
    "lengthened",
    "late money",
    "sharp",
    "public",
    "adjusted",
    "opened",
    "closing",
]

RISK_TERMS = [
    "injury",
    "questionable",
    "out",
    "rest",
    "back-to-back",
    "travel",
    "bullpen",
    "pitching",
    "lineup",
    "scratch",
    "weather",
    "minutes restriction",
]

PRESSURE_TERMS = [
    "playoff",
    "postseason",
    "elimination",
    "must-win",
    "standings",
    "race",
    "clinched",
    "finals",
    "game 7",
    "series",
]

LIVE_TERMS = [
    "live",
    "in progress",
    "halftime",
    "quarter",
    "period",
    "overtime",
    "extra innings",
    "final",
]


# =============================================================================
# TIME / LOGGING
# =============================================================================

def now_et() -> datetime:
    if ZoneInfo is None:
        return datetime.now()
    return datetime.now(ZoneInfo(SITE_TZ))


def ts() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


def log(message: str) -> None:
    print(f"[{ts()}] {message}")


# =============================================================================
# TEXT / DATA SAFETY
# =============================================================================

def clean_text(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    replacements = {
        "\ufeff": "",
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2014": "-",
        "\u2013": "-",
        "\xa0": " ",
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€”": "-",
        "â€“": "-",
        "Ã©": "é",
        "Ã¡": "á",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã±": "ñ",
        "Ã¼": "ü",
        "Ã": "",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value.strip()


def trim_text(value: Any, max_chars: int = 260) -> str:
    text = clean_text(value)
    if len(text) <= max_chars:
        return text
    shortened = text[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{shortened}..." if shortened else text[:max_chars]


def safe_join_parts(value: Any) -> str:
    flattened: list[str] = []

    def walk(item: Any) -> None:
        if item is None:
            return
        if isinstance(item, str):
            txt = clean_text(item)
            if txt:
                flattened.append(txt)
            return
        if isinstance(item, (int, float, bool)):
            flattened.append(str(item))
            return
        if isinstance(item, dict):
            for _, v in item.items():
                walk(v)
            return
        if isinstance(item, (list, tuple, set)):
            for sub in item:
                walk(sub)
            return
        txt = clean_text(str(item))
        if txt:
            flattened.append(txt)

    walk(value)
    return "\n\n".join(part for part in flattened if part.strip()).strip()


def normalize_lines(value: Any, limit: int = 8) -> list[str]:
    if value is None:
        return []

    raw_items: list[Any]

    if isinstance(value, str):
        raw_items = re.split(r"\n+|•|\||;", value)
    elif isinstance(value, list):
        raw_items = value
    elif isinstance(value, dict):
        raw_items = list(value.values())
    else:
        raw_items = [value]

    cleaned: list[str] = []
    seen: set[str] = set()

    for item in raw_items:
        if isinstance(item, dict):
            for sub in item.values():
                for line in normalize_lines(sub, limit=limit):
                    key = line.lower()
                    if key not in seen:
                        seen.add(key)
                        cleaned.append(line)
                    if len(cleaned) >= limit:
                        return cleaned
            continue

        line = clean_text(item)
        line = re.sub(r"^[-*•\d.)\s]+", "", line).strip()
        if not line:
            continue

        key = line.lower()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(line)

        if len(cleaned) >= limit:
            break

    return cleaned


def text_contains_any(text: Any, terms: list[str]) -> bool:
    lower = clean_text(text).lower()
    return any(term in lower for term in terms)


def format_label(key: str) -> str:
    labels = {
        "betting_odds": "Betting Market Watch",
        "mlb": "MLB Betting",
        "nba": "NBA Betting",
        "wnba": "WNBA Betting",
        "nhl": "NHL Betting",
        "nfl": "NFL Betting",
        "ncaafb": "College Football Betting",
        "soccer": "Soccer Betting",
        "fantasy": "Fantasy Market Watch",
    }
    return labels.get(key, key.replace("_", " ").title())


def first_meaningful_line(text: str) -> str:
    ignored = {
        "HEADLINE",
        "SNAPSHOT",
        "KEY DATA",
        "KEY DATA POINTS",
        "WHY IT MATTERS",
        "WHAT TO WATCH",
        "BETTING MARKET NOTE",
        "WATCH LIST",
        "MATCHUP FLAGS",
        "UPDATED",
        "DISCLAIMER",
        "LIVE",
        "UPCOMING",
        "FINAL SCORES",
    }

    for line in clean_text(text).splitlines():
        line = line.strip(" -:\t")
        if line and line.upper() not in ignored:
            return line

    return ""


def parse_timestamp_from_text(text: str) -> str | None:
    patterns = [
        r"Generated:\s*([0-9:\-\sAPMET]+)",
        r"UPDATED\s*\n\s*([0-9:\-\sAPMET]+)",
        r"Updated:\s*([0-9:\-\sAPMET]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))

    return None


# =============================================================================
# FILE IO
# =============================================================================

def read_text_file(path: Path) -> str:
    if not path.exists():
        return ""
    return clean_text(path.read_text(encoding="utf-8", errors="replace"))


def read_json_file(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def write_text_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(clean_text(text) + "\n", encoding="utf-8")
    log(f"Saved: {path}")


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"Saved: {path}")


def copy_file_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    log(f"Copied: {src} -> {dst}")
    return True


# =============================================================================
# SECTION PARSING
# =============================================================================

SECTION_HEADER_RE = re.compile(
    r"^(HEADLINE|SNAPSHOT|KEY DATA|KEY DATA POINTS|WHY IT MATTERS|WHAT TO WATCH|"
    r"BETTING MARKET NOTE|WATCH LIST|MATCHUP FLAGS|UPDATED|DISCLAIMER|LIVE|UPCOMING|"
    r"FINAL SCORES|TODAY SCHEDULE|TODAY LIVE|CURRENT DATA AND ANALYTICS|STORY ANGLES)$",
    flags=re.IGNORECASE | re.MULTILINE,
)


def slugify(text: str) -> str:
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "section"


def split_named_sections(text: str) -> dict[str, list[str]]:
    text = clean_text(text)
    if not text:
        return {}

    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current_key: str | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if SECTION_HEADER_RE.match(line):
            current_key = slugify(line)
            sections.setdefault(current_key, [])
            continue

        if current_key is None:
            continue

        if line:
            sections[current_key].append(line)

    return sections


def json_first_value(data: Any, keys: list[str]) -> Any:
    if not isinstance(data, dict):
        return None

    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value

    return None


def extract_url(section_key: str, json_data: Any, text: str) -> str:
    if isinstance(json_data, dict):
        direct = json_first_value(
            json_data,
            ["url", "source_url", "game_url", "espn_url", "link", "story_url"],
        )
        if isinstance(direct, str) and direct.startswith("http"):
            return clean_text(direct)

        for collection_name in ["cards", "stories", "games", "events", "odds"]:
            collection = json_data.get(collection_name)
            if isinstance(collection, list):
                for item in collection:
                    if isinstance(item, dict):
                        value = json_first_value(
                            item,
                            ["url", "source_url", "game_url", "espn_url", "link", "story_url"],
                        )
                        if isinstance(value, str) and value.startswith("http"):
                            return clean_text(value)

    match = re.search(r"https?://[^\s)>\]]+", text)
    if match:
        return match.group(0).rstrip(".,;")

    fallbacks = {
        "betting_odds": "https://www.actionnetwork.com/odds",
        "mlb": "https://www.espn.com/mlb/scoreboard",
        "nba": "https://www.espn.com/nba/scoreboard",
        "wnba": "https://www.espn.com/wnba/scoreboard",
        "nhl": "https://www.espn.com/nhl/scoreboard",
        "nfl": "https://www.espn.com/nfl/scoreboard",
        "ncaafb": "https://www.espn.com/college-football/scoreboard",
        "soccer": "https://www.espn.com/soccer/",
        "fantasy": "https://www.cbssports.com/fantasy/",
    }
    return fallbacks.get(section_key, "https://globalbettingreport.com")


# =============================================================================
# BETTING EDITORIAL BRAIN V3
# =============================================================================

def extract_moneylines(text: str) -> list[str]:
    return re.findall(r"(?<!\w)([+-]\d{3,4})(?!\w)", clean_text(text))


def extract_percentages(text: str) -> list[str]:
    return re.findall(r"\b\d{1,3}(?:\.\d+)?%", clean_text(text))


def detect_market_signal(text: str) -> str:
    lower = clean_text(text).lower()

    if text_contains_any(lower, VOLATILITY_TERMS):
        return "market_movement"
    if "favorite" in lower:
        return "favorite_watch"
    if "underdog" in lower:
        return "underdog_watch"
    if "total" in lower or "over" in lower or "under" in lower:
        return "total_watch"
    if "spread" in lower:
        return "spread_watch"
    if text_contains_any(lower, RISK_TERMS):
        return "risk_watch"
    if text_contains_any(lower, PRESSURE_TERMS):
        return "pressure_watch"
    if text_contains_any(lower, LIVE_TERMS):
        return "live_market_watch"

    return "market_board"


def build_key_data(section_key: str, headline: str, snapshot: str, source_lines: list[str]) -> list[str]:
    text = " ".join([headline, snapshot, " ".join(source_lines)])
    moneylines = extract_moneylines(text)
    percentages = extract_percentages(text)

    key_data: list[str] = []

    if moneylines:
        unique_moneylines = []
        for line in moneylines:
            if line not in unique_moneylines:
                unique_moneylines.append(line)
        key_data.append(f"Moneyline signal detected: {', '.join(unique_moneylines[:4])}.")

    if percentages:
        unique_percentages = []
        for pct in percentages:
            if pct not in unique_percentages:
                unique_percentages.append(pct)
        key_data.append(f"Implied-probability signal detected: {', '.join(unique_percentages[:4])}.")

    lower = text.lower()

    if "spread" in lower:
        key_data.append("Spread context is present, which frames expected margin rather than only winner probability.")
    if "total" in lower or "over" in lower or "under" in lower:
        key_data.append("Total context is present, adding pace, scoring environment and game-script angles.")
    if "favorite" in lower:
        key_data.append("Favorite pricing is present, creating a clear expectation baseline.")
    if "underdog" in lower:
        key_data.append("Underdog pricing is present, creating upset-watch and value-market context.")
    if text_contains_any(lower, VOLATILITY_TERMS):
        key_data.append("Market-movement language is present, which can signal late information or changing sentiment.")
    if text_contains_any(lower, RISK_TERMS):
        key_data.append("Risk context is present through injury, rest, lineup, weather, pitching or travel-related language.")
    if section_key == "wnba":
        key_data.append("WNBA betting window is active and ready for odds, props, lineup and fantasy-market context.")

    if not key_data:
        key_data.append("Market signal: sportsbook pricing is being used as context, not as a prediction.")

    return key_data[:5]


def build_why_it_matters(section_key: str, headline: str, snapshot: str, source_lines: list[str]) -> list[str]:
    text = " ".join([headline, snapshot, " ".join(source_lines)]).lower()
    why: list[str] = []

    if "favorite" in text:
        why.append("The favorite price gives reporters a clean expectation baseline to compare against the actual result.")
    if "underdog" in text:
        why.append("The underdog number creates an immediate upset-watch angle if game flow moves against the market.")
    if "spread" in text:
        why.append("The spread shows how much separation the market expects, not just which team is favored.")
    if "total" in text or "over" in text or "under" in text:
        why.append("The total points to pace, scoring environment, defensive matchups and game-script assumptions.")
    if text_contains_any(text, VOLATILITY_TERMS):
        why.append("Line movement matters because it can reflect new information, injury updates or sharper market opinion.")
    if text_contains_any(text, RISK_TERMS):
        why.append("Risk factors can change both the betting board and the editorial framing before the game starts.")
    if text_contains_any(text, PRESSURE_TERMS):
        why.append("High-pressure standings or postseason context can change motivation, rotation choices and late-game decision-making.")
    if section_key == "wnba":
        why.append("WNBA betting coverage belongs on the board because the league is rising in audience attention, fantasy interest and market activity.")

    if not why:
        why.append("The betting board matters because it turns matchup expectations into measurable pressure points for journalists.")

    return why[:5]


def build_what_to_watch(section_key: str, headline: str, snapshot: str, source_lines: list[str]) -> list[str]:
    text = " ".join([headline, snapshot, " ".join(source_lines)]).lower()
    watch: list[str] = []

    if text_contains_any(text, RISK_TERMS):
        watch.append("Watch late injury, lineup, pitching, rest, travel or weather updates before treating the market as settled.")
    if text_contains_any(text, VOLATILITY_TERMS):
        watch.append("Watch whether the number keeps moving or stabilizes before game time.")
    if "total" in text or "over" in text or "under" in text:
        watch.append("Watch whether tempo, pitching, goalie, defensive or weather factors support the listed total.")
    if "favorite" in text:
        watch.append("Watch whether the favorite controls early game flow or leaves room for live-market pressure.")
    if "underdog" in text:
        watch.append("Watch whether the underdog has a path through pace, defense, pitching, shooting variance or matchup leverage.")
    if section_key == "wnba":
        watch.append("Watch for WNBA lineup availability, star usage, travel spots and prop-market movement as the section matures.")

    watch.append("Compare the market expectation with the live result once games begin.")

    deduped: list[str] = []
    seen: set[str] = set()
    for item in watch:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:5]


def build_headline(section_key: str, text: str, json_data: Any) -> str:
    if isinstance(json_data, dict):
        value = json_first_value(json_data, ["headline", "title", "lead_headline"])
        if value:
            return trim_text(value, 180)

        cards = json_data.get("cards")
        if isinstance(cards, list) and cards:
            first = cards[0]
            if isinstance(first, dict):
                value = json_first_value(first, ["headline", "title", "matchup", "game"])
                if value:
                    return trim_text(value, 180)

        stories = json_data.get("stories")
        if isinstance(stories, list) and stories:
            first = stories[0]
            if isinstance(first, dict):
                value = json_first_value(first, ["headline", "title", "matchup", "game"])
                if value:
                    return trim_text(value, 180)

    sections = split_named_sections(text)
    headline_lines = sections.get("headline", [])
    if headline_lines:
        return trim_text(headline_lines[0], 180)

    first = first_meaningful_line(text)
    if first:
        return trim_text(first, 180)

    return f"{format_label(section_key)} market board is active"


def build_snapshot(section_key: str, text: str, json_data: Any, headline: str) -> str:
    if isinstance(json_data, dict):
        value = json_first_value(json_data, ["snapshot", "summary", "description", "lead_summary"])
        if value:
            return trim_text(value, 280)

        cards = json_data.get("cards")
        if isinstance(cards, list) and cards:
            first = cards[0]
            if isinstance(first, dict):
                value = json_first_value(first, ["snapshot", "summary", "description", "note"])
                if value:
                    return trim_text(value, 280)

        stories = json_data.get("stories")
        if isinstance(stories, list) and stories:
            first = stories[0]
            if isinstance(first, dict):
                value = json_first_value(first, ["snapshot", "summary", "description", "note"])
                if value:
                    return trim_text(value, 280)

    sections = split_named_sections(text)
    snapshot_lines = sections.get("snapshot", [])
    if snapshot_lines:
        return trim_text(snapshot_lines[0], 280)

    if headline:
        return trim_text(f"{headline} is the lead betting-market signal in the current update window.", 280)

    return f"{format_label(section_key)} remains active in the current betting report window."


def build_editorial_fields(section_key: str, text: str, json_data: Any) -> dict[str, Any]:
    sections = split_named_sections(text)

    headline = build_headline(section_key, text, json_data)
    snapshot = build_snapshot(section_key, text, json_data, headline)

    existing_key_data = normalize_lines(
        sections.get("key_data")
        or sections.get("key_data_points")
        or sections.get("current_data_and_analytics"),
        limit=5,
    )
    existing_why = normalize_lines(sections.get("why_it_matters"), limit=5)
    existing_watch = normalize_lines(sections.get("what_to_watch") or sections.get("watch_list"), limit=5)

    source_lines = normalize_lines(
        [headline, snapshot]
        + existing_key_data
        + existing_why
        + existing_watch
        + normalize_lines(text, limit=10),
        limit=16,
    )

    key_data = existing_key_data or build_key_data(section_key, headline, snapshot, source_lines)
    why_it_matters = existing_why or build_why_it_matters(section_key, headline, snapshot, source_lines)
    what_to_watch = existing_watch or build_what_to_watch(section_key, headline, snapshot, source_lines)

    signal = detect_market_signal(" ".join([headline, snapshot, " ".join(source_lines)]))

    return {
        "key": section_key,
        "label": format_label(section_key),
        "headline": headline,
        "snapshot": snapshot,
        "key_data": key_data[:5],
        "key_data_points": key_data[:5],
        "why_it_matters": why_it_matters[:5],
        "what_to_watch": what_to_watch[:5],
        "story_type": signal,
        "market_signal": signal,
        "url": extract_url(section_key, json_data, text),
        "editorial_brain": {
            "version": EDITORIAL_BRAIN_VERSION,
            "status": "active",
            "section": section_key,
            "label": format_label(section_key),
            "signal": signal,
            "standard": "Betting data is used for context and reporting signals, not gambling advice.",
        },
    }


def parse_section(section_key: str) -> dict[str, Any] | None:
    json_path = INPUT_JSON_FILES.get(section_key)
    text_path = INPUT_TEXT_FILES.get(section_key)

    json_data = read_json_file(json_path) if json_path else None
    text = read_text_file(text_path) if text_path else ""

    if not text and json_data is None:
        return None

    if not text and json_data is not None:
        text = safe_join_parts(json_data)

    updated_at = parse_timestamp_from_text(text) or ts()

    section = {
        "title": format_label(section_key),
        "source_file": text_path.name if text_path else "",
        "json_source_file": json_path.name if json_path and json_path.exists() else "",
        "updated_at": updated_at,
        "content": text,
    }

    section.update(build_editorial_fields(section_key, text, json_data))

    if isinstance(json_data, dict):
        for carry_key in [
            "cards",
            "stories",
            "games",
            "events",
            "odds",
            "freshness",
            "sports_checked",
            "total_games_checked",
            "links",
            "source_label",
        ]:
            if carry_key in json_data and carry_key not in section:
                section[carry_key] = json_data[carry_key]

    return section


def load_sections() -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}

    for key in SECTION_ORDER:
        parsed = parse_section(key)
        if parsed:
            sections[key] = parsed
            log(f"Loaded section: {key}")
        else:
            log(f"Missing section: {key}")

    return sections


# =============================================================================
# PAYLOAD BUILDERS
# =============================================================================

def section_priority_score(key: str, section: dict[str, Any]) -> int:
    text = " ".join(
        [
            clean_text(section.get("headline", "")),
            clean_text(section.get("snapshot", "")),
            safe_join_parts(section.get("key_data", [])),
            safe_join_parts(section.get("why_it_matters", [])),
            safe_join_parts(section.get("what_to_watch", [])),
        ]
    ).lower()

    score = 10

    if key == "betting_odds":
        score += 45
    if key in {"mlb", "nba", "wnba", "nhl"}:
        score += 18
    if key in {"nfl", "ncaafb"}:
        score += 12
    if key == "fantasy":
        score += 10

    if text_contains_any(text, BETTING_TERMS):
        score += 25
    if text_contains_any(text, VOLATILITY_TERMS):
        score += 28
    if text_contains_any(text, RISK_TERMS):
        score += 20
    if text_contains_any(text, PRESSURE_TERMS):
        score += 22
    if text_contains_any(text, LIVE_TERMS):
        score += 16

    if key in SECTION_ORDER:
        score += max(0, 20 - SECTION_ORDER.index(key))

    return score


def infer_headline(sections: dict[str, dict[str, Any]]) -> str:
    if not sections:
        return "The betting board is active across the sports market."

    ranked = sorted(
        sections.items(),
        key=lambda item: section_priority_score(item[0], item[1]),
        reverse=True,
    )

    for _, section in ranked:
        headline = clean_text(section.get("headline", ""))
        if headline:
            return headline

    return "The betting board is active across the sports market."


def infer_snapshot(sections: dict[str, dict[str, Any]]) -> str:
    if "betting_odds" in sections:
        why = normalize_lines(sections["betting_odds"].get("why_it_matters"), limit=1)
        if why:
            return why[0]

    ranked = sorted(
        sections.items(),
        key=lambda item: section_priority_score(item[0], item[1]),
        reverse=True,
    )

    for _, section in ranked:
        snapshot = clean_text(section.get("snapshot", ""))
        if snapshot:
            return snapshot

    return "Global Betting Report is monitoring odds, implied probability, market movement and matchup risk across the current sports board."


def build_key_storylines(sections: dict[str, dict[str, Any]]) -> list[str]:
    storylines: list[str] = []

    ranked = sorted(
        sections.items(),
        key=lambda item: section_priority_score(item[0], item[1]),
        reverse=True,
    )

    for key, section in ranked:
        headline = clean_text(section.get("headline", ""))
        snapshot = clean_text(section.get("snapshot", ""))
        if snapshot:
            storylines.append(f"{format_label(key)}: {snapshot}")
        elif headline:
            storylines.append(f"{format_label(key)}: {headline}")

    return storylines[:6]


def build_homepage_cards(sections: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    ranked = sorted(
        sections.items(),
        key=lambda item: section_priority_score(item[0], item[1]),
        reverse=True,
    )

    for key, section in ranked:
        cards.append(
            {
                "league": format_label(key),
                "key": key,
                "headline": trim_text(section.get("headline", ""), 180),
                "snapshot": trim_text(section.get("snapshot", ""), 260),
                "url": clean_text(section.get("url", "")),
                "source_label": clean_text(section.get("source_label", "")) or format_label(key),
                "story_type": clean_text(section.get("story_type", "market_board")),
                "market_signal": clean_text(section.get("market_signal", "market_board")),
                "key_data": normalize_lines(section.get("key_data") or section.get("key_data_points"), limit=4),
                "why_it_matters": normalize_lines(section.get("why_it_matters"), limit=3),
                "what_to_watch": normalize_lines(section.get("what_to_watch"), limit=3),
                "editorial_brain": section.get("editorial_brain", {}),
            }
        )

    return cards[:12]


def build_live_newsroom(sections: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    newsroom: list[dict[str, Any]] = []

    ranked = sorted(
        sections.items(),
        key=lambda item: section_priority_score(item[0], item[1]),
        reverse=True,
    )

    for key, section in ranked:
        newsroom.append(
            {
                "section": key,
                "label": format_label(key),
                "headline": clean_text(section.get("headline", "")),
                "snapshot": clean_text(section.get("snapshot", "")),
                "market_signal": clean_text(section.get("market_signal", "")),
                "updated_at": clean_text(section.get("updated_at", "")),
                "url": clean_text(section.get("url", "")),
            }
        )

    return newsroom[:10]


def build_editor_signals(sections: dict[str, dict[str, Any]]) -> list[str]:
    signals = [
        "Betting Editorial Brain v3 is active: odds are being interpreted as market context, not gambling advice.",
        "Cards now carry cleaner key_data, why_it_matters and what_to_watch fields for journalist-facing readability.",
        "Market context now detects favorite, underdog, spread, total, volatility, risk and live-board signals.",
    ]

    if "wnba" in sections:
        signals.append("WNBA betting window is active because WNBA data was detected.")
    else:
        signals.append("WNBA betting window is ready and will appear automatically when WNBA data files are generated.")

    if "fantasy" in sections:
        signals.append("Fantasy crossover watch is active for betting/fantasy context.")

    return signals


def build_payload(sections: dict[str, dict[str, Any]]) -> dict[str, Any]:
    now_string = ts()
    date_string = now_et().strftime("%Y-%m-%d")

    payload = {
        "site": SITE,
        "vertical": VERTICAL,
        "title": f"{TITLE} | {date_string}",
        "headline": infer_headline(sections),
        "snapshot": infer_snapshot(sections),
        "key_storylines": build_key_storylines(sections),
        "updated_at": now_string,
        "generated_at": now_string,
        "published_at": now_string,
        "x_handle": os.getenv("GSR_X_HANDLE", DEFAULT_X_HANDLE),
        "substack_url": os.getenv("GSR_SUBSTACK_URL", DEFAULT_SUBSTACK_URL),
        "disclaimer": DISCLAIMER,
        "editorial_brain_version": EDITORIAL_BRAIN_VERSION,
        "editorial_standard": "Betting data is used for context, signals and reporting structure only. This is not gambling advice.",
        "sections": {},
    }

    for key in SECTION_ORDER:
        if key in sections:
            payload["sections"][key] = sections[key]

    payload["homepage_cards"] = build_homepage_cards(sections)
    payload["live_newsroom"] = build_live_newsroom(sections)
    payload["editor_signals"] = build_editor_signals(sections)

    freshness = {}
    betting = sections.get("betting_odds", {})
    if isinstance(betting, dict):
        freshness = betting.get("freshness", {}) if isinstance(betting.get("freshness"), dict) else {}

    payload["freshness"] = {
        "last_checked": now_string,
        "source": "build_betting_distribution.py",
        "editorial_brain": EDITORIAL_BRAIN_VERSION,
        **freshness,
    }

    return payload


def build_text_report(payload: dict[str, Any]) -> str:
    parts: list[str] = [
        payload.get("title", TITLE),
        "",
        "HEADLINE",
        payload.get("headline", ""),
        "",
        "SNAPSHOT",
        payload.get("snapshot", ""),
        "",
        "KEY STORYLINES",
    ]

    for item in payload.get("key_storylines", []):
        parts.append(f"- {item}")

    parts += ["", "EDITOR SIGNALS"]

    for item in payload.get("editor_signals", []):
        parts.append(f"- {item}")

    parts.append("")

    for key in SECTION_ORDER:
        section = payload.get("sections", {}).get(key)
        if not section:
            continue

        parts.append(format_label(key).upper())

        headline = clean_text(section.get("headline", ""))
        snapshot = clean_text(section.get("snapshot", ""))

        if headline:
            parts.append("HEADLINE")
            parts.append(headline)

        if snapshot:
            parts.append("SNAPSHOT")
            parts.append(snapshot)

        key_data = normalize_lines(section.get("key_data") or section.get("key_data_points"), limit=5)
        if key_data:
            parts.append("KEY DATA")
            for item in key_data:
                parts.append(f"- {item}")

        why = normalize_lines(section.get("why_it_matters"), limit=5)
        if why:
            parts.append("WHY IT MATTERS")
            for item in why:
                parts.append(f"- {item}")

        watch = normalize_lines(section.get("what_to_watch"), limit=5)
        if watch:
            parts.append("WHAT TO WATCH")
            for item in watch:
                parts.append(f"- {item}")

        parts.append("")

    parts.append(DISCLAIMER)
    return safe_join_parts(parts)


# =============================================================================
# OPTIONAL GIT SYNC
# =============================================================================

def maybe_run_git_sync() -> bool:
    if os.getenv("WEBSITE_AUTO_GIT", "0").strip() != "1":
        log("Git sync skipped.")
        return False

    commands = [
        ["git", "add", "latest_report.json", "latest_report.txt", "global_betting_report.txt", "public/latest_report.json", "public/latest_report.txt", "public/global_betting_report.txt"],
        ["git", "commit", "-m", f"Update betting report {now_et().strftime('%Y-%m-%d %H:%M:%S ET')}"],
        ["git", "pull", "--rebase"],
        ["git", "push", "origin", "master"],
    ]

    try:
        for cmd in commands:
            result = subprocess.run(
                cmd,
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout.strip():
                log(result.stdout.strip())
            if result.stderr.strip():
                log(result.stderr.strip())
        return True
    except Exception as exc:
        log(f"Git sync exception: {exc}")
        return False


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    log("Starting Global Betting Report distribution build.")

    env_path = BASE_DIR / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)

    log(f"ENV PATH: {env_path}")
    log(f"ENV EXISTS: {env_path.exists()}")
    log(f"PUBLIC DIR: {PUBLIC_DIR}")

    sections = load_sections()

    if not sections:
        log("FATAL ERROR: No betting sections loaded.")
        return 1

    payload = build_payload(sections)
    text_report = build_text_report(payload)

    write_json_file(OUTPUT_LATEST_JSON, payload)
    write_text_file(OUTPUT_LATEST_TXT, text_report)
    write_text_file(OUTPUT_FULL_TXT, text_report)

    copy_file_if_exists(OUTPUT_LATEST_JSON, PUBLIC_LATEST_JSON)
    copy_file_if_exists(OUTPUT_LATEST_TXT, PUBLIC_LATEST_TXT)
    copy_file_if_exists(OUTPUT_FULL_TXT, PUBLIC_FULL_TXT)

    git_ok = maybe_run_git_sync()

    log("==============================================")
    log("GLOBAL BETTING REPORT DISTRIBUTION SUMMARY")
    log("==============================================")
    log(f"Sections loaded: {len(sections)}")
    for key in sections:
        log(f" - {format_label(key)}")
    log(f"Homepage cards: {len(payload.get('homepage_cards', []))}")
    log(f"Live newsroom items: {len(payload.get('live_newsroom', []))}")
    log(f"Editorial Brain: {EDITORIAL_BRAIN_VERSION}")
    log(f"Git sync OK: {git_ok}")
    log("NO CRITICAL ERRORS DETECTED")
    log("==============================================")
    log("GLOBAL BETTING REPORT DISTRIBUTION BUILD COMPLETE")
    log("==============================================")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        log(f"FATAL ERROR: {exc}")
        traceback.print_exc()
        raise SystemExit(1)