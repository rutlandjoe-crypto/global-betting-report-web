from pathlib import Path
from dotenv import load_dotenv
import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================================================
# ENV / PATH / CONFIG
# =========================================================
BASE_DIR = Path(__file__).resolve().parent

ENV_CANDIDATES = [
    BASE_DIR / ".env",
    BASE_DIR.parent / ".env",
    Path.cwd() / ".env",
]

ENV_PATH = next((candidate for candidate in ENV_CANDIDATES if candidate.exists()), None)
if ENV_PATH:
    load_dotenv(dotenv_path=ENV_PATH, override=True)

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "").strip()

TIMEZONE = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

REPORT_FILE = Path(
    os.getenv("BETTING_ODDS_REPORT_FILE", str(BASE_DIR / "betting_odds_report.txt"))
)

BASE_URL = "https://api.the-odds-api.com/v4/sports"

SPORTS = [
    {"label": "NBA", "key": "basketball_nba"},
    {"label": "MLB", "key": "baseball_mlb"},
    {"label": "NHL", "key": "icehockey_nhl"},
    {"label": "NFL", "key": "americanfootball_nfl"},
]

MARKETS = "h2h,spreads,totals"
REGIONS = "us"
ODDS_FORMAT = "american"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GlobalSportsReport Betting Desk)"
}

# =========================================================
# TIME HELPERS
# =========================================================
def now_et() -> datetime:
    return datetime.now(TIMEZONE)


def report_date_string() -> str:
    return now_et().strftime("%Y-%m-%d")


def format_generated_timestamp() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


def parse_commence_time(dt_str: str):
    if not dt_str:
        return None

    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(dt_str, "%Y-%m-%dT%H:%MZ").replace(tzinfo=UTC)
        except Exception:
            return None


def format_time(dt_str: str) -> str:
    dt = parse_commence_time(dt_str)
    if not dt:
        return "TBD"
    return dt.astimezone(TIMEZONE).strftime("%I:%M %p ET").lstrip("0")


# =========================================================
# FORMAT HELPERS
# =========================================================
def clean_text(value, fallback="N/A") -> str:
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def format_price(val) -> str:
    if val is None:
        return "N/A"
    try:
        val = int(val)
        return f"+{val}" if val > 0 else str(val)
    except (TypeError, ValueError):
        return str(val)

def format_point(val) -> str:
    if val is None:
        return "N/A"
    try:
        number = float(val)
        if number > 0:
            return f"+{number:g}"
        return f"{number:g}"
    except (TypeError, ValueError):
        return str(val)

# =========================================================
# REPORT LANGUAGE
# =========================================================
def build_lede() -> str:
    return (
        "Across the betting landscape, attention turns to the board, where moneylines, "
        "spreads, and totals help frame the day’s market outlook."
    )


def build_snapshot(event_count: int) -> str:
    if event_count >= 15:
        return "A full betting board is in place across multiple leagues, offering broad market coverage."
    if event_count >= 1:
        return "A focused betting board highlights key matchups across the day’s schedule."
    return "Limited betting data was available during this report window."


def build_market_note() -> str:
    return (
        "This report reflects publicly available odds data at the time of generation. "
        "Lines may move and can vary across sportsbooks."
    )


def build_disclaimer() -> str:
    return (
        "This report is an automated summary intended to support, not replace, human sports journalism."
    )


# =========================================================
# API HELPERS
# =========================================================
def safe_get(url: str, params=None):
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=20)

        remaining = response.headers.get("x-requests-remaining")
        used = response.headers.get("x-requests-used")
        if remaining is not None and used is not None:
            print(f"[ODDS API] requests used={used} remaining={remaining}")

        response.raise_for_status()
        return response.json(), None

    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        try:
            body = exc.response.text[:300] if exc.response is not None else ""
        except Exception:
            body = ""
        return None, f"HTTP {status}: {body}".strip()

    except requests.RequestException as exc:
        return None, str(exc)


def fetch_odds(sport_key: str) -> dict:
    if not ODDS_API_KEY:
        return {"error": "Missing API key"}

    url = f"{BASE_URL}/{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
    }

    data, error = safe_get(url, params=params)
    if error:
        return {"error": error}

    if data is None:
        return {"error": "No data returned"}

    if not isinstance(data, list):
        return {"error": "Unexpected API response"}

    events = sorted(
        data,
        key=lambda event: parse_commence_time(event.get("commence_time")) or datetime.max.replace(tzinfo=UTC),
    )

    return {"events": events}


# =========================================================
# ODDS PARSING
# =========================================================
def get_first_bookmaker(event: dict):
    bookmakers = event.get("bookmakers", [])
    return bookmakers[0] if bookmakers else None


def get_market(bookmaker: dict, market_key: str):
    if not bookmaker:
        return None

    for market in bookmaker.get("markets", []):
        if market.get("key") == market_key:
            return market

    return None


def get_outcome_by_name(market: dict, outcome_name: str):
    if not market:
        return None

    for outcome in market.get("outcomes", []):
        if outcome.get("name") == outcome_name:
            return outcome

    return None


def get_total_outcome(market: dict, side: str):
    if not market:
        return None

    target = str(side).lower()
    for outcome in market.get("outcomes", []):
        if str(outcome.get("name", "")).lower() == target:
            return outcome

    return None


def summarize_event(event: dict) -> list[str]:
    away = clean_text(event.get("away_team"), "Unknown Team")
    home = clean_text(event.get("home_team"), "Unknown Team")
    start_time = format_time(event.get("commence_time"))

    lines = [f"{away} at {home} — {start_time}"]

    bookmaker = get_first_bookmaker(event)
    if not bookmaker:
        lines.append("No bookmaker pricing available.")
        return lines

    bookmaker_title = clean_text(bookmaker.get("title"), "Sportsbook")
    lines.append(f"Bookmaker: {bookmaker_title}")

    h2h = get_market(bookmaker, "h2h")
    spreads = get_market(bookmaker, "spreads")
    totals = get_market(bookmaker, "totals")

    if h2h:
        away_outcome = get_outcome_by_name(h2h, away)
        home_outcome = get_outcome_by_name(h2h, home)

        away_price = away_outcome.get("price") if away_outcome else None
        home_price = home_outcome.get("price") if home_outcome else None

        lines.append(
            f"Moneyline: {away} {format_price(away_price)} / {home} {format_price(home_price)}"
        )

    if spreads:
        away_spread = get_outcome_by_name(spreads, away)
        home_spread = get_outcome_by_name(spreads, home)

        away_point = away_spread.get("point") if away_spread else None
        away_price = away_spread.get("price") if away_spread else None
        home_point = home_spread.get("point") if home_spread else None
        home_price = home_spread.get("price") if home_spread else None

        lines.append(
            "Spread: "
            f"{away} {format_point(away_point)} ({format_price(away_price)}) / "
            f"{home} {format_point(home_point)} ({format_price(home_price)})"
        )

    if totals:
        over = get_total_outcome(totals, "over")
        under = get_total_outcome(totals, "under")

        total_point = over.get("point") if over else (under.get("point") if under else None)
        over_price = over.get("price") if over else None
        under_price = under.get("price") if under else None

        lines.append(
            f"Total: {format_point(total_point)} "
            f"(Over {format_price(over_price)} / Under {format_price(under_price)})"
        )

    if not h2h and not spreads and not totals:
        lines.append("Pricing was limited for this matchup during this report window.")

    return lines


# =========================================================
# SPORT SECTION BUILDER
# =========================================================
def no_board_message(label: str) -> str:
    messages = {
        "NBA": "No NBA betting board is currently available.",
        "MLB": "No MLB betting board is currently available.",
        "NHL": "No NHL betting board is currently available.",
        "NFL": "No NFL betting board is currently available.",
    }
    return messages.get(label, "No betting board is currently available.")


def build_sport_section(sport: dict):
    label = sport.get("label", "UNKNOWN")
    key = sport.get("key", "")
    lines = [label]

    try:
        result = fetch_odds(key)
    except Exception as exc:
        lines.append(f"Could not load odds: {exc}")
        return "\n".join(lines), 0

    if result.get("error"):
        error_text = result["error"]

        if "404" in error_text or "no data" in error_text.lower():
            lines.append(no_board_message(label))
        elif "Missing API key" in error_text:
            lines.append("Could not load odds: Missing API key.")
        else:
            lines.append(f"Could not load odds: {error_text}")

        return "\n".join(lines), 0

    events = result.get("events", [])
    count = len(events)

    if not events:
        lines.append(no_board_message(label))
        return "\n".join(lines), 0

    lines.append("TOP BOARD")
    lines.append("")

    for event in events[:5]:
        lines.extend(summarize_event(event))
        lines.append("")

    return "\n".join(lines).strip(), count


# =========================================================
# CLEANUP / WRITE HELPERS
# =========================================================
def cleanup_report_text(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "â€™": "'",
        "â€”": "—",
        "â€“": "–",
        "â€œ": '"',
        "â€\x9d": '"',
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    lines = [line.rstrip() for line in text.splitlines()]
    cleaned = []
    blank_count = 0

    for line in lines:
        if line.strip():
            cleaned.append(line)
            blank_count = 0
        else:
            blank_count += 1
            if blank_count <= 1:
                cleaned.append("")

    return "\n".join(cleaned).strip()


def save_report(report: str) -> None:
    REPORT_FILE.write_text(report + "\n", encoding="utf-8")


# =========================================================
# REPORT BUILD
# =========================================================
def build_report() -> str:
    total_events = 0
    all_sections = []

    for sport in SPORTS:
        section_text, count = build_sport_section(sport)
        all_sections.append(section_text)
        total_events += count

    report_lines = [
        f"BETTING ODDS REPORT | {report_date_string()}",
        "",
        build_lede(),
        "",
        "GLOBAL SNAPSHOT",
        build_snapshot(total_events),
        "",
        "\n\n".join(all_sections),
        "",
        "BETTING MARKET NOTE",
        build_market_note(),
        "",
        build_disclaimer(),
        f"Generated: {format_generated_timestamp()}",
    ]

    return cleanup_report_text("\n".join(report_lines))


def generate_betting_odds_report() -> str:
    report = build_report()
    save_report(report)
    print(f"[OK] Betting odds report written to: {REPORT_FILE}")
    return report


def main():
    report = generate_betting_odds_report()
    print(report)


if __name__ == "__main__":
    main()