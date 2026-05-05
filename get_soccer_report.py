from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TIMEZONE = ZoneInfo("America/New_York")
OUTPUT_FILE = Path("soccer_report.txt")
REQUEST_TIMEOUT = 20

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, human sports journalism."
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GlobalSportsReport/1.0)",
    "Accept": "application/json",
}

LEAGUES = [
    ("all", "Global"),
    ("eng.1", "Premier League"),
    ("esp.1", "LaLiga"),
    ("ger.1", "Bundesliga"),
    ("ita.1", "Serie A"),
    ("fra.1", "Ligue 1"),
]

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
# TIME
# =========================

def now_et() -> datetime:
    return datetime.now(TIMEZONE)


def report_date_label() -> str:
    return now_et().strftime("%Y-%m-%d")


def generated_timestamp() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


# =========================
# SAFE HELPERS
# =========================

def safe_get_competitors(event: dict) -> tuple[dict, dict]:
    try:
        competition = event.get("competitions", [{}])[0]
        competitors = competition.get("competitors", [])

        home = next((team for team in competitors if team.get("homeAway") == "home"), {})
        away = next((team for team in competitors if team.get("homeAway") == "away"), {})

        return away, home
    except Exception:
        return {}, {}


def safe_team_name(team_obj: dict) -> str:
    try:
        team = team_obj.get("team", {})
        return (
            team.get("displayName")
            or team.get("shortDisplayName")
            or team.get("name")
            or "Unknown Club"
        )
    except Exception:
        return "Unknown Club"


def safe_team_score(team_obj: dict) -> str:
    try:
        return str(team_obj.get("score", "0")).strip()
    except Exception:
        return "0"


def safe_team_record(team_obj: dict) -> str:
    try:
        for record in team_obj.get("records", []):
            summary = record.get("summary")
            if summary:
                return str(summary).strip()
    except Exception:
        pass
    return ""


def safe_status_detail(event: dict) -> str:
    try:
        competition = event.get("competitions", [{}])[0]
        status_type = competition.get("status", {}).get("type", {})
        return (
            status_type.get("shortDetail")
            or status_type.get("detail")
            or "Scheduled"
        )
    except Exception:
        return "Scheduled"


def safe_status_state(event: dict) -> str:
    try:
        competition = event.get("competitions", [{}])[0]
        return str(competition.get("status", {}).get("type", {}).get("state", "")).lower()
    except Exception:
        return ""


# =========================
# FETCH
# =========================

def fetch_events() -> list[dict]:
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"

    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json().get("events", [])
    except Exception:
        return []


# =========================
# LINE BUILDERS
# =========================

def build_final_line(event: dict) -> str:
    away, home = safe_get_competitors(event)

    away_name = safe_team_name(away)
    home_name = safe_team_name(home)
    away_score = safe_team_score(away)
    home_score = safe_team_score(home)

    if away_name == "Unknown Club" and home_name == "Unknown Club":
        return event.get("name", "Match Final.")

    return f"{home_name} {home_score}, {away_name} {away_score}."


def build_live_line(event: dict) -> str:
    away, home = safe_get_competitors(event)

    away_name = safe_team_name(away)
    home_name = safe_team_name(home)
    away_score = safe_team_score(away)
    home_score = safe_team_score(home)
    detail = safe_status_detail(event)

    if away_name == "Unknown Club" and home_name == "Unknown Club":
        return f"{event.get('name', 'Match')} - {detail}."

    return f"{away_name} {away_score}, {home_name} {home_score} - {detail}."


def build_upcoming_line(event: dict) -> str:
    away, home = safe_get_competitors(event)

    away_name = safe_team_name(away)
    home_name = safe_team_name(home)
    away_record = safe_team_record(away)
    home_record = safe_team_record(home)
    detail = safe_status_detail(event)

    if away_name == "Unknown Club" and home_name == "Unknown Club":
        return f"{event.get('name', 'Match')} - {detail}."

    matchup = f"{away_name} at {home_name} - {detail}."
    notes = []

    if away_record:
        notes.append(f"{away_name} enters at {away_record}")
    if home_record:
        notes.append(f"{home_name} comes in at {home_record}")

    if notes:
        return matchup + " " + ", while ".join(notes) + "."

    return matchup


# =========================
# BUILD REPORT
# =========================

def build_soccer_report(events: list[dict]) -> str:
    finals: list[str] = []
    live: list[str] = []
    upcoming: list[str] = []

    for event in events:
        state = safe_status_state(event)

        if state == "post":
            finals.append(build_final_line(event))
        elif state == "in":
            live.append(build_live_line(event))
        else:
            upcoming.append(build_upcoming_line(event))

    lines: list[str] = [
        f"SOCCER REPORT | {report_date_label()}",
        "",
        "SNAPSHOT",
        f"The soccer slate currently shows {len(finals)} final, {len(live)} live, and {len(upcoming)} upcoming matches.",
        "",
        "FINAL SCORES",
    ]

    if finals:
        for line in finals[:10]:
            lines.append(f"- {fix_spacing(line)}")
    else:
        lines.append("No final scores were available during this report window.")

    lines.extend([
        "",
        "LIVE",
    ])

    if live:
        for line in live[:10]:
            lines.append(f"- {fix_spacing(line)}")
    else:
        lines.append("No live matches were available during this report window.")

    lines.extend([
        "",
        "UPCOMING",
    ])

    if upcoming:
        for line in upcoming[:10]:
            lines.append(f"- {fix_spacing(line)}")
    else:
        lines.append("No upcoming matches were available during this report window.")

    lines.extend([
        "",
        DISCLAIMER,
        f"Generated: {generated_timestamp()}",
    ])

    report = "\n".join(lines)
    return fix_spacing(report) + "\n"


def write_report(report: str) -> None:
    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print("Soccer report written.")


def main() -> None:
    events = fetch_events()
    report = build_soccer_report(events)
    write_report(report)


if __name__ == "__main__":
    main()