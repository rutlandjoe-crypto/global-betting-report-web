from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)
REPORT_FILE = BASE_DIR / "betting_odds_report.txt"
SUCCESS_MARKER = BASE_DIR / ".gbr_betting_success.json"
TIMEZONE = ZoneInfo("America/New_York")

API_KEY = os.getenv("SPORTRADAR_API_KEY", "").strip()
ACCESS_LEVEL = os.getenv("SPORTRADAR_ACCESS_LEVEL", "trial").strip().lower()
RUN_TOKEN = os.getenv("GBR_RUN_TOKEN", "").strip() or uuid.uuid4().hex
MIN_VALID_EVENTS = 8
MAX_EVENTS_PER_LEAGUE = 12
SOURCE_MAX_AGE = timedelta(hours=3)
EVENT_WINDOW = timedelta(days=7)

COMPETITIONS = (
    ("NBA", "sr:competition:132"),
    ("MLB", "sr:competition:109"),
    ("NHL", "sr:competition:234"),
    ("NFL", "sr:competition:31"),
)
BOOK_PRIORITY = (
    "DraftKings", "FanDuel", "ESPNbetCom", "MGM", "Bet365.US.NJ",
    "WilliamHillNewJersey", "BetRivers", "Consensus",
)
MONEYLINE_MARKETS = {"2way", "3way", "moneyline", "money_line"}
SPREAD_MARKETS = {"handicap", "point_spread", "spread", "run_line", "puck_line"}
TOTAL_MARKETS = {"total", "totals"}


class ProviderError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_start(value: object) -> str:
    parsed = parse_datetime(value)
    return "TBD ET" if parsed is None else parsed.astimezone(TIMEZONE).strftime("%I:%M %p ET").lstrip("0")


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


class SportradarClient:
    def __init__(self, api_key: str = API_KEY, access_level: str = ACCESS_LEVEL):
        if not api_key:
            raise ProviderError("SPORTRADAR_API_KEY is not configured; refusing to generate unsourced odds.")
        if access_level not in {"trial", "production"}:
            raise ProviderError("SPORTRADAR_ACCESS_LEVEL must be 'trial' or 'production'.")
        self.access_level = access_level
        self.base_url = f"https://api.sportradar.com/oddscomparison-prematch/{access_level}/v2/en"
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "GlobalBettingReport/1.0",
            "x-api-key": api_key,
        })
        retry = Retry(
            total=2, connect=2, read=2, status=2, backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}), respect_retry_after_header=True,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def get_json(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self.session.get(url, params=params, timeout=(5, 20), allow_redirects=True)
        except requests.RequestException as exc:
            raise ProviderError(f"Sportradar request failed for {url}: {type(exc).__name__}: {exc}") from exc
        if response.status_code == 403:
            raise ProviderError(
                f"Sportradar returned HTTP 403 for {url}. The key is not entitled to Odds Comparison "
                f"Prematch {self.access_level} v2, or the configured access level is wrong."
            )
        if response.status_code in {401, 404}:
            excerpt = " ".join(response.text.split())[:240]
            raise ProviderError(f"Sportradar returned HTTP {response.status_code} for {url}: {excerpt}")
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            excerpt = " ".join(response.text.split())[:240]
            raise ProviderError(f"Sportradar returned HTTP {response.status_code} for {url}: {excerpt}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError(f"Sportradar returned non-JSON data for {url}.") from exc
        if not isinstance(payload, dict):
            raise ProviderError(f"Sportradar returned an unexpected payload for {url}.")
        return payload

    def competition_markets(self, competition_id: str) -> dict:
        return self.get_json(
            f"competitions/{competition_id}/sport_event_markets.json",
            params={"start": 0, "limit": 50},
        )


def market_entries(payload: dict) -> list[dict]:
    entries = (
        payload.get("competition_sport_event_markets")
        or payload.get("sport_event_markets")
        or []
    )
    if isinstance(entries, dict):
        entries = entries.get("sport_event_market") or entries.get("sport_events") or []
    parsed = [entry for entry in entries if isinstance(entry, dict)]
    if not parsed and isinstance(payload.get("sport_event"), dict):
        parsed = [payload]
    return parsed


def source_generated_at(payload: dict) -> datetime:
    generated = parse_datetime(payload.get("generated_at"))
    if generated is None:
        raise ProviderError("Sportradar response is missing a valid generated_at timestamp.")
    age = utc_now() - generated
    if age < timedelta(minutes=-5) or age > SOURCE_MAX_AGE:
        raise ProviderError("Sportradar response is outside the 3-hour freshness window.")
    return generated


def active_books(market: dict) -> list[dict]:
    return [
        book for book in (market.get("books") or [])
        if isinstance(book, dict)
        and str(book.get("removed", "false")).lower() != "true"
        and any(
            isinstance(outcome, dict)
            and str(outcome.get("removed", "false")).lower() != "true"
            and outcome_price(outcome)
            for outcome in (book.get("outcomes") or [])
        )
    ]


def choose_book(markets: list[dict]) -> str | None:
    counts: dict[str, int] = {}
    primary = MONEYLINE_MARKETS | SPREAD_MARKETS | TOTAL_MARKETS
    for market in markets:
        if clean(market.get("name")).lower() not in primary:
            continue
        for book in active_books(market):
            name = clean(book.get("name"))
            if name:
                counts[name] = counts.get(name, 0) + 1
    if not counts:
        return None
    priority = {name: index for index, name in enumerate(BOOK_PRIORITY)}
    return min(counts, key=lambda name: (-counts[name], priority.get(name, 999), name))


def outcomes_for(markets: list[dict], names: set[str], book_name: str) -> list[dict]:
    for market in markets:
        if clean(market.get("name")).lower() not in names:
            continue
        book = next((item for item in active_books(market) if clean(item.get("name")) == book_name), None)
        if book:
            return [
                outcome for outcome in (book.get("outcomes") or [])
                if isinstance(outcome, dict) and str(outcome.get("removed", "false")).lower() != "true"
            ]
    return []


def competitor_names(event: dict) -> tuple[str, str] | None:
    by_side = {
        clean(item.get("qualifier")).lower(): clean(item.get("name"))
        for item in (event.get("competitors") or []) if isinstance(item, dict)
    }
    away, home = by_side.get("away", ""), by_side.get("home", "")
    return (away, home) if away and home else None


def american(value: object) -> str:
    text = clean(value)
    if text and not text.startswith(("+", "-")):
        try:
            if float(text) > 0:
                return f"+{text}"
        except ValueError:
            pass
    return text


def decimal_to_american(value: object) -> str:
    text = clean(value)
    try:
        decimal = float(text)
    except (TypeError, ValueError):
        return ""
    if decimal <= 1:
        return ""
    converted = (decimal - 1) * 100 if decimal >= 2 else -100 / (decimal - 1)
    rounded = int(round(converted))
    return f"+{rounded}" if rounded > 0 else str(rounded)


def outcome_price(outcome: dict) -> str:
    direct = outcome.get("odds_american")
    if direct not in (None, ""):
        return american(direct)
    return decimal_to_american(outcome.get("odds"))


def side_outcome(outcomes: list[dict], side: str) -> dict | None:
    return next((item for item in outcomes if clean(item.get("type")).lower() == side), None)


def format_moneyline(outcomes: list[dict], away: str, home: str) -> str:
    away_value, home_value = side_outcome(outcomes, "away"), side_outcome(outcomes, "home")
    if not away_value or not home_value:
        return ""
    away_odds, home_odds = outcome_price(away_value), outcome_price(home_value)
    return f"Moneyline: {away} {away_odds} / {home} {home_odds}" if away_odds and home_odds else ""


def format_spread(outcomes: list[dict], away: str, home: str) -> str:
    away_value, home_value = side_outcome(outcomes, "away"), side_outcome(outcomes, "home")
    if not away_value or not home_value:
        return ""
    away_line = clean(away_value.get("spread") or away_value.get("handicap"))
    home_line = clean(home_value.get("spread") or home_value.get("handicap"))
    away_odds, home_odds = outcome_price(away_value), outcome_price(home_value)
    return (
        f"Spread: {away} {away_line} ({away_odds}) / {home} {home_line} ({home_odds})"
        if all((away_line, home_line, away_odds, home_odds)) else ""
    )


def format_total(outcomes: list[dict]) -> str:
    over, under = side_outcome(outcomes, "over"), side_outcome(outcomes, "under")
    if not over or not under:
        return ""
    total = clean(over.get("total") or under.get("total"))
    over_odds, under_odds = outcome_price(over), outcome_price(under)
    return f"Total: {total} (Over {over_odds} / Under {under_odds})" if all((total, over_odds, under_odds)) else ""


def event_lines(entry: dict, now: datetime) -> list[str] | None:
    event = entry.get("sport_event") or {}
    start_value = event.get("start_time") or event.get("scheduled")
    start = parse_datetime(start_value)
    if start is None or start < now - timedelta(minutes=5) or start > now + EVENT_WINDOW:
        return None
    names = competitor_names(event)
    if names is None:
        return None
    away, home = names
    markets_value = entry.get("markets") or event.get("markets") or []
    if isinstance(markets_value, dict):
        markets_value = markets_value.get("market") or []
    markets = [market for market in markets_value if isinstance(market, dict)]
    book_name = choose_book(markets)
    if not book_name:
        return None
    prices = [
        format_moneyline(outcomes_for(markets, MONEYLINE_MARKETS, book_name), away, home),
        format_spread(outcomes_for(markets, SPREAD_MARKETS, book_name), away, home),
        format_total(outcomes_for(markets, TOTAL_MARKETS, book_name)),
    ]
    prices = [price for price in prices if price]
    if not prices:
        return None
    return [f"{away} at {home} - {format_start(start_value)}", f"Bookmaker: {book_name}", *prices]


def response_shape(payload: dict, entries: list[dict]) -> str:
    parts = [f"root={sorted(payload)}", f"entries={len(entries)}"]
    if not entries:
        return " ".join(parts)
    entry = entries[0]
    event = entry.get("sport_event") or {}
    markets = entry.get("markets") or event.get("markets") or []
    if isinstance(markets, dict):
        markets = markets.get("market") or []
    parts.extend([
        f"entry={sorted(entry)}",
        f"event={sorted(event) if isinstance(event, dict) else type(event).__name__}",
        f"markets={len(markets) if isinstance(markets, list) else type(markets).__name__}",
    ])
    if isinstance(markets, list) and markets:
        market = markets[0]
        parts.append(f"market={sorted(market) if isinstance(market, dict) else type(market).__name__}")
        books = market.get("books") or [] if isinstance(market, dict) else []
        parts.append(f"books={len(books) if isinstance(books, list) else type(books).__name__}")
        if isinstance(books, list) and books:
            book = books[0]
            parts.append(f"book={sorted(book) if isinstance(book, dict) else type(book).__name__}")
            outcomes = book.get("outcomes") or [] if isinstance(book, dict) else []
            parts.append(f"outcomes={len(outcomes) if isinstance(outcomes, list) else type(outcomes).__name__}")
            if isinstance(outcomes, list) and outcomes:
                outcome = outcomes[0]
                parts.append(f"outcome={sorted(outcome) if isinstance(outcome, dict) else type(outcome).__name__}")
    return " ".join(parts)


def response_labels(entries: list[dict]) -> str:
    market_names: set[str] = set()
    book_names: set[str] = set()
    outcome_types: set[str] = set()
    for entry in entries:
        event = entry.get("sport_event") or {}
        markets = entry.get("markets") or event.get("markets") or []
        if isinstance(markets, dict):
            markets = markets.get("market") or []
        for market in markets if isinstance(markets, list) else []:
            market_names.add(clean(market.get("name")))
            for book in market.get("books") or []:
                book_names.add(clean(book.get("name")))
                for outcome in book.get("outcomes") or []:
                    outcome_types.add(clean(outcome.get("type")))
    return (
        f"market_names={sorted(market_names)} "
        f"book_names={sorted(book_names)} outcome_types={sorted(outcome_types)}"
    )


def build_report(client: SportradarClient) -> tuple[str, dict]:
    now = utc_now()
    sections: list[str] = []
    valid_events = 0
    valid_markets = 0
    source_times: list[datetime] = []
    for label, competition_id in COMPETITIONS:
        payload = client.competition_markets(competition_id)
        source_times.append(source_generated_at(payload))
        entries = market_entries(payload)
        seen: set[str] = set()
        games: list[list[str]] = []
        for entry in entries:
            event_id = clean((entry.get("sport_event") or {}).get("id"))
            if not event_id or event_id in seen:
                continue
            lines = event_lines(entry, now)
            if lines:
                seen.add(event_id)
                games.append(lines)
            if len(games) >= MAX_EVENTS_PER_LEAGUE:
                break
        if games:
            body = [label, "TOP BOARD", ""]
            for lines in games:
                body.extend(lines)
                body.append("")
                valid_events += 1
                valid_markets += len(lines) - 2
            sections.append("\n".join(body).strip())
        print(f"[SPORTRADAR] {label}: {len(games)} valid prematch events")
        if not games:
            print(f"[SPORTRADAR] {label} response shape: {response_shape(payload, entries)}")
            print(f"[SPORTRADAR] {label} response labels: {response_labels(entries)}")
    if valid_events < MIN_VALID_EVENTS:
        raise ProviderError(
            f"Only {valid_events} valid sourced events were available; {MIN_VALID_EVENTS} are required. "
            "No Betting output was published."
        )
    generated_et = now.astimezone(TIMEZONE)
    report = "\n\n".join([
        f"BETTING ODDS REPORT | {generated_et:%Y-%m-%d}",
        "Current prematch prices sourced from Sportradar Odds Comparison Prematch v2.",
        *sections,
        "BETTING MARKET NOTE\nLines may move and can vary across sportsbooks.",
        "This report is an automated summary intended to support, not replace, human sports journalism.",
        f"Generated: {generated_et:%Y-%m-%d %I:%M:%S %p ET}",
    ]).strip() + "\n"
    return report, {
        "source": "sportradar_oddscomparison_prematch_v2",
        "source_generated_at": max(source_times).isoformat(),
        "valid_event_count": valid_events,
        "valid_market_count": valid_markets,
    }


def generate_betting_odds_report(client: SportradarClient | None = None) -> str:
    SUCCESS_MARKER.unlink(missing_ok=True)
    report, metadata = build_report(client or SportradarClient())
    marker = {
        **metadata,
        "run_token": RUN_TOKEN,
        "generated_utc": utc_now().isoformat(),
        "report_sha256": hashlib.sha256(report.encode("utf-8")).hexdigest(),
    }
    atomic_write(REPORT_FILE, report)
    atomic_write(SUCCESS_MARKER, json.dumps(marker, indent=2, sort_keys=True) + "\n")
    print(f"[OK] Wrote {REPORT_FILE} with {metadata['valid_event_count']} sourced events")
    print(f"[OK] Wrote current-run handoff marker {SUCCESS_MARKER.name}")
    return report


def main() -> int:
    try:
        generate_betting_odds_report()
        return 0
    except ProviderError as exc:
        print(f"[ERROR] {exc}")
        return 1
    except Exception as exc:
        print(f"[ERROR] Unexpected Betting generator failure: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
