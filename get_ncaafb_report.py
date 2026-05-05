from __future__ import annotations

import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

# =========================================================
# PATH + ENV
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# =========================================================
# CONFIG
# =========================================================
TIMEZONE = ZoneInfo("America/New_York")

SPORT = "football"
LEAGUE = "college-football"
SCOREBOARD_URL = f"https://site.api.espn.com/apis/site/v2/sports/{SPORT}/{LEAGUE}/scoreboard"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GlobalSportsReport/1.0)"
}

OUTPUT_FILE = Path(os.getenv("NCAAFB_REPORT_FILE", str(BASE_DIR / "ncaafb_report.txt")))

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, human sports journalism."
)

# =========================================================
# TEXT CLEANING
# =========================================================
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

        # Preserve records like 10-2 while still cleaning accidental dash spacing
        line = re.sub(r"\s*-\s*", " - ", line)
        line = re.sub(r"(\d) - (\d)", r"\1-\2", line)

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


# =========================================================
# TIME HELPERS
# =========================================================
def now_et() -> datetime:
    return datetime.now(TIMEZONE)


def format_generated_timestamp() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


def parse_event_datetime_et(event: dict) -> datetime | None:
    dt_str = event.get("date")
    if not dt_str:
        return None

    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(TIMEZONE)
    except Exception:
        return None


def format_kickoff_et(event: dict) -> str:
    dt = parse_event_datetime_et(event)
    if not dt:
        return "TBD"
    return dt.strftime("%I:%M %p ET").lstrip("0")


def get_report_date_et():
    current = now_et()
    return current.date() - timedelta(days=1) if current.hour < 3 else current.date()


# =========================================================
# DATA HELPERS
# =========================================================
def safe_get(url: str, params: dict | None = None) -> dict:
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {}


def fetch_scoreboard_for_date(date_obj) -> dict:
    return safe_get(SCOREBOARD_URL, params={"dates": date_obj.strftime("%Y%m%d")})


def collect_events() -> list[dict]:
    report_date = get_report_date_et()
    dates = [report_date - timedelta(days=1), report_date, report_date + timedelta(days=1)]

    events: list[dict] = []
    seen: set[str] = set()

    for d in dates:
        data = fetch_scoreboard_for_date(d)
        for event in data.get("events", []):
            event_id = event.get("id")
            if event_id and event_id not in seen:
                seen.add(event_id)
                events.append(event)

    return events


def get_competition(event: dict) -> dict:
    competitions = event.get("competitions", [])
    if competitions:
        return competitions[0]
    return {}


def get_competitors(event: dict) -> tuple[dict, dict]:
    competition = get_competition(event)
    competitors = competition.get("competitors", [])

    away = {}
    home = {}

    for team in competitors:
        if team.get("homeAway") == "away":
            away = team
        elif team.get("homeAway") == "home":
            home = team

    return away, home


def team_name(team_obj: dict) -> str:
    team = team_obj.get("team", {})
    return (
        team.get("displayName")
        or team.get("shortDisplayName")
        or team.get("name")
        or "Unknown Team"
    )


def team_score(team_obj: dict) -> str:
    return str(team_obj.get("score", "")).strip()


def team_record(team_obj: dict) -> str:
    records = team_obj.get("records", [])
    for record in records:
        summary = record.get("summary")
        if summary:
            return summary.strip()
    return ""


def event_state(event: dict) -> str:
    status = event.get("status", {})
    type_info = status.get("type", {})
    return type_info.get("state", "").lower()


def event_status_detail(event: dict) -> str:
    status = event.get("status", {})
    type_info = status.get("type", {})
    return (
        type_info.get("shortDetail")
        or type_info.get("detail")
        or status.get("displayClock")
        or ""
    ).strip()


# =========================================================
# LINE BUILDERS
# =========================================================
def build_final_line(event: dict) -> str:
    away, home = get_competitors(event)

    away_name = team_name(away)
    home_name = team_name(home)
    away_score = team_score(away)
    home_score = team_score(home)

    if away_score and home_score:
        return f"{away_name} {away_score}, {home_name} {home_score}."
    return f"{away_name} at {home_name} - Final."


def build_live_line(event: dict) -> str:
    away, home = get_competitors(event)

    away_name = team_name(away)
    home_name = team_name(home)
    away_score = team_score(away) or "0"
    home_score = team_score(home) or "0"
    detail = event_status_detail(event)

    if detail:
        return f"{away_name} {away_score}, {home_name} {home_score} - {detail}."
    return f"{away_name} {away_score}, {home_name} {home_score} - Live."


def build_upcoming_line(event: dict) -> str:
    away, home = get_competitors(event)

    away_name = team_name(away)
    home_name = team_name(home)
    away_record = team_record(away)
    home_record = team_record(home)
    kickoff = format_kickoff_et(event)

    matchup = f"{away_name} at {home_name} - {kickoff}."

    details = []
    if away_record:
        details.append(f"{away_name} enters at {away_record}")
    if home_record:
        details.append(f"{home_name} comes in at {home_record}")

    if details:
        return matchup + " " + ", while ".join(details) + "."

    return matchup


# =========================================================
# MAIN REPORT
# =========================================================
def build_ncaafb_report() -> str:
    report_date = get_report_date_et().strftime("%Y-%m-%d")
    events = collect_events()

    final_lines: list[str] = []
    live_lines: list[str] = []
    upcoming_lines: list[str] = []

    for event in sorted(events, key=lambda e: e.get("date", "")):
        state = event_state(event)

        if state == "post":
            final_lines.append(build_final_line(event))
        elif state == "in":
            live_lines.append(build_live_line(event))
        else:
            upcoming_lines.append(build_upcoming_line(event))

    snapshot_parts = []
    if final_lines:
        snapshot_parts.append(f"{len(final_lines)} final")
    if live_lines:
        snapshot_parts.append(f"{len(live_lines)} live")
    if upcoming_lines:
        snapshot_parts.append(f"{len(upcoming_lines)} upcoming")

    if snapshot_parts:
        snapshot_text = "The college football slate currently shows " + ", ".join(snapshot_parts) + " games."
    else:
        snapshot_text = "The college football slate currently shows no games in this report window."

    lines: list[str] = [
        f"NCAAFB REPORT | {report_date}",
        "",
        "SNAPSHOT",
        snapshot_text,
        "",
        "FINAL SCORES",
    ]

    if final_lines:
        for line in final_lines[:10]:
            lines.append(f"- {line}")
    else:
        lines.append("No final scores were available during this report window.")

    lines.extend([
        "",
        "LIVE",
    ])

    if live_lines:
        for line in live_lines[:10]:
            lines.append(f"- {line}")
    else:
        lines.append("No games are currently in progress.")

    lines.extend([
        "",
        "UPCOMING",
    ])

    if upcoming_lines:
        for line in upcoming_lines[:10]:
            lines.append(f"- {line}")
    else:
        lines.append("No upcoming games were scheduled.")

    lines.extend([
        "",
        DISCLAIMER,
        f"Generated: {format_generated_timestamp()}",
    ])

    report = "\n".join(lines)
    report = fix_spacing(report) + "\n"

    print(f"Saving report to: {OUTPUT_FILE}")
    OUTPUT_FILE.write_text(report, encoding="utf-8")

    return report


def main() -> None:
    report = build_ncaafb_report()
    print(report)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR generating NCAAFB report: {exc}")