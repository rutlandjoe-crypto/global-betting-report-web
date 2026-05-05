from __future__ import annotations

import re
from pathlib import Path

from mlb_advanced_utils import (
    today_et,
    log,
    get_mlb_games_for_today,
    extract_pitcher_watch,
    extract_matchup_flags,
    build_board_context,
    build_advanced_fallback_report,
)

OUTPUT_FILE = Path("mlb_advanced_report.txt")
REPORT_LABEL = "MLB ADVANCED REPORT"
DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, human sports journalism."
)


def fix_spacing(text: str) -> str:
    if not text:
        return ""

    text = str(text)

    # Fix common encoding junk
    replacements = {
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€“": "-",
        "â€”": "—",
        "\u00a0": " ",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Add missing spaces after punctuation
    text = re.sub(r"([.,;:!?])([A-Za-z])", r"\1 \2", text)

    # Split jammed lowercase-uppercase words
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    # Split number-letter boundaries when jammed
    text = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", text)

    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)

    # Preserve record formats like 10-4
    text = re.sub(r"\s*-\s*", " - ", text)
    text = re.sub(r"(\d) - (\d)", r"\1-\2", text)

    return text.strip()


def clean_report_text(text: str) -> str:
    if not text:
        return ""

    lines = [fix_spacing(line.rstrip()) if line.strip() else "" for line in text.splitlines()]

    cleaned: list[str] = []
    blank_count = 0

    for line in lines:
        if line.strip():
            cleaned.append(line)
            blank_count = 0
        else:
            blank_count += 1
            if blank_count <= 1:
                cleaned.append("")

    return "\n".join(cleaned).strip() + "\n"


def build_report() -> str:
    games = get_mlb_games_for_today()

    pitcher_watch = extract_pitcher_watch(games, limit=3)
    matchup_flags = extract_matchup_flags(games, limit=3)
    board_context = fix_spacing(build_board_context(games))

    lines: list[str] = [
        f"{REPORT_LABEL} | {today_et()}",
        "",
        "STATCAST WATCH",
    ]

    if pitcher_watch:
        for line in pitcher_watch:
            lines.append(f"- {fix_spacing(line)}")
    else:
        lines.append("- No Statcast watch items were available in this report window.")

    lines.extend([
        "",
        "MATCHUP FLAGS",
    ])

    if matchup_flags:
        for line in matchup_flags:
            lines.append(f"- {fix_spacing(line)}")
    else:
        lines.append("- No matchup flags were available in this report window.")

    lines.extend([
        "",
        "BOARD CONTEXT",
        f"- {board_context or 'No board context was available in this report window.'}",
        "",
        DISCLAIMER,
    ])

    return clean_report_text("\n".join(lines))


def save_report(text: str, output_path: Path = OUTPUT_FILE) -> None:
    output_path.write_text(clean_report_text(text), encoding="utf-8")


def main() -> None:
    try:
        report = build_report()
        print(report)
        save_report(report)
        log(f"Saved: {OUTPUT_FILE}")

    except Exception as exc:
        error_report = build_advanced_fallback_report(
            disclaimer=DISCLAIMER,
            error_message=str(exc),
        )
        error_report = clean_report_text(error_report)
        print(error_report)

        try:
            save_report(error_report)
            log(f"Saved fallback report: {OUTPUT_FILE}")
        except Exception as save_exc:
            log(f"Failed to save fallback MLB advanced report: {save_exc}")
            raise


if __name__ == "__main__":
    main()