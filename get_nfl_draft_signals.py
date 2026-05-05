from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TIMEZONE = ZoneInfo("America/New_York")
OUTPUT_FILE = Path("nfl_draft_signals.txt")
REQUEST_TIMEOUT = 20

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, human sports journalism."
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GlobalSportsReport/1.0)",
    "Accept": "application/json",
}

NFL_STANDINGS_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/football/nfl/standings"
)

TEAM_NEEDS = {
    "Arizona Cardinals": ["Edge", "Wide Receiver", "Cornerback"],
    "Atlanta Falcons": ["Edge", "Cornerback", "Wide Receiver"],
    "Baltimore Ravens": ["Offensive Line", "Wide Receiver", "Cornerback"],
    "Buffalo Bills": ["Wide Receiver", "Safety", "Defensive Line"],
    "Carolina Panthers": ["Wide Receiver", "Offensive Line", "Edge"],
    "Chicago Bears": ["Wide Receiver", "Defensive Line", "Offensive Line"],
    "Cincinnati Bengals": ["Offensive Line", "Tight End", "Defensive Line"],
    "Cleveland Browns": ["Offensive Tackle", "Wide Receiver", "Linebacker"],
    "Dallas Cowboys": ["Offensive Line", "Running Back", "Defensive Tackle"],
    "Denver Broncos": ["Quarterback", "Wide Receiver", "Defensive Line"],
    "Detroit Lions": ["Cornerback", "Edge", "Guard"],
    "Green Bay Packers": ["Offensive Tackle", "Safety", "Linebacker"],
    "Houston Texans": ["Defensive Tackle", "Cornerback", "Wide Receiver"],
    "Indianapolis Colts": ["Tight End", "Cornerback", "Edge"],
    "Jacksonville Jaguars": ["Cornerback", "Interior Offensive Line", "Wide Receiver"],
    "Kansas City Chiefs": ["Wide Receiver", "Offensive Tackle", "Defensive Tackle"],
    "Las Vegas Raiders": ["Quarterback", "Cornerback", "Offensive Tackle"],
    "Los Angeles Chargers": ["Wide Receiver", "Cornerback", "Defensive Tackle"],
    "Los Angeles Rams": ["Cornerback", "Linebacker", "Offensive Tackle"],
    "Miami Dolphins": ["Offensive Line", "Safety", "Defensive Tackle"],
    "Minnesota Vikings": ["Quarterback", "Defensive Line", "Cornerback"],
    "New England Patriots": ["Quarterback", "Wide Receiver", "Offensive Tackle"],
    "New Orleans Saints": ["Offensive Tackle", "Edge", "Wide Receiver"],
    "New York Giants": ["Quarterback", "Wide Receiver", "Offensive Line"],
    "New York Jets": ["Offensive Tackle", "Wide Receiver", "Safety"],
    "Philadelphia Eagles": ["Cornerback", "Offensive Tackle", "Edge"],
    "Pittsburgh Steelers": ["Cornerback", "Wide Receiver", "Offensive Line"],
    "San Francisco 49ers": ["Offensive Tackle", "Cornerback", "Defensive Tackle"],
    "Seattle Seahawks": ["Interior Offensive Line", "Linebacker", "Defensive Line"],
    "Tampa Bay Buccaneers": ["Edge", "Interior Offensive Line", "Cornerback"],
    "Tennessee Titans": ["Offensive Tackle", "Wide Receiver", "Edge"],
    "Washington Commanders": ["Offensive Line", "Cornerback", "Edge"],
}


# =========================
# TEXT CLEANING
# =========================

def fix_encoding(text: str) -> str:
    return (
        text.replace("â€™", "’")
        .replace("â€˜", "‘")
        .replace("â€œ", '"')
        .replace("â€\x9d", '"')
        .replace("â€“", "–")
        .replace("â€”", "—")
        .replace("â€¦", "…")
        .replace("Â", "")
    )


def clean_text(text: str) -> str:
    text = fix_encoding(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fix_spacing(text: str) -> str:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z])(\d)", r"\1 \2", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


# =========================
# TIME / LOGGING
# =========================

def report_date() -> str:
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d")


def et_timestamp() -> str:
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %I:%M:%S %p ET")


def log(message: str) -> None:
    print(f"[{et_timestamp()}] {message}", flush=True)


# =========================
# NETWORK HELPERS
# =========================

def fetch_json(url: str) -> dict:
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


# =========================
# DATA PARSING
# =========================

def parse_standings(data: dict) -> list[dict]:
    teams: list[dict] = []

    children = data.get("children", [])
    for conference in children:
        for division in conference.get("children", []):
            standings = division.get("standings", {})
            entries = standings.get("entries", [])

            for entry in entries:
                team_info = entry.get("team", {})
                stats = entry.get("stats", [])

                stat_map: dict[str, str] = {}
                for stat in stats:
                    key = stat.get("name")
                    display_value = stat.get("displayValue")
                    if key:
                        stat_map[key] = display_value

                wins = int(stat_map.get("wins", "0"))
                losses = int(stat_map.get("losses", "0"))
                ties = int(stat_map.get("ties", "0"))
                win_pct = float(stat_map.get("winPercent", "0") or 0)
                points_for = stat_map.get("pointsFor", "0")
                points_against = stat_map.get("pointsAgainst", "0")

                team_name = team_info.get("displayName", "Unknown Team")

                teams.append(
                    {
                        "team": team_name,
                        "abbr": team_info.get("abbreviation", ""),
                        "wins": wins,
                        "losses": losses,
                        "ties": ties,
                        "win_pct": win_pct,
                        "points_for": points_for,
                        "points_against": points_against,
                    }
                )

    teams.sort(key=lambda x: (x["win_pct"], x["wins"], -x["losses"]))
    return teams


def tier_label(win_pct: float) -> str:
    if win_pct <= 0.250:
        return "Top-of-board pressure"
    if win_pct <= 0.400:
        return "Early-round pressure"
    if win_pct <= 0.550:
        return "Middle-of-board swing range"
    if win_pct <= 0.700:
        return "Playoff-caliber roster with targeted draft needs"
    return "Contender drafting for refinement"


def build_draft_board(teams: list[dict]) -> list[dict]:
    board: list[dict] = []

    for index, team in enumerate(teams, start=1):
        needs = TEAM_NEEDS.get(team["team"], ["Offensive Line", "Defensive Line", "Cornerback"])
        board.append(
            {
                "pick_range": index,
                "team": team["team"],
                "abbr": team["abbr"],
                "record": f"{team['wins']}-{team['losses']}-{team['ties']}",
                "win_pct": team["win_pct"],
                "tier": tier_label(team["win_pct"]),
                "needs": needs,
                "points_for": team["points_for"],
                "points_against": team["points_against"],
            }
        )

    return board


# =========================
# REPORT BUILDERS
# =========================

def headline_text(board: list[dict]) -> str:
    if not board:
        return (
            "The NFL draft board is in focus, with roster pressure points and team-build signals "
            "driving the current projection window."
        )

    top_team = board[0]["team"]
    return (
        f"The NFL draft board is taking shape through roster pressure, team needs, and early-order "
        f"positioning, with {top_team} currently sitting at the front of the signal board."
    )


def snapshot_text(board: list[dict]) -> str:
    if not board:
        return "The current draft signals board is unavailable in this report window."

    top_5 = min(5, len(board))
    qb_teams = [
        item["team"]
        for item in board[:12]
        if "Quarterback" in item["needs"]
    ]

    return (
        f"The draft signals board currently highlights {len(board)} teams, with the top {top_5} slots "
        f"showing the strongest early-order pressure. {len(qb_teams)} team(s) inside the top 12 "
        f"currently profile as quarterback-watch clubs."
    )


def key_data_points(board: list[dict]) -> list[str]:
    if not board:
        return [
            "Standings-based draft order signals were unavailable during this report window.",
            "The report falls back to editorial needs framing when live team-order data cannot be confirmed.",
        ]

    points: list[str] = []

    top_five = board[:5]
    top_five_names = ", ".join(item["team"] for item in top_five)
    points.append(f"The current top five of the draft signal board is: {top_five_names}.")

    qb_teams = [item["team"] for item in board[:12] if "Quarterback" in item["needs"]]
    if qb_teams:
        points.append(
            f"{len(qb_teams)} team(s) inside the top 12 project as quarterback-watch teams: "
            f"{', '.join(qb_teams[:6])}."
        )

    ol_teams = [item["team"] for item in board[:10] if "Offensive Tackle" in item["needs"] or "Offensive Line" in item["needs"]]
    if ol_teams:
        points.append(
            f"Offensive line need remains a major top-board theme, with "
            f"{len(ol_teams)} of the top 10 teams showing tackle or line pressure."
        )

    cb_teams = [item["team"] for item in board[:12] if "Cornerback" in item["needs"]]
    if cb_teams:
        points.append(
            f"Cornerback continues to show as a major board lever, with "
            f"{len(cb_teams)} top-12 teams carrying that need."
        )

    most_extreme = board[0]
    points.append(
        f"{most_extreme['team']} currently carries the strongest early-order signal at "
        f"{most_extreme['record']} and is sitting in the '{most_extreme['tier']}' bucket."
    )

    return points[:5]


def why_it_matters(board: list[dict]) -> str:
    if not board:
        return (
            "Even without a confirmed live board, draft conversation stays relevant because team needs, "
            "quarterback pressure, and roster-building timelines continue to shape league-wide coverage."
        )

    qb_count = len([item for item in board[:12] if "Quarterback" in item["needs"]])
    return (
        f"Draft coverage matters because the order board, quarterback pressure, and positional scarcity "
        f"are already shaping the league conversation. In this report window, {qb_count} of the current "
        f"top 12 teams profile as possible quarterback-watch spots, which can shift the entire first-round story."
    )


def story_angles(board: list[dict]) -> list[str]:
    if not board:
        return [
            "Which roster holes are most likely to reshape the first round?",
            "How much quarterback demand is building beneath the surface of the board?",
            "Which contenders can use the draft to close smaller but meaningful gaps?",
        ]

    angles: list[str] = []

    top_team = board[0]
    angles.append(
        f"Why {top_team['team']} is setting the tone for the early draft board at {top_team['record']}."
    )

    qb_teams = [item["team"] for item in board[:12] if "Quarterback" in item["needs"]]
    if qb_teams:
        angles.append(
            f"Quarterback market pressure check: how {', '.join(qb_teams[:4])} could alter the top 12."
        )

    edge_teams = [item["team"] for item in board[:16] if "Edge" in item["needs"]]
    if edge_teams:
        angles.append(
            f"Pass-rush demand is building, with edge need showing up for {len(edge_teams)} teams in the top 16."
        )

    contender_team = next(
        (item for item in board if item["win_pct"] >= 0.600),
        None,
    )
    if contender_team:
        angles.append(
            f"How contenders like {contender_team['team']} can use the draft for refinement instead of repair."
        )

    return angles[:4]


def watch_list(board: list[dict]) -> list[str]:
    if not board:
        return [
            "Watch for quarterback-needy teams to drive the strongest movement once the board tightens.",
            "Monitor offensive tackle demand as one of the cleanest league-wide pressure points.",
            "Keep an eye on cornerback depth as a likely separator in the middle of Round 1.",
        ]

    items: list[str] = []

    for item in board[:8]:
        primary_need = item["needs"][0] if item["needs"] else "Roster help"
        items.append(
            f"{item['team']} ({item['record']}) — Primary draft pressure: {primary_need}. "
            f"Tier: {item['tier']}."
        )

    return items


def build_report(board: list[dict]) -> str:
    headline = headline_text(board)
    snapshot = snapshot_text(board)
    key_points = key_data_points(board)
    why = why_it_matters(board)
    angles = story_angles(board)
    watch_items = watch_list(board)

    report = f"""NFL DRAFT SIGNALS | {report_date()}

HEADLINE
{headline}

SNAPSHOT
{snapshot}

KEY DATA POINTS
{chr(10).join([f"- {fix_spacing(clean_text(item))}" for item in key_points])}

WHY IT MATTERS
{fix_spacing(clean_text(why))}

STORY ANGLES
{chr(10).join([f"- {fix_spacing(clean_text(item))}" for item in angles])}

WATCH LIST
{chr(10).join([f"- {fix_spacing(clean_text(item))}" for item in watch_items])}

DISCLAIMER
{DISCLAIMER}
"""
    return clean_text(report) + "\n"


def build_fallback_report(reason: str) -> str:
    report = f"""NFL DRAFT SIGNALS | {report_date()}

HEADLINE
The NFL draft board remains a major roster-building storyline, even when live signal data is limited in this report window.

SNAPSHOT
The live draft signals board could not be fully confirmed, so this edition falls back to broad roster-pressure framing.

KEY DATA POINTS
- Live standings-based draft order signals were unavailable during this report window.
- Quarterback pressure, offensive line demand, and coverage needs still remain core first-round themes.
- Editorial draft coverage can still center on roster repair teams, trade-up pressure, and positional scarcity.

WHY IT MATTERS
The NFL draft remains one of the strongest year-round league story engines because team-building pressure never really goes away, especially around quarterback, pass protection, and premium defensive positions.

STORY ANGLES
- Which teams are most likely to drive early-round urgency?
- Where quarterback demand could reshape the top of the board.
- Why roster repair teams and playoff teams enter the draft with very different pressure points.

WATCH LIST
- Quarterback-needy teams
- Offensive tackle demand
- Cornerback depth
- Pass-rush pressure

REPORT NOTE
{fix_spacing(clean_text(reason))}

DISCLAIMER
{DISCLAIMER}
"""
    return clean_text(report) + "\n"


# =========================
# MAIN
# =========================

def main() -> None:
    try:
        log("Fetching NFL standings data...")
        standings_data = fetch_json(NFL_STANDINGS_URL)

        log("Parsing standings into draft board...")
        teams = parse_standings(standings_data)
        board = build_draft_board(teams)

        report = build_report(board)
        OUTPUT_FILE.write_text(report, encoding="utf-8")

        print(report)
        log(f"Saved: {OUTPUT_FILE.resolve()}")

    except Exception as exc:
        error_message = f"Draft signals module fell back because of an error: {exc}"
        log(error_message)

        report = build_fallback_report(error_message)
        OUTPUT_FILE.write_text(report, encoding="utf-8")

        print(report)
        log(f"Saved fallback: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()