import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE_DIR = Path(__file__).resolve().parent
SOURCE_FILE = BASE_DIR / "betting_news_sources.json"
OUT_JSON = BASE_DIR / "betting_news_report.json"
OUT_TXT = BASE_DIR / "betting_news_report.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GSRNetworkBot/1.0; +https://www.gsrnetwork.io)"
}

MAX_ITEMS_PER_SOURCE = 5
MAX_TOTAL_ITEMS = 12
MIN_HEADLINE_LENGTH = 18

BAD_HEADLINE_PATTERNS = [
    "subscribe", "sign in", "log in", "privacy", "terms", "advertise",
    "newsletter", "cookies", "responsible gambling",
    "promo code", "bonus code", "sign up offer", "online sportsbooks",
    "bonuses", "sportsbook promo", "betting bonuses", "reviews",
    "sportsbook review", "legal states tracker", "sports betting apps",
    "betting apps", "how to bet", "betting guide", "point spread betting guide",
    "new jersey sports betting", "new york sports betting",
    "north carolina sports betting", "canada sports betting",
    "ontario sports betting", "best sports betting apps",
]

BAD_URL_PATTERNS = [
    "privacy", "terms", "login", "signup", "subscribe",
    "bonus", "promo", "reviews", "bonuses",
    "online-sports-betting", "/guides/", "/betting/canada/",
    "/betting/best-betting-apps",
]


def now_stamp():
    return datetime.now().strftime("%Y-%m-%d %I:%M:%S %p ET")


def clean_text(value):
    if not value:
        return ""
    text = re.sub(r"\s+", " ", str(value))
    text = text.replace("&amp;", "&")
    text = text.replace("&#8217;", "'")
    text = text.replace("&#x27;", "'")
    text = text.replace("&quot;", '"')
    return text.strip()


def is_good_headline(headline):
    headline = clean_text(headline)
    if len(headline) < MIN_HEADLINE_LENGTH:
        return False
    if headline.count(" ") < 3:
        return False
    lower = headline.lower()
    return not any(bad in lower for bad in BAD_HEADLINE_PATTERNS)


def is_good_url(url):
    lower = str(url).lower()
    if not lower.startswith("http"):
        return False
    return not any(bad in lower for bad in BAD_URL_PATTERNS)


def extract_article_links(html, base_url):
    links = []

    for href, text in re.findall(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html,
        flags=re.I | re.S,
    ):
        headline = clean_text(re.sub(r"<[^>]+>", "", text))
        url = urljoin(base_url, href)

        if is_good_headline(headline) and is_good_url(url):
            links.append({"headline": headline, "url": url})

    return links


def fetch_source(source):
    name = source.get("name", "Unknown Source")
    url = source.get("url", "")

    if not url:
        return []

    print(f"[FETCH] {name}: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except Exception as exc:
        print(f"[WARN] {name} failed: {exc}")
        return []

    items = []
    for item in extract_article_links(response.text, url):
        items.append({
            "headline": item["headline"],
            "source_headline": item["headline"],
            "source": name,
            "url": item["url"],
            "story_type": "betting_news",
        })

    deduped = []
    seen = set()

    for item in items:
        key = item["headline"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped[:MAX_ITEMS_PER_SOURCE]


def main():
    print(f"[{now_stamp()}] BETTING NEWS FETCH STARTED")

    if not SOURCE_FILE.exists():
        print(f"[ERROR] Missing {SOURCE_FILE}")
        return 1

    config = json.loads(SOURCE_FILE.read_text(encoding="utf-8-sig"))
    sources = config.get("sources", [])
    headline_rule = config.get("headline_rule", "Use original source headlines.")

    all_items = []
    for source in sources:
        all_items.extend(fetch_source(source))

    payload = {
        "site": "Global Betting Report",
        "vertical": "Betting",
        "headline_rule": headline_rule,
        "generated_at": now_stamp(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "items": all_items[:MAX_TOTAL_ITEMS],
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    txt_lines = [
        "GLOBAL BETTING REPORT NEWS",
        f"Generated: {payload['generated_at']}",
        "",
        headline_rule,
        "",
    ]

    for item in payload["items"]:
        txt_lines.extend([
            item["headline"],
            f"Source: {item['source']}",
            f"URL: {item['url']}",
            "",
        ])

    OUT_TXT.write_text("\n".join(txt_lines).strip() + "\n", encoding="utf-8")

    print(f"[OK] Wrote {OUT_JSON}")
    print(f"[OK] Wrote {OUT_TXT}")
    print(f"[CHECK] Betting news items: {len(payload['items'])}")
    print(f"[{now_stamp()}] BETTING NEWS FETCH COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
