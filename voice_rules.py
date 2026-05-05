# voice_rules.py
"""
Global Sports Report voice and language rules.

This file should contain definitions only.
Do not put preview code, print statements, or test report-building code here.
"""

from typing import List


BRAND_NAME = "Global Sports Report"
X_HANDLE = "@GlobalSportsRep"

DISCLAIMER_LONG = (
    "This report is an automated summary of game data, designed to support—not replace—"
    "human sports journalism."
)

DISCLAIMER_SHORT = (
    "Automated game data summary built to support—not replace—human sports journalism."
)


SECTION_LINES = {
    "headline_busy_day": "Today’s schedule in the sports world is looking pretty busy.",
    "headline_results_day": "Results are beginning to define the shape of the day across the sports calendar.",
    "headline_upcoming_day": "Upcoming matchups dominate the current report window across multiple leagues.",
    "headline_light_day": "The schedule is lighter today, but key matchups still shape the day.",

    "snapshot_single": "This edition includes 1 report.",
    "snapshot_default": "This edition includes {n} reports.",

    "injury_none": "No major injury updates were available during this report window.",
    "nfl_none": "No games available for this report window.",
    "live_none": "No live games were available during this report window.",
    "final_none": "No final scores were available during this report window.",

    "outlook_fantasy": (
        "This report tracks game flow, results, and schedule positioning to support real-time "
        "fantasy awareness across leagues."
    ),
    "outlook_general": (
        "This report tracks results, live developments, and upcoming matchups across the sports calendar."
    ),
    "outlook_journalist": (
        "This report is built to help journalists, editors, and sports audiences quickly scan the shape of the day."
    ),
}


LEAGUE_INTROS = {
    "MLB": "Major League Baseball brings a full view of today’s schedule.",
    "NBA": "The NBA schedule spotlights tonight’s key matchups across the league.",
    "NHL": "The NHL board features a busy night of hockey across the league.",
    "NFL": "NFL coverage reflects the current report window and available schedule data.",
    "SOCCER": "Soccer coverage tracks matches across the available competitions on the schedule.",
    "FANTASY": "A cross-league fantasy snapshot tracks where production is developing and where opportunities remain.",
}


PHRASE_REPLACEMENTS = {
    "The day’s board is still taking shape across the available reports.":
        "Today’s schedule in the sports world is looking pretty busy.",

    "Across the available reports, the board is still taking shape.":
        "Today’s schedule in the sports world is looking pretty busy.",

    "The slate is still taking shape.":
        "Today’s schedule is still coming into focus.",

    "The board was anchored by completed results.":
        "The day’s action was defined by completed results across the schedule.",

    "The slate currently shows":
        "The schedule currently shows",

    "No games were available at the time of this report.":
        "No games were available during this report window.",

    "No final scores were available at the time of this report.":
        "No final scores were available during this report window.",

    "No live games were available at the time of this report.":
        "No live games were available during this report window.",

    "No major injury updates were available at the time of this report.":
        "No major injury updates were available during this report window.",

    "This edition combines":
        "This edition includes",

    "report(s).":
        "reports.",

    "game(s).":
        "games.",
}


DISCOURAGED_PHRASES = [
    "board taking shape",
    "across the available reports",
    "at the time of this report",
    "features completed games, live action, and upcoming",
    "the slate currently shows",
    "did enough late",
    "stayed in front of",
    "got past",
    "survived a back-and-forth finish",
    "the focus shifts to",
]


RESULT_VERBS = {
    "close_win": ["edged", "held off", "narrowly beat"],
    "comfortable_win": ["beat", "handled", "pulled away from"],
    "blowout_win": ["routed", "rolled past", "cruised past"],
    "shutout_win": ["blanked", "shut out"],
    "comeback_win": ["rallied past", "came back to beat"],
}


def get_key_storyline_busy() -> str:
    return "• Today’s schedule in the sports world is looking pretty busy."


def get_key_storyline_results() -> str:
    return "• Results are beginning to define the shape of the day across the sports calendar."


def get_key_storyline_upcoming() -> str:
    return "• Upcoming matchups dominate the current report window across multiple leagues."


def get_snapshot_line(report_count: int) -> str:
    if report_count == 1:
        return SECTION_LINES["snapshot_single"]
    return SECTION_LINES["snapshot_default"].format(n=report_count)


def get_outlook(report_type: str = "general") -> str:
    report_type = (report_type or "").lower()

    if report_type == "fantasy":
        return SECTION_LINES["outlook_fantasy"]
    if report_type == "journalist":
        return SECTION_LINES["outlook_journalist"]
    return SECTION_LINES["outlook_general"]


def get_league_intro(league: str) -> str:
    return LEAGUE_INTROS.get((league or "").upper(), "")


def clean_phrase(text: str) -> str:
    if not text:
        return text

    cleaned = text
    for old, new in PHRASE_REPLACEMENTS.items():
        cleaned = cleaned.replace(old, new)
    return cleaned


def normalize_pluralization(text: str) -> str:
    if not text:
        return text

    replacements = {
        "1 report(s)": "1 report",
        "1 game(s)": "1 game",
        "1 final game(s)": "1 final game",
        "1 live game(s)": "1 live game",
        "1 upcoming game(s)": "1 upcoming game",
        "0 report(s)": "0 reports",
        "0 game(s)": "0 games",
    }

    normalized = text
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    return normalized


def clean_report_text(text: str) -> str:
    if not text:
        return text

    text = clean_phrase(text)
    text = normalize_pluralization(text)

    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text.strip()


def choose_result_verb(margin: int, shutout: bool = False, comeback: bool = False) -> str:
    if comeback:
        return RESULT_VERBS["comeback_win"][0]
    if shutout:
        return RESULT_VERBS["shutout_win"][0]
    if margin <= 2:
        return RESULT_VERBS["close_win"][0]
    if margin >= 7:
        return RESULT_VERBS["blowout_win"][0]
    return RESULT_VERBS["comfortable_win"][0]


def make_result_sentence(
    winner: str,
    loser: str,
    winner_score: int,
    loser_score: int,
    shutout: bool = False,
    comeback: bool = False,
) -> str:
    margin = abs(winner_score - loser_score)
    verb = choose_result_verb(margin=margin, shutout=shutout, comeback=comeback)
    return f"{winner} {verb} {loser}, {winner_score}-{loser_score}."


def find_discouraged_phrases(text: str) -> List[str]:
    found = []
    lowered = (text or "").lower()

    for phrase in DISCOURAGED_PHRASES:
        if phrase.lower() in lowered:
            found.append(phrase)

    return found


def validate_report_voice(text: str) -> List[str]:
    warnings = []

    if not text:
        warnings.append("Report is empty.")
        return warnings

    bad_phrases = find_discouraged_phrases(text)
    for phrase in bad_phrases:
        warnings.append(f"Discouraged phrase found: '{phrase}'")

    if "report(s)" in text:
        warnings.append("Awkward pluralization found: 'report(s)'")

    if "game(s)" in text:
        warnings.append("Awkward pluralization found: 'game(s)'")

    if "at the time of this report" in text.lower():
        warnings.append("Use 'during this report window' instead of 'at the time of this report'")

    return warnings