import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from report_style import (
    league_opener,
    build_report_header,
    build_generated_line,
    final_line,
    live_line,
    upcoming_line,
    join_report_parts,
    no_games_line,
    closing_line,
    ordered_sections,
)

REPORT_FILE = os.getenv("NFL_REPORT_FILE", "nfl_report.txt")
TIMEZONE = os.getenv("REPORT_TIMEZONE", "America/Denver")

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def now_local():
    return datetime.now(ZoneInfo(TIMEZONE))


def safe_get(url, params=None):
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}")
        return {}


def infer_nfl_phase(dt):
    month = dt.month

    if 3 <= month <= 7:
        return "offseason"
    if month == 8:
        return "preseason"
    if month in (9, 10, 11, 12, 1):
        return "season"
    if month == 2:
        return "postseason"

    return "offseason"


def get_scoreboard():
    """
    Use the generic scoreboard first.
    Fall back to broader season views only if needed.
    """
    data = safe_get(SCOREBOARD_URL)
    if data.get("events"):
        return data

    current_year = now_local().year
    fallback_params = [
        {"dates": str(current_year), "seasontype": 2},
        {"dates": str(current_year), "seasontype": 3},
        {"dates": str(current_year - 1), "seasontype": 3},
        {"dates": str(current_year + 1), "seasontype": 1},
    ]

    for params in fallback_params:
        data = safe_get(SCOREBOARD_URL, params=params)
        if data.get("events"):
            return data

    return {}


def team_name(team_obj):
    if not isinstance(team_obj, dict):
        return "Unknown Team"
    return (
        team_obj.get("displayName")
        or team_obj.get("shortDisplayName")
        or team_obj.get("name")
        or "Unknown Team"
    )


def parse_event_datetime(date_str):
    if not date_str:
        return None

    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.astimezone(ZoneInfo(TIMEZONE))
    except Exception:
        return None


def is_relevant_event(event_dt, phase):
    """
    Filters out stale or cached old games.
    In offseason we want to be very strict.
    """
    if event_dt is None:
        return False

    now = now_local()
    diff_seconds = abs((event_dt - now).total_seconds())

    if phase == "offseason":
        return diff_seconds <= 3 * 24 * 3600

    if phase in ("preseason", "postseason"):
        return diff_seconds <= 10 * 24 * 3600

    return diff_seconds <= 14 * 24 * 3600


def format_kickoff(date_str):
    dt = parse_event_datetime(date_str)
    if not dt:
        return "TBD"

    try:
        return dt.strftime("%#I:%M %p %Z")
    except Exception:
        return dt.strftime("%I:%M %p %Z").lstrip("0")


def summarize_event(event):
    competitions = event.get("competitions", [])
    if not competitions:
        return None

    comp = competitions[0]
    competitors = comp.get("competitors", [])

    home = None
    away = None

    for competitor in competitors:
        if competitor.get("homeAway") == "home":
            home = competitor
        elif competitor.get("homeAway") == "away":
            away = competitor

    if not home or not away:
        return None

    home_team = team_name(home.get("team", {}))
    away_team = team_name(away.get("team", {}))

    home_score = home.get("score", "0")
    away_score = away.get("score", "0")

    try:
        home_score_int = int(home_score)
    except Exception:
        home_score_int = 0

    try:
        away_score_int = int(away_score)
    except Exception:
        away_score_int = 0

    status = comp.get("status", {})
    status_type = status.get("type", {})
    state = status_type.get("state", "")
    detail = status_type.get("detail", "") or status_type.get("shortDetail", "")
    completed = status_type.get("completed", False)

    if completed:
        if home_score_int > away_score_int:
            winner = home_team
            loser = away_team
            win_score = home_score_int
            lose_score = away_score_int
        else:
            winner = away_team
            loser = home_team
            win_score = away_score_int
            lose_score = home_score_int

        return {
            "section": "final",
            "winner": winner,
            "loser": loser,
            "win_score": win_score,
            "lose_score": lose_score,
        }

    if state == "in":
        return {
            "section": "live",
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score_int,
            "away_score": away_score_int,
            "detail": detail if detail else "Live",
        }

    kickoff_text = format_kickoff(comp.get("date") or event.get("date"))

    return {
        "section": "upcoming",
        "away_team": away_team,
        "home_team": home_team,
        "kickoff": kickoff_text,
    }


def build_lede(phase, finals, live, upcoming):
    base = league_opener("NFL")

    if phase == "offseason":
        if upcoming:
            return (
                f"{base} The league remains in its offseason window, with attention centered on roster movement, "
                "preparation, and the road to training camp."
            )
        return (
            f"{base} The league remains in its offseason window, with attention centered on roster movement, "
            "preparation, and the broader rhythm of the calendar."
        )

    if phase == "preseason":
        if finals and live:
            return f"{base} Preseason results came in while live action continued elsewhere."
        if finals:
            return f"{base} Preseason play offered another look at depth, evaluation, and early momentum."
        if upcoming:
            return f"{base} Attention now shifts to the upcoming preseason slate."
        return f"{base} Clubs continue their preseason buildup as attention turns toward evaluation and roster battles."

    if phase == "postseason":
        if finals and live:
            return f"{base} Postseason results came in while live action continued elsewhere."
        if finals:
            return f"{base} The postseason spotlight remained on high-leverage possessions and narrow margins."
        if upcoming:
            return f"{base} Attention now shifts to the next postseason matchup."
        return f"{base} The league sits in its postseason-to-offseason transition."

    if live and finals:
        return f"{base} Final results came in while part of the slate remained in progress."
    if finals and not live:
        return f"{base} Completed games were shaped by key stretches on both sides of the ball."
    if upcoming and not finals and not live:
        return f"{base} Attention now shifts to the upcoming slate."
    return base


def build_key_developments(final_events):
    if not final_events:
        return []

    developments = []

    highest = max(
        final_events,
        key=lambda event: (
            event["win_score"] + event["lose_score"]
        ),
    )

    developments.append(
        f"The highest-scoring final on the board was {highest['winner']} versus {highest['loser']}, which combined for {highest['win_score'] + highest['lose_score']} points."
    )

    blowouts = []
    close_games = []

    for event in final_events:
        matchup = f"{event['winner']} vs. {event['loser']}"
        margin = abs(event["win_score"] - event["lose_score"])

        if margin >= 14:
            blowouts.append(matchup)
        elif margin <= 3:
            close_games.append(matchup)

    if blowouts:
        developments.append(
            f"Several games turned decisively, including {', '.join(blowouts[:3])}."
        )

    if close_games:
        developments.append(
            f"A few games stayed tight deep into the day, including {', '.join(close_games[:3])}."
        )

    return list(dict.fromkeys(developments))


def build_final_lines(final_events):
    lines = []

    for event in final_events:
        lines.append(
            final_line(
                event["winner"],
                event["loser"],
                event["win_score"],
                event["lose_score"],
            )
        )

    return lines


def build_live_lines(live_events):
    lines = []

    for event in live_events:
        lines.append(
            live_line(
                event["home_team"],
                event["away_team"],
                event["home_score"],
                event["away_score"],
                event["detail"],
            )
        )

    return lines


def build_upcoming_lines(upcoming_events):
    lines = []

    for event in upcoming_events:
        lines.append(
            upcoming_line(
                event["away_team"],
                event["home_team"],
                event["kickoff"],
            )
        )

    return lines


def build_report():
    local_now = now_local()
    report_date = local_now.strftime("%Y-%m-%d")
    phase = infer_nfl_phase(local_now)

    data = get_scoreboard()
    events = data.get("events", [])

    final_events = []
    live_events = []
    upcoming_events = []

    for event in events:
        event_dt = parse_event_datetime(event.get("date"))

        if not is_relevant_event(event_dt, phase):
            continue

        summary = summarize_event(event)
        if not summary:
            continue

        section = summary["section"]

        if section == "final":
            final_events.append(summary)
        elif section == "live":
            live_events.append(summary)
        elif section == "upcoming":
            upcoming_events.append(summary)

    header = build_report_header("NFL Journalist Report", report_date)
    lede = build_lede(phase, final_events, live_events, upcoming_events)
    key_developments = build_key_developments(final_events)

    finals_section = build_final_lines(final_events)
    live_section = build_live_lines(live_events)
    upcoming_section = build_upcoming_lines(upcoming_events)

    sections = ordered_sections(
        finals=finals_section,
        live=live_section,
        upcoming=upcoming_section,
    )

    if not sections:
        if phase == "offseason":
            sections = [
                no_games_line(
                    "No live NFL games are on the board right now. This is a normal offseason outcome for the current football calendar."
                )
            ]
        else:
            sections = [
                no_games_line("No NFL games were available from the current data feed.")
            ]

    parts = [
        header,
        "",
        lede,
    ]

    if key_developments:
        parts.extend(["", "KEY DEVELOPMENTS", *key_developments])

    if sections:
        parts.extend(["", *sections])

    parts.extend(
        [
            "",
            closing_line(),
            "",
            build_generated_line(local_now),
        ]
    )

    return join_report_parts(parts)


def save_report(text):
    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        file.write(text)


def main():
    report = build_report()
    print(report)
    save_report(report)


if __name__ == "__main__":
    main()