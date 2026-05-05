from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TIMEZONE = ZoneInfo("America/New_York")
OUTPUT_FILE = Path("nfl_report.txt")
SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, human sports journalism."
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GlobalSportsReport/1.0)",
    "Accept": "application/json",
}

# =========================
# TEXT CLEANING
# =========================

def fix_encoding(text: str) -> str:
    if not text:
        return ""

    return (
        str(text)
        .replace("â€™", "’")
        .replace("â€˜", "‘")
        .replace("â€œ", '"')
        .replace("â€\x9d", '"')
        .replace("â€\x9c", '"')
        .replace("â€”", "—")
        .replace("â€“", "-")
        .replace("â€¢", "-")
        .replace("\u00a0", " ")
    )


def fix_spacing(text: str) -> str:
    if not text:
        return ""

    text = fix_encoding(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    fixed_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        if not line.strip():
            fixed_lines.append("")
            continue

        line = re.sub(r"[ \t]+", " ", line)
        line = re.sub(r"\s+([.,;:!?])", r"\1", line)
        line = re.sub(r"([.,;:!?])([A-Za-z])", r"\1 \2", line)
        line = re.sub(r"([a-z])([A-Z])", r"\1 \2", line)
        line = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", line)
        line = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", line)

        # Normalize bullet spacing
        if line.startswith("-") and not line.startswith("- "):
            line = "- " + line[1:].lstrip()

        fixed_lines.append(line.strip())

    cleaned: list[str] = []
    blank_count = 0

    for line in fixed_lines:
        if line.strip():
            cleaned.append(line)
            blank_count = 0
        else:
            blank_count += 1
            if blank_count <= 1:
                cleaned.append("")

    return "\n".join(cleaned).strip()


# =========================
# TIME HELPERS
# =========================

def now_et() -> datetime:
    return datetime.now(TIMEZONE)


def get_today_string() -> str:
    return now_et().strftime("%Y-%m-%d")


def format_generated_timestamp() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


# =========================
# SAFE HELPERS
# =========================

def safe_get_score(competitor: dict) -> str:
    try:
        return str(competitor.get("score", "0")).strip()
    except Exception:
        return "0"


def safe_get_team_name(competitor: dict) -> str:
    try:
        return competitor["team"]["displayName"].strip()
    except Exception:
        return "Unknown Team"


def safe_get_team_record(competitor: dict) -> str:
    try:
        records = competitor.get("records", [])
        for record in records:
            summary = record.get("summary")
            if summary:
                return str(summary).strip()
        return ""
    except Exception:
        return ""


# =========================
# API FETCH
# =========================

def fetch_scoreboard() -> dict:
    date_str = get_today_string()
    api_date = date_str.replace("-", "")
    url = f"{SCOREBOARD_URL}?dates={api_date}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception:
        try:
            response = requests.get(SCOREBOARD_URL, headers=HEADERS, timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}


# =========================
# GAME CLASSIFICATION
# =========================

def format_status(event: dict) -> str:
    try:
        competition = event["competitions"][0]
        status = competition.get("status", {}).get("type", {})
        return (
            status.get("shortDetail")
            or status.get("detail")
            or "Scheduled"
        )
    except Exception:
        return "Scheduled"


def classify_game(event: dict) -> tuple[str | None, str | None]:
    try:
        competition = event["competitions"][0]
        teams = competition["competitors"]

        away = next(team for team in teams if team.get("homeAway") == "away")
        home = next(team for team in teams if team.get("homeAway") == "home")

        away_name = safe_get_team_name(away)
        home_name = safe_get_team_name(home)
        away_score = safe_get_score(away)
        home_score = safe_get_score(home)
        away_record = safe_get_team_record(away)
        home_record = safe_get_team_record(home)

        status = competition.get("status", {}).get("type", {})
        state = status.get("state", "").lower()
        detail = format_status(event)

        if status.get("completed") or state == "post":
            return "final", f"{home_name} beat {away_name}, {home_score}-{away_score}."

        if state == "in":
            return "live", f"{away_name} {away_score}, {home_name} {home_score} - {detail}."

        matchup = f"{away_name} at {home_name} - {detail}."
        notes = []

        if away_record:
            notes.append(f"{away_name} enters at {away_record}")
        if home_record:
            notes.append(f"{home_name} comes in at {home_record}")

        if notes:
            return "upcoming", matchup + " " + ", while ".join(notes) + "."

        return "upcoming", matchup

    except Exception:
        return None, None


# =========================
# REPORT BUILD
# =========================

def build_report() -> str:
    data = fetch_scoreboard()
    events = data.get("events", [])

    finals: list[str] = []
    live: list[str] = []
    upcoming: list[str] = []

    for event in events:
        bucket, line = classify_game(event)
        if not bucket or not line:
            continue

        line = fix_spacing(line)

        if bucket == "final":
            finals.append(line)
        elif bucket == "live":
            live.append(line)
        else:
            upcoming.append(line)

    lines: list[str] = [
        f"NFL REPORT | {get_today_string()}",
        "",
        "SNAPSHOT",
        f"The NFL slate currently shows {len(finals)} final, {len(live)} live, and {len(upcoming)} upcoming games.",
        "",
        "FINAL SCORES",
    ]

    if finals:
        for line in finals:
            lines.append(f"- {line}")
    else:
        lines.append("No final scores were available during this report window.")

    lines.extend([
        "",
        "LIVE",
    ])

    if live:
        for line in live:
            lines.append(f"- {line}")
    else:
        lines.append("No live games were available during this report window.")

    lines.extend([
        "",
        "UPCOMING",
    ])

    if upcoming:
        for line in upcoming:
            lines.append(f"- {line}")
    else:
        lines.append("No upcoming games were available during this report window.")

    lines.extend([
        "",
        DISCLAIMER,
        f"Generated: {format_generated_timestamp()}",
    ])

    report = "\n".join(lines)
    report = fix_spacing(report) + "\n"

    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print("NFL report written successfully.")
    return report


if __name__ == "__main__":
    build_report()