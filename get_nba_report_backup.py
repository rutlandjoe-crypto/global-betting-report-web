import os
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from report_style import closing_line

load_dotenv()

REPORT_FILE = os.getenv("NBA_REPORT_FILE", "nba_report.txt")
TIMEZONE = os.getenv("REPORT_TIMEZONE", "America/Denver")

BASE_URL = "https://api.balldontlie.io/nba/v1"
API_KEY = os.getenv("BALLDONTLIE_API_KEY")

if not API_KEY:
    raise SystemExit("BALLDONTLIE_API_KEY is not set.")

HEADERS = {
    "Authorization": API_KEY
}


def safe_get(url, params=None):
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Request failed for {url}: {e}")
        return {}


def get_games_for_date(date_str):
    data = safe_get(
        f"{BASE_URL}/games",
        params={"dates[]": date_str, "per_page": 100}
    )
    return data.get("data", [])


def get_today_and_yesterday_games():
    now_local = datetime.now(ZoneInfo(TIMEZONE))
    today_str = now_local.strftime("%Y-%m-%d")
    yesterday_str = (now_local - timedelta(days=1)).strftime("%Y-%m-%d")

    today_games = get_games_for_date(today_str)
    yesterday_games = get_games_for_date(yesterday_str)

    return today_games, yesterday_games, now_local


def parse_game_time(game):
    game_time = game.get("datetime")
    if not game_time:
        return None

    try:
        dt = datetime.fromisoformat(game_time.replace("Z", "+00:00"))
        return dt.astimezone(ZoneInfo(TIMEZONE))
    except Exception:
        return None


def format_tipoff(game):
    dt = parse_game_time(game)
    if not dt:
        return "TBD"

    # Windows-safe hour format
    try:
        return dt.strftime("%#I:%M %p %Z")
    except Exception:
        return dt.strftime("%I:%M %p %Z").lstrip("0")


def team_name(team_obj, fallback="Unknown Team"):
    if not isinstance(team_obj, dict):
        return fallback
    return team_obj.get("full_name") or team_obj.get("name") or fallback


def get_scores(game):
    home_score = game.get("home_team_score")
    visitor_score = game.get("visitor_team_score")

    if home_score is None:
        home_score = 0
    if visitor_score is None:
        visitor_score = 0

    return visitor_score, home_score


def game_status_text(game):
    status = (game.get("status") or "").strip().lower()

    if "final" in status:
        return "final"

    if status in {"scheduled", "time tbd", "tbd"}:
        return "upcoming"

    # Guard against unusual statuses
    if "postpon" in status or "cancel" in status or "suspend" in status:
        return "upcoming"

    if status:
        return "live"

    dt = parse_game_time(game)
    if dt:
        now_local = datetime.now(ZoneInfo(TIMEZONE))
        if dt > now_local:
            return "upcoming"

    return "live"


def build_final_line(game):
    home = team_name(game.get("home_team"))
    visitor = team_name(game.get("visitor_team"))
    visitor_score, home_score = get_scores(game)

    if home_score > visitor_score:
        winner = home
        loser = visitor
        winner_score = home_score
        loser_score = visitor_score
    else:
        winner = visitor
        loser = home
        winner_score = visitor_score
        loser_score = home_score

    margin = abs(home_score - visitor_score)

    if margin >= 20:
        style = "in a one-sided result"
    elif margin >= 10:
        style = "after pulling away in the second half"
    elif margin <= 3:
        style = "in a tight finish"
    else:
        style = "in a solid all-around effort"

    return f"The {winner} beat the {loser} {winner_score}-{loser_score} {style}."


def build_live_line(game):
    home = team_name(game.get("home_team"))
    visitor = team_name(game.get("visitor_team"))
    visitor_score, home_score = get_scores(game)

    status = (game.get("status") or "").strip()
    time_remaining = (game.get("time") or "").strip()
    period = game.get("period")

    lowered = status.lower()

    if status and lowered not in {"live"}:
        detail = status
    elif time_remaining and period:
        detail = f"Q{period} {time_remaining}"
    elif period:
        detail = f"Q{period}"
    else:
        detail = "Live"

    return f"LIVE: {visitor} {visitor_score}, {home} {home_score} — {detail}."


def build_upcoming_line(game):
    home = team_name(game.get("home_team"))
    visitor = team_name(game.get("visitor_team"))
    return f"UPCOMING: {visitor} at {home} — {format_tipoff(game)}."


def classify_games(today_games, yesterday_games):
    finals = []
    live = []
    upcoming = []

    for game in today_games:
        category = game_status_text(game)
        if category == "final":
            finals.append(game)
        elif category == "live":
            live.append(game)
        else:
            upcoming.append(game)

    if not finals:
        for game in yesterday_games:
            if game_status_text(game) == "final":
                finals.append(game)

    tz = ZoneInfo(TIMEZONE)
    finals.sort(key=lambda g: parse_game_time(g) or datetime.min.replace(tzinfo=tz))
    live.sort(key=lambda g: parse_game_time(g) or datetime.min.replace(tzinfo=tz))
    upcoming.sort(key=lambda g: parse_game_time(g) or datetime.max.replace(tzinfo=tz))

    return finals, live, upcoming


def build_lede(finals, live, upcoming):
    if live and finals and upcoming:
        return (
            "Around the NBA, the night featured live action, completed results, "
            "and a schedule still unfolding across the league."
        )
    if live and finals:
        return (
            "Around the NBA, the night featured completed results and live action "
            "still unfolding late on the slate."
        )
    if live:
        return (
            "Around the NBA, several games were in progress as the night developed "
            "and the scoreboard continued to shift."
        )
    if finals and upcoming:
        return (
            "Around the NBA, the slate featured completed results early and more matchups still ahead."
        )
    if finals:
        return (
            "Around the NBA, the focus was on completed results, with several teams finding their rhythm."
        )
    if upcoming:
        return "Around the league, the focus shifts to the upcoming NBA slate."
    return "Around the NBA, there were no games available from the current data feed."


def build_report():
    today_games, yesterday_games, now_local = get_today_and_yesterday_games()
    finals, live, upcoming = classify_games(today_games, yesterday_games)

    lines = []
    lines.append(f"NBA Journalist Report | {now_local.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(build_lede(finals, live, upcoming))
    lines.append("")

    if finals:
        section_title = (
            "FINAL SCORES"
            if any(game_status_text(g) == "final" for g in today_games)
            else "YESTERDAY'S SCORES"
        )
        lines.append(section_title)
        for game in finals:
            lines.append(build_final_line(game))
        lines.append("")

    if live:
        lines.append("LIVE")
        for game in live:
            lines.append(build_live_line(game))
        lines.append("")

    if upcoming:
        lines.append("UPCOMING")
        for game in upcoming:
            lines.append(build_upcoming_line(game))
        lines.append("")

    if not finals and not live and not upcoming:
        lines.append("SCORES / SCHEDULE")
        lines.append("No games scheduled today.")
        lines.append("")

    lines.append(f"Generated: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    return "\n".join(lines)


def main():
    report = build_report()

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)


if __name__ == "__main__":
    main()