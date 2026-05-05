from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "nba_advanced_report.txt"

TIMEZONE = ZoneInfo("America/New_York")
REQUEST_TIMEOUT = 30

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, human sports journalism."
)

SCOREBOARD_URL = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
LEAGUE_DASH_URL = "https://stats.nba.com/stats/leaguedashteamstats"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

TEAM_NAME_MAP = {
    "hawks": "atlanta hawks",
    "celtics": "boston celtics",
    "nets": "brooklyn nets",
    "hornets": "charlotte hornets",
    "bulls": "chicago bulls",
    "cavaliers": "cleveland cavaliers",
    "mavericks": "dallas mavericks",
    "nuggets": "denver nuggets",
    "pistons": "detroit pistons",
    "warriors": "golden state warriors",
    "rockets": "houston rockets",
    "pacers": "indiana pacers",
    "clippers": "los angeles clippers",
    "lakers": "los angeles lakers",
    "grizzlies": "memphis grizzlies",
    "heat": "miami heat",
    "bucks": "milwaukee bucks",
    "timberwolves": "minnesota timberwolves",
    "pelicans": "new orleans pelicans",
    "knicks": "new york knicks",
    "thunder": "oklahoma city thunder",
    "magic": "orlando magic",
    "76ers": "philadelphia 76ers",
    "suns": "phoenix suns",
    "trail blazers": "portland trail blazers",
    "blazers": "portland trail blazers",
    "kings": "sacramento kings",
    "spurs": "san antonio spurs",
    "raptors": "toronto raptors",
    "jazz": "utah jazz",
    "wizards": "washington wizards",
}


def et_now() -> datetime:
    return datetime.now(TIMEZONE)


def report_date() -> str:
    return et_now().strftime("%Y-%m-%d")


def current_season_string(today: datetime | None = None) -> str:
    now = today or et_now()
    year = now.year
    if now.month >= 10:
        start_year = year
    else:
        start_year = year - 1
    end_year = str(start_year + 1)[-2:]
    return f"{start_year}-{end_year}"


def fix_encoding(text: str) -> str:
    return (
        text.replace("â€™", "’")
        .replace("â€˜", "‘")
        .replace("â€œ", '"')
        .replace("â€\x9d", '"')
        .replace("â€”", "—")
        .replace("â€“", "–")
        .replace("â€¦", "…")
        .replace("Â", "")
    )


def clean_text(text: str) -> str:
    text = fix_encoding(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def format_pct(value: Any, decimals: int = 1) -> str:
    try:
        return f"{float(value) * 100:.{decimals}f}%"
    except Exception:
        return "N/A"


def format_number(value: Any, decimals: int = 1) -> str:
    try:
        return f"{float(value):.{decimals}f}"
    except Exception:
        return "N/A"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def write_report(text: str) -> None:
    OUTPUT_FILE.write_text(clean_text(text) + "\n", encoding="utf-8")


def fetch_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def fetch_scoreboard() -> list[dict[str, Any]]:
    payload = fetch_json(SCOREBOARD_URL)
    games = payload.get("scoreboard", {}).get("games", [])
    return games if isinstance(games, list) else []


def fetch_advanced_team_stats() -> list[dict[str, Any]]:
    try:
        params = {
            "MeasureType": "Advanced",
            "PerMode": "PerGame",
            "Season": current_season_string(),
            "SeasonType": "Regular Season",
            "LeagueID": "00",
        }

        payload = fetch_json(LEAGUE_DASH_URL, params=params)

        result_sets = payload.get("resultSets")
        if not result_sets:
            return []

        result = result_sets[0]
        headers = result.get("headers", [])
        rows = result.get("rowSet", [])

        if not rows:
            return []

        return [dict(zip(headers, row)) for row in rows]

    except Exception:
        return []


def team_stats_index(
    stats_rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_name: dict[str, dict[str, Any]] = {}
    by_id: dict[str, dict[str, Any]] = {}

    for row in stats_rows:
        team_name = str(row.get("TEAM_NAME", "")).strip().lower()
        team_id = str(row.get("TEAM_ID", "")).strip()

        if team_name:
            by_name[team_name] = row

            short_name = team_name.split()[-1]
            if short_name and short_name not in by_name:
                by_name[short_name] = row

        if team_id:
            by_id[team_id] = row

    return by_name, by_id


def lookup_team_stats(
    team: dict[str, Any],
    by_name: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    team_id = str(team.get("teamId", "")).strip()
    team_name = str(team.get("teamName", "")).strip().lower()

    if team_id and team_id in by_id:
        return by_id[team_id]

    if team_name in TEAM_NAME_MAP:
        mapped_name = TEAM_NAME_MAP[team_name]
        if mapped_name in by_name:
            return by_name[mapped_name]

    if team_name in by_name:
        return by_name[team_name]

    return None


def game_time_text(game: dict[str, Any]) -> str:
    game_status = str(game.get("gameStatusText", "")).strip()
    game_et = str(game.get("gameEt", "")).strip()

    if game_status:
        return game_status
    if game_et:
        return game_et
    return "Time TBD"


def summarize_matchup(
    game: dict[str, Any],
    away_team: dict[str, Any],
    home_team: dict[str, Any],
    away_stats: dict[str, Any] | None,
    home_stats: dict[str, Any] | None,
) -> str:
    away_name = away_team.get("teamName", "Away Team")
    home_name = home_team.get("teamName", "Home Team")
    tipoff = game_time_text(game)

    if not away_stats or not home_stats:
        return (
            f"{away_name} at {home_name} ({tipoff}) remains on the board, "
            f"with limited advanced inputs confirmed, so the matchup leans on baseline team context and scoreboard flow."
        )

    away_net = safe_float(away_stats.get("NET_RATING"))
    home_net = safe_float(home_stats.get("NET_RATING"))
    away_off = safe_float(away_stats.get("OFF_RATING"))
    home_off = safe_float(home_stats.get("OFF_RATING"))
    away_def = safe_float(away_stats.get("DEF_RATING"))
    home_def = safe_float(home_stats.get("DEF_RATING"))
    away_pace = safe_float(away_stats.get("PACE"))
    home_pace = safe_float(home_stats.get("PACE"))
    away_ts = safe_float(away_stats.get("TS_PCT"))
    home_ts = safe_float(home_stats.get("TS_PCT"))
    away_tov = safe_float(away_stats.get("TM_TOV_PCT"))
    home_tov = safe_float(home_stats.get("TM_TOV_PCT"))

    combined_pace = (away_pace + home_pace) / 2 if away_pace and home_pace else 0.0
    net_gap = abs(home_net - away_net)

    stronger_team = home_name if home_net >= away_net else away_name
    better_offense = home_name if home_off >= away_off else away_name
    better_defense = home_name if home_def <= away_def else away_name
    cleaner_team = home_name if home_tov <= away_tov else away_name
    efficient_team = home_name if home_ts >= away_ts else away_name

    return (
        f"{away_name} at {home_name} ({tipoff}) lines up as a {format_number(net_gap)} net-rating gap matchup, "
        f"with {stronger_team} carrying the stronger overall profile. {better_offense} brings the better offensive rating, "
        f"{better_defense} owns the stronger defensive mark, {efficient_team} holds the better true shooting rate, "
        f"and {cleaner_team} has been cleaner with the ball. The projected tempo check sits around {format_number(combined_pace)} pace."
    )


def build_league_leaders(
    stats_rows: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    if not stats_rows:
        return [], [], []

    by_net = sorted(
        stats_rows,
        key=lambda row: safe_float(row.get("NET_RATING")),
        reverse=True,
    )
    by_pace = sorted(
        stats_rows,
        key=lambda row: safe_float(row.get("PACE")),
        reverse=True,
    )
    by_ts = sorted(
        stats_rows,
        key=lambda row: safe_float(row.get("TS_PCT")),
        reverse=True,
    )

    net_lines = [
        f"{row.get('TEAM_NAME', 'Unknown')} is sitting at {format_number(row.get('NET_RATING'))} net rating."
        for row in by_net[:3]
    ]
    pace_lines = [
        f"{row.get('TEAM_NAME', 'Unknown')} is playing at a {format_number(row.get('PACE'))} pace."
        for row in by_pace[:3]
    ]
    ts_lines = [
        f"{row.get('TEAM_NAME', 'Unknown')} is converting at {format_pct(row.get('TS_PCT'))} true shooting."
        for row in by_ts[:3]
    ]

    return net_lines, pace_lines, ts_lines


def build_key_data_points(
    games: list[dict[str, Any]],
    stats_rows: list[dict[str, Any]],
) -> list[str]:
    points: list[str] = []

    points.append(
        f"The NBA advanced layer reviewed {len(games)} game(s) against current season team-level efficiency data."
    )

    if stats_rows:
        by_net = sorted(
            stats_rows,
            key=lambda row: safe_float(row.get("NET_RATING")),
            reverse=True,
        )
        by_pace = sorted(
            stats_rows,
            key=lambda row: safe_float(row.get("PACE")),
            reverse=True,
        )
        by_ts = sorted(
            stats_rows,
            key=lambda row: safe_float(row.get("TS_PCT")),
            reverse=True,
        )

        if by_net:
            team = by_net[0]
            points.append(
                f"{team.get('TEAM_NAME', 'Unknown')} leads the current net-rating board at {format_number(team.get('NET_RATING'))}."
            )

        if by_pace:
            team = by_pace[0]
            points.append(
                f"{team.get('TEAM_NAME', 'Unknown')} is setting one of the fastest tempo profiles in the league at {format_number(team.get('PACE'))} pace."
            )

        if by_ts:
            team = by_ts[0]
            points.append(
                f"{team.get('TEAM_NAME', 'Unknown')} brings one of the strongest true shooting profiles in the league at {format_pct(team.get('TS_PCT'))}."
            )

    if games:
        first_game = games[0]
        away_team = first_game.get("awayTeam", {})
        home_team = first_game.get("homeTeam", {})
        points.append(
            f"The board opens with {away_team.get('teamName', 'Away Team')} at {home_team.get('teamName', 'Home Team')}, giving the slate an immediate efficiency matchup to frame."
        )

    return points[:5]


def build_story_angles(
    games: list[dict[str, Any]],
    stats_rows: list[dict[str, Any]],
) -> list[str]:
    angles: list[str] = []

    if stats_rows:
        best_def = min(
            stats_rows,
            key=lambda row: safe_float(row.get("DEF_RATING"), 9999.0),
        )
        best_off = max(
            stats_rows,
            key=lambda row: safe_float(row.get("OFF_RATING"), -9999.0),
        )
        best_ast = max(
            stats_rows,
            key=lambda row: safe_float(row.get("AST_RATIO"), -9999.0),
        )

        angles.append(
            f"Efficiency watch: {best_off.get('TEAM_NAME', 'Unknown')} remains a useful offensive benchmark with a {format_number(best_off.get('OFF_RATING'))} offensive rating."
        )
        angles.append(
            f"Defensive pressure angle: {best_def.get('TEAM_NAME', 'Unknown')} is still setting the pace defensively at {format_number(best_def.get('DEF_RATING'))} defensive rating."
        )
        angles.append(
            f"Ball movement lens: {best_ast.get('TEAM_NAME', 'Unknown')} continues to rate well in assist ratio, offering a clean team-playmaking storyline."
        )

    if games:
        angles.append(
            "Playoff-context framing: pace, shot efficiency, and turnover control become more useful editorial signals as the postseason environment tightens."
        )
        angles.append(
            "Matchup framing: use net rating gaps to separate true team-strength edges from simple win-loss record noise."
        )

    return angles[:5]


def build_matchup_flags(
    games: list[dict[str, Any]],
    by_name: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> list[str]:
    flags: list[str] = []

    for game in games[:6]:
        away_team = game.get("awayTeam", {})
        home_team = game.get("homeTeam", {})
        away_stats = lookup_team_stats(away_team, by_name, by_id)
        home_stats = lookup_team_stats(home_team, by_name, by_id)

        flags.append(
            summarize_matchup(game, away_team, home_team, away_stats, home_stats)
        )

    if not flags:
        flags.append(
            "No NBA games were available on the current board, so the analytics focus stays on league-level efficiency context."
        )

    return flags


def build_report(games: list[dict[str, Any]], stats_rows: list[dict[str, Any]]) -> str:
    title = f"NBA ADVANCED REPORT | {report_date()}"

    if not stats_rows and not games:
        return f"""{title}

HEADLINE
The NBA advanced analytics layer did not return usable game or league data in this report window.

SNAPSHOT
No advanced NBA data was available during this report window.

KEY DATA POINTS
- No scoreboard or advanced team-stat data could be confirmed during this report window.

WHY IT MATTERS
- Without usable advanced inputs, the safest editorial posture is to avoid overstating efficiency-based conclusions.

STORY ANGLES
- Recheck team-level advanced feeds and daily game availability before publishing analytics-driven NBA copy.

{DISCLAIMER}
"""

    if games:
        snapshot = (
            f"The NBA analytics board currently shows {len(games)} game(s) with matchup-level efficiency context."
        )
    else:
        snapshot = (
            "No NBA games are currently listed, but league-wide advanced team metrics still provide context."
        )

    headline = (
        "The NBA board is best framed through net rating, pace, shot efficiency, and turnover control as matchup signals sharpen."
    )

    key_data_points = build_key_data_points(games, stats_rows)
    story_angles = build_story_angles(games, stats_rows)

    by_name, by_id = team_stats_index(stats_rows)
    matchup_flags = build_matchup_flags(games, by_name, by_id)
    net_lines, pace_lines, ts_lines = build_league_leaders(stats_rows)

    parts: list[str] = [
        title,
        "",
        "HEADLINE",
        headline,
        "",
        "SNAPSHOT",
        snapshot,
        "",
        "KEY DATA POINTS",
    ]

    for item in key_data_points:
        parts.append(f"- {item}")

    parts.extend(["", "MATCHUP FLAGS"])
    for item in matchup_flags:
        parts.append(f"- {item}")

    if net_lines or pace_lines or ts_lines:
        parts.extend(["", "LEAGUE EFFICIENCY WATCH"])
        for item in net_lines:
            parts.append(f"- {item}")
        for item in pace_lines:
            parts.append(f"- {item}")
        for item in ts_lines:
            parts.append(f"- {item}")
    else:
        parts.extend(
            [
                "",
                "LEAGUE EFFICIENCY WATCH",
                "- League-wide advanced metrics were not fully available in this report window, but net rating, pace, and shooting efficiency remain the primary evaluation anchors.",
            ]
        )

    parts.extend(
        [
            "",
            "WHY IT MATTERS",
            "- Net rating helps separate sustainable team strength from surface-level record noise.",
            "- Pace matters because it shapes possession volume, transition pressure, and live scoring environment.",
            "- True shooting percentage offers a cleaner read on shot-quality conversion than raw field goal percentage alone.",
            "- Turnover rate and defensive rating help identify which teams are more likely to survive tighter postseason-style possessions.",
            "",
            "STORY ANGLES",
        ]
    )

    for item in story_angles:
        parts.append(f"- {item}")

    parts.extend(["", DISCLAIMER])

    return "\n".join(parts)


def main() -> None:
    try:
        games = fetch_scoreboard()
    except Exception:
        games = []

    try:
        stats_rows = fetch_advanced_team_stats()
    except Exception:
        stats_rows = []

    report = build_report(games, stats_rows)
    write_report(report)
    print(report)


if __name__ == "__main__":
    main()