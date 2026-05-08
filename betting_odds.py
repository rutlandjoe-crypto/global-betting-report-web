from pathlib import Path
from dotenv import load_dotenv
import json
import os
import re
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
JSON_REPORT_FILE = Path(
    os.getenv("BETTING_ODDS_JSON_FILE", str(BASE_DIR / "betting_odds_report.json"))
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
    "User-Agent": "Mozilla/5.0 (GlobalBettingReport Betting Desk)"
}

DISCLAIMER = (
    "This report is an automated betting-market summary intended to support, "
    "not replace, human sports journalism. It is not betting advice."
)

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
# FORMAT / MARKET HELPERS
# =========================================================
def clean_text(value, fallback="N/A") -> str:
    if value is None:
        return fallback

    value = str(value)

    replacements = {
        "__TEAM_76 ERS__": "76ers",
        "__TEAM_76ERS__": "76ers",
        "__TEAM_49 ERS__": "49ers",
        "__TEAM_49ERS__": "49ers",
        "_TEAM_76 ERS_": "76ers",
        "_TEAM_49 ERS_": "49ers",
        "Philadelphia __TEAM_76 ERS__": "Philadelphia 76ers",
        "Philadelphia __TEAM_76ERS__": "Philadelphia 76ers",
        "San Francisco __TEAM_49 ERS__": "San Francisco 49ers",
        "San Francisco __TEAM_49ERS__": "San Francisco 49ers",
    }

    for bad, good in replacements.items():
        value = value.replace(bad, good)

    value = re.sub(r"__TEAM_76\s*ERS__", "76ers", value)
    value = re.sub(r"__TEAM_49\s*ERS__", "49ers", value)

    value = re.sub(r"\s+", " ", value).strip()

    return value if value else fallback

def safe_slug(value: str) -> str:
    text = clean_text(value, "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "market"


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


def american_to_implied_probability(price) -> float | None:
    try:
        price = int(price)
    except (TypeError, ValueError):
        return None

    if price < 0:
        return abs(price) / (abs(price) + 100)
    if price > 0:
        return 100 / (price + 100)
    return None


def format_probability(probability: float | None) -> str:
    if probability is None:
        return "N/A"
    return f"{probability * 100:.1f}%"


def market_strength_from_price(price) -> str:
    try:
        price = int(price)
    except (TypeError, ValueError):
        return "unpriced"

    if price <= -220:
        return "heavy favorite"
    if price <= -150:
        return "clear favorite"
    if price < 0:
        return "slight favorite"
    if price >= 200:
        return "long underdog"
    if price >= 140:
        return "plus-money underdog"
    return "near coin-flip"


def total_environment(total_point) -> str:
    try:
        total = float(total_point)
    except (TypeError, ValueError):
        return "unknown scoring environment"

    if total >= 225:
        return "high-scoring basketball environment"
    if total >= 9.5:
        return "elevated run-scoring baseball environment"
    if total >= 6.5:
        return "higher-scoring hockey environment"
    if total >= 48:
        return "elevated football scoring environment"
    if total <= 5.5:
        return "lower-scoring hockey environment"
    if total <= 7:
        return "lower run-scoring baseball environment"
    if total <= 41:
        return "lower football scoring environment"
    return "balanced scoring environment"


def build_game_url(sport_label: str) -> str:
    urls = {
        "NBA": "https://www.espn.com/nba/scoreboard",
        "MLB": "https://www.espn.com/mlb/scoreboard",
        "NHL": "https://www.espn.com/nhl/scoreboard",
        "NFL": "https://www.espn.com/nfl/scoreboard",
    }
    return urls.get(sport_label, "https://www.espn.com")


# =========================================================
# REPORT LANGUAGE
# =========================================================
def build_lede() -> str:
    return (
        "Global Betting Report reads the board through moneylines, spreads and totals, "
        "then translates those prices into newsroom context for betting-focused readers."
    )


def build_snapshot(event_count: int, cards: list[dict]) -> str:
    if event_count >= 15:
        return "A full multi-league betting board is live, giving the desk enough volume to compare favorites, totals and matchup pricing."
    if event_count >= 5:
        return "A useful betting board is available, with enough games to separate market favorites from tighter matchup spots."
    if event_count >= 1:
        lead = cards[0] if cards else {}
        return clean_text(
            lead.get("snapshot"),
            "A focused betting board is available during this report window."
        )
    return "Limited betting data was available during this report window, so the desk is preserving market structure and freshness context."


def build_market_note() -> str:
    return (
        "Odds are a market signal, not a prediction guarantee. Moneylines show implied win probability, "
        "spreads show expected margin, and totals frame the scoring environment. Lines may move quickly "
        "and can vary by sportsbook."
    )


def build_empty_board_context() -> list[str]:
    return [
        "No reliable live odds board was available during this report window.",
        "The betting desk should re-check API credentials, sportsbook availability and league schedule timing.",
        "When the board returns, the strongest cards should explain favorite price, spread pressure and total environment instead of listing odds alone.",
    ]


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


def extract_event_market(event: dict, sport_label: str) -> dict:
    away = clean_text(event.get("away_team"), "Unknown Team")
    home = clean_text(event.get("home_team"), "Unknown Team")
    start_time = format_time(event.get("commence_time"))
    bookmaker = get_first_bookmaker(event)

    market = {
        "sport": sport_label,
        "away_team": away,
        "home_team": home,
        "matchup": f"{away} at {home}",
        "start_time": start_time,
        "bookmaker": "N/A",
        "moneyline": {},
        "spread": {},
        "total": {},
        "has_pricing": False,
        "url": build_game_url(sport_label),
    }

    if not bookmaker:
        return market

    market["bookmaker"] = clean_text(bookmaker.get("title"), "Sportsbook")

    h2h = get_market(bookmaker, "h2h")
    spreads = get_market(bookmaker, "spreads")
    totals = get_market(bookmaker, "totals")

    if h2h:
        away_outcome = get_outcome_by_name(h2h, away)
        home_outcome = get_outcome_by_name(h2h, home)
        away_price = away_outcome.get("price") if away_outcome else None
        home_price = home_outcome.get("price") if home_outcome else None

        market["moneyline"] = {
            "away_price": away_price,
            "home_price": home_price,
            "away_price_text": format_price(away_price),
            "home_price_text": format_price(home_price),
            "away_implied_probability": american_to_implied_probability(away_price),
            "home_implied_probability": american_to_implied_probability(home_price),
        }
        market["has_pricing"] = True

    if spreads:
        away_spread = get_outcome_by_name(spreads, away)
        home_spread = get_outcome_by_name(spreads, home)
        away_point = away_spread.get("point") if away_spread else None
        away_price = away_spread.get("price") if away_spread else None
        home_point = home_spread.get("point") if home_spread else None
        home_price = home_spread.get("price") if home_spread else None

        market["spread"] = {
            "away_point": away_point,
            "home_point": home_point,
            "away_point_text": format_point(away_point),
            "home_point_text": format_point(home_point),
            "away_price": away_price,
            "home_price": home_price,
            "away_price_text": format_price(away_price),
            "home_price_text": format_price(home_price),
        }
        market["has_pricing"] = True

    if totals:
        over = get_total_outcome(totals, "over")
        under = get_total_outcome(totals, "under")
        total_point = over.get("point") if over else (under.get("point") if under else None)
        over_price = over.get("price") if over else None
        under_price = under.get("price") if under else None

        market["total"] = {
            "point": total_point,
            "point_text": format_point(total_point),
            "over_price": over_price,
            "under_price": under_price,
            "over_price_text": format_price(over_price),
            "under_price_text": format_price(under_price),
            "environment": total_environment(total_point),
        }
        market["has_pricing"] = True

    return market


def choose_favorite(market: dict) -> dict | None:
    ml = market.get("moneyline") or {}
    away_price = ml.get("away_price")
    home_price = ml.get("home_price")

    if away_price is None and home_price is None:
        return None

    try:
        away_int = int(away_price) if away_price is not None else 99999
        home_int = int(home_price) if home_price is not None else 99999
    except (TypeError, ValueError):
        return None

    away = market.get("away_team")
    home = market.get("home_team")

    # In American odds, the favorite is usually the lower number, especially negative.
    if away_int < home_int:
        team = away
        price = away_price
        probability = ml.get("away_implied_probability")
        opponent = home
    else:
        team = home
        price = home_price
        probability = ml.get("home_implied_probability")
        opponent = away

    return {
        "team": team,
        "opponent": opponent,
        "price": price,
        "price_text": format_price(price),
        "implied_probability": probability,
        "implied_probability_text": format_probability(probability),
        "strength": market_strength_from_price(price),
    }


def market_priority_score(market: dict) -> int:
    score = 10
    favorite = choose_favorite(market)

    if favorite:
        score += 40
        try:
            price = int(favorite.get("price"))
            if price <= -180:
                score += 22
            elif price <= -135:
                score += 15
            elif price >= 160:
                score += 10
        except (TypeError, ValueError):
            pass

    spread = market.get("spread") or {}
    total = market.get("total") or {}

    if spread:
        score += 18
        try:
            home_point = abs(float(spread.get("home_point")))
            if home_point >= 7:
                score += 14
            elif home_point >= 3.5:
                score += 8
        except (TypeError, ValueError):
            pass

    if total:
        score += 14
        env = total.get("environment", "")
        if "elevated" in env or "high-scoring" in env or "lower" in env:
            score += 8

    return score


def build_market_interpretation(market: dict) -> dict:
    favorite = choose_favorite(market)
    spread = market.get("spread") or {}
    total = market.get("total") or {}
    sport = market.get("sport", "Sports")
    matchup = market.get("matchup", "Matchup")

    if favorite:
        headline = f"{sport}: {favorite['team']} priced as {favorite['strength']} vs {favorite['opponent']} ({favorite['price_text']})"
        snapshot = (
            f"{favorite['team']} carries an implied win probability of approximately "
            f"{favorite['implied_probability_text']} based on the listed moneyline."
        )
    else:
        headline = f"{sport}: {matchup} pricing is limited in this report window"
        snapshot = "The market card is active, but sportsbook pricing was incomplete when the report generated."

    key_data = []
    if favorite:
        key_data.append(f"Favorite: {favorite['team']} {favorite['price_text']} ({favorite['implied_probability_text']} implied).")

    if spread:
        key_data.append(
            "Spread: "
            f"{market['away_team']} {spread.get('away_point_text', 'N/A')} ({spread.get('away_price_text', 'N/A')}) / "
            f"{market['home_team']} {spread.get('home_point_text', 'N/A')} ({spread.get('home_price_text', 'N/A')})."
        )

    if total:
        key_data.append(
            f"Total: {total.get('point_text', 'N/A')} "
            f"(Over {total.get('over_price_text', 'N/A')} / Under {total.get('under_price_text', 'N/A')}); "
            f"{total.get('environment', 'scoring environment unavailable')}."
        )

    if not key_data:
        key_data.append("Pricing was limited for this matchup during this report window.")

    why_it_matters = []
    if favorite:
        why_it_matters.append(
            f"The moneyline shows how strongly the market is leaning toward {favorite['team']} before lineup, injury and late-news adjustments."
        )
    if spread:
        why_it_matters.append(
            "The spread gives reporters a cleaner read on expected margin than the moneyline alone."
        )
    if total:
        why_it_matters.append(
            "The total frames the scoring environment and can be a useful signal for fantasy, pace and game-script coverage."
        )
    if not why_it_matters:
        why_it_matters.append(
            "Limited pricing is still a signal: the desk should monitor whether the board opens, pauses or reprices before game time."
        )

    what_to_watch = [
        "Line movement after injury, lineup, weather or starting-goalie news.",
        "Whether the favorite price gets shorter or drifts back toward the underdog.",
        "Whether the total moves enough to change the expected game environment.",
    ]

    return {
        "headline": headline,
        "snapshot": snapshot,
        "key_data": key_data[:5],
        "why_it_matters": why_it_matters[:4],
        "what_to_watch": what_to_watch,
        "priority_score": market_priority_score(market),
        "story_type": "market_signal",
    }


def summarize_event(event: dict, sport_label: str = "Sports") -> tuple[list[str], dict]:
    market = extract_event_market(event, sport_label)
    interpretation = build_market_interpretation(market)

    lines = [f"{market['matchup']} — {market['start_time']}"]
    lines.append(f"Bookmaker: {market['bookmaker']}")

    ml = market.get("moneyline") or {}
    if ml:
        lines.append(
            f"Moneyline: {market['away_team']} {ml.get('away_price_text', 'N/A')} / "
            f"{market['home_team']} {ml.get('home_price_text', 'N/A')}"
        )

    spread = market.get("spread") or {}
    if spread:
        lines.append(
            "Spread: "
            f"{market['away_team']} {spread.get('away_point_text', 'N/A')} ({spread.get('away_price_text', 'N/A')}) / "
            f"{market['home_team']} {spread.get('home_point_text', 'N/A')} ({spread.get('home_price_text', 'N/A')})"
        )

    total = market.get("total") or {}
    if total:
        lines.append(
            f"Total: {total.get('point_text', 'N/A')} "
            f"(Over {total.get('over_price_text', 'N/A')} / Under {total.get('under_price_text', 'N/A')})"
        )

    lines.append("Market read:")
    lines.append(f"- {interpretation['snapshot']}")

    for item in interpretation["why_it_matters"][:2]:
        lines.append(f"- {item}")

    if not market.get("has_pricing"):
        lines.append("Pricing was limited for this matchup during this report window.")

    card = {
        "id": f"{safe_slug(sport_label)}-{safe_slug(market['away_team'])}-at-{safe_slug(market['home_team'])}",
        "sport": sport_label,
        "title": f"{sport_label} Betting Market",
        "headline": interpretation["headline"],
        "snapshot": interpretation["snapshot"],
        "matchup": market["matchup"],
        "start_time": market["start_time"],
        "bookmaker": market["bookmaker"],
        "key_data": interpretation["key_data"],
        "why_it_matters": interpretation["why_it_matters"],
        "what_to_watch": interpretation["what_to_watch"],
        "priority_score": interpretation["priority_score"],
        "story_type": interpretation["story_type"],
        "url": market["url"],
        "source_label": "ESPN Scoreboard",
        "market": market,
        "updated_at": format_generated_timestamp(),
    }

    return lines, card


# =========================================================
# SPORT SECTION BUILDER
# =========================================================
def no_board_message(label: str) -> str:
    messages = {
        "NBA": "No NBA betting board is currently available. Monitor injury reports, rotation news and playoff schedule movement before the next pricing window.",
        "MLB": "No MLB betting board is currently available. Monitor probable pitchers, lineup confirmations and weather before the next pricing window.",
        "NHL": "No NHL betting board is currently available. Monitor goalie confirmations, injury reports and series context before the next pricing window.",
        "NFL": "No NFL betting board is currently available. Monitor injuries, depth-chart signals and schedule context before the next pricing window.",
    }
    return messages.get(label, "No betting board is currently available.")


def build_error_card(label: str, error_text: str) -> dict:
    missing_key = "Missing API key" in error_text
    headline = (
        f"{label}: betting board unavailable because ODDS_API_KEY is missing"
        if missing_key
        else f"{label}: betting board unavailable during this report window"
    )
    snapshot = (
        "The betting desk could not reach live sportsbook pricing because the API key was not available in the environment."
        if missing_key
        else "The betting desk preserved market structure, but live sportsbook pricing was unavailable during this run."
    )

    return {
        "id": f"{safe_slug(label)}-betting-board-unavailable",
        "sport": label,
        "title": f"{label} Betting Market",
        "headline": headline,
        "snapshot": snapshot,
        "matchup": "",
        "start_time": "",
        "bookmaker": "",
        "key_data": [
            f"Status: {error_text}.",
            "Fallback mode: active.",
            "Market card is preserved so the site stays orderly while live pricing is unavailable.",
        ],
        "why_it_matters": [
            "A missing or unavailable odds feed should not produce placeholder sludge on the front end.",
            "The newsroom should see a clear operational status and know what to check next.",
        ],
        "what_to_watch": [
            "Verify ODDS_API_KEY in the workflow or deployment environment.",
            "Confirm the league has an active betting board.",
            "Re-run the workflow after credentials and schedule timing are confirmed.",
        ],
        "priority_score": 1,
        "story_type": "odds_feed_status",
        "url": build_game_url(label),
        "source_label": "Odds API",
        "updated_at": format_generated_timestamp(),
    }


def build_sport_section(sport: dict) -> tuple[str, int, list[dict]]:
    label = sport.get("label", "UNKNOWN")
    key = sport.get("key", "")
    lines = [label]
    cards: list[dict] = []

    try:
        result = fetch_odds(key)
    except Exception as exc:
        error_text = str(exc)
        lines.append(f"Could not load odds: {error_text}")
        cards.append(build_error_card(label, error_text))
        return "\n".join(lines), 0, cards

    if result.get("error"):
        error_text = result["error"]

        if "404" in error_text or "no data" in error_text.lower():
            lines.append(no_board_message(label))
        elif "Missing API key" in error_text:
            lines.append("Could not load odds: Missing API key.")
        else:
            lines.append(f"Could not load odds: {error_text}")

        cards.append(build_error_card(label, error_text))
        return "\n".join(lines), 0, cards

    events = result.get("events", [])
    count = len(events)

    if not events:
        lines.append(no_board_message(label))
        cards.append({
            "id": f"{safe_slug(label)}-no-current-board",
            "sport": label,
            "title": f"{label} Betting Market",
            "headline": f"{label}: no active betting board available",
            "snapshot": no_board_message(label),
            "key_data": ["Status: no current board returned by the odds feed."],
            "why_it_matters": [
                "No-board windows are normal around schedule gaps, league offseason periods or delayed sportsbook posting."
            ],
            "what_to_watch": [
                "Check again when games move closer to start time.",
                "Monitor injury and lineup news that may influence opening numbers.",
            ],
            "priority_score": 1,
            "story_type": "no_board",
            "url": build_game_url(label),
            "source_label": "ESPN Scoreboard",
            "updated_at": format_generated_timestamp(),
        })
        return "\n".join(lines), 0, cards

    lines.append("TOP BOARD")
    lines.append("")

    event_cards = []
    for event in events[:8]:
        event_lines, card = summarize_event(event, label)
        event_cards.append(card)
        lines.extend(event_lines)
        lines.append("")

    event_cards = sorted(event_cards, key=lambda item: item.get("priority_score", 0), reverse=True)
    cards.extend(event_cards[:5])

    return "\n".join(lines).strip(), count, cards


# =========================================================
# PAYLOAD BUILDER
# =========================================================
def select_lead_card(cards: list[dict]) -> dict | None:
    if not cards:
        return None
    return sorted(cards, key=lambda item: item.get("priority_score", 0), reverse=True)[0]


def build_homepage_cards(cards: list[dict]) -> list[dict]:
    ordered = sorted(cards, key=lambda item: item.get("priority_score", 0), reverse=True)
    homepage = []

    for card in ordered[:12]:
        homepage.append({
            "league": card.get("sport", "Betting"),
            "title": card.get("title", "Betting Market"),
            "headline": card.get("headline", ""),
            "snapshot": card.get("snapshot", ""),
            "url": card.get("url", "https://www.espn.com"),
            "source_label": card.get("source_label", "Market Source"),
            "key_data": card.get("key_data", []),
            "why_it_matters": card.get("why_it_matters", []),
            "what_to_watch": card.get("what_to_watch", []),
            "priority_score": card.get("priority_score", 0),
            "story_type": card.get("story_type", "market_signal"),
            "updated_at": card.get("updated_at", format_generated_timestamp()),
        })

    return homepage


def build_sections(cards_by_sport: dict[str, list[dict]], section_text_by_sport: dict[str, str]) -> dict:
    sections = {}

    for sport in SPORTS:
        label = sport["label"]
        cards = sorted(cards_by_sport.get(label, []), key=lambda item: item.get("priority_score", 0), reverse=True)
        lead = cards[0] if cards else None

        sections[label.lower()] = {
            "title": f"{label} Betting Market",
            "headline": lead.get("headline") if lead else f"{label}: betting market checked",
            "snapshot": lead.get("snapshot") if lead else no_board_message(label),
            "cards": cards,
            "content": section_text_by_sport.get(label, ""),
            "key_data": lead.get("key_data", []) if lead else [],
            "why_it_matters": lead.get("why_it_matters", []) if lead else [],
            "what_to_watch": lead.get("what_to_watch", []) if lead else [],
            "updated_at": format_generated_timestamp(),
            "source_label": "The Odds API",
            "url": build_game_url(label),
        }

    return sections


def build_live_newsroom(cards: list[dict]) -> list[dict]:
    newsroom = []
    for card in sorted(cards, key=lambda item: item.get("priority_score", 0), reverse=True)[:10]:
        newsroom.append({
            "headline": card.get("headline", ""),
            "snapshot": card.get("snapshot", ""),
            "source": card.get("source_label", "Market Source"),
            "url": card.get("url", ""),
            "league": card.get("sport", "Betting"),
            "key_data": card.get("key_data", []),
            "why_it_matters": card.get("why_it_matters", []),
            "what_to_watch": card.get("what_to_watch", []),
            "updated_at": card.get("updated_at", format_generated_timestamp()),
        })
    return newsroom


def build_editor_signals(total_events: int, cards: list[dict]) -> list[str]:
    if not cards or total_events == 0:
        return build_empty_board_context()

    lead = select_lead_card(cards)
    signals = [
        f"Lead market: {lead.get('headline')}" if lead else "Lead market unavailable.",
        f"Total games checked: {total_events}.",
        "Cards prioritize implied probability, expected margin and scoring environment instead of raw odds alone.",
        "Betting context should remain descriptive and journalist-facing, not prescriptive wagering advice.",
    ]

    sports_seen = sorted({card.get("sport", "Betting") for card in cards if card.get("sport")})
    if sports_seen:
        signals.append(f"Active sports on board: {', '.join(sports_seen)}.")

    return signals[:7]


def build_json_payload(total_events: int, cards: list[dict], cards_by_sport: dict[str, list[dict]], section_text_by_sport: dict[str, str]) -> dict:
    generated = format_generated_timestamp()
    lead = select_lead_card(cards)
    headline = lead.get("headline") if lead else "Betting board checked with limited live odds available"
    snapshot = build_snapshot(total_events, cards)

    return {
        "site": "Global Betting Report",
        "vertical": "Betting",
        "title": "Global Betting Report",
        "headline": headline,
        "snapshot": snapshot,
        "updated_at": generated,
        "generated_at": generated,
        "freshness": {
            "last_checked": generated,
            "sports_checked": [sport["label"] for sport in SPORTS],
            "total_games_checked": total_events,
            "total_market_cards": len(cards),
            "odds_api_key_found": bool(ODDS_API_KEY),
            "source": "The Odds API",
        },
        "editorial_brain": {
            "status": "active",
            "version": "2026-05-08-betting-market-context-v2",
            "focus": [
                "Implied probability",
                "Favorite and underdog context",
                "Spread pressure",
                "Total environment",
                "Injury, lineup and weather monitoring",
                "Journalist-facing betting interpretation",
            ],
            "safety": "Descriptive market context only; no wagering instructions.",
        },
        "live_newsroom": build_live_newsroom(cards),
        "editor_signals": build_editor_signals(total_events, cards),
        "homepage_cards": build_homepage_cards(cards),
        "sections": build_sections(cards_by_sport, section_text_by_sport),
        "disclaimer": DISCLAIMER,
    }


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


def save_json_report(payload: dict) -> None:
    JSON_REPORT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# =========================================================
# REPORT BUILD
# =========================================================
def build_report() -> tuple[str, dict]:
    total_events = 0
    all_sections = []
    all_cards: list[dict] = []
    cards_by_sport: dict[str, list[dict]] = {}
    section_text_by_sport: dict[str, str] = {}

    for sport in SPORTS:
        section_text, count, cards = build_sport_section(sport)
        label = sport.get("label", "UNKNOWN")
        all_sections.append(section_text)
        section_text_by_sport[label] = section_text
        cards_by_sport[label] = cards
        all_cards.extend(cards)
        total_events += count

    lead = select_lead_card(all_cards)
    top_headline = lead.get("headline") if lead else "Betting board checked with limited live odds available"

    report_lines = [
        f"BETTING ODDS REPORT | {report_date_string()}",
        "",
        "HEADLINE",
        top_headline,
        "",
        "SNAPSHOT",
        build_snapshot(total_events, all_cards),
        "",
        "KEY DATA",
        f"- Total games checked: {total_events}",
        f"- Market cards generated: {len(all_cards)}",
        f"- Odds API key found: {bool(ODDS_API_KEY)}",
        "",
        "EDITORIAL SIGNALS",
    ]

    for signal in build_editor_signals(total_events, all_cards):
        report_lines.append(f"- {signal}")

    report_lines.extend([
        "",
        build_lede(),
        "",
        "GLOBAL SNAPSHOT",
        build_snapshot(total_events, all_cards),
        "",
        "\n\n".join(all_sections),
        "",
        "BETTING MARKET NOTE",
        build_market_note(),
        "",
        DISCLAIMER,
        f"Generated: {format_generated_timestamp()}",
    ])

    payload = build_json_payload(total_events, all_cards, cards_by_sport, section_text_by_sport)
    return cleanup_report_text("\n".join(report_lines)), payload


def generate_betting_odds_report() -> str:
    report, payload = build_report()
    save_report(report)
    save_json_report(payload)
    print(f"[OK] Betting odds report written to: {REPORT_FILE}")
    print(f"[OK] Betting odds JSON written to: {JSON_REPORT_FILE}")
    return report


def main():
    report = generate_betting_odds_report()
    print(report)


if __name__ == "__main__":
    main()
