from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

BASE_DIR = Path(__file__).resolve().parent
REPORT_FILE = BASE_DIR / "nba_report.txt"

TIMEZONE = ZoneInfo("America/New_York")
SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, human sports journalism."
)

REQUEST_TIMEOUT = 20


def fix_spacing(text: str) -> str:
    if not text:
        return ""

    # Add spaces in camel-case or merged alpha/number strings,
    # but never remove legitimate spaces.
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", text)
    text = re.sub(r"(?<=[0-9])(?=[A-Za-z])", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def now_et() -> datetime:
    return datetime.now(TIMEZONE)


def report_date() -> str:
    return now_et().strftime("%Y-%m-%d")


def generated_stamp() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


def clean_text(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2014": "—",
        "\u2013": "–",
        "\xa0": " ",
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€”": "—",
        "â€“": "–",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def save_report(text: str) -> None:
    REPORT_FILE.write_text(text.rstrip() + "\n", encoding="utf-8")


def fetch_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_scoreboard() -> tuple[dict[str, Any], str]:
    today = now_et().date()
    candidate_dates = [
        today.strftime("%Y-%m-%d"),
        (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        (today + timedelta(days=1)).strftime("%Y-%m-%d"),
    ]

    last_error = ""
    for date_str in candidate_dates:
        try:
            payload = fetch_json(SCOREBOARD_URL, {"dates": date_str})
            return payload, f"dated scoreboard lookup succeeded for {date_str}"
        except requests.HTTPError as exc:
            last_error = clean_text(str(exc))
        except Exception as exc:
            last_error = clean_text(str(exc))

    try:
        payload = fetch_json(SCOREBOARD_URL)
        return payload, "base scoreboard lookup succeeded without explicit date"
    except Exception as exc:
        base_error = clean_text(str(exc))
        if last_error:
            raise RuntimeError(
                f"NBA scoreboard lookup failed. Dated lookup error: {last_error}. "
                f"Base lookup error: {base_error}"
            ) from exc
        raise RuntimeError(f"NBA scoreboard lookup failed: {base_error}") from exc


def format_game_time(date_str: str | None) -> str:
    if not date_str:
        return "TBD"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(TIMEZONE)
        return dt.strftime("%I:%M %p ET").lstrip("0")
    except Exception:
        return "TBD"


def get_competition(event: dict[str, Any]) -> dict[str, Any]:
    competitions = event.get("competitions", [])
    return competitions[0] if competitions else {}


def get_competitors(event: dict[str, Any]) -> list[dict[str, Any]]:
    return get_competition(event).get("competitors", [])


def team_name(team_block: dict[str, Any]) -> str:
    team = team_block.get("team", {})
    display_name = team.get("displayName")
    if display_name:
        return clean_text(str(display_name))

    location = clean_text(str(team.get("location", "")))
    nickname = clean_text(str(team.get("name", "")))
    combined = f"{location} {nickname}".strip()
    if combined:
        return combined

    return "Unknown Team"


def team_score(team_block: dict[str, Any]) -> int | None:
    raw = clean_text(str(team_block.get("score", "")))
    return int(raw) if raw.isdigit() else None


def split_home_away(event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    away: dict[str, Any] = {}
    home: dict[str, Any] = {}

    for comp in get_competitors(event):
        side = clean_text(str(comp.get("homeAway", ""))).lower()
        if side == "away":
            away = comp
        elif side == "home":
            home = comp

    return away, home


def game_status(event: dict[str, Any]) -> tuple[str, str]:
    status = event.get("status", {})
    typ = status.get("type", {})
    state = clean_text(str(typ.get("state", ""))).lower()
    detail = clean_text(str(typ.get("detail", "")))
    description = clean_text(str(typ.get("description", ""))).lower()
    completed = bool(typ.get("completed", False))

    if completed or state == "post" or "final" in description:
        return "final", detail or "Final"
    if state in {"in", "live"}:
        return "live", detail or "Live"
    return "upcoming", detail or "Scheduled"


def build_final_line(event: dict[str, Any]) -> str:
    away, home = split_home_away(event)
    away_name = team_name(away)
    home_name = team_name(home)
    away_score = team_score(away)
    home_score = team_score(home)

    if away_score is None or home_score is None:
        return f"{away_name} at {home_name} - Final."

    if away_score > home_score:
        winner, loser = away_name, home_name
        win_score, lose_score = away_score, home_score
    else:
        winner, loser = home_name, away_name
        win_score, lose_score = home_score, away_score

    return f"{winner} beat {loser}, {win_score}-{lose_score}."


def build_live_line(event: dict[str, Any]) -> str:
    away, home = split_home_away(event)
    away_name = team_name(away)
    home_name = team_name(home)
    away_score = team_score(away)
    home_score = team_score(home)
    _, detail = game_status(event)

    if away_score is None or home_score is None:
        return f"{away_name} at {home_name} - {detail}."

    return f"{away_name} {away_score}, {home_name} {home_score} - {detail}."


def build_upcoming_line(event: dict[str, Any]) -> str:
    away, home = split_home_away(event)
    away_name = team_name(away)
    home_name = team_name(home)
    game_time = format_game_time(event.get("date"))
    return f"{away_name} at {home_name} - {game_time}."


def extract_record(team_block: dict[str, Any]) -> str:
    for rec in team_block.get("records", []):
        summary = clean_text(str(rec.get("summary", "")))
        if summary:
            return summary
    return ""


def parse_wins(record: str) -> int:
    match = re.match(r"(\d+)-(\d+)", record)
    return int(match.group(1)) if match else 0


def build_team_context(event: dict[str, Any]) -> list[str]:
    away, home = split_home_away(event)
    away_name = team_name(away)
    home_name = team_name(home)
    away_record = extract_record(away)
    home_record = extract_record(home)

    if away_record and home_record:
        return [f"{away_name} enters at {away_record}, while {home_name} comes in at {home_record}."]
    if away_record:
        return [f"{away_name} enters this matchup at {away_record}."]
    if home_record:
        return [f"{home_name} enters this matchup at {home_record}."]
    return []


def determine_marquee_games(upcoming_events: list[dict[str, Any]]) -> list[str]:
    ranked: list[tuple[int, str]] = []

    for event in upcoming_events:
        away, home = split_home_away(event)
        away_record = extract_record(away)
        home_record = extract_record(home)
        score = parse_wins(away_record) + parse_wins(home_record)

        line = (
            f"{team_name(away)} at {team_name(home)} "
            f"({format_game_time(event.get('date'))}) stands out as one of the stronger board matchups by record profile."
        )
        ranked.append((score, line))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [line for _, line in ranked[:3]]


def build_pro_sections(
    events: list[dict[str, Any]], lookup_note: str
) -> tuple[list[str], list[str], list[str]]:
    finals = [e for e in events if game_status(e)[0] == "final"]
    live = [e for e in events if game_status(e)[0] == "live"]
    upcoming = [e for e in events if game_status(e)[0] == "upcoming"]

    key_data_points: list[str] = []
    why_it_matters: list[str] = []
    story_angles: list[str] = []

    total_games = len(events)
    key_data_points.append(f"The NBA board features {total_games} total games in this report window.")

    if upcoming:
        key_data_points.append(
            f"{len(upcoming)} games remain ahead on the schedule, keeping the editorial focus on matchup framing and board positioning."
        )
    if live:
        key_data_points.append(
            f"{len(live)} games are live, shifting part of the coverage window toward pace, leverage possessions, and closing stretches."
        )
    if finals:
        key_data_points.append(
            f"{len(finals)} games have gone final, adding recap value alongside any remaining live or upcoming matchups."
        )

    context_added = 0
    for event in upcoming:
        for line in build_team_context(event):
            key_data_points.append(line)
            context_added += 1
            if context_added >= 2:
                break
        if context_added >= 2:
            break

    if "without explicit date" in lookup_note:
        key_data_points.append(
            "ESPN's base NBA scoreboard feed was used for this report window after the dated endpoint rejected the requested date."
        )

    if upcoming:
        why_it_matters.append(
            "With scheduled games still on the board, matchup context, team records, and late-season positioning offer the clearest entry points for pregame coverage."
        )
    if live:
        why_it_matters.append(
            "Live NBA action increases the value of game-flow framing, especially around pace swings, fourth-quarter leverage, and rotation pressure."
        )
    if finals:
        why_it_matters.append(
            "Completed games add quick-turn recap value, allowing writers to balance immediate reaction coverage with the remaining slate."
        )
    if not why_it_matters:
        why_it_matters.append(
            "The NBA board remains useful primarily through schedule context and matchup setup in this report window."
        )

    marquee = determine_marquee_games(upcoming)
    story_angles.extend(marquee[:2])
    story_angles.append(
        "Where the board mixes finals, live action, and upcoming games, the strongest NBA coverage can shift quickly from recap writing to real-time reaction and then back to pregame framing."
    )
    if upcoming:
        story_angles.append(
            "Late-day NBA windows are especially useful for newsletters, aggregation, and digital desk planning because lineup news and seeding context can quickly change story value."
        )

    return key_data_points[:5], why_it_matters[:3], story_angles[:4]


def build_report(events: list[dict[str, Any]], lookup_note: str) -> str:
    finals: list[str] = []
    live: list[str] = []
    upcoming: list[str] = []

    for event in events:
        status_group, _ = game_status(event)
        if status_group == "final":
            finals.append(build_final_line(event))
        elif status_group == "live":
            live.append(build_live_line(event))
        else:
            upcoming.append(build_upcoming_line(event))

    snapshot_parts = []
    if finals:
        snapshot_parts.append(f"{len(finals)} final")
    if live:
        snapshot_parts.append(f"{len(live)} live")
    if upcoming:
        snapshot_parts.append(f"{len(upcoming)} upcoming")

    snapshot_text = (
        f"The NBA slate currently shows {', '.join(snapshot_parts)} games."
        if snapshot_parts
        else "No NBA games were available during this report window."
    )

    key_data_points, why_it_matters, story_angles = build_pro_sections(events, lookup_note)

    lines: list[str] = [
        f"NBA PRO REPORT | {report_date()}",
        "",
        "HEADLINE",
        "The NBA board is shaping the day through matchup positioning, team context, and the shifting value of live, final, and upcoming game windows.",
        "",
        "SNAPSHOT",
        snapshot_text,
        "",
        "KEY DATA POINTS",
    ]

    if key_data_points:
        lines.extend([f"- {fix_spacing(clean_text(item))}" for item in key_data_points])
    else:
        lines.append("- No NBA data points were available during this report window.")

    lines.extend(["", "WHY IT MATTERS"])
    if why_it_matters:
        lines.extend([f"- {fix_spacing(clean_text(item))}" for item in why_it_matters])
    else:
        lines.append("- The NBA board remains useful primarily through game status, matchup framing, and schedule positioning.")

    lines.extend(["", "STORY ANGLES"])
    if story_angles:
        lines.extend([f"- {fix_spacing(clean_text(item))}" for item in story_angles])
    else:
        lines.append("- Matchup framing and board sequencing remain the clearest NBA story entry points in this report window.")

    lines.extend(["", "FINAL SCORES"])
    lines.extend(finals if finals else ["No final scores were available during this report window."])

    lines.extend(["", "LIVE"])
    lines.extend(live if live else ["No live games were available during this report window."])

    lines.extend(["", "UPCOMING"])
    lines.extend(upcoming if upcoming else ["No upcoming games were available during this report window."])

    lines.extend([
        "",
        DISCLAIMER,
        "",
        f"Generated: {generated_stamp()}",
    ])

    return "\n".join(lines)


def build_fallback_report(reason: str) -> str:
    reason = clean_text(reason)
    return "\n".join([
        f"NBA PRO REPORT | {report_date()}",
        "",
        "HEADLINE",
        "The NBA board remains in focus, but full report generation was limited during this window.",
        "",
        "SNAPSHOT",
        "The NBA board could not be fully processed during this report window.",
        "",
        "KEY DATA POINTS",
        "- Live NBA scoreboard data was temporarily unavailable.",
        "",
        "WHY IT MATTERS",
        "- Even when data is interrupted, the NBA calendar still drives daily planning for previews, recaps, and reaction coverage.",
        "",
        "STORY ANGLES",
        "- The next clean data pull should restore game-state context, matchup framing, and board-level structure.",
        "",
        "FINAL SCORES",
        "No final scores were available during this report window.",
        "",
        "LIVE",
        "No live games were available during this report window.",
        "",
        "UPCOMING",
        "No upcoming games were available during this report window.",
        "",
        DISCLAIMER,
        "",
        f"Generated: {generated_stamp()}",
        f"Fallback reason: {reason}",
    ])


def main() -> None:
    try:
        payload, lookup_note = fetch_scoreboard()
        events = payload.get("events", [])
        report = build_report(events, lookup_note)
        save_report(report)
        print(report)
        print()
        print(f"Saved: {REPORT_FILE}")
    except Exception as exc:
        fallback = build_fallback_report(str(exc))
        save_report(fallback)
        print(fallback)
        print()
        print(f"Saved fallback: {REPORT_FILE}")


if __name__ == "__main__":
    main()