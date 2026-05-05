from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List, Set


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "personalized_global_report.txt"

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, human sports journalism."
)

LEAGUE_FILES: Dict[str, List[str]] = {
    "global": ["global_sports_report.txt"],
    "mlb": ["mlb_report.txt"],
    "nba": ["nba_report.txt"],
    "nfl": ["nfl_report.txt"],
    "nhl": ["nhl_report.txt"],
    "ncaafb": ["ncaafb_report.txt", "college_football_report.txt"],
    "soccer": ["soccer_report.txt"],
    "premier league": ["premier_league_report.txt", "soccer_report.txt"],
    "bundesliga": ["bundesliga_report.txt", "soccer_report.txt"],
    "la liga": ["la_liga_report.txt", "laliga_report.txt", "soccer_report.txt"],
    "serie a": ["serie_a_report.txt", "soccer_report.txt"],
    "ligue 1": ["ligue1_report.txt", "ligue_1_report.txt", "soccer_report.txt"],
}

LEAGUE_ALIASES: Dict[str, str] = {
    "prem": "premier league",
    "epl": "premier league",
    "english premier league": "premier league",
    "bundesliga": "bundesliga",
    "la liga": "la liga",
    "laliga": "la liga",
    "nfl": "nfl",
    "nhl": "nhl",
    "nba": "nba",
    "ncaafb": "ncaafb",
    "college football": "ncaafb",
    "cfb": "ncaafb",
    "mlb": "mlb",
    "soccer": "soccer",
    "global": "global",
    "serie a": "serie a",
    "ligue 1": "ligue 1",
}

LEAGUE_FOCUS_HEADERS: Dict[str, str] = {
    "global": "GLOBAL FOCUS",
    "mlb": "MLB FOCUS",
    "nba": "NBA FOCUS",
    "nfl": "NFL FOCUS",
    "nhl": "NHL FOCUS",
    "ncaafb": "NCAAFB FOCUS",
    "soccer": "SOCCER FOCUS",
    "premier league": "PREMIER LEAGUE FOCUS",
    "bundesliga": "BUNDESLIGA FOCUS",
    "la liga": "LA LIGA FOCUS",
    "serie a": "SERIE A FOCUS",
    "ligue 1": "LIGUE 1 FOCUS",
}

SOCCER_TERMS = {
    "soccer", "fc", "cf", "sc", "united", "city", "real", "inter", "atletico",
    "barcelona", "madrid", "arsenal", "chelsea", "liverpool", "tottenham",
    "bundesliga", "premier league", "la liga", "serie a", "ligue 1",
    "psg", "bayern", "dortmund", "leverkusen", "girona", "juventus",
    "napoli", "milan", "roma", "monaco", "lyon", "marseille"
}

NON_SOCCER_LEAK_TERMS = {
    "quarter", "1st quarter", "2nd quarter", "3rd quarter", "4th quarter",
    "top 1", "top 2", "top 3", "top 4", "top 5", "top 6", "top 7", "top 8", "top 9",
    "bottom 1", "bottom 2", "bottom 3", "bottom 4", "bottom 5", "bottom 6", "bottom 7", "bottom 8", "bottom 9",
    "innings", "inning", "end 1", "end 2", "end 3", "end 4", "end 5", "end 6", "end 7", "end 8", "end 9",
    "1st period", "2nd period", "3rd period",
    "tipoff", "shootout", "overtime"
}


def fix_encoding(text: str) -> str:
    return (
        text.replace("â€™", "’")
        .replace("â€˜", "‘")
        .replace("â€œ", "“")
        .replace("â€\x9d", "”")
        .replace("â€”", "—")
        .replace("â€“", "–")
        .replace("â€¢", "•")
        .replace("\ufeff", "")
    )


def clean_line(line: str) -> str:
    line = fix_encoding(line).strip()
    line = re.sub(r"\s+", " ", line)
    return line


def normalize_league_name(name: str) -> str:
    value = name.strip().lower()
    return LEAGUE_ALIASES.get(value, value)


def split_csv_field(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def read_text_file(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return fix_encoding(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return fix_encoding(path.read_text(encoding="cp1252", errors="ignore"))


def dedupe_keep_order(items: List[str]) -> List[str]:
    seen: Set[str] = set()
    output: List[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def get_league_files(league: str | None) -> List[Path]:
    if not league:
        return [BASE_DIR / "global_sports_report.txt"]

    normalized = normalize_league_name(league)
    filenames = LEAGUE_FILES.get(normalized, [])
    return [BASE_DIR / filename for filename in filenames]


def load_source_text(league: str | None) -> str:
    texts: List[str] = []

    for file_path in get_league_files(league):
        text = read_text_file(file_path)
        if text:
            texts.append(text)

    return "\n".join(texts)


def is_heading_like(line: str) -> bool:
    headings = {
        "HEADLINE",
        "KEY STORYLINES",
        "SNAPSHOT",
        "FINAL SCORES",
        "LIVE",
        "LIVE GAMES",
        "UPCOMING",
        "PLAYER WATCH",
        "TEAM WATCH",
        "QUERY WATCH",
        "QUERY",
        "LEAGUE",
        "SOCCER FOCUS",
        "NBA FOCUS",
        "NFL FOCUS",
        "NHL FOCUS",
        "MLB FOCUS",
        "NCAAFB FOCUS",
        "GLOBAL FOCUS",
        "PREMIER LEAGUE FOCUS",
        "BUNDESLIGA FOCUS",
        "LA LIGA FOCUS",
        "SERIE A FOCUS",
        "LIGUE 1 FOCUS",
        "SOCCER",
        "NBA",
        "NFL",
        "NHL",
        "MLB",
        "NCAAFB",
    }
    return line.upper() in headings


def extract_relevant_lines(text: str) -> List[str]:
    lines: List[str] = []

    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line:
            continue
        if is_heading_like(line):
            continue
        if line.startswith("Saved:"):
            continue
        if line.startswith("Generated:"):
            continue
        if line.startswith("This report is an automated summary"):
            continue
        if re.fullmatch(r"[A-Z0-9 \|\-]+REPORT\s*\|\s*\d{4}-\d{2}-\d{2}", line):
            continue
        lines.append(line)

    return lines


def contains_any(text: str, terms: Set[str]) -> bool:
    text_l = text.lower()
    return any(term in text_l for term in terms)


def line_matches_league(line: str, league: str | None) -> bool:
    if not league:
        return True

    normalized = normalize_league_name(league)
    line_l = line.lower()

    if normalized in {"soccer", "premier league", "bundesliga", "la liga", "serie a", "ligue 1"}:
        if contains_any(line_l, NON_SOCCER_LEAK_TERMS):
            return False

        if normalized == "soccer":
            return True

        if normalized in line_l:
            return True

        if contains_any(line_l, SOCCER_TERMS):
            return True

        return False

    if normalized == "nba":
        return ("quarter" in line_l) or ("nba" in line_l) or ("playoffs" in line_l)
    if normalized == "nfl":
        return ("nfl" in line_l) or ("touchdown" in line_l) or ("quarterback" in line_l) or ("draft" in line_l)
    if normalized == "nhl":
        return ("period" in line_l) or ("nhl" in line_l) or ("goalie" in line_l)
    if normalized == "mlb":
        return ("top " in line_l) or ("bottom " in line_l) or ("mlb" in line_l) or ("inning" in line_l)
    if normalized == "ncaafb":
        return ("ncaafb" in line_l) or ("college football" in line_l) or ("quarterback" in line_l) or ("spring practice" in line_l)

    return True


def tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9']+", text.lower()) if t]


def strict_entity_match_score(line: str, phrase: str) -> int:
    """
    For PLAYER WATCH and TEAM WATCH:
    require a meaningful match to the actual entity.
    """
    line_l = line.lower()
    words = tokenize(phrase)

    if not words:
        return 0

    matched = sum(1 for w in words if w in line_l)

    if matched == 0:
        return 0

    if len(words) == 1:
        return 100 if words[0] in line_l else 0

    # require at least half the words, rounded up
    needed = (len(words) + 1) // 2
    if matched < needed:
        return 0

    score = matched * 20
    if phrase.lower() in line_l:
        score += 40
    if matched == len(words):
        score += 25

    return score


def strict_query_match_score(line: str, query: str) -> int:
    """
    For QUERY WATCH:
    require stronger alignment than generic league lines.
    """
    line_l = line.lower()
    query_l = query.lower().strip()

    if not query_l:
        return 0

    if query_l in line_l:
        return 100

    words = tokenize(query)
    if not words:
        return 0

    matched = sum(1 for w in words if w in line_l)
    if matched < 2:
        return 0

    score = matched * 15
    if matched == len(words):
        score += 20
    return score


def general_term_score(line: str, term: str) -> int:
    line_l = line.lower()
    term_l = term.lower().strip()

    if not term_l:
        return 0

    score = 0

    if term_l == line_l:
        score += 20

    if term_l in line_l:
        score += 12

    words = [w for w in re.split(r"\s+", term_l) if w]
    if words:
        matched_words = sum(1 for w in words if w in line_l)
        score += matched_words * 4
        if matched_words == len(words) and len(words) > 1:
            score += 8

    return score


def top_entity_matches(lines: List[str], phrase: str, league: str | None, limit: int = 3) -> List[str]:
    scored = []
    for line in lines:
        if not line_matches_league(line, league):
            continue
        score = strict_entity_match_score(line, phrase)
        if score > 0:
            scored.append((score, line))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return dedupe_keep_order([line for _, line in scored])[:limit]


def top_query_matches(lines: List[str], query: str, league: str | None, limit: int = 4) -> List[str]:
    scored = []
    for line in lines:
        if not line_matches_league(line, league):
            continue
        score = strict_query_match_score(line, query)
        if score > 0:
            scored.append((score, line))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return dedupe_keep_order([line for _, line in scored])[:limit]


def score_line(line: str, search_terms: List[str], league: str | None) -> int:
    if not line_matches_league(line, league):
        return -1000

    score = 0
    for term in search_terms:
        score += general_term_score(line, term)

    if line.startswith(("FINAL:", "LIVE:", "UPCOMING:")):
        score += 1

    return score


def top_matches(lines: List[str], search_terms: List[str], league: str | None, limit: int = 8) -> List[str]:
    scored = []
    for line in lines:
        score = score_line(line, search_terms, league)
        if score > 0:
            scored.append((score, line))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return dedupe_keep_order([line for _, line in scored])[:limit]


def fallback_league_lines(lines: List[str], league: str | None, limit: int = 6) -> List[str]:
    filtered = [line for line in lines if line_matches_league(line, league)]

    preferred = []
    for line in filtered:
        if line.startswith(("FINAL:", "LIVE:", "UPCOMING:")):
            preferred.append(line)

    if preferred:
        return dedupe_keep_order(preferred)[:limit]

    return dedupe_keep_order(filtered)[:limit]


def build_search_terms(players: List[str], teams: List[str], queries: List[str], league: str | None) -> List[str]:
    terms: List[str] = []
    terms.extend(players)
    terms.extend(teams)
    terms.extend(queries)

    if league:
        normalized = normalize_league_name(league)
        if normalized != "global":
            terms.append(normalized)

    return dedupe_keep_order([term for term in terms if term.strip()])


def build_player_watch(lines: List[str], players: List[str], league: str | None) -> List[str]:
    output: List[str] = []

    for player in players:
        matches = top_entity_matches(lines, player, league, limit=3)
        if matches:
            output.extend([f"- {match}" for match in matches])
        else:
            output.append(f"- {player} was not mentioned in today’s report window.")

    return dedupe_keep_order(output)


def build_team_watch(lines: List[str], teams: List[str], league: str | None) -> List[str]:
    output: List[str] = []

    for team in teams:
        matches = top_entity_matches(lines, team, league, limit=3)
        if matches:
            output.extend([f"- {match}" for match in matches])
        else:
            output.append(f"- No recent updates found for {team}.")

    return dedupe_keep_order(output)


def build_query_watch(lines: List[str], queries: List[str], league: str | None) -> List[str]:
    output: List[str] = []

    for query in queries:
        matches = top_query_matches(lines, query, league, limit=4)
        if matches:
            output.extend([f"- {match}" for match in matches])
        else:
            output.append(f"- No direct report hits were found for: {query}")

    return dedupe_keep_order(output)


def select_focus_heading(league: str | None) -> str:
    if not league:
        return "PERSONALIZED FOCUS"
    return LEAGUE_FOCUS_HEADERS.get(normalize_league_name(league), "PERSONALIZED FOCUS")


def build_focus_section(
    lines: List[str],
    players: List[str],
    teams: List[str],
    queries: List[str],
    league: str | None,
) -> List[str]:
    search_terms = build_search_terms(players, teams, queries, league)
    matches = top_matches(lines, search_terms, league, limit=8)

    if matches:
        return [f"- {line}" for line in matches]

    fallback = fallback_league_lines(lines, league, limit=6)
    if fallback:
        return [f"- {line}" for line in fallback]

    if league:
        return ["- No direct league-specific matches were found for the selected players, teams, or queries in this report window."]

    return ["- No direct personalized matches were found in this report window."]


def build_headline(players: List[str], teams: List[str], queries: List[str], league: str | None) -> str:
    parts: List[str] = []

    if league:
        parts.append(normalize_league_name(league).title())
    if players:
        parts.append("player-specific")
    if teams:
        parts.append("team-specific")
    if queries:
        parts.append("query-driven")

    if not parts:
        return "Your selected interests are driving this report."

    if len(parts) == 1:
        return f"This report is tailored around {parts[0]} interests."
    if len(parts) == 2:
        return f"This report is tailored around {parts[0]} and {parts[1]} interests."

    return "This report is tailored around " + ", ".join(parts[:-1]) + f", and {parts[-1]} interests."


def format_block(title: str, items: List[str]) -> List[str]:
    block = [title]
    block.extend(items if items else ["- No items available."])
    block.append("")
    return block


def build_personalized_report(
    players: List[str],
    teams: List[str],
    queries: List[str],
    league: str | None,
) -> str:
    raw_text = load_source_text(league)
    lines = extract_relevant_lines(raw_text)

    headline = build_headline(players, teams, queries, league)
    player_watch = build_player_watch(lines, players, league) if players else []
    team_watch = build_team_watch(lines, teams, league) if teams else []
    query_watch = build_query_watch(lines, queries, league) if queries else []
    focus_heading = select_focus_heading(league)
    focus_lines = build_focus_section(lines, players, teams, queries, league)

    report_lines: List[str] = [
        "PERSONALIZED GLOBAL SPORTS REPORT",
        "",
        "HEADLINE",
        headline,
        "",
    ]

    if league:
        report_lines.extend([
            "LEAGUE",
            normalize_league_name(league).title(),
            "",
        ])

    if queries:
        report_lines.extend([
            "QUERY",
            ", ".join(queries),
            "",
        ])

    if players:
        report_lines.extend(format_block("PLAYER WATCH", player_watch))

    if teams:
        report_lines.extend(format_block("TEAM WATCH", team_watch))

    if queries:
        report_lines.extend(format_block("QUERY WATCH", query_watch))

    report_lines.extend(format_block(focus_heading, focus_lines))
    report_lines.append(DISCLAIMER)

    return "\n".join(report_lines).strip() + "\n"


def save_report(report_text: str) -> Path:
    OUTPUT_FILE.write_text(report_text, encoding="utf-8")
    return OUTPUT_FILE


def interactive_prompt() -> argparse.Namespace:
    print("\nBuild a personalized sports report.\n")

    players = input("Players (comma-separated, optional): ").strip()
    teams = input("Teams (comma-separated, optional): ").strip()
    queries = input("Queries (comma-separated, optional): ").strip()
    league = input(
        "League (optional: premier league, bundesliga, la liga, nfl, nhl, nba, ncaafb, mlb, soccer, global): "
    ).strip()

    return argparse.Namespace(
        players=players,
        teams=teams,
        queries=queries,
        league=league,
        interactive=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a personalized sports report.")
    parser.add_argument("--players", type=str, help="Comma-separated player names")
    parser.add_argument("--teams", type=str, help="Comma-separated team names")
    parser.add_argument("--queries", type=str, help="Comma-separated free-text queries")
    parser.add_argument("--league", type=str, help="Target league")
    parser.add_argument("--interactive", action="store_true", help="Run with prompts")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.interactive or not any([args.players, args.teams, args.queries, args.league]):
        args = interactive_prompt()

    players = split_csv_field(args.players)
    teams = split_csv_field(args.teams)
    queries = split_csv_field(args.queries)
    league = args.league.strip() if args.league else None

    report_text = build_personalized_report(
        players=players,
        teams=teams,
        queries=queries,
        league=league,
    )

    output_path = save_report(report_text)
    print(f"\nSaved: {output_path}\n")
    print(report_text)


if __name__ == "__main__":
    main()