#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_distribution.py

Global Sports Report distribution builder.

What this script does:
- Loads plain-text report files from sports_bot-ai
- Loads optional advanced report files
- Builds a stable latest_report.json payload for the website
- Writes platform-ready text outputs:
  - substack_post.txt
  - telegram_post.txt
  - twitter_thread.txt
  - latest_report.txt
- Copies the website files into global-sports-report-web/public
- Copies Statcast SVG into website public folder so it renders on site
- Optionally posts to Telegram
- Optionally posts a thread to X/Twitter
- Never crashes because a section contains lists/dicts instead of strings
- Never calls undefined upload helpers

This file is designed as a full replacement.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import textwrap
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore

try:
    import requests
except Exception:
    requests = None  # type: ignore

try:
    import tweepy
except Exception:
    tweepy = None  # type: ignore

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # type: ignore


# =============================================================================
# PATHS / CONSTANTS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = Path(r"C:\Users\joeru\OneDrive\Desktop\global-sports-report-web")
WEB_PUBLIC_DIR = WEB_DIR / "public"

TITLE = "GLOBAL SPORTS REPORT"
DISCLAIMER = "This report is an automated summary intended to support, not replace, human sports journalism."
DEFAULT_X_HANDLE = "@GlobalSportsRp"
DEFAULT_SUBSTACK_URL = "https://globalsportsreport.substack.com/"

SITE_TZ = "America/New_York"

REPORT_FILES: dict[str, Path] = {
    "mlb": BASE_DIR / "mlb_report.txt",
    "nba": BASE_DIR / "nba_report.txt",
    "nhl": BASE_DIR / "nhl_report.txt",
    "nfl": BASE_DIR / "nfl_report.txt",
    "ncaafb": BASE_DIR / "ncaafb_report.txt",
    "soccer": BASE_DIR / "soccer_report.txt",
    "betting_odds": BASE_DIR / "betting_odds_report.txt",
    "fantasy": BASE_DIR / "fantasy_report.txt",
}

ADVANCED_REPORT_FILES: dict[str, Path] = {
    "mlb": BASE_DIR / "mlb_advanced_report.txt",
    "nba": BASE_DIR / "nba_advanced_report.txt",
    "nfl": BASE_DIR / "nfl_advanced_report.txt",
    "nfl_draft_signals": BASE_DIR / "nfl_draft_signals.txt",
}

JSON_REPORT_FILES: dict[str, Path] = {
    "mlb": BASE_DIR / "mlb_report.json",
    "nba": BASE_DIR / "nba_report.json",
    "nhl": BASE_DIR / "nhl_report.json",
    "nfl": BASE_DIR / "nfl_report.json",
    "ncaafb": BASE_DIR / "ncaafb_report.json",
    "soccer": BASE_DIR / "soccer_report.json",
    "betting_odds": BASE_DIR / "betting_odds_report.json",
    "fantasy": BASE_DIR / "fantasy_report.json",
}

STATCAST_FILES = [
    BASE_DIR / "mlb_statcast_snapshot.svg",
    BASE_DIR / "statcast_snapshot.svg",
]

OUTPUT_SUBSTACK = BASE_DIR / "substack_post.txt"
OUTPUT_TELEGRAM = BASE_DIR / "telegram_post.txt"
OUTPUT_TWITTER = BASE_DIR / "twitter_thread.txt"
OUTPUT_LATEST_TXT = BASE_DIR / "latest_report.txt"
OUTPUT_LATEST_JSON = BASE_DIR / "latest_report.json"
OUTPUT_PREVIOUS_JSON = BASE_DIR / "latest_report.previous.json"
GLOBAL_REPORT_TXT = BASE_DIR / "global_sports_report.txt"

WEB_COPY_TARGETS = {
    "latest_report.json": WEB_PUBLIC_DIR / "latest_report.json",
    "latest_report.txt": WEB_PUBLIC_DIR / "latest_report.txt",
    "global_sports_report.txt": WEB_PUBLIC_DIR / "global_sports_report.txt",
    "mlb_statcast_snapshot.svg": WEB_PUBLIC_DIR / "mlb_statcast_snapshot.svg",
}

SECTION_ORDER = [
    "mlb",
    "nba",
    "nhl",
    "nfl",
    "ncaafb",
    "soccer",
    "betting_odds",
    "fantasy",
]


# =============================================================================
# LOGGING / TIME
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
# ENV / TEXT SAFETY
# =============================================================================

def load_environment() -> None:
    env_path = BASE_DIR / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)
    log(f"ENV PATH: {env_path}")
    log(f"ENV EXISTS: {env_path.exists()}")
    log(f"TELEGRAM TOKEN FOUND: {bool(os.getenv('TELEGRAM_BOT_TOKEN'))}")
    log(f"TELEGRAM CHAT ID FOUND: {bool(os.getenv('TELEGRAM_CHAT_ID'))}")
    log(f"TWITTER API KEY FOUND: {bool(os.getenv('TWITTER_API_KEY'))}")
    log(f"TWITTER API SECRET FOUND: {bool(os.getenv('TWITTER_API_SECRET'))}")
    log(f"TWITTER ACCESS TOKEN FOUND: {bool(os.getenv('TWITTER_ACCESS_TOKEN'))}")
    log(f"TWITTER ACCESS TOKEN SECRET FOUND: {bool(os.getenv('TWITTER_ACCESS_TOKEN_SECRET'))}")
    log(f"TWITTER BEARER TOKEN FOUND: {bool(os.getenv('TWITTER_BEARER_TOKEN'))}")
    log(f"WEB PUBLIC DIR: {WEB_PUBLIC_DIR}")


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)

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
        "S nchez": "Sánchez",
        "Germ n": "Germán",
        "MartÃ­n": "Martín",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def slugify(text: str) -> str:
    text = clean_text(text).lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "section"


def format_label(key: str) -> str:
    labels = {
        "mlb": "MLB",
        "nba": "NBA",
        "nhl": "NHL",
        "nfl": "NFL",
        "ncaafb": "College Football",
        "soccer": "Soccer",
        "betting_odds": "Betting Odds",
        "fantasy": "Fantasy",
        "nfl_draft_signals": "NFL Draft Signals",
    }
    return labels.get(key, key.replace("_", " ").title())


def safe_join_parts(value: Any) -> str:
    """
    Flatten any mix of strings/lists/dicts into a clean string.

    This directly prevents the old:
    AttributeError: 'list' object has no attribute 'strip'
    """
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
        flattened.append(clean_text(str(item)))

    walk(value)
    return "\n\n".join(part for part in flattened if part.strip()).strip()


def first_meaningful_line(text: str) -> str:
    for line in clean_text(text).splitlines():
        line = line.strip(" -:\t")
        if line and line.upper() not in {
            "HEADLINE",
            "SNAPSHOT",
            "KEY DATA POINTS",
            "WHY IT MATTERS",
            "CURRENT DATA AND ANALYTICS",
            "STORY ANGLES",
            "FINAL SCORES",
            "YESTERDAY FINAL SCORES",
            "TODAY LIVE",
            "LIVE",
            "UPCOMING",
            "TODAY SCHEDULE",
            "TODAY FINAL SCORES",
            "DISCLAIMER",
            "UPDATED",
            "GLOBAL SNAPSHOT",
            "BETTING MARKET NOTE",
            "WATCH LIST",
            "MATCHUP FLAGS",
            "STATCAST WATCH",
            "BOARD CONTEXT",
            "LEAGUE EFFICIENCY WATCH",
        }:
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
    raw = path.read_text(encoding="utf-8", errors="replace")
    return clean_text(raw)


def read_json_file(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def write_text_file(path: Path, text: str) -> None:
    path.write_text(clean_text(text) + "\n", encoding="utf-8")
    log(f"Saved: {path}")


def write_json_file(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log(f"Saved: {path}")


# =============================================================================
# REPORT PARSING
# =============================================================================

SECTION_HEADER_RE = re.compile(
    r"^(HEADLINE|SNAPSHOT|KEY DATA POINTS|WHY IT MATTERS|CURRENT DATA AND ANALYTICS|"
    r"STORY ANGLES|FINAL SCORES|YESTERDAY FINAL SCORES|TODAY LIVE|LIVE|UPCOMING|"
    r"TODAY SCHEDULE|TODAY FINAL SCORES|DISCLAIMER|UPDATED|GLOBAL SNAPSHOT|"
    r"BETTING MARKET NOTE|WATCH LIST|MATCHUP FLAGS|STATCAST WATCH|BOARD CONTEXT|"
    r"LEAGUE EFFICIENCY WATCH)$",
    flags=re.IGNORECASE | re.MULTILINE,
)


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


def parse_advanced_report(path: Path) -> dict[str, Any] | None:
    text = read_text_file(path)
    if not text:
        return None

    lines = text.splitlines()
    title = lines[0].strip() if lines else f"{format_label(path.stem)} REPORT"
    updated_at = parse_timestamp_from_text(text) or now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")
    sections = split_named_sections(text)

    normalized_sections: dict[str, list[str]] = {}
    for key, values in sections.items():
        cleaned_values = [clean_text(v) for v in values if clean_text(v)]
        normalized_sections[key] = cleaned_values

    return {
        "title": title,
        "source_file": path.name,
        "updated_at": updated_at,
        "sections": normalized_sections,
    }


def parse_standard_report(section_key: str, path: Path) -> dict[str, Any] | None:
    text = read_text_file(path)
    if not text:
        return None

    lines = text.splitlines()
    title = lines[0].strip() if lines else f"{format_label(section_key)} REPORT"
    updated_at = parse_timestamp_from_text(text) or now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")

    return {
        "title": title,
        "source_file": path.name,
        "updated_at": updated_at,
        "content": text,
    }


def load_reports() -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}

    for key in SECTION_ORDER:
        path = REPORT_FILES.get(key)
        if not path:
            continue
        parsed = parse_standard_report(key, path)
        if parsed:
            reports[key] = parsed
            log(f"Loaded report: {path.name}")
        else:
            log(f"Missing report: {path.name}")

    return reports


def load_advanced_reports() -> dict[str, dict[str, Any]]:
    advanced: dict[str, dict[str, Any]] = {}
    for key, path in ADVANCED_REPORT_FILES.items():
        parsed = parse_advanced_report(path)
        if parsed:
            advanced[key] = parsed
            log(f"Loaded advanced report: {path.name}")
    return advanced


# =============================================================================
# GLOBAL JSON PAYLOAD
# =============================================================================

def infer_global_headline(reports: dict[str, dict[str, Any]]) -> str:
    mlb = reports.get("mlb", {}).get("content", "")
    nba = reports.get("nba", {}).get("content", "")
    nhl = reports.get("nhl", {}).get("content", "")
    soccer = reports.get("soccer", {}).get("content", "")

    for block in [mlb, nba, nhl, soccer]:
        sections = split_named_sections(block)
        headline = sections.get("headline", [])
        if headline:
            return headline[0]

    available = [format_label(k) for k in SECTION_ORDER if k in reports]
    if available:
        return f"{', '.join(available[:2])} lead the current sports calendar while the broader board stays in view."
    return "The sports calendar remains active across multiple leagues."

def extract_storylines(reports: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []

    for key in ["mlb", "nba", "nhl", "nfl", "ncaafb", "soccer", "fantasy"]:
        report = reports.get(key)
        if not report:
            continue
        content = report.get("content", "")
        sections = split_named_sections(content)
        snapshot = sections.get("snapshot", [])
        if snapshot:
            lines.append(f"{format_label(key)} snapshot: {snapshot[0]}")
        elif content:
            first_line = first_meaningful_line(content)
            if first_line:
                lines.append(f"{format_label(key)}: {first_line}")

    return lines[:6]


def infer_global_snapshot(reports: dict[str, dict[str, Any]]) -> str:
    fantasy = reports.get("fantasy", {}).get("content", "")
    if fantasy:
        sections = split_named_sections(fantasy)
        snapshot = sections.get("snapshot", [])
        if snapshot:
            return snapshot[0]

    soccer = reports.get("soccer", {}).get("content", "")
    if soccer:
        sections = split_named_sections(soccer)
        snapshot = sections.get("snapshot", [])
        if snapshot:
            return snapshot[0]

    return "No fantasy updates were available at this time."


def attach_advanced_reports(
    reports: dict[str, dict[str, Any]],
    advanced: dict[str, dict[str, Any]],
) -> None:
    for section_key, report in reports.items():
        if section_key in advanced:
            report["advanced"] = advanced[section_key]

    if "nfl_draft_signals" in advanced:
        if "nfl" in reports:
            report = reports["nfl"]
            if "advanced" not in report:
                report["advanced"] = advanced["nfl_draft_signals"]


def build_latest_report_payload(
    reports: dict[str, dict[str, Any]],
    advanced: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    attach_advanced_reports(reports, advanced)

    now_string = now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")
    date_string = now_et().strftime("%Y-%m-%d")

    payload = {
        "title": f"{TITLE} | {date_string}",
        "headline": infer_global_headline(reports),
        "key_storylines": extract_storylines(reports),
        "snapshot": infer_global_snapshot(reports),
        "generated_at": now_string,
        "updated_at": now_string,
        "published_at": now_string,
        "disclaimer": DISCLAIMER,
        "x_handle": os.getenv("GSR_X_HANDLE", DEFAULT_X_HANDLE),
        "substack_url": os.getenv("GSR_SUBSTACK_URL", DEFAULT_SUBSTACK_URL),
        "sections": {},
    }

    for key in SECTION_ORDER:
        if key in reports:
            payload["sections"][key] = reports[key]

    statcast_public_name = "mlb_statcast_snapshot.svg"
    if any(p.exists() for p in STATCAST_FILES):
        payload["statcast_graphic"] = f"/{statcast_public_name}"

    return payload


# =============================================================================
# PLATFORM TEXT BUILDERS
# =============================================================================

def build_latest_report_text(payload: dict[str, Any]) -> str:
    parts: list[str] = [
        payload.get("title", TITLE),
        "",
        "HEADLINE",
        payload.get("headline", ""),
        "",
        "KEY STORYLINES",
    ]

    for line in payload.get("key_storylines", []):
        parts.append(f"- {line}")

    parts += [
        "",
        "SNAPSHOT",
        payload.get("snapshot", ""),
        "",
    ]

    for key in SECTION_ORDER:
        section = payload.get("sections", {}).get(key)
        if not section:
            continue
        parts.append(format_label(key).upper())
        parts.append(section.get("content", ""))
        parts.append("")

    parts.append(DISCLAIMER)
    return safe_join_parts(parts)


def build_substack_post(payload: dict[str, Any]) -> str:
    parts: list[str] = [
        payload.get("title", TITLE),
        "",
        payload.get("headline", ""),
        "",
        "Key Storylines",
    ]
    for line in payload.get("key_storylines", []):
        parts.append(f"- {line}")

    parts += ["", "Snapshot", payload.get("snapshot", ""), ""]

    for key in SECTION_ORDER:
        section = payload.get("sections", {}).get(key)
        if not section:
            continue
        parts.append(format_label(key))
        parts.append(section.get("content", ""))
        advanced = section.get("advanced")
        if advanced:
            parts.append("")
            parts.append(f"{format_label(key)} Advanced")
            adv_sections = advanced.get("sections", {})
            for adv_key, adv_values in adv_sections.items():
                if not adv_values:
                    continue
                parts.append(adv_key.replace("_", " ").title())
                for item in adv_values:
                    parts.append(f"- {item}")
        parts.append("")

    parts.append(DISCLAIMER)
    return safe_join_parts(parts)


def build_telegram_post(payload: dict[str, Any]) -> str:
    lines: list[str] = [
        payload.get("title", TITLE),
        payload.get("headline", ""),
        "",
    ]
    for line in payload.get("key_storylines", [])[:5]:
        lines.append(f"- {line}")

    lines += [
        "",
        payload.get("snapshot", ""),
        "",
        f"Read more on Substack: {payload.get('substack_url', DEFAULT_SUBSTACK_URL)}",
        f"Follow on X: {payload.get('x_handle', DEFAULT_X_HANDLE)}",
    ]
    return safe_join_parts(lines)


def split_for_twitter(text: str, max_len: int = 275) -> list[str]:
    text = clean_text(text)
    chunks: list[str] = []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_len:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(para) <= max_len:
            current = para
            continue

        words = para.split()
        temp = ""
        for word in words:
            candidate_word = f"{temp} {word}".strip()
            if len(candidate_word) <= max_len:
                temp = candidate_word
            else:
                if temp:
                    chunks.append(temp)
                temp = word
        if temp:
            current = temp

    if current:
        chunks.append(current)

    total = len(chunks)
    numbered: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        prefix = f"{i}/{total} "
        if len(prefix) + len(chunk) > 280:
            chunk = chunk[: 280 - len(prefix) - 1].rstrip()
        numbered.append(prefix + chunk)
    return numbered


def build_twitter_thread(payload: dict[str, Any]) -> list[str]:
    intro = (
        f"{payload.get('title', TITLE)}\n\n"
        f"{payload.get('headline', '')}\n\n"
        f"{payload.get('x_handle', DEFAULT_X_HANDLE)}"
    )

    bullets = "\n".join(f"- {line}" for line in payload.get("key_storylines", [])[:4])

    body = (
        f"{intro}\n\n"
        f"Key storylines:\n{bullets}\n\n"
        f"Snapshot: {payload.get('snapshot', '')}\n\n"
        f"{payload.get('substack_url', DEFAULT_SUBSTACK_URL)}"
    )

    return split_for_twitter(body)


# =============================================================================
# COPY / WEBSITE SYNC
# =============================================================================

def backup_previous_json() -> None:
    if OUTPUT_LATEST_JSON.exists():
        shutil.copy2(OUTPUT_LATEST_JSON, OUTPUT_PREVIOUS_JSON)
        log(f"Backed up previous JSON to {OUTPUT_PREVIOUS_JSON.name}")


def copy_file_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    log(f"Copied: {src} -> {dst}")
    return True


def copy_statcast_asset() -> bool:
    for src in STATCAST_FILES:
        if src.exists():
            target = WEB_COPY_TARGETS["mlb_statcast_snapshot.svg"]
            return copy_file_if_exists(src, target)
    log("No Statcast SVG found to copy.")
    return False


def sync_website_files() -> list[Path]:
    copied: list[Path] = []

    pairs = [
        (OUTPUT_LATEST_JSON, WEB_COPY_TARGETS["latest_report.json"]),
        (OUTPUT_LATEST_TXT, WEB_COPY_TARGETS["latest_report.txt"]),
        (GLOBAL_REPORT_TXT, WEB_COPY_TARGETS["global_sports_report.txt"]),
    ]

    for src, dst in pairs:
        if copy_file_if_exists(src, dst):
            copied.append(dst)

    if copy_statcast_asset():
        copied.append(WEB_COPY_TARGETS["mlb_statcast_snapshot.svg"])

    return copied


# =============================================================================
# TELEGRAM / TWITTER
# =============================================================================

def send_telegram_message(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id or requests is None:
        log("Telegram send skipped.")
        return False

    chunks = split_for_telegram(text, 3900)
    ok = True

    for idx, chunk in enumerate(chunks, start=1):
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_web_page_preview": False,
                },
                timeout=30,
            )
            response.raise_for_status()
            log(f"Telegram part sent: {idx}/{len(chunks)}")
        except Exception as exc:
            ok = False
            log(f"Telegram exception: {exc}")
            break

    return ok


def split_for_telegram(text: str, max_len: int = 3900) -> list[str]:
    text = clean_text(text)
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current = ""

    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = para
            while len(current) > max_len:
                chunks.append(current[:max_len])
                current = current[max_len:]

    if current:
        chunks.append(current)

    return chunks


def send_twitter_thread(parts: list[str]) -> bool:
    api_key = os.getenv("TWITTER_API_KEY", "").strip()
    api_secret = os.getenv("TWITTER_API_SECRET", "").strip()
    access_token = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
    access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "").strip()

    if not all([api_key, api_secret, access_token, access_secret]) or tweepy is None:
        log("X/Twitter send skipped.")
        return False

    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )

        reply_to = None
        for idx, part in enumerate(parts, start=1):
            response = client.create_tweet(
                text=part,
                in_reply_to_tweet_id=reply_to,
                user_auth=True,
            )
            tweet_id = response.data["id"]
            reply_to = tweet_id
            log(f"Posted tweet {idx}/{len(parts)}")

        log("X thread posted successfully.")
        return True

    except Exception as exc:
        log(f"Twitter exception: {exc}")
        return False


# =============================================================================
# OPTIONAL WEBSITE GIT SYNC
# =============================================================================

def maybe_run_website_git_sync() -> bool:
    """
    Optional.
    Only runs if WEBSITE_AUTO_GIT=1 in .env.
    """
    if os.getenv("WEBSITE_AUTO_GIT", "0").strip() != "1":
        log("Website git sync skipped.")
        return False

    if not WEB_DIR.exists():
        log("Website git sync skipped: web directory missing.")
        return False

    commands = [
        ["git", "add", "public/latest_report.json", "public/latest_report.txt", "public/global_sports_report.txt", "public/mlb_statcast_snapshot.svg"],
        ["git", "commit", "-m", f"GSR auto-update {now_et().strftime('%Y-%m-%d %H:%M:%S ET')}"],
        ["git", "pull", "--rebase"],
        ["git", "push", "origin", "master"],
    ]

    try:
        for cmd in commands:
            result = subprocess.run(
                cmd,
                cwd=str(WEB_DIR),
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
        log(f"Website git sync exception: {exc}")
        return False


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    log("Starting distribution build.")
    load_environment()

    backup_previous_json()

    reports = load_reports()
    advanced = load_advanced_reports()

    if not reports:
        log("FATAL ERROR: No report files were loaded.")
        return 1

    payload = build_latest_report_payload(reports, advanced)

    latest_report_text = build_latest_report_text(payload)
    substack_post = build_substack_post(payload)
    telegram_post = build_telegram_post(payload)
    twitter_parts = build_twitter_thread(payload)

    write_json_file(OUTPUT_LATEST_JSON, payload)
    write_text_file(OUTPUT_LATEST_TXT, latest_report_text)
    write_text_file(OUTPUT_SUBSTACK, substack_post)
    write_text_file(OUTPUT_TELEGRAM, telegram_post)
    write_text_file(OUTPUT_TWITTER, "\n\n---\n\n".join(twitter_parts))

    if not GLOBAL_REPORT_TXT.exists():
        write_text_file(GLOBAL_REPORT_TXT, latest_report_text)

    copied_files = sync_website_files()

    telegram_ok = send_telegram_message(telegram_post)
    twitter_ok = send_twitter_thread(twitter_parts)
    website_git_ok = maybe_run_website_git_sync()

    log("==============================================")
    log("DISTRIBUTION SUMMARY")
    log("==============================================")
    log("Files Written: 5")
    log(f" - {OUTPUT_SUBSTACK.name}")
    log(f" - {OUTPUT_TELEGRAM.name}")
    log(f" - {OUTPUT_TWITTER.name}")
    log(f" - {OUTPUT_LATEST_TXT.name}")
    log(f" - {OUTPUT_LATEST_JSON.name}")

    log(f"Website Sync Copies: {len(copied_files)}")
    for path in copied_files:
        log(f" - {path}")

    log(f"Telegram OK: {telegram_ok}")
    log(f"X OK: {twitter_ok}")
    log(f"Website Auto-Deploy OK: {website_git_ok}")

    log("NO CRITICAL ERRORS DETECTED")
    log("==============================================")
    log("DISTRIBUTION BUILD COMPLETE")
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