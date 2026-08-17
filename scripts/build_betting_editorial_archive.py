from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "public" / "latest_report.json"
DEFAULT_ARCHIVE = ROOT / "public" / "editorial_archive.json"


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " • ".join(filter(None, (clean_text(item) for item in value)))
    if isinstance(value, dict):
        return " • ".join(filter(None, (clean_text(item) for item in value.values())))
    return re.sub(r"\s+", " ", str(value)).strip()


def as_list(value: object) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [text for item in value if (text := clean_text(item))]
    if isinstance(value, dict):
        return [text for item in value.values() if (text := clean_text(item))]
    return [part.strip() for part in re.split(r"\r?\n|•|\|", str(value)) if part.strip()]


def publication_date(report: dict) -> str:
    for key in ("updated_at", "generated_at", "generated_utc", "published_at"):
        match = re.search(r"\d{4}-\d{2}-\d{2}", clean_text(report.get(key)))
        if match:
            return match.group(0)
    return ""


def publication_time(report: dict) -> str:
    return clean_text(
        report.get("generated_utc")
        or report.get("updated_at")
        or report.get("generated_at")
        or report.get("published_at")
    )


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9\s-]", "", ascii_value.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")[:105]


def event_name(story: dict) -> str:
    candidates = (
        clean_text(story.get("game")),
        clean_text(story.get("matchup")),
        clean_text(story.get("headline") or story.get("title")),
    )
    for candidate in candidates:
        if not re.search(r"\s(?:at|vs\.?|versus)\s", candidate, re.IGNORECASE):
            continue
        candidate = re.split(r"\s+-\s+\d{1,2}:\d{2}\s", candidate, maxsplit=1)[0]
        candidate = candidate.split(":", 1)[0]
        return clean_text(candidate)
    return ""


def is_durable_editorial(story: dict) -> bool:
    title = clean_text(story.get("headline") or story.get("title"))
    summary = clean_text(
        story.get("snapshot")
        or story.get("summary")
        or story.get("description")
        or story.get("body")
    )
    why = as_list(story.get("why_it_matters") or story.get("whyItMatters"))
    watch = as_list(story.get("what_to_watch") or story.get("whatToWatch"))
    story_type = clean_text(story.get("story_type") or story.get("type")).lower()

    # Betting reports also contain raw odds rows and live-score/fallback cards. Only
    # named matchup reports with their own context survive as editorial inventory.
    return bool(
        title
        and event_name(story)
        and len(summary) >= 120
        and why
        and watch
        and story_type in {"", "market_context"}
    )


def normalize_story(story: dict, report: dict) -> dict:
    date = publication_date(report)
    event = event_name(story)
    title = clean_text(story.get("headline") or story.get("title"))
    source_url = clean_text(
        story.get("url")
        or story.get("link")
        or story.get("source_url")
        or story.get("sourceUrl")
    )
    market = [
        *as_list(story.get("market")),
        *as_list(story.get("key_data") or story.get("keyData")),
    ]
    return {
        "slug": f"{date}-{slugify(event)}",
        "title": title,
        "label": clean_text(story.get("league") or story.get("sport") or "Betting"),
        "summary": clean_text(
            story.get("snapshot")
            or story.get("summary")
            or story.get("description")
            or story.get("body")
        ),
        "sourceUrl": source_url if source_url.startswith(("http://", "https://")) else "",
        "publishedAt": publication_time(report),
        "reportDate": date,
        "game": event,
        "market": list(dict.fromkeys(filter(None, market))),
        "impliedProbability": as_list(
            story.get("implied_probability") or story.get("impliedProbability")
        ),
        "whyItMatters": as_list(
            story.get("why_it_matters") or story.get("whyItMatters") or story.get("why")
        ),
        "whatToWatch": as_list(
            story.get("what_to_watch") or story.get("whatToWatch") or story.get("watch")
        ),
        "storyAngles": as_list(
            story.get("story_angles") or story.get("storyAngles") or story.get("angles")
        ),
    }


def stories_from_report(report: dict) -> list[dict]:
    if not publication_date(report):
        return []
    cards = report.get("homepage_cards")
    if not isinstance(cards, list):
        return []
    return [normalize_story(story, report) for story in cards if isinstance(story, dict) and is_durable_editorial(story)]


def report_history() -> Iterable[dict]:
    listing = subprocess.run(
        ["git", "rev-list", "--objects", "--all", "--", "public/latest_report.json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    hashes = list(
        dict.fromkeys(
            line.split(" ", 1)[0]
            for line in listing
            if line.endswith(" public/latest_report.json")
        )
    )
    batch = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=ROOT,
        input=("\n".join(hashes) + "\n").encode(),
        check=True,
        capture_output=True,
    )
    stream = io.BytesIO(batch.stdout)
    for _ in hashes:
        header = stream.readline().decode().strip().split()
        size = int(header[2])
        raw = stream.read(size)
        stream.read(1)
        try:
            yield json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue


def read_archive(path: Path) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload.get("stories", []) if isinstance(payload, dict) else []


def build_archive(reports: Iterable[dict], existing: Iterable[dict] = ()) -> list[dict]:
    stories = {story["slug"]: story for story in existing if isinstance(story, dict) and story.get("slug")}
    for report in reports:
        for story in stories_from_report(report):
            previous = stories.get(story["slug"])
            if not previous or story["publishedAt"] >= clean_text(previous.get("publishedAt")):
                stories[story["slug"]] = story
    return sorted(stories.values(), key=lambda story: (story["reportDate"], story["slug"]), reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Retain durable Betting matchup analysis.")
    parser.add_argument("--history", action="store_true", help="Recover legitimate reports from Git history.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    args = parser.parse_args()

    reports = list(report_history()) if args.history else []
    reports.append(json.loads(args.report.read_text(encoding="utf-8-sig")))
    stories = build_archive(reports, read_archive(args.archive))
    payload = {
        "site": "Global Betting Report",
        "generatedAt": stories[0]["publishedAt"] if stories else "",
        "storyCount": len(stories),
        "stories": stories,
    }
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    args.archive.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Retained {len(stories)} durable Betting editorial stories in {args.archive}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
