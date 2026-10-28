"""Give app cards real destinations without relabeling scoreboard links as articles."""
from __future__ import annotations

from copy import deepcopy
from urllib.parse import urlsplit

from scripts.build_betting_editorial_archive import (
    build_archive, is_durable_editorial, normalize_story,
)

SITE = "https://www.globalbettingreport.com"


def link_report(report: dict, existing: list[dict], news: list[dict] = ()) -> tuple[dict, list[dict]]:
    result = deepcopy(report)
    archive = build_archive([report], existing)
    links = {}
    for card in result.get("homepage_cards", []):
        if is_durable_editorial(card):
            slug = normalize_story(card, report)["slug"]
            links[card["headline"]] = f"{SITE}/editorial/{slug}"

    def link_card(card: dict) -> None:
        destination = links.get(card.get("headline"))
        if destination:
            card.setdefault("source_url", card.get("url", ""))
            card["url"] = destination
            card.setdefault("source_name", card.get("source_label") or card.get("source", ""))

    for key in ("homepage_cards", "live_newsroom"):
        for card in result.get(key, []):
            link_card(card)
            if "/scoreboard" in str(card.get("url", "")):
                raise ValueError("A Betting card has no readable matchup page; preserving the previous publication.")
    sections = result.get("sections", {})
    for section in sections.values() if isinstance(sections, dict) else sections:
        link_card(section)
        for card in section.get("cards", []):
            link_card(card)

    # Fetch failures must not remove verified market reporting. Source headlines
    # and exact article URLs are retained; news never claims odds verification.
    articles = []
    seen = set()
    for item in news:
        headline, url = item.get("headline", "").strip(), item.get("url", "").strip()
        parsed = urlsplit(url)
        if not headline or parsed.scheme != "https" or not parsed.netloc or "/scoreboard" in parsed.path:
            continue
        if url in seen:
            continue
        seen.add(url)
        articles.append({
            "headline": headline, "url": url,
            "snapshot": f"Betting coverage from {item.get('source', 'the original publisher')}.",
            "source_name": item.get("source", ""), "story_type": "betting_news",
            "key_data": [], "why_it_matters": [], "what_to_watch": [],
        })
    result["live_newsroom"] = articles[:8] + result.get("live_newsroom", [])
    return result, archive
