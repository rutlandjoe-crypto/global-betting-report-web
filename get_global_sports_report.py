from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================================================
# PATH / TIME SETUP
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
TIMEZONE = ZoneInfo("America/New_York")
OUTPUT_FILE = BASE_DIR / "global_sports_report.txt"

REPORT_FILES = [
    ("MLB", BASE_DIR / "mlb_report.txt"),
    ("NBA", BASE_DIR / "nba_report.txt"),
    ("NHL", BASE_DIR / "nhl_report.txt"),
    ("SOCCER", BASE_DIR / "soccer_report.txt"),
    ("FANTASY", BASE_DIR / "fantasy_report.txt"),
    # ("BETTING", BASE_DIR / "betting_odds_report.txt"),
]

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, "
    "human sports journalism."
)

FALLBACK_TEXT = "No report content was available at the time of this update."

# =========================================================
# OPTIONAL GENERATOR IMPORTS
# =========================================================

try:
    from get_mlb_report import generate_mlb_report
except Exception:
    generate_mlb_report = None

try:
    from get_nba_report import generate_nba_report
except Exception:
    generate_nba_report = None

try:
    from get_nhl_report import generate_nhl_report
except Exception:
    generate_nhl_report = None

try:
    from get_soccer_report import generate_soccer_report
except Exception:
    generate_soccer_report = None

try:
    from get_fantasy_report import generate_fantasy_report
except Exception:
    generate_fantasy_report = None

try:
    from get_betting_odds_report import generate_betting_odds_report
except Exception:
    generate_betting_odds_report = None

# =========================================================
# OPTIONAL VOICE POLISH
# =========================================================

try:
    from voice_rules import polish_report_text
except Exception:
    polish_report_text = None

# =========================================================
# TIME HELPERS
# =========================================================

def now_et() -> datetime:
    return datetime.now(TIMEZONE)


def report_date_string() -> str:
    return now_et().strftime("%Y-%m-%d")


def report_timestamp_string() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M %p %Z")


# =========================================================
# FILE HELPERS
# =========================================================

def safe_read_text(path: Path) -> str:
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def fix_encoding(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€": '"',
        "â€“": "-",
        "â€”": "—",
        "\u00a0": " ",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return text


def fix_spacing_issues(text: str) -> str:
    if not text:
        return ""

    # Normalize line-by-line so section structure stays intact
    fixed_lines = []

    for line in str(text).splitlines():
        working = line.rstrip()

        if not working.strip():
            fixed_lines.append("")
            continue

        # Collapse repeated whitespace
        working = re.sub(r"[ \t]+", " ", working)

        # Fix missing space after punctuation before a letter
        working = re.sub(r"([.,;:!?])([A-Za-z])", r"\1 \2", working)

        # Fix collapsed lowercase-uppercase words: "TheNBAboard" -> "The NBAboard"
        working = re.sub(r"([a-z])([A-Z])", r"\1 \2", working)

        # Fix number-letter boundaries when words get jammed
        working = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", working)
        working = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", working)

        # Keep record formats like 43-39 intact while cleaning accidental spacing around dashes
        working = re.sub(r"\s*-\s*", " - ", working)
        working = re.sub(r"(\d) - (\d)", r"\1-\2", working)

        # Clean spaces before punctuation
        working = re.sub(r"\s+([.,;:!?])", r"\1", working)

        # Bullet consistency
        if working.startswith("-") and not working.startswith("- "):
            working = "- " + working[1:].lstrip()

        fixed_lines.append(working)

    return "\n".join(fixed_lines).strip()


def cleanup_report_text(text: str) -> str:
    if not text:
        return ""

    text = fix_encoding(text)
    text = fix_spacing_issues(text)

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


def strip_existing_header(text: str, sport_name: str) -> str:
    if not text:
        return ""

    lines = text.splitlines()
    filtered = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Remove first title line like:
        # MLB REPORT | 2026-04-06
        # Fantasy Report | 2026-04-06
        if i == 0 and ("REPORT |" in stripped or "Report |" in stripped):
            continue

        # Remove repeated generated lines
        if stripped.startswith("Generated:"):
            continue

        # Remove repeated disclaimer lines
        if stripped == DISCLAIMER:
            continue

        filtered.append(line)

    while filtered and not filtered[0].strip():
        filtered.pop(0)

    return "\n".join(filtered).strip()


def format_section(title: str, body: str) -> str:
    body = cleanup_report_text(body)

    if not body.strip():
        body = FALLBACK_TEXT

    return f"{title}\n\n{body}"


# =========================================================
# GENERATORS
# =========================================================

def run_generator(label: str, func) -> None:
    if func is None:
        print(f"[WARN] {label}: generator unavailable")
        return

    try:
        try:
            func(write_file=True)
        except TypeError:
            func()
        print(f"[OK] {label} generated")
    except Exception as exc:
        print(f"[ERROR] {label}: {exc}")


def build_reports() -> None:
    run_generator("MLB", generate_mlb_report)
    run_generator("NBA", generate_nba_report)
    run_generator("NHL", generate_nhl_report)
    run_generator("SOCCER", generate_soccer_report)
    run_generator("FANTASY", generate_fantasy_report)
    run_generator("BETTING", generate_betting_odds_report)


# =========================================================
# SECTION BUILDING
# =========================================================

def get_intro_text() -> str:
    return (
        "A cross-league briefing built in a newsroom style to support journalists, "
        "broadcasters, and analysts."
    )


def get_section_body(name: str, path: Path) -> str:
    raw = safe_read_text(path)

    if not raw:
        return FALLBACK_TEXT

    cleaned = cleanup_report_text(raw)
    stripped = strip_existing_header(cleaned, name)
    stripped = cleanup_report_text(stripped)

    if not stripped:
        return FALLBACK_TEXT

    return stripped


def build_sections() -> list[str]:
    sections = []

    for name, path in REPORT_FILES:
        body = get_section_body(name, path)
        sections.append(format_section(name, body))

    return sections


# =========================================================
# FINAL BUILD
# =========================================================

def build_default_report() -> str:
    header = f"GLOBAL SPORTS REPORT | {report_date_string()}"
    generated = f"Generated: {report_timestamp_string()}"

    parts = [
        header,
        generated,
        "",
        get_intro_text(),
    ]

    for section in build_sections():
        parts.extend(["", section])

    parts.extend([
        "",
        DISCLAIMER,
    ])

    return cleanup_report_text("\n".join(parts)) + "\n"


def apply_voice(report: str) -> str:
    if polish_report_text is None:
        return report

    try:
        polished = polish_report_text(report)
        return cleanup_report_text(polished) + "\n"
    except Exception as exc:
        print(f"[WARN] voice polish failed: {exc}")
        return report


# =========================================================
# MAIN
# =========================================================

def generate_global_report() -> str:
    build_reports()

    base = build_default_report()
    final = apply_voice(base)

    OUTPUT_FILE.write_text(final, encoding="utf-8")

    print(f"[OK] Global report written to: {OUTPUT_FILE}")
    return final


def generate_global_sports_report() -> str:
    return generate_global_report()


if __name__ == "__main__":
    print(generate_global_report())