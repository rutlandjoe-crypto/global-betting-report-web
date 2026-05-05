import os
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

SPORT = "baseball"
LEAGUE = "mlb"
TIMEZONE = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

REPORT_FILE = os.getenv("MLB_REPORT_FILE", "mlb_report.txt")

SCOREBOARD_URL = f"https://site.api.espn.com/apis/site/v2/sports/{SPORT}/{LEAGUE}/scoreboard"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GlobalSportsReport/1.0)"
}


def now_et():
    return datetime.now(TIMEZONE)


def format_et_time(dt_str):
    if not dt_str:
        return "Time TBD"

    try:
        dt_utc = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        dt_et = dt_utc.astimezone(TIMEZONE)
        return dt_et.strftime("%I:%M %p ET").lstrip("0")
    except Exception:
        try:
            dt_utc = datetime.strptime(dt_str, "%Y-%m-%dT%H:%MZ").replace(tzinfo=UTC)
            dt_et = dt_utc.astimezone(TIMEZONE)
            return dt_et.strftime("%I:%M %p ET").lstrip("0")
        except Exception:
            return "Time TBD"


def format_generated_timestamp():
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


def parse_event_datetime_et(event):
    dt_str = event.get("date")
    if not dt_str:
        return None

    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(TIMEZONE)
    except Exception:
        try:
            return datetime.strptime(dt_str, "%Y-%m-%dT%H:%MZ").replace(tzinfo=UTC).astimezone(TIMEZONE)
        except Exception:
            return None


def get_report_date_et():
    current = now_et()
    if current.hour < 3:
        return current.date() - timedelta(days=1)
    return current.date()


def is_event_relevant_to_report_day(event, report_date):
    event_dt = parse_event_datetime_et(event)
    if not event_dt:
        return False
    return event_dt.date() == report_date


def fetch_scoreboard_for_date(date_obj):
    date_str = date_obj.strftime("%Y%m%d")

    try:
        response = requests.get(
            SCOREBOARD_URL,
            params={"dates": date_str},
            timeout=20,
            headers=HEADERS,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        print(f"Request failed for {date_str}: {exc}")
        return {}


def collect_events():
    report_date = get_report_date_et()

    dates_to_check = [
        report_date - timedelta(days=1),
        report_date,
        report_date + timedelta(days=1),
    ]

    all_events = []
    seen_ids = set()

    for day in dates_to_check:
        data = fetch_scoreboard_for_date(day)
        events = data.get("events", [])

        for event in events:
            event_id = event.get("id")
            if not event_id or event_id in seen_ids:
                continue

            if is_event_relevant_to_report_day(event, report_date):
                seen_ids.add(event_id)
                all_events.append(event)

    return all_events


def get_competition(event):
    competitions = event.get("competitions", [])
    return competitions[0] if competitions else {}


def get_competitors(event):
    competition = get_competition(event)
    competitors = competition.get("competitors", [])

    away = None
    home = None

    for team in competitors:
        if team.get("homeAway") == "away":
            away = team
        elif team.get("homeAway") == "home":
            home = team

    return away, home


def get_team_name(team_obj):
    if not team_obj:
        return "Unknown Team"

    team = team_obj.get("team", {})
    return team.get("displayName") or team.get("name") or "Unknown Team"


def get_team_score(team_obj):
    if not team_obj:
        return "0"

    return str(team_obj.get("score", "0"))


def get_status_type(event):
    return event.get("status", {}).get("type", {})


def get_game_state(event):
    type_info = get_status_type(event)

    state = str(type_info.get("state", "")).lower()
    name = str(type_info.get("name", "")).lower()
    description = str(type_info.get("description", "")).lower()
    detail = str(type_info.get("detail", "")).lower()
    short_detail = str(type_info.get("shortDetail", "")).lower()
    completed = bool(type_info.get("completed", False))

    combined = " | ".join([state, name, description, detail, short_detail])

    if completed or "final" in combined or state == "post":
        return "final"

    if (
        state in {"in", "live"}
        or name == "status_in_progress"
        or "in progress" in combined
        or "top " in combined
        or "bot " in combined
        or "mid " in combined
        or "end " in combined
        or "delayed" in combined
        or "warmup" in combined
    ):
        return "live"

    return "upcoming"


def get_live_detail(event):
    type_info = get_status_type(event)
    detail = (type_info.get("detail") or "").strip()
    short_detail = (type_info.get("shortDetail") or "").strip()
    return detail or short_detail or "In Progress"


def build_game_line(event, mode):
    away, home = get_competitors(event)

    away_name = get_team_name(away)
    home_name = get_team_name(home)
    away_score = get_team_score(away)
    home_score = get_team_score(home)

    game_time = format_et_time(event.get("date"))

    if mode == "final":
        return f"FINAL: {away_name} {away_score}, {home_name} {home_score}."

    if mode == "live":
        return f"LIVE: {away_name} {away_score}, {home_name} {home_score} — {get_live_detail(event)}."

    return f"UPCOMING: {away_name} at {home_name} — {game_time}."


def sort_events(events):
    def event_sort_key(event):
        dt = parse_event_datetime_et(event)
        if dt:
            return dt
        return datetime.max.replace(tzinfo=TIMEZONE)

    return sorted(events, key=event_sort_key)


def categorize_events(events):
    finals = []
    live = []
    upcoming = []

    for event in sort_events(events):
        state = get_game_state(event)

        if state == "final":
            finals.append(event)
        elif state == "live":
            live.append(event)
        else:
            upcoming.append(event)

    return finals, live, upcoming


def build_intro(finals, live, upcoming):
    if live and upcoming:
        return "Across Major League Baseball, live action is underway while the rest of the day’s slate continues to take shape."
    if live and finals:
        return "Across Major League Baseball, games remain in progress as completed results begin to settle into focus."
    if live:
        return "Across Major League Baseball, live action is unfolding across the schedule."
    if finals and upcoming:
        return "Across Major League Baseball, completed results are on the board while more first pitches still lie ahead."
    if finals:
        return "Across Major League Baseball, the day’s results are beginning to settle into focus."
    if upcoming:
        return "Across Major League Baseball, attention turns to today’s schedule as clubs look to build early momentum."
    return "Across Major League Baseball, no active games were available at the time of this report."


def build_snapshot(finals, live, upcoming):
    parts = []

    if finals:
        parts.append(f"{len(finals)} final")
    if live:
        parts.append(f"{len(live)} live")
    if upcoming:
        parts.append(f"{len(upcoming)} upcoming")

    if not parts:
        return "No MLB games were available at the time of this report."

    return "The MLB slate currently features " + ", ".join(parts) + " game(s)."


def section_lines(title, events, mode):
    lines = [title]

    if not events:
        if mode == "final":
            lines.append("No final scores were available at the time of this report.")
        elif mode == "live":
            lines.append("No games are currently in progress.")
        else:
            lines.append("No upcoming games were scheduled.")
        return lines

    for event in events:
        lines.append(build_game_line(event, mode))

    return lines


def build_report():
    report_date = get_report_date_et().strftime("%Y-%m-%d")
    events = collect_events()
    finals, live, upcoming = categorize_events(events)

    lines = [
        f"MLB REPORT | {report_date}",
        "",
        build_intro(finals, live, upcoming),
        "",
        "SNAPSHOT",
        build_snapshot(finals, live, upcoming),
        "",
    ]

    lines.extend(section_lines("FINAL SCORES", finals, "final"))
    lines.append("")
    lines.extend(section_lines("LIVE GAMES", live, "live"))
    lines.append("")
    lines.extend(section_lines("UPCOMING", upcoming, "upcoming"))
    lines.append("")
    lines.append("This report is an automated summary of game data and is intended to support, not replace, human sports journalism.")
    lines.append(f"Generated: {format_generated_timestamp()}")

    return "\n".join(lines)


def save_report(report_text):
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)


def main():
    report = build_report()
    save_report(report)
    print(report)


if __name__ == "__main__":
    main()