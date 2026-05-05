from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import re

# =========================================================
# SETTINGS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
TIMEZONE = ZoneInfo("America/New_York")

GLOBAL_REPORT_FILE = BASE_DIR / "global_sports_report.txt"
OUTPUT_FILE = BASE_DIR / "substack_post.txt"

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, "
    "human sports journalism."
)

PREFERRED_SECTIONS = ["MLB", "NBA", "NHL", "NFL", "SOCCER", "FANTASY", "BETTING"]

# =========================================================
# HELPERS
# =========================================================

def read_global_report() -> str:
    if not GLOBAL_REPORT_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {GLOBAL_REPORT_FILE.name}. Run global_report.py first."
        )

    text = GLOBAL_REPORT_FILE.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("global_sports_report.txt is empty.")

    return text


def clean_text(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2014": "-",
        "\u2013": "-",
        "\xa0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.rstrip() for line in text.split("\n")]
    cleaned = "\n".join(lines)

    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")

    return cleaned.strip()


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def parse_sections(report_text: str) -> dict[str, list[str]]:
    paragraphs = split_paragraphs(report_text)

    sections: dict[str, list[str]] = {"INTRO": []}
    current_section = "INTRO"

    for para in paragraphs:
        stripped = para.strip()

        if (
            stripped.isupper()
            and len(stripped) <= 40
            and any(c.isalpha() for c in stripped)
            and "\n" not in stripped
        ):
            current_section = stripped
            sections.setdefault(current_section, [])
        else:
            sections.setdefault(current_section, []).append(stripped)

    return sections


def first_nonempty(items: list[str], default: str = "") -> str:
    for item in items:
        if item.strip():
            return item.strip()
    return default


def remove_disclaimer_from_text(text: str) -> str:
    lines = text.split("\n")
    filtered = [line for line in lines if DISCLAIMER.lower() not in line.lower()]
    return "\n".join(filtered).strip()


def normalize_sentence(text: str) -> str:
    return " ".join(text.split()).strip()


def sentence_case_heading(section_name: str) -> str:
    special = {
        "MLB": "MLB",
        "NBA": "NBA",
        "NHL": "NHL",
        "NFL": "NFL",
        "SOCCER": "Soccer",
        "FANTASY": "Fantasy",
        "BETTING": "Betting",
    }
    return special.get(section_name, section_name.title())


def section_has_real_content(items: list[str]) -> bool:
    return any(item.strip() for item in items)


def compact_text(text: str) -> str:
    return " ".join(text.split()).strip()


def strip_score_style(text: str) -> str:
    """
    Soft-clean report lines into headline-friendly fragments.
    """
    text = compact_text(text)
    text = remove_disclaimer_from_text(text)

    replacements = [
        (" got past ", " beat "),
        (" edged ", " beat "),
        (" cruised by ", " beat "),
        (" stayed in front of ", " beat "),
        (" outpaced ", " beat "),
        (" survived a back-and-forth with ", " beat "),
        (" did enough late to beat ", " beat "),
        (" rallied past ", " beat "),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    return text.rstrip(".")


def extract_team_names(text: str) -> list[str]:
    """
    Light team-name extraction from score/result lines.
    """
    text = strip_score_style(text)

    matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", text)

    blacklist = {
        "Across",
        "Major League Baseball",
        "The",
        "Today",
        "Daily",
        "Global Sports Report",
        "NBA",
        "MLB",
        "NHL",
        "NFL",
        "Soccer",
        "Fantasy",
        "Betting",
        "Live",
        "Upcoming",
        "Final Scores",
        "Snapshot",
        "What",
        "Watch",
    }

    cleaned = []
    for match in matches:
        match = match.strip()
        if match in blacklist:
            continue
        if len(match) < 3:
            continue
        cleaned.append(match)

    seen = set()
    result = []

    for item in cleaned:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def summarize_team_list(teams: list[str]) -> str:
    if not teams:
        return ""
    if len(teams) == 1:
        return teams[0]
    if len(teams) == 2:
        return f"{teams[0]} and {teams[1]}"
    return f"{teams[0]}, {teams[1]} and {teams[2]}"


def build_smart_headline(sections: dict[str, list[str]], today: str) -> str:
    """
    Builds a more journalistic Substack headline.

    Priority:
    1. Strong result-driven MLB/NBA/NHL/NFL/Soccer line
    2. Schedule/live-action line
    3. Broad fallback
    """
    preferred_sections = ["MLB", "NBA", "NHL", "NFL", "SOCCER"]

    section_firsts = []
    for league in preferred_sections:
        items = sections.get(league, [])
        if items:
            first_line = compact_text(remove_disclaimer_from_text(items[0]))
            if first_line:
                section_firsts.append((league, first_line))

    # 1. Result-style lead
    for league, line in section_firsts:
        lower = line.lower()

        result_signals = [
            " beat ",
            " beats ",
            " defeated ",
            " topped ",
            " won ",
            " final ",
            " finals ",
            " edged ",
            " cruised by ",
            " got past ",
            " stayed in front of ",
            " outpaced ",
            " did enough late to beat ",
            " blanked ",
            " rallied past ",
        ]

        if any(signal in lower for signal in result_signals):
            cleaned = strip_score_style(line)
            teams = extract_team_names(cleaned)

            if len(teams) >= 3 and league == "MLB":
                lead_teams = summarize_team_list(teams[:3])
                return f"{lead_teams} headline a busy MLB board"

            if len(cleaned) <= 80:
                return cleaned

            if len(teams) >= 2:
                return f"{teams[0]} and {teams[1]} lead the morning sports report"

            return f"Final results lead the {today} morning sports report"

    # 2. Watch/live-action lead
    for league, line in section_firsts:
        lower = line.lower()

        if any(signal in lower for signal in [
            "live",
            "upcoming",
            "today's slate",
            "todays slate",
            "first pitch",
            "tipoff",
            "kickoff",
            "faceoff",
            "still ahead",
        ]):
            if league == "MLB":
                return "Live action and first pitches lead today’s MLB briefing"
            if league == "NBA":
                return "Live action and tipoffs lead today’s NBA briefing"
            return "Live action and upcoming matchups lead the morning briefing"

    # 3. Multi-league fallback
    available = [league for league in preferred_sections if sections.get(league)]

    if len(available) >= 3:
        return "A cross-league morning briefing built for the sports news cycle"
    if len(available) == 2:
        return f"{available[0]} and {available[1]} lead today’s sports briefing"
    if len(available) == 1:
        return f"{available[0]} leads today’s Global Sports Report"

    # 4. Final fallback
    return f"Global Sports Report | {today}"


def build_deck(sections: dict[str, list[str]]) -> str:
    intro = first_nonempty(
        sections.get("INTRO", []),
        "A cross-league morning briefing built in a newsroom format."
    )

    intro = remove_disclaimer_from_text(intro)
    intro = normalize_sentence(intro)

    if not intro:
        intro = "A cross-league morning briefing built in a newsroom format."

    return (
        f"{intro}\n\n"
        "Built to help journalists, broadcasters, and analysts get quickly oriented "
        "before the news cycle fully turns."
    )


def build_key_results(sections: dict[str, list[str]]) -> list[str]:
    key_results: list[str] = []

    for league in PREFERRED_SECTIONS:
        items = sections.get(league, [])
        if not section_has_real_content(items):
            continue

        first_item = remove_disclaimer_from_text(first_nonempty(items))
        first_item = normalize_sentence(first_item)

        if first_item:
            key_results.append(first_item)

    return key_results[:5]


def build_what_to_watch(sections: dict[str, list[str]]) -> list[str]:
    watch_items: list[str] = []

    for league in PREFERRED_SECTIONS:
        for item in sections.get(league, []):
            cleaned = normalize_sentence(remove_disclaimer_from_text(item))
            lower = cleaned.lower()

            if any(
                phrase in lower for phrase in [
                    "live",
                    "upcoming",
                    "still ahead",
                    "still to go",
                    "tonight",
                    "later today",
                    "today's slate",
                    "todays slate",
                    "first pitch",
                    "tipoff",
                    "kickoff",
                    "faceoff",
                ]
            ):
                watch_items.append(cleaned)
                break

    return watch_items[:3]


def build_section_block(section_name: str, paragraphs: list[str]) -> str:
    label = sentence_case_heading(section_name)

    cleaned_paragraphs = []
    for paragraph in paragraphs:
        paragraph = remove_disclaimer_from_text(paragraph)
        paragraph = normalize_sentence(paragraph)
        if paragraph:
            cleaned_paragraphs.append(paragraph)

    if not cleaned_paragraphs:
        return ""

    body = f"## {label}\n\n"
    for paragraph in cleaned_paragraphs:
        body += f"{paragraph}\n\n"

    return body.strip()


# =========================================================
# BUILDER
# =========================================================

def build_substack_post(report_text: str) -> str:
    today = datetime.now(TIMEZONE).strftime("%B %d, %Y")

    cleaned = clean_text(report_text)
    cleaned = remove_disclaimer_from_text(cleaned)
    sections = parse_sections(cleaned)

    headline = build_smart_headline(sections, today)
    deck = build_deck(sections)
    key_results = build_key_results(sections)
    what_to_watch = build_what_to_watch(sections)

    parts: list[str] = []

    # BRAND + HEADLINE
    parts.append("Global Sports Report")
    parts.append(f"# {headline}")

    # DECK
    parts.append(deck)

    # KEY RESULTS
    if key_results:
        key_block = "## Key Results\n\n"
        for item in key_results:
            key_block += f"- {item}\n"
        parts.append(key_block.strip())

    # WHAT TO WATCH
    if what_to_watch:
        watch_block = "## What to Watch\n\n"
        for item in what_to_watch:
            watch_block += f"- {item}\n"
        parts.append(watch_block.strip())

    # LEAGUE SECTIONS
    for section in PREFERRED_SECTIONS:
        block = build_section_block(section, sections.get(section, []))
        if block:
            parts.append(block)

    # FALLBACK
    league_blocks_present = any(
        section_has_real_content(sections.get(section, []))
        for section in PREFERRED_SECTIONS
    )

    if not league_blocks_present:
        body = remove_disclaimer_from_text(cleaned)
        if body:
            parts.append("## Full Report\n\n" + body)

    # CLOSING NOTE
    parts.append(
        "## Closing Note\n\n"
        f"{DISCLAIMER}"
    )

    return "\n\n".join(part.strip() for part in parts if part.strip()).strip()


# =========================================================
# MAIN
# =========================================================

def main() -> None:
    try:
        report_text = read_global_report()
        substack_post = build_substack_post(report_text)
        OUTPUT_FILE.write_text(substack_post + "\n", encoding="utf-8")

        print(f"Saved: {OUTPUT_FILE.name}")

    except Exception as e:
        print(f"build_substack.py failed: {e}")


if __name__ == "__main__":
    main()