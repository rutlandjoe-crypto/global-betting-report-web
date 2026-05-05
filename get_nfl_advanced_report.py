from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "nfl_advanced_report.txt"
STANDARD_REPORT_FILE = BASE_DIR / "nfl_report.txt"

TIMEZONE = ZoneInfo("America/New_York")
REQUEST_TIMEOUT = 30

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, "
    "human sports journalism."
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GlobalSportsReport/1.0)",
    "Accept": "text/csv,application/json,text/plain,*/*",
}


# =========================================================
# DATE / SEASON HELPERS
# =========================================================
def et_now() -> datetime:
    return datetime.now(TIMEZONE)


def report_date() -> str:
    return et_now().strftime("%Y-%m-%d")


def current_nfl_season_year(today: datetime | None = None) -> int:
    now = today or et_now()
    return now.year if now.month >= 9 else now.year - 1


def current_draft_year(today: datetime | None = None) -> int:
    now = today or et_now()
    return now.year


# =========================================================
# URLS
# =========================================================
def team_stats_url(season: int) -> str:
    return (
        "https://github.com/nflverse/nflverse-data/releases/download/"
        f"stats_team/stats_team_reg_{season}.csv"
    )


DRAFT_PICKS_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "draft_picks/draft_picks.csv"
)


# =========================================================
# TEXT CLEANING
# =========================================================
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


def write_report(text: str) -> None:
    OUTPUT_FILE.write_text(clean_text(text) + "\n", encoding="utf-8")


# =========================================================
# CSV / DATA HELPERS
# =========================================================
def fetch_csv_rows(url: str) -> list[dict[str, str]]:
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    response.encoding = "utf-8"
    reader = csv.DictReader(StringIO(response.text))
    return [dict(row) for row in reader]


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        text = str(value).strip()
        if text == "":
            return default
        return float(text)
    except Exception:
        return default


def safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None:
            return default
        text = str(value).strip()
        if text == "":
            return default
        return int(float(text))
    except Exception:
        return default


def format_number(value: float | None, decimals: int = 3) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"


def first_present(row: dict[str, Any], candidates: list[str]) -> Any:
    for key in candidates:
        if key in row and str(row.get(key, "")).strip() != "":
            return row.get(key)
    return None


def per_play_value(total: float | None, plays: float | None) -> float | None:
    if total is None or plays is None or plays <= 0:
        return None
    return total / plays


# =========================================================
# TEAM NAME / ABBR HELPERS
# =========================================================
TEAM_NAME_TO_ABBR = {
    "arizona cardinals": "ARI",
    "atlanta falcons": "ATL",
    "baltimore ravens": "BAL",
    "buffalo bills": "BUF",
    "carolina panthers": "CAR",
    "chicago bears": "CHI",
    "cincinnati bengals": "CIN",
    "cleveland browns": "CLE",
    "dallas cowboys": "DAL",
    "denver broncos": "DEN",
    "detroit lions": "DET",
    "green bay packers": "GB",
    "houston texans": "HOU",
    "indianapolis colts": "IND",
    "jacksonville jaguars": "JAX",
    "kansas city chiefs": "KC",
    "las vegas raiders": "LV",
    "los angeles chargers": "LAC",
    "los angeles rams": "LAR",
    "miami dolphins": "MIA",
    "minnesota vikings": "MIN",
    "new england patriots": "NE",
    "new orleans saints": "NO",
    "new york giants": "NYG",
    "new york jets": "NYJ",
    "philadelphia eagles": "PHI",
    "pittsburgh steelers": "PIT",
    "san francisco 49ers": "SF",
    "seattle seahawks": "SEA",
    "tampa bay buccaneers": "TB",
    "tennessee titans": "TEN",
    "washington commanders": "WAS",
}

TEAM_ABBR_TO_NAME = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}


def normalize_team_abbr(text: str) -> str:
    text = str(text or "").strip().upper()
    aliases = {
        "ARZ": "ARI",
        "BLT": "BAL",
        "CLV": "CLE",
        "GNB": "GB",
        "HST": "HOU",
        "JAC": "JAX",
        "KAN": "KC",
        "LVR": "LV",
        "NWE": "NE",
        "NOR": "NO",
        "SFO": "SF",
        "TAM": "TB",
        "WSH": "WAS",
        "LA": "LAR",
    }
    return aliases.get(text, text)


# =========================================================
# LOCAL STANDARD REPORT PARSING
# =========================================================
def read_standard_nfl_report() -> str:
    if not STANDARD_REPORT_FILE.exists():
        return ""
    try:
        return STANDARD_REPORT_FILE.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return STANDARD_REPORT_FILE.read_text(encoding="utf-8", errors="ignore")


def extract_upcoming_lines(report_text: str) -> list[str]:
    if not report_text.strip():
        return []

    text = report_text.replace("\r\n", "\n").replace("\r", "\n")
    match = re.search(
        r"(?ms)^UPCOMING\s*\n(.+?)(?:\n[A-Z][A-Z ]+\n|\Z)",
        text,
    )
    if not match:
        return []

    lines: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped:
            lines.append(re.sub(r"^\-\s*", "", stripped))
    return lines[:8]


# =========================================================
# DATA LOADERS
# =========================================================
def load_team_stats() -> tuple[int, list[dict[str, str]]]:
    season = current_nfl_season_year()
    last_error: Exception | None = None

    for candidate in [season, season - 1]:
        try:
            rows = fetch_csv_rows(team_stats_url(candidate))
            if rows:
                return candidate, rows
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error

    return season, []


def load_draft_picks() -> list[dict[str, str]]:
    return fetch_csv_rows(DRAFT_PICKS_URL)


# =========================================================
# TEAM STATS NORMALIZATION
# =========================================================
def normalize_team_stats(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for row in rows:
        team_abbr = normalize_team_abbr(str(row.get("team", "")))
        if not team_abbr:
            continue

        pass_epa_total = safe_float(row.get("passing_epa"))
        rush_epa_total = safe_float(row.get("rushing_epa"))

        pass_plays = safe_float(row.get("attempts"))
        rush_plays = safe_float(row.get("carries"))

        pass_epa = per_play_value(pass_epa_total, pass_plays)
        rush_epa = per_play_value(rush_epa_total, rush_plays)

        total_plays = (pass_plays or 0.0) + (rush_plays or 0.0)
        total_epa = (pass_epa_total or 0.0) + (rush_epa_total or 0.0)
        epa_per_play = per_play_value(total_epa, total_plays)

        normalized.append(
            {
                "team_abbr": team_abbr,
                "team_name": TEAM_ABBR_TO_NAME.get(team_abbr, team_abbr),
                "epa_per_play": epa_per_play,
                "pass_epa": pass_epa,
                "rush_epa": rush_epa,
            }
        )

    return normalized


def team_stats_index(stats: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["team_abbr"]: row for row in stats if row.get("team_abbr")}


def top_n_by_metric(
    stats: list[dict[str, Any]],
    metric: str,
    n: int = 3,
    reverse: bool = True,
) -> list[dict[str, Any]]:
    valid = [row for row in stats if row.get(metric) is not None]
    return sorted(valid, key=lambda row: row[metric], reverse=reverse)[:n]


# =========================================================
# DRAFT SIGNALS
# =========================================================
def current_year_draft_rows(rows: list[dict[str, str]], year: int) -> list[dict[str, str]]:
    filtered: list[dict[str, str]] = []
    for row in rows:
        season = safe_int(row.get("season"))
        if season == year:
            filtered.append(row)
    return filtered

def build_draft_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "team_pick_counts": Counter(),
        "top_100_counts": Counter(),
        "round_1_positions": Counter(),
        "top_10_players": [],
        "earliest_pick_by_team": {},
    }

    for row in rows:
        raw_team = str(row.get("team", "")).strip()
        team = normalize_team_abbr(raw_team)

        if not team and raw_team:
            lower_team = raw_team.lower()
            if lower_team in TEAM_NAME_TO_ABBR:
                team = TEAM_NAME_TO_ABBR[lower_team]
            elif lower_team.upper() in TEAM_ABBR_TO_NAME:
                team = lower_team.upper()

        if not team:
            continue

        overall = safe_int(row.get("pick"))
        rnd = safe_int(row.get("round"))
        position = str(row.get("position", "")).strip().upper()
        player_name = str(row.get("pfr_player_name", "")).strip()

        summary["team_pick_counts"][team] += 1

        if overall is not None:
            earliest = summary["earliest_pick_by_team"].get(team)
            if earliest is None or overall < earliest:
                summary["earliest_pick_by_team"][team] = overall

            if overall <= 100:
                summary["top_100_counts"][team] += 1

            if overall <= 10:
                summary["top_10_players"].append(
                    {
                        "overall": overall,
                        "team": team,
                        "player": player_name or "Unknown",
                        "position": position or "UNK",
                    }
                )

        if rnd == 1 and position:
            summary["round_1_positions"][position] += 1

    summary["top_10_players"] = sorted(
        summary["top_10_players"], key=lambda item: item["overall"]
    )

    return summary

# =========================================================
# MATCHUP FLAGS FROM STANDARD REPORT
# =========================================================
def infer_matchup_flags(
    upcoming_lines: list[str],
    team_index: dict[str, dict[str, Any]],
) -> list[str]:
    flags: list[str] = []

    for line in upcoming_lines[:5]:
        lower_line = line.lower()

        matched_teams: list[tuple[str, str]] = []
        for full_name, abbr in TEAM_NAME_TO_ABBR.items():
            if full_name in lower_line:
                matched_teams.append((full_name.title(), abbr))

        unique: list[tuple[str, str]] = []
        seen: set[str] = set()
        for item in matched_teams:
            if item[1] not in seen:
                unique.append(item)
                seen.add(item[1])

        if len(unique) < 2:
            continue

        team1_name, team1_abbr = unique[0]
        team2_name, team2_abbr = unique[1]

        stats1 = team_index.get(team1_abbr)
        stats2 = team_index.get(team2_abbr)

        if not stats1 or not stats2:
            continue

        team1_epa = stats1.get("epa_per_play")
        team2_epa = stats2.get("epa_per_play")
        team1_pass = stats1.get("pass_epa")
        team2_pass = stats2.get("pass_epa")

        stronger_epa = team1_name if (team1_epa or -999) >= (team2_epa or -999) else team2_name
        better_pass = team1_name if (team1_pass or -999) >= (team2_pass or -999) else team2_name

        flags.append(
            f"{team1_name} vs. {team2_name} can be framed through last season’s efficiency profile, "
            f"with {stronger_epa} holding the stronger overall EPA/play mark and {better_pass} showing the better pass-game efficiency signal."
        )

    return flags[:5]


# =========================================================
# REPORT BUILDERS
# =========================================================
def build_key_data_points(
    season_used: int,
    team_stats: list[dict[str, Any]],
    draft_summary: dict[str, Any],
    draft_year: int,
) -> list[str]:
    points: list[str] = []

    points.append(
        f"The NFL advanced layer is anchored to {season_used} regular-season team efficiency data and {draft_year} draft-pick structure."
    )

    top_epa = top_n_by_metric(team_stats, "epa_per_play", n=1, reverse=True)
    if top_epa:
        row = top_epa[0]
        points.append(
            f"{row['team_name']} led the available EPA/play board at {format_number(row['epa_per_play'])}."
        )

    top_pass = top_n_by_metric(team_stats, "pass_epa", n=1, reverse=True)
    if top_pass:
        row = top_pass[0]
        points.append(
            f"{row['team_name']} set the strongest pass-efficiency signal in the available data at {format_number(row['pass_epa'])} pass EPA per play."
        )

    most_picks = draft_summary["team_pick_counts"].most_common(1)
    if most_picks:
        team, count = most_picks[0]
        team_name = TEAM_ABBR_TO_NAME.get(team, team)
        points.append(
            f"{team_name} currently holds {count} pick(s) in the {draft_year} draft file, giving that front office added flexibility."
        )

    return points[:5]


def build_efficiency_watch(team_stats: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []

    for row in top_n_by_metric(team_stats, "epa_per_play", n=3, reverse=True):
        lines.append(
            f"{row['team_name']} checked in at {format_number(row['epa_per_play'])} EPA per play."
        )

    for row in top_n_by_metric(team_stats, "pass_epa", n=3, reverse=True):
        lines.append(
            f"{row['team_name']} generated {format_number(row['pass_epa'])} pass EPA per play."
        )

    for row in top_n_by_metric(team_stats, "rush_epa", n=3, reverse=True):
        lines.append(
            f"{row['team_name']} turned in {format_number(row['rush_epa'])} rush EPA per play."
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for item in lines:
        if item not in seen:
            deduped.append(item)
            seen.add(item)

    return deduped[:12]


def build_draft_signals(draft_summary: dict[str, Any], draft_year: int) -> list[str]:
    lines: list[str] = []

    for team, count in draft_summary["top_100_counts"].most_common(4):
        if count <= 0:
            continue
        team_name = TEAM_ABBR_TO_NAME.get(team, team)
        lines.append(
            f"{team_name} holds {count} pick(s) inside the top 100 of the {draft_year} draft structure."
        )

    if draft_summary["top_10_players"]:
        first_three = draft_summary["top_10_players"][:3]
        joined = "; ".join(
            f"No. {item['overall']} to {TEAM_ABBR_TO_NAME.get(item['team'], item['team'])}: "
            f"{item['player']} ({item['position']})"
            for item in first_three
        )
        lines.append(f"Top-of-board signal: {joined}.")

    round_1_positions = draft_summary["round_1_positions"].most_common(4)
    if round_1_positions:
        position_text = ", ".join(
            f"{pos} ({count})" for pos, count in round_1_positions
        )
        lines.append(
            f"Round 1 position concentration currently leans toward: {position_text}."
        )

    earliest_picks = sorted(
        draft_summary["earliest_pick_by_team"].items(),
        key=lambda item: item[1]
    )[:4]
    if earliest_picks:
        earliest_text = ", ".join(
            f"{TEAM_ABBR_TO_NAME.get(team, team)} (No. {pick})"
            for team, pick in earliest_picks
        )
        lines.append(
            f"Earliest current team entry points on the board include {earliest_text}."
        )

    return lines[:6]


def build_story_angles(
    team_stats: list[dict[str, Any]],
    draft_summary: dict[str, Any],
    draft_year: int,
) -> list[str]:
    angles: list[str] = []

    top_rush = top_n_by_metric(team_stats, "rush_epa", n=1, reverse=True)
    if top_rush:
        row = top_rush[0]
        angles.append(
            f"Rushing-structure angle: the {row['team_name']} bring one of the strongest available run-game efficiency profiles at {format_number(row['rush_epa'])} rush EPA per play."
        )

    earliest_picks = sorted(
        draft_summary["earliest_pick_by_team"].items(),
        key=lambda item: item[1]
    )[:4]
    if earliest_picks:
        teams_text = ", ".join(
            f"{TEAM_ABBR_TO_NAME.get(team, team)} (No. {pick})"
            for team, pick in earliest_picks
        )
        angles.append(
            f"Draft-control angle: the earliest team entry points on the board currently include {teams_text}."
        )

    angles.append(
        "Quarterback and offensive-line stories usually gain the most traction near the draft, but EPA-based efficiency helps separate true team-building need from surface-level narrative."
    )
    angles.append(
        "During the season, this file can shift from draft framing into matchup framing by using the prior efficiency profile as a baseline."
    )

    return angles[:5]


def build_report(
    season_used: int,
    team_stats: list[dict[str, Any]],
    draft_rows: list[dict[str, str]],
    upcoming_lines: list[str],
) -> str:
    title = f"NFL ADVANCED REPORT | {report_date()}"
    draft_year = current_draft_year()
    draft_summary = build_draft_summary(draft_rows)
    team_index = team_stats_index(team_stats)

    if not team_stats and not draft_rows:
        return f"""{title}

HEADLINE
The NFL advanced analytics layer did not return usable efficiency or draft data in this report window.

SNAPSHOT
No advanced NFL data was available during this report window.

KEY DATA POINTS
- No usable NFL efficiency or draft inputs were available during this report window.

WHY IT MATTERS
- Without reliable data inputs, the safest editorial posture is to avoid overstating team-strength or draft-board conclusions.

STORY ANGLES
- Recheck team-level efficiency and draft-pick feeds before publishing analytics-driven NFL copy.

{DISCLAIMER}
"""

    if upcoming_lines:
        snapshot = (
            f"The NFL advanced layer is leaning on {season_used} team efficiency context, "
            f"{draft_year} draft signals, and {len(upcoming_lines)} upcoming line(s) from the standard NFL report."
        )
    else:
        snapshot = (
            f"The NFL advanced layer is leaning on {season_used} team efficiency context "
            f"and {draft_year} draft signals during a non-game-window period."
        )

    headline = (
        "The NFL board is best framed through EPA, passing efficiency, rushing efficiency, and draft-position leverage as team-building signals sharpen."
    )

    key_data_points = build_key_data_points(
        season_used=season_used,
        team_stats=team_stats,
        draft_summary=draft_summary,
        draft_year=draft_year,
    )

    efficiency_watch = build_efficiency_watch(team_stats)
    draft_signals = build_draft_signals(draft_summary, draft_year)
    matchup_flags = infer_matchup_flags(upcoming_lines, team_index)

    if not matchup_flags and upcoming_lines:
        matchup_flags = [
            "Upcoming NFL matchups are on the board, with prior-season EPA and pass-game efficiency serving as the best early framing tools until fresher game-window data arrives."
        ]

    story_angles = build_story_angles(team_stats, draft_summary, draft_year)

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

    if matchup_flags:
        parts.extend(["", "MATCHUP FLAGS"])
        for item in matchup_flags:
            parts.append(f"- {item}")

    if efficiency_watch:
        parts.extend(["", "TEAM EFFICIENCY WATCH"])
        for item in efficiency_watch:
            parts.append(f"- {item}")

    if draft_signals:
        parts.extend(["", "DRAFT SIGNALS"])
        for item in draft_signals:
            parts.append(f"- {item}")

    parts.extend(
        [
            "",
            "WHY IT MATTERS",
            "- EPA/play gives a stronger snapshot of down-to-down offensive value than raw yardage alone.",
            "- Passing EPA and rushing EPA help separate where teams are creating value instead of relying on surface-level totals.",
            "- Draft-pick concentration matters because multiple early selections can shift roster construction, trade flexibility, and positional strategy.",
            "- In non-game windows, draft structure and the previous season’s efficiency profile are often the clearest editorial anchors for NFL analysis.",
            "",
            "STORY ANGLES",
        ]
    )

    for item in story_angles:
        parts.append(f"- {item}")

    parts.extend(["", DISCLAIMER])

    return "\n".join(parts)


# =========================================================
# MAIN
# =========================================================
def main() -> None:
    standard_report_text = read_standard_nfl_report()
    upcoming_lines = extract_upcoming_lines(standard_report_text)

    try:
        season_used, raw_team_stats = load_team_stats()
    except Exception:
        season_used, raw_team_stats = current_nfl_season_year(), []

    try:
        raw_draft_rows = load_draft_picks()
    except Exception:
        raw_draft_rows = []

    team_stats = normalize_team_stats(raw_team_stats)
    draft_rows = current_year_draft_rows(raw_draft_rows, current_draft_year())

    report = build_report(
        season_used=season_used,
        team_stats=team_stats,
        draft_rows=draft_rows,
        upcoming_lines=upcoming_lines,
    )

    write_report(report)
    print(report)


if __name__ == "__main__":
    main()