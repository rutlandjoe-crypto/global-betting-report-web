from pathlib import Path
from voice_rules import validate_report_voice

BASE_DIR = Path(__file__).resolve().parent
REPORT_FILE = BASE_DIR / "global_sports_report.txt"

LEGACY_FOOTER_MARKERS = [
    "This report is an automated summary of game data and is intended to support, not replace, human sports journalism.",
    "This report is an automated summary intended to support, not replace, human sports journalism.",
    "Generated:",
    "Follow on X:",
]

NEW_FOOTER_MARKERS = [
    "This report is an automated summary of game data, designed to support—not replace—human sports journalism.",
    "Follow @GlobalSportsRep",
]


def load_report_text() -> str:
    if not REPORT_FILE.exists():
        raise FileNotFoundError(f"Report file not found: {REPORT_FILE}")
    return REPORT_FILE.read_text(encoding="utf-8")


def count_occurrences(text: str, phrase: str) -> int:
    return text.count(phrase)


def check_duplicate_footer_blocks(text: str) -> list[str]:
    warnings = []

    legacy_hits = sum(1 for marker in LEGACY_FOOTER_MARKERS if marker in text)
    new_hits = sum(1 for marker in NEW_FOOTER_MARKERS if marker in text)

    if legacy_hits > 0 and new_hits > 0:
        warnings.append("Legacy footer text and new standardized footer text are both present.")

    if text.count("---") >= 2:
        warnings.append("Multiple horizontal rule separators ('---') detected. Footer may be duplicated.")

    return warnings


def check_disclaimer_count(text: str) -> list[str]:
    warnings = []

    disclaimer_variants = [
        "This report is an automated summary of game data and is intended to support, not replace, human sports journalism.",
        "This report is an automated summary intended to support, not replace, human sports journalism.",
        "This report is an automated summary of game data, designed to support—not replace—human sports journalism.",
    ]

    total = sum(count_occurrences(text, phrase) for phrase in disclaimer_variants)

    # Source report should NOT contain disclaimer/footer language anymore.
    if total > 0:
        warnings.append("Disclaimer/footer language detected in source report. Keep it in distribution only.")

    return warnings


def check_generated_timestamp(text: str) -> list[str]:
    warnings = []

    if "Generated:" in text:
        warnings.append("Raw 'Generated:' timestamp found in report body. Move timestamp to platform footer only.")

    return warnings


def check_follow_lines(text: str) -> list[str]:
    warnings = []

    follow_variants = [
        "Follow on X:",
        "Follow Global Sports Report on X:",
        "Follow @GlobalSportsRep",
    ]

    hits = sum(count_occurrences(text, phrase) for phrase in follow_variants)

    if hits > 0:
        warnings.append("Follow/CTA line detected in source report. Keep CTA language in distribution only.")

    return warnings


def check_structure(text: str) -> list[str]:
    warnings = []

    required_sections = [
        "HEADLINE",
        "KEY STORYLINES",
        "SNAPSHOT",
    ]

    for section in required_sections:
        if section not in text:
            warnings.append(f"Missing expected section: {section}")

    return warnings


def run_checks(text: str) -> list[str]:
    warnings = []

    warnings.extend(validate_report_voice(text))
    warnings.extend(check_duplicate_footer_blocks(text))
    warnings.extend(check_disclaimer_count(text))
    warnings.extend(check_generated_timestamp(text))
    warnings.extend(check_follow_lines(text))
    warnings.extend(check_structure(text))

    return warnings


def main():
    try:
        report_text = load_report_text()
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}\n")
        return

    warnings = run_checks(report_text)

    print("\n===== REPORT STYLE CHECK =====\n")
    print(f"File: {REPORT_FILE.name}")
    print(f"Characters: {len(report_text)}")
    print()

    if not warnings:
        print("PASS: Report looks clean and on-brand.")
    else:
        print(f"FAIL: {len(warnings)} issue(s) found.\n")
        for i, warning in enumerate(warnings, start=1):
            print(f"{i}. {warning}")

    print("\n===== END STYLE CHECK =====\n")


if __name__ == "__main__":
    main()