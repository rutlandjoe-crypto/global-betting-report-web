from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


ET = ZoneInfo("America/New_York")
BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

OUTPUT_FILE = BASE_DIR / "mlb_report.txt"
JSON_OUTPUT_FILE = BASE_DIR / "mlb_report.json"
ADVANCED_FILE = BASE_DIR / "mlb_advanced_report.txt"

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"

HEADERS = {
    "User-Agent": "GlobalSportsReport/1.0 (+https://globalsportsreport.com)",
    "Accept": "application/json",
}


def now_et() -> datetime:
    return datetime.now(ET)


def ts() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


def get_sportradar_key() -> str:
    candidates = [
        "SPORTRADAR_MLB_KEY",
        "SPORTRADAR_MLB_API_KEY",
        "SPORTRADAR_API_KEY",
        "SPORTRADAR_KEY",
    ]

    for name in candidates:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()

    return ""


SPORTRADAR_KEY = get_sportradar_key()


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_json(url: str) -> Optional[Dict[str, Any]]:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception as exc:
        print(f"[MLB] Fetch failed: {url} | {exc}")
        return None


def espn_scoreboard_for_date(date_obj: datetime) -> Dict[str, Any]:
    date_key = date_obj.strftime("%Y%m%d")
    url = f"{ESPN_SCOREBOARD_URL}?dates={date_key}&limit=200"
    data = fetch_json(url)
    return data or {}


def get_team_name(comp: Dict[str, Any]) -> str:
    team = comp.get("team", {}) or {}
    return clean_text(
        team.get("shortDisplayName")
        or team.get("displayName")
        or team.get("name")
        or "TBD"
    )


def get_record(comp: Dict[str, Any]) -> str:
    records = comp.get("records") or []
    if not records:
        return ""

    first = records[0] or {}
    summary = clean_text(first.get("summary"))
    return summary


def get_probable_pitcher(comp: Dict[str, Any]) -> str:
    probable = comp.get("probables") or []
    if probable:
        athlete = probable[0].get("athlete", {}) or {}
        name = clean_text(athlete.get("displayName"))
        if name:
            return name

    leaders = comp.get("leaders") or []
    for leader_group in leaders:
        if clean_text(leader_group.get("name")).lower() in {"probable pitchers", "probables"}:
            leaders_items = leader_group.get("leaders") or []
            if leaders_items:
                athlete = leaders_items[0].get("athlete", {}) or {}
                name = clean_text(athlete.get("displayName"))
                if name:
                    return name

    return ""


def parse_event(event: Dict[str, Any]) -> Dict[str, Any]:
    competitions = event.get("competitions") or []
    competition = competitions[0] if competitions else {}

    competitors = competition.get("competitors") or []
    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0] if competitors else {})
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1] if len(competitors) > 1 else {})

    status = competition.get("status", {}) or event.get("status", {}) or {}
    status_type = status.get("type", {}) or {}

    status_name = clean_text(status_type.get("name"))
    status_state = clean_text(status_type.get("state"))
    detail = clean_text(status_type.get("detail") or status.get("displayClock") or status_type.get("shortDetail"))

    home_score = clean_text(home.get("score"))
    away_score = clean_text(away.get("score"))

    home_team = get_team_name(home)
    away_team = get_team_name(away)

    event_date_raw = clean_text(event.get("date") or competition.get("date"))
    event_dt = None

    if event_date_raw:
        try:
            event_dt = datetime.fromisoformat(event_date_raw.replace("Z", "+00:00")).astimezone(ET)
        except Exception:
            event_dt = None

    start_time = event_dt.strftime("%I:%M %p ET").lstrip("0") if event_dt else "TBD"

    venue = competition.get("venue", {}) or {}
    venue_name = clean_text(venue.get("fullName"))

    return {
        "id": clean_text(event.get("id")),
        "name": clean_text(event.get("name")),
        "short_name": clean_text(event.get("shortName")),
        "home_team": home_team,
        "away_team": away_team,
        "home_score": home_score,
        "away_score": away_score,
        "home_record": get_record(home),
        "away_record": get_record(away),
        "home_probable_pitcher": get_probable_pitcher(home),
        "away_probable_pitcher": get_probable_pitcher(away),
        "status_name": status_name,
        "status_state": status_state,
        "detail": detail,
        "start_time": start_time,
        "venue": venue_name,
    }


def classify_games(events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    finals: List[Dict[str, Any]] = []
    live: List[Dict[str, Any]] = []
    upcoming: List[Dict[str, Any]] = []

    for event in events:
        parsed = parse_event(event)
        state = parsed["status_state"].lower()
        name = parsed["status_name"].lower()

        if state == "post" or "final" in name:
            finals.append(parsed)
        elif state == "in":
            live.append(parsed)
        else:
            upcoming.append(parsed)

    return {
        "finals": finals,
        "live": live,
        "upcoming": upcoming,
    }


def score_line(game: Dict[str, Any]) -> str:
    away = game["away_team"]
    home = game["home_team"]
    away_score = game["away_score"]
    home_score = game["home_score"]
    detail = game["detail"] or "Final"

    if away_score and home_score:
        return f"{away} {away_score}, {home} {home_score} — {detail}"

    return f"{away} at {home} — {detail}"


def live_line(game: Dict[str, Any]) -> str:
    away = game["away_team"]
    home = game["home_team"]
    away_score = game["away_score"]
    home_score = game["home_score"]
    detail = game["detail"] or "Live"

    if away_score and home_score:
        return f"{away} {away_score}, {home} {home_score} — {detail}"

    return f"{away} at {home} — {detail}"


def schedule_line(game: Dict[str, Any]) -> str:
    away = game["away_team"]
    home = game["home_team"]
    start = game["start_time"]
    venue = game["venue"]

    pitchers = []
    if game["away_probable_pitcher"]:
        pitchers.append(f"{away}: {game['away_probable_pitcher']}")
    if game["home_probable_pitcher"]:
        pitchers.append(f"{home}: {game['home_probable_pitcher']}")

    pitcher_text = f" — Probables: {'; '.join(pitchers)}" if pitchers else ""
    venue_text = f" — {venue}" if venue else ""

    return f"{away} at {home} — {start}{venue_text}{pitcher_text}"


def build_headline(finals: List[Dict[str, Any]], live: List[Dict[str, Any]], upcoming: List[Dict[str, Any]]) -> str:
    if finals:
        game = finals[0]
        return f"{game['away_team']} and {game['home_team']} headline MLB scoreboard after latest final"

    if live:
        game = live[0]
        return f"{game['away_team']} and {game['home_team']} lead live MLB window"

    if upcoming:
        game = upcoming[0]
        return f"{game['away_team']} visit {game['home_team']} as MLB schedule opens"

    return "MLB schedule quiet as Global Sports Report monitors next update window"


def build_snapshot(finals: List[Dict[str, Any]], live: List[Dict[str, Any]], upcoming: List[Dict[str, Any]]) -> str:
    parts = []

    if finals:
        parts.append(f"{len(finals)} final score{'s' if len(finals) != 1 else ''}")
    if live:
        parts.append(f"{len(live)} live game{'s' if len(live) != 1 else ''}")
    if upcoming:
        parts.append(f"{len(upcoming)} upcoming game{'s' if len(upcoming) != 1 else ''}")

    if parts:
        return "MLB update: " + ", ".join(parts) + "."

    return "MLB update: No active scoreboard items were available from the public feed at generation time."


def build_storylines(finals: List[Dict[str, Any]], live: List[Dict[str, Any]], upcoming: List[Dict[str, Any]]) -> List[str]:
    storylines: List[str] = []

    for game in finals[:3]:
        storylines.append(score_line(game))

    for game in live[:3]:
        storylines.append(live_line(game))

    for game in upcoming[:4]:
        storylines.append(schedule_line(game))

    if not storylines:
        storylines.append("No MLB games were available from the public scoreboard feed at generation time.")

    return storylines[:8]


def load_advanced_notes() -> List[str]:
    if not ADVANCED_FILE.exists():
        return [
            "Advanced MLB notes unavailable until the next Statcast/analytics refresh.",
            "Monitor starting pitching matchups, bullpen workload and recent run prevention trends.",
        ]

    try:
        raw = ADVANCED_FILE.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return [
            "Advanced MLB notes could not be loaded during this run.",
            "Monitor lineup, pitching and bullpen context as new data arrives.",
        ]

    lines = []
    for line in raw.splitlines():
        cleaned = clean_text(line)
        if not cleaned:
            continue
        if cleaned.startswith("[") and cleaned.endswith("]"):
            continue
        if cleaned.upper() in {"MLB ADVANCED REPORT", "STATCAST WATCH"}:
            continue
        lines.append(cleaned)

    if not lines:
        return [
            "Advanced MLB notes file was present but did not contain usable lines.",
            "Monitor starting pitching matchups, bullpen workload and recent Statcast indicators.",
        ]

    return lines[:8]


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []

    lines.append("GLOBAL SPORTS REPORT — MLB")
    lines.append(f"UPDATED: {payload['updated_at']}")
    lines.append("")
    lines.append("HEADLINE")
    lines.append(payload["headline"])
    lines.append("")
    lines.append("SNAPSHOT")
    lines.append(payload["snapshot"])
    lines.append("")

    lines.append("KEY STORYLINES")
    for item in payload["key_storylines"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("FINAL SCORES")
    for item in payload["final_scores"]:
        lines.append(f"- {item}")
    if not payload["final_scores"]:
        lines.append("- No final scores available yet.")
    lines.append("")

    lines.append("TODAY LIVE")
    for item in payload["live_games"]:
        lines.append(f"- {item}")
    if not payload["live_games"]:
        lines.append("- No live MLB games at generation time.")
    lines.append("")

    lines.append("TODAY SCHEDULE")
    for item in payload["upcoming_games"]:
        lines.append(f"- {item}")
    if not payload["upcoming_games"]:
        lines.append("- No upcoming MLB games found for today.")
    lines.append("")

    lines.append("STATCAST WATCH")
    for item in payload["statcast_watch"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("WHY IT MATTERS")
    lines.append(payload["why_it_matters"])
    lines.append("")

    lines.append("SOURCE NOTE")
    lines.append(payload["source_note"])

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    print(f"[{ts()}] MLB REPORT STARTED")
    print(f"[{ts()}] SPORTRADAR TOKEN DETECTED: {bool(SPORTRADAR_KEY)}")

    today = now_et()
    yesterday = today - timedelta(days=1)

    today_data = espn_scoreboard_for_date(today)
    yesterday_data = espn_scoreboard_for_date(yesterday)

    today_events = today_data.get("events") or []
    yesterday_events = yesterday_data.get("events") or []

    today_games = classify_games(today_events)
    yesterday_games = classify_games(yesterday_events)

    finals = today_games["finals"]
    live = today_games["live"]
    upcoming = today_games["upcoming"]

    if not finals and not live and not upcoming:
        finals = yesterday_games["finals"]

    final_scores = [score_line(game) for game in finals[:12]]
    live_games = [live_line(game) for game in live[:12]]
    upcoming_games = [schedule_line(game) for game in upcoming[:15]]

    headline = build_headline(finals, live, upcoming)
    snapshot = build_snapshot(finals, live, upcoming)
    key_storylines = build_storylines(finals, live, upcoming)
    statcast_watch = load_advanced_notes()

    payload: Dict[str, Any] = {
        "sport": "MLB",
        "league": "Major League Baseball",
        "title": "MLB Report",
        "headline": headline,
        "snapshot": snapshot,
        "updated_at": ts(),
        "generated_at": ts(),
        "published_at": ts(),
        "source_file": "get_mlb_report.py",
        "source_note": "ESPN public scoreboard feed with local advanced-note fallback. Sportradar token detection is included for authenticated integrations.",
        "sportradar_token_detected": bool(SPORTRADAR_KEY),
        "key_storylines": key_storylines,
        "final_scores": final_scores,
        "live_games": live_games,
        "upcoming_games": upcoming_games,
        "statcast_watch": statcast_watch,
        "why_it_matters": "MLB coverage should separate final scores, live games, upcoming matchups and analytics notes so journalists can scan the card quickly without blob text.",
        "card_blocks": [
            {
                "label": "Final Scores",
                "items": final_scores if final_scores else ["No final scores available yet."],
            },
            {
                "label": "Today Live",
                "items": live_games if live_games else ["No live MLB games at generation time."],
            },
            {
                "label": "Today Schedule",
                "items": upcoming_games if upcoming_games else ["No upcoming MLB games found for today."],
            },
            {
                "label": "Statcast Watch",
                "items": statcast_watch,
            },
        ],
    }

    OUTPUT_FILE.write_text(build_text_report(payload), encoding="utf-8")

    with open(JSON_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"[{ts()}] WROTE: {OUTPUT_FILE}")
    print(f"[{ts()}] WROTE: {JSON_OUTPUT_FILE}")
    print(f"[{ts()}] MLB REPORT COMPLETE")


if __name__ == "__main__":
    main()