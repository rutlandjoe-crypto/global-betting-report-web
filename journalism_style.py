from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = "America/Denver"


def now_local():
    return datetime.now(ZoneInfo(TIMEZONE))


def build_report_header(title, report_date):
    return f"{title} | {report_date}"


def format_generated_stamp():
    return f"Generated: {now_local().strftime('%Y-%m-%d %H:%M:%S %Z')}"


def classify_margin(margin):
    if margin <= 3:
        return "tight"
    if margin >= 14:
        return "lopsided"
    return "solid"


def result_verb(margin):
    kind = classify_margin(margin)
    if kind == "tight":
        return "edged"
    if kind == "lopsided":
        return "handled"
    return "beat"


def build_headline(sport, total_finals, total_live, total_upcoming):
    total = total_finals + total_live + total_upcoming

    if total_live:
        return f"Live action and completed results shaped the {sport} landscape."
    if total >= 10:
        return f"A full slate of {sport} action unfolded across the schedule."
    if total > 0:
        return f"A focused day of {sport} coverage took shape across the board."
    return f"A quieter moment defined the {sport} calendar."


def build_intro(sport, total_finals, total_live, total_upcoming):
    if total_live:
        return (
            f"Around {sport}, the slate featured completed results and live action still unfolding, "
            f"with key stretches continuing to shape the day."
        )

    if total_finals and total_upcoming:
        return (
            f"Around {sport}, completed results shared the spotlight with the next wave of matchups, "
            f"offering a broad look across the schedule."
        )

    if total_finals:
        return (
            f"Around {sport}, the day was defined by finished results, timely execution, and the margins "
            f"that separated clubs and teams."
        )

    if total_upcoming:
        return (
            f"Around {sport}, attention turns to the upcoming slate as teams prepare for their next test."
        )

    return (
        f"Around {sport}, the calendar remains in motion, with attention shifting between competition, "
        f"preparation, and the broader rhythm of the season."
    )


def build_global_snapshot_label():
    return "GLOBAL SNAPSHOT"


def build_top_games_label():
    return "TOP MATCHES"


def build_disclaimer(kind="game"):
    if kind == "match":
        return (
            "This report is an automated summary of match data and is intended to support, "
            "not replace, human sports journalism."
        )
    return (
        "This report is an automated summary of game data and is intended to support, "
        "not replace, human sports journalism."
    )