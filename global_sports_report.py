from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "global_sports_report.txt"
TIMEZONE = ZoneInfo("America/New_York")

LEAGUE_FILES: list[tuple[str, Path]] = [
    ("MLB", BASE_DIR / "mlb_report.txt"),
    ("NBA", BASE_DIR / "nba_report.txt"),
    ("NHL", BASE_DIR / "nhl_report.txt"),
    ("NFL", BASE_DIR / "nfl_report.txt"),
    ("NFL_DRAFT", BASE_DIR / "nfl_draft_signals.txt"),
    ("SOCCER", BASE_DIR / "soccer_report.txt"),
    ("FANTASY", BASE_DIR / "fantasy_report.txt"),
]

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, human sports journalism."
)

SECTION_HEADERS = {
    "HEADLINE",
    "KEY STORYLINES",
    "KEY RESULTS",
    "KEY DATA POINTS",
    "SNAPSHOT",
    "FINAL SCORES",
    "LIVE",
    "LIVE GAMES",
    "UPCOMING",
    "OUTLOOK",
    "TOP PERFORMERS",
    "GLOBAL SNAPSHOT",
    "FALLBACK NOTE",
    "BETTING MARKET NOTE",
    "TOP BOARD",
    "NOTE",
    "ERROR",
    "WHY IT MATTERS",
    "STORY ANGLES",
    "WATCH LIST",
    "REPORT NOTE",
    "DISCLAIMER",
    "DRAFT SIGNALS",
}

LEAGUE_HEADERS = {
    "MLB",
    "NBA",
    "NHL",
    "NFL",
    "NFL DRAFT SIGNALS",
    "SOCCER",
    "FANTASY",
    "BETTING ODDS",
}

PLACEHOLDER_LINES = (
    "no final scores were available",
    "no live games were available",
    "no live matches were available",
    "no upcoming games were available",
    "no upcoming matches were available",
)

DISPLAY_NAMES = {
    "MLB": "MLB",
    "NBA": "NBA",
    "NHL": "NHL",
    "NFL": "NFL",
    "NFL_DRAFT": "NFL DRAFT SIGNALS",
    "SOCCER": "SOCCER",
    "FANTASY": "FANTASY",
}


def now_et() -> datetime:
    return datetime.now(TIMEZONE)


def fix_encoding(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "â€™": "’",
        "â€˜": "‘",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€": '"',
        "â€”": "—",
        "â€“": "–",
        "â€¢": "•",
        "Â ": " ",
        "Â": "",
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã±": "ñ",
        "Ã‰": "É",
        "Ã": "Á",
        "Ã“": "Ó",
        "Ãš": "Ú",
        "Ã‘": "Ñ",
        "Ã¼": "ü",
        "Ãœ": "Ü",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return text


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = fix_encoding(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    normalized_lines: list[str] = []
    blank_pending = False

    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()

        if not line:
            if normalized_lines:
                blank_pending = True
            continue

        if blank_pending and normalized_lines:
            normalized_lines.append("")
            blank_pending = False

        normalized_lines.append(line)

    return "\n".join(normalized_lines).strip()


def read_file(path: Path) -> str:
    if not path.exists():
        return ""

    try:
        return normalize_text(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR reading {path}: {exc}")
        return ""


def is_section_header(line: str) -> bool:
    return line.strip() in SECTION_HEADERS


def is_league_header(line: str) -> bool:
    return line.strip() in LEAGUE_HEADERS


def extract_section(text: str, header: str) -> str:
    lines = text.splitlines()
    capture = False
    bucket: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()

        if line == header:
            capture = True
            continue

        if not capture:
            continue

        if is_section_header(line) or is_league_header(line):
            break

        bucket.append(raw_line)

    return normalize_text("\n".join(bucket)) if bucket else ""


def is_placeholder_line(line: str) -> bool:
    lowered = line.strip().lower()
    return any(lowered.startswith(prefix) for prefix in PLACEHOLDER_LINES)


def clean_lines(block: str) -> list[str]:
    if not block:
        return []

    cleaned: list[str] = []

    for raw_line in block.splitlines():
        line = normalize_text(raw_line)
        if not line:
            continue

        lowered = line.lower()

        if "automated summary" in lowered:
            continue
        if line.startswith("Generated:"):
            continue
        if line.startswith("Updated:"):
            continue
        if line in LEAGUE_HEADERS:
            continue
        if line == "LIVE GAMES":
            continue

        if line.startswith("UPCOMING: "):
            line = line.replace("UPCOMING: ", "", 1)
        if line.startswith("LIVE: "):
            line = line.replace("LIVE: ", "", 1)
        if line.startswith("FINAL: "):
            line = line.replace("FINAL: ", "", 1)
        if line.startswith("- "):
            line = line[2:].strip()

        if line:
            cleaned.append(line)

    return cleaned


def summarize_league(league: str, text: str) -> dict[str, Any]:
    snapshot = extract_section(text, "SNAPSHOT")
    headline = extract_section(text, "HEADLINE")
    key_storylines = extract_section(text, "KEY STORYLINES")
    key_data_points = extract_section(text, "KEY DATA POINTS")
    final_scores = extract_section(text, "FINAL SCORES")
    live_games = extract_section(text, "LIVE")
    if not live_games:
        live_games = extract_section(text, "LIVE GAMES")
    upcoming_games = extract_section(text, "UPCOMING")
    outlook = extract_section(text, "OUTLOOK")
    why_it_matters = extract_section(text, "WHY IT MATTERS")
    story_angles = extract_section(text, "STORY ANGLES")
    watch_list = extract_section(text, "WATCH LIST")
    report_note = extract_section(text, "REPORT NOTE")

    final_lines = [line for line in clean_lines(final_scores) if not is_placeholder_line(line)]
    live_lines = [line for line in clean_lines(live_games) if not is_placeholder_line(line)]
    upcoming_lines = [line for line in clean_lines(upcoming_games) if not is_placeholder_line(line)]
    key_storyline_lines = clean_lines(key_storylines)
    key_data_lines = clean_lines(key_data_points)
    story_angle_lines = clean_lines(story_angles)
    watch_list_lines = clean_lines(watch_list)

    return {
        "league": league,
        "display_name": DISPLAY_NAMES.get(league, league),
        "headline": headline,
        "key_storylines": key_storyline_lines,
        "key_data_points": key_data_lines,
        "snapshot": snapshot,
        "final_scores": final_scores,
        "live_games": live_games,
        "upcoming_games": upcoming_games,
        "outlook": outlook,
        "why_it_matters": why_it_matters,
        "story_angles": story_angle_lines,
        "watch_list": watch_list_lines,
        "report_note": report_note,
        "final_count": len(final_lines),
        "live_count": len(live_lines),
        "upcoming_count": len(upcoming_lines),
    }


def normalize_snapshot_line(line: str) -> str:
    line = normalize_text(line)

    replacements = {
        "at the time of this report": "during this report window",
        "across the available reports": "across the included reports",
        "the focus shifts to": "The focus turns to",
        "report(s)": "reports",
        "game(s)": "games",
        "match(es)": "matches",
    }

    for bad, good in replacements.items():
        line = line.replace(bad, good)
        line = line.replace(bad.capitalize(), good)

    return line.strip()


def format_count_phrase(count: int, label: str) -> str:
    return f"{count} {label}"


def build_headline(parts: list[tuple[str, dict[str, Any]]]) -> str:
    leagues = [name for name, _ in parts if name not in {"FANTASY"}]
    display_leagues = [DISPLAY_NAMES.get(name, name) for name in leagues]

    if not leagues:
        return "No active league data was available during this report window."

    has_mlb = "MLB" in leagues
    has_nba = "NBA" in leagues
    has_nhl = "NHL" in leagues
    has_nfl = "NFL" in leagues
    has_nfl_draft = "NFL_DRAFT" in leagues

    if has_mlb and has_nba:
        return "Major League Baseball leads the daytime board while the NBA carries the night schedule into focus."
    if has_nfl and has_nfl_draft:
        return "The NFL board is being shaped by current league movement and draft-positioning pressure as roster-building storylines stay in focus."
    if has_mlb and has_nhl:
        return "Major League Baseball anchors the board while the NHL adds later movement to the schedule."
    if has_nba and has_nhl:
        return "The NBA and NHL carry the board with live action and later windows still ahead."
    if has_nfl_draft and len(leagues) == 1:
        return "NFL draft positioning, team needs, and roster pressure are driving the board in this report window."
    if len(display_leagues) == 1:
        return f"{display_leagues[0]} leads the board with current activity and schedule movement."

    return "Multiple leagues are active across the board with a mix of final results, live action, upcoming matchups, and draft signals."


def build_key_storylines(parts: list[tuple[str, dict[str, Any]]]) -> list[str]:
    lines: list[str] = []

    for league, data in parts:
        if league == "FANTASY":
            continue

        if league == "NFL_DRAFT":
            if data["key_data_points"]:
                for item in data["key_data_points"][:2]:
                    lines.append(f"- {item}")
                continue
            if data["snapshot"]:
                lines.append(f"- {normalize_snapshot_line(data['snapshot'])}")
                continue

        pieces: list[str] = []

        if data["final_count"] > 0:
            pieces.append(format_count_phrase(data["final_count"], "final"))
        if data["live_count"] > 0:
            pieces.append(format_count_phrase(data["live_count"], "live"))
        if data["upcoming_count"] > 0:
            pieces.append(format_count_phrase(data["upcoming_count"], "upcoming"))

        if not pieces:
            if data["snapshot"]:
                lines.append(f"- {data['display_name']} snapshot: {normalize_snapshot_line(data['snapshot'])}")
            continue

        if len(pieces) == 1:
            summary = pieces[0]
        elif len(pieces) == 2:
            summary = f"{pieces[0]} and {pieces[1]}"
        else:
            summary = f"{pieces[0]}, {pieces[1]}, and {pieces[2]}"

        lines.append(f"- {data['display_name']} shows {summary} on the board.")

    if any(name == "FANTASY" for name, _ in parts):
        lines.append("- The fantasy layer keeps a cross-league view on developing production and later opportunity.")

    return lines[:5]


def build_standard_league_block(league: str, data: dict[str, Any]) -> str:
    block: list[str] = [data["display_name"]]

    snapshot = normalize_snapshot_line(data["snapshot"]) if data["snapshot"] else ""
    if snapshot:
        block.extend(["SNAPSHOT", snapshot])

    final_lines = clean_lines(data["final_scores"])
    live_lines = clean_lines(data["live_games"])
    upcoming_lines = clean_lines(data["upcoming_games"])

    if league == "NBA":
        block.append("FINAL SCORES")
        if final_lines:
            block.extend(final_lines)
        else:
            block.append("No final scores were available during this report window.")

        block.append("LIVE")
        if live_lines:
            block.extend(live_lines)
        else:
            block.append("No live games were available during this report window.")

        block.append("UPCOMING")
        if upcoming_lines:
            block.extend(upcoming_lines)
        else:
            block.append("No upcoming games were available during this report window.")

        return "\n".join(block).strip()

    block.append("FINAL SCORES")
    if final_lines:
        block.extend(final_lines[:3])
    else:
        block.append("No final scores were available during this report window.")

    block.append("LIVE")
    if live_lines:
        block.extend(live_lines[:3])
    else:
        block.append("No live games were available during this report window.")

    block.append("UPCOMING")
    if upcoming_lines:
        block.extend(upcoming_lines[:3])
    else:
        block.append("No upcoming games were available during this report window.")

    return "\n".join(block).strip()


def build_nfl_draft_block(data: dict[str, Any]) -> str:
    block: list[str] = [data["display_name"]]

    snapshot = normalize_snapshot_line(data["snapshot"]) if data["snapshot"] else ""
    if snapshot:
        block.extend(["SNAPSHOT", snapshot])

    key_data_points = data["key_data_points"][:5]
    if key_data_points:
        block.append("KEY DATA POINTS")
        for item in key_data_points:
            block.append(f"- {item}")

    why_it_matters = normalize_snapshot_line(data["why_it_matters"]) if data["why_it_matters"] else ""
    if why_it_matters:
        block.extend(["WHY IT MATTERS", why_it_matters])

    story_angles = data["story_angles"][:4]
    if story_angles:
        block.append("STORY ANGLES")
        for item in story_angles:
            block.append(f"- {item}")

    watch_list = data["watch_list"][:6]
    if watch_list:
        block.append("WATCH LIST")
        for item in watch_list:
            block.append(f"- {item}")

    report_note = normalize_snapshot_line(data["report_note"]) if data["report_note"] else ""
    if report_note:
        block.extend(["REPORT NOTE", report_note])

    return "\n".join(block).strip()


def build_fantasy_block(data: dict[str, Any]) -> str:
    intro = (
        "A cross-league fantasy snapshot tracking where today's production is coming from, "
        "where it is still developing, and where opportunities remain on the board."
    )

    snapshot = normalize_snapshot_line(data["snapshot"]) if data["snapshot"] else ""
    if not snapshot:
        snapshot = "The focus turns to upcoming matchups as the fantasy slate builds."

    outlook = normalize_snapshot_line(data["outlook"]) if data["outlook"] else ""
    if not outlook:
        outlook = (
            "This report tracks game flow, results, and schedule positioning to support "
            "real-time fantasy awareness across leagues."
        )

    block = [
        "FANTASY",
        intro,
        "",
        "SNAPSHOT",
        snapshot,
        "",
        "OUTLOOK",
        outlook,
    ]

    return "\n".join(block).strip()


def build_report_sections(parts: list[tuple[str, dict[str, Any]]]) -> list[str]:
    sections: list[str] = []

    for league, data in parts:
        if league == "FANTASY":
            sections.append(build_fantasy_block(data))
        elif league == "NFL_DRAFT":
            sections.append(build_nfl_draft_block(data))
        else:
            sections.append(build_standard_league_block(league, data))

    return sections


def build_global_report() -> str:
    date_str = now_et().strftime("%Y-%m-%d")
    included_parts: list[tuple[str, dict[str, Any]]] = []

    for league, path in LEAGUE_FILES:
        text = read_file(path)
        if not text:
            continue

        summary = summarize_league(league, text)
        has_content = any(
            [
                summary["headline"],
                summary["snapshot"],
                summary["key_storylines"],
                summary["key_data_points"],
                summary["final_scores"],
                summary["live_games"],
                summary["upcoming_games"],
                summary["outlook"],
                summary["why_it_matters"],
                summary["story_angles"],
                summary["watch_list"],
                summary["report_note"],
            ]
        )

        if has_content:
            included_parts.append((league, summary))

    if not included_parts:
        empty_report = [
            f"GLOBAL SPORTS REPORT | {date_str}",
            "",
            "HEADLINE",
            "No league reports were available during this report window.",
            "",
            "SNAPSHOT",
            "This edition includes 0 reports.",
            "",
            DISCLAIMER,
        ]
        return "\n".join(empty_report).strip() + "\n"

    headline = build_headline(included_parts)
    key_storylines = build_key_storylines(included_parts)
    sections = build_report_sections(included_parts)

    output: list[str] = [
        f"GLOBAL SPORTS REPORT | {date_str}",
        "",
        "HEADLINE",
        headline,
        "",
        "KEY STORYLINES",
    ]

    if key_storylines:
        output.extend(key_storylines)
    else:
        output.append("- The board continues to develop across the included reports.")

    output.extend(
        [
            "",
            "SNAPSHOT",
            f"This edition includes {len(included_parts)} reports.",
            "",
        ]
    )

    for index, section in enumerate(sections):
        output.append(section)
        if index != len(sections) - 1:
            output.append("")

    output = [line for line in output if "automated summary" not in line.lower()]
    output.append("")
    output.append(DISCLAIMER)

    final_text = "\n".join(output)
    final_text = normalize_text(final_text)
    final_text = re.sub(r"\n{3,}", "\n\n", final_text).strip() + "\n"

    return final_text


def main() -> None:
    report = build_global_report()
    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()