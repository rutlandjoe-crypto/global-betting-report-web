from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import html
import os
import re

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

TIMEZONE = ZoneInfo("America/New_York")

REPORT_FILE = BASE_DIR / "global_sports_report.txt"
SUBSTACK_TXT = BASE_DIR / "substack_post.txt"
SUBSTACK_HTML = BASE_DIR / "substack_post.html"
LOG_FILE = BASE_DIR / "substack_log.txt"

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, "
    "human sports journalism."
)

SECTION_HEADERS = {
    "HEADLINE",
    "KEY STORYLINES",
    "KEY RESULTS",
    "SNAPSHOT",
    "FINAL SCORES",
    "LIVE",
    "LIVE GAMES",
    "UPCOMING",
    "INJURY WATCH",
    "OUTLOOK",
    "NBA",
    "MLB",
    "NHL",
    "NFL",
    "SOCCER",
    "FANTASY",
}


def log(message: str) -> None:
    timestamp = datetime.now(TIMEZONE).strftime("%Y-%m-%d %I:%M:%S %p ET")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_report() -> str:
    if not REPORT_FILE.exists():
        raise FileNotFoundError(f"Missing report file: {REPORT_FILE}")

    text = REPORT_FILE.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("global_sports_report.txt is empty.")

    return text


def clean_report(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned = []
    seen_disclaimer = False
    blank_streak = 0

    for line in lines:
        stripped = line.strip()

        if stripped == DISCLAIMER:
            if seen_disclaimer:
                continue
            seen_disclaimer = True

        if not stripped:
            blank_streak += 1
            if blank_streak <= 1 and cleaned:
                cleaned.append("")
            continue

        blank_streak = 0
        cleaned.append(stripped)

    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    return "\n".join(cleaned).strip()


def extract_report_date(report_text: str):
    match = re.search(r"GLOBAL SPORTS REPORT\s*\|\s*(\d{4}-\d{2}-\d{2})", report_text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


def parse_sections(report_text: str):
    lines = [line.strip() for line in report_text.splitlines()]
    sections = []
    current_header = None
    current_lines = []

    for line in lines:
        if not line:
            if current_header is not None:
                current_lines.append("")
            continue

        upper = line.upper()

        if upper.startswith("GLOBAL SPORTS REPORT |"):
            continue

        if upper in SECTION_HEADERS:
            if current_header is not None:
                sections.append((current_header, current_lines))
            current_header = upper
            current_lines = []
        else:
            if current_header is None:
                current_header = "INTRO"
            current_lines.append(line)

    if current_header is not None:
        sections.append((current_header, current_lines))

    return sections


def build_title(report_date: str | None) -> str:
    if report_date:
        dt = datetime.strptime(report_date, "%Y-%m-%d")
        pretty = dt.strftime("%B %d, %Y")
    else:
        pretty = datetime.now(TIMEZONE).strftime("%B %d, %Y")

    return f"Global Sports Report — {pretty}"


def format_section_text(header: str, lines: list[str]) -> str:
    filtered = [line for line in lines if line.strip() and line.strip() != DISCLAIMER]
    if not filtered:
        return ""

    chunks = []

    if header not in {"INTRO"}:
        chunks.append(header)

    for line in filtered:
        chunks.append(line)

    return "\n".join(chunks).strip()


def build_plaintext_post(report_text: str) -> str:
    report_date = extract_report_date(report_text)
    title = build_title(report_date)
    sections = parse_sections(report_text)

    parts = [
        title,
        "",
        "A journalist-first daily briefing built to surface the most relevant cross-league developments, live boards, and upcoming action.",
        "",
    ]

    for header, lines in sections:
        block = format_section_text(header, lines)
        if not block:
            continue
        parts.append(block)
        parts.append("")

    parts.append(DISCLAIMER)

    return "\n".join(parts).strip() + "\n"


def html_escape_preserve_em_dash(text: str) -> str:
    return html.escape(text, quote=False)


def lines_to_html(lines: list[str]) -> str:
    filtered = [line.strip() for line in lines if line.strip() and line.strip() != DISCLAIMER]
    if not filtered:
        return ""

    bullet_lines = []
    regular_lines = []

    for line in filtered:
        if line.startswith("•"):
            bullet_lines.append(line.lstrip("•").strip())
        else:
            regular_lines.append(line)

    html_parts = []

    for line in regular_lines:
        html_parts.append(f"<p>{html_escape_preserve_em_dash(line)}</p>")

    if bullet_lines:
        html_parts.append("<ul>")
        for item in bullet_lines:
            html_parts.append(f"  <li>{html_escape_preserve_em_dash(item)}</li>")
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def build_html_post(report_text: str) -> str:
    report_date = extract_report_date(report_text)
    title = build_title(report_date)
    sections = parse_sections(report_text)

    html_parts = [
        "<div>",
        f"  <h1>{html_escape_preserve_em_dash(title)}</h1>",
        "  <p><em>A journalist-first daily briefing built to surface the most relevant cross-league developments, live boards, and upcoming action.</em></p>",
    ]

    for header, lines in sections:
        block_html = lines_to_html(lines)
        if not block_html:
            continue

        if header != "INTRO":
            html_parts.append(f"  <h2>{html_escape_preserve_em_dash(header.title())}</h2>")

        for line in block_html.splitlines():
            html_parts.append(f"  {line}")

    html_parts.append(f"  <p><em>{html_escape_preserve_em_dash(DISCLAIMER)}</em></p>")
    html_parts.append("</div>")

    return "\n".join(html_parts) + "\n"


def main() -> None:
    try:
        raw = read_report()
        cleaned = clean_report(raw)

        plaintext = build_plaintext_post(cleaned)
        html_post = build_html_post(cleaned)

        SUBSTACK_TXT.write_text(plaintext, encoding="utf-8")
        log(f"Saved: {SUBSTACK_TXT.name}")

        SUBSTACK_HTML.write_text(html_post, encoding="utf-8")
        log(f"Saved: {SUBSTACK_HTML.name}")

        log("Substack post build complete.")

    except Exception as e:
        log(f"FATAL ERROR: {e}")


if __name__ == "__main__":
    main()