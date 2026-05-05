import random


def pick(options):
    return random.choice(options) if options else ""


# ============================================================
# PRODUCT LANGUAGE SETTINGS
# ============================================================

DEFAULT_SECTION_ORDER = [
    "FINAL SCORES",
    "LIVE",
    "UPCOMING",
    "KEY DEVELOPMENTS",
]

DEFAULT_DISCLAIMER = (
    "This report is an automated summary of game data and is intended to support, "
    "not replace, human sports journalism."
)


# ============================================================
# LEAGUE OPENERS
# Keep these tight, factual, and newsroom-friendly.
# Variation is okay, but tone must stay unified.
# ============================================================

LEAGUE_OPENERS = {
    "NBA": [
        "Around the NBA, the night featured a mix of offensive bursts, momentum swings, and results that took shape across the slate.",
        "Around the NBA, the slate delivered a blend of scoring runs, competitive stretches, and several games that turned decisively.",
    ],
    "MLB": [
        "Around the league, the day featured timely hitting, steady pitching, and several games that tightened late.",
        "Across Major League Baseball, the slate brought a mix of clean pitching, opportunistic offense, and games that shifted late.",
    ],
    "NFL": [
        "Around the NFL, the action centered on execution, field position, and momentum swings that shaped the results.",
        "Across the NFL, the slate featured timely drives, defensive stops, and outcomes that took shape over key stretches.",
    ],
    "NHL": [
        "Around the NHL, the night featured tight checking, timely scoring, and several games decided in key stretches.",
        "Across the NHL, the slate delivered a mix of disciplined defensive play, opportunistic offense, and competitive finishes.",
    ],
    "WNBA": [
        "Around the WNBA, the night featured scoring runs, defensive adjustments, and results that developed across key stretches.",
        "Across the WNBA, the slate brought efficient offense, timely stops, and several games that turned with momentum.",
    ],
    "NCAAF": [
        "Around college football, the action centered on execution, field position, and momentum swings that shaped the day.",
        "Across college football, the slate featured timely scoring drives, defensive responses, and results shaped by key stretches.",
    ],
    "NCAAB": [
        "Around college basketball, the slate brought scoring runs, defensive adjustments, and several games that shifted with momentum.",
        "Across the college game, the night featured disciplined stretches, late pushes, and a handful of decisive finishes.",
    ],
    "SOCCER": [
        "Around the pitch, the slate featured disciplined defending, timely finishing, and several matches that turned on key stretches.",
        "Across the soccer schedule, the action delivered compact defending, quality finishing, and competitive results.",
    ],
    "EPL": [
        "Around the Premier League, the slate featured disciplined defending, timely finishing, and several matches that turned on key stretches.",
        "Across the Premier League, the action delivered compact defending, quality finishing, and competitive results.",
    ],
    "BUNDESLIGA": [
        "Around the Bundesliga, the slate featured decisive finishing, pressure shifts, and several matches shaped by key stretches.",
        "Across the Bundesliga, the action brought a mix of attacking quality, organized defending, and meaningful results.",
    ],
    "GENERIC": [
        "Around the league, the slate featured competitive matchups and several notable results.",
        "Across the schedule, the action brought momentum swings, standout stretches, and meaningful outcomes.",
    ],
}


# ============================================================
# RESULT LANGUAGE
# Controlled verb pools keep variety without losing brand voice.
# ============================================================

WIN_PHRASES_CLOSE = [
    "edged",
    "held off",
    "outlasted",
]

WIN_PHRASES_STANDARD = [
    "beat",
    "defeated",
    "topped",
]

WIN_PHRASES_COMFORTABLE = [
    "beat",
    "defeated",
    "handled",
    "pulled away from",
]

WIN_PHRASES_LOPSIDED = [
    "routed",
    "overwhelmed",
    "rolled past",
]

UPCOMING_PHRASES = [
    "is set for",
    "will begin at",
    "is scheduled for",
]


# ============================================================
# CORE STYLE HELPERS
# ============================================================

def league_opener(league_code: str) -> str:
    league_code = (league_code or "").upper()
    return pick(LEAGUE_OPENERS.get(league_code, LEAGUE_OPENERS["GENERIC"]))


def classify_margin(score_a, score_b):
    try:
        margin = abs(int(score_a) - int(score_b))
    except Exception:
        return "standard"

    if margin <= 5:
        return "close"
    if margin >= 15:
        return "lopsided"
    if margin >= 8:
        return "comfortable"
    return "standard"


def choose_win_verb(winner_score, loser_score):
    game_type = classify_margin(winner_score, loser_score)

    if game_type == "close":
        return pick(WIN_PHRASES_CLOSE)
    if game_type == "comfortable":
        return pick(WIN_PHRASES_COMFORTABLE)
    if game_type == "lopsided":
        return pick(WIN_PHRASES_LOPSIDED)
    return pick(WIN_PHRASES_STANDARD)


# ============================================================
# REPORT LINE BUILDERS
# These should stay universal across products.
# ============================================================

def final_line(winner, loser, winner_score, loser_score):
    verb = choose_win_verb(winner_score, loser_score)
    return f"{winner} {verb} {loser} {winner_score}-{loser_score}."


def live_line(home_team, away_team, home_score, away_score, detail=None):
    suffix = f" — {detail}" if detail else ""
    return f"LIVE: {away_team} {away_score}, {home_team} {home_score}{suffix}."


def upcoming_line(away_team, home_team, start_text):
    phrase = pick(UPCOMING_PHRASES)
    return f"UPCOMING: {away_team} at {home_team} {phrase} {start_text}."


def neutral_result_line(winner, loser, winner_score, loser_score):
    return f"{winner} beat {loser} {winner_score}-{loser_score}."


def no_games_line(section_name="games"):
    return f"No {section_name} available for this report window."


def stat_unavailable_line():
    return "Detailed player stat lines were unavailable from the current data feed for this run."


def summarize_top_performer(player_name, team_name, stat_line):
    if not player_name or not stat_line:
        return ""
    if team_name:
        return f"{player_name} ({team_name}) led the way with {stat_line}."
    return f"{player_name} stood out with {stat_line}."


# ============================================================
# STRUCTURE BUILDERS
# These enforce consistent product presentation.
# ============================================================

def build_report_header(league_name, report_date):
    return f"{league_name} Journalist Report | {report_date}"


def build_generated_line(timestamp_text):
    return f"Generated: {timestamp_text}"


def closing_line():
    return DEFAULT_DISCLAIMER


def make_section(title, lines):
    clean_lines = [str(line).strip() for line in lines if line and str(line).strip()]
    if not clean_lines:
        return ""
    return f"{title}\n" + "\n".join(clean_lines)


def join_report_parts(parts):
    clean_parts = [str(part).strip() for part in parts if part and str(part).strip()]
    return "\n\n".join(clean_parts).strip() + "\n"


def ordered_sections(section_map, section_order=None):
    """
    Build sections in a fixed product order.

    section_map example:
    {
        "FINAL SCORES": [...],
        "LIVE": [...],
        "UPCOMING": [...],
        "KEY DEVELOPMENTS": [...],
    }
    """
    section_order = section_order or DEFAULT_SECTION_ORDER
    built = []

    for title in section_order:
        lines = section_map.get(title, [])
        section_text = make_section(title, lines)
        if section_text:
            built.append(section_text)

    return built


# ============================================================
# SAFETY / CLEANUP HELPERS
# ============================================================

def safe_team_name(name, fallback="Unknown Team"):
    name = (name or "").strip()
    return name if name else fallback


def dedupe_lines(lines):
    seen = set()
    output = []
    for line in lines:
        clean = str(line).strip()
        if clean and clean not in seen:
            output.append(clean)
            seen.add(clean)
    return output