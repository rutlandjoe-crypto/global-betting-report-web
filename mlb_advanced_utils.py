from __future__ import annotations

import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import statsapi

try:
    from pybaseball import playerid_lookup, statcast_pitcher
except ImportError:
    playerid_lookup = None
    statcast_pitcher = None

TIMEZONE = ZoneInfo("America/New_York")


def now_et() -> datetime:
    return datetime.now(TIMEZONE)


def today_et() -> str:
    return now_et().strftime("%Y-%m-%d")


def log(message: str) -> None:
    print(f"[{now_et().strftime('%Y-%m-%d %I:%M:%S %p ET')}] {message}", flush=True)


def clean_name(name: str | None) -> str:
    if not name:
        return "Unknown"

    cleaned = name.strip()

    if cleaned == "Athletics Athletics":
        return "Athletics"

    return cleaned


def format_et_time(utc_datetime_str: str) -> str:
    if not utc_datetime_str:
        return "TBD ET"

    try:
        dt = datetime.fromisoformat(utc_datetime_str.replace("Z", "+00:00"))
        return dt.astimezone(TIMEZONE).strftime("%I:%M %p ET").lstrip("0")
    except Exception:
        return "TBD ET"


def get_mlb_games_for_today() -> list[dict]:
    try:
        games = statsapi.schedule(date=today_et())
        return games if isinstance(games, list) else []
    except Exception as exc:
        log(f"ERROR fetching MLB games: {exc}")
        return []


def is_upcoming_game(game: dict) -> bool:
    status = (game.get("status") or "").strip().lower()

    upcoming_markers = {
        "scheduled",
        "pre-game",
        "preview",
    }

    if status in upcoming_markers:
        return True

    return "scheduled" in status or "pre-game" in status or "preview" in status


def get_upcoming_games(games: list[dict]) -> list[dict]:
    return [game for game in games if is_upcoming_game(game)]


def build_pitcher_watch_line(
    pitcher: str,
    team: str,
    opponent: str,
    game_time: str,
    slot_index: int = 0,
) -> str:
    templates = [
        f"{pitcher} gets the ball for {team} against {opponent} at {game_time}, putting the early tone of the matchup in focus.",
        f"{pitcher} is set to start for {team} versus {opponent} at {game_time}, making him a key arm to watch before first pitch.",
        f"{pitcher} takes the mound for {team} against {opponent} at {game_time}, giving this matchup a clear pitching storyline.",
        f"{pitcher} draws the assignment for {team} against {opponent} at {game_time}, placing extra attention on how the game opens.",
        f"{pitcher} is lined up for {team} versus {opponent} at {game_time}, with the pitching matchup shaping the early read on this game.",
    ]

    if 0 <= slot_index < len(templates):
        return templates[slot_index]

    return random.choice(templates)


def build_matchup_line(
    away_team: str,
    home_team: str,
    away_sp: str,
    home_sp: str,
    game_time: str,
    slot_index: int = 0,
) -> str:
    if away_sp != "Unknown" and home_sp != "Unknown":
        templates = [
            f"{away_team} at {home_team} ({game_time}) features a listed starters matchup of {away_sp} vs. {home_sp}, giving the game a strong pregame pitching frame.",
            f"{away_team} at {home_team} ({game_time}) draws attention with {away_sp} lined up against {home_sp}, making starting pitching the clearest early storyline.",
            f"{away_team} at {home_team} ({game_time}) stands out behind a probable starters matchup of {away_sp} and {home_sp}.",
            f"{away_team} at {home_team} ({game_time}) carries a defined pitching setup with {away_sp} opposing {home_sp}, which sharpens the pregame focus.",
            f"{away_team} at {home_team} ({game_time}) offers one of the cleaner pitching matchups on the board with {away_sp} matched against {home_sp}.",
        ]

        if 0 <= slot_index < len(templates):
            return templates[slot_index]

        return random.choice(templates)

    fallback_templates = [
        f"{away_team} at {home_team} ({game_time}) stands out as a game to watch as lineups and pitching context settle closer to first pitch.",
        f"{away_team} at {home_team} ({game_time}) remains worth watching even without a fully defined pitching frame.",
        f"{away_team} at {home_team} ({game_time}) is still a notable spot on the board as pregame details continue to take shape.",
    ]

    if 0 <= slot_index < len(fallback_templates):
        return fallback_templates[slot_index]

    return random.choice(fallback_templates)


def score_game_for_matchup_priority(game: dict) -> tuple[int, datetime]:
    score = 0

    away_sp = clean_name(game.get("away_probable_pitcher"))
    home_sp = clean_name(game.get("home_probable_pitcher"))
    away_team = clean_name(game.get("away_name"))
    home_team = clean_name(game.get("home_name"))

    if away_sp != "Unknown":
        score += 2
    if home_sp != "Unknown":
        score += 2
    if away_team != "Unknown":
        score += 1
    if home_team != "Unknown":
        score += 1

    game_dt = parse_game_datetime(game)
    return score, game_dt


def parse_game_datetime(game: dict) -> datetime:
    raw = game.get("game_datetime", "")
    if not raw:
        return datetime.max.replace(tzinfo=TIMEZONE)

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return datetime.max.replace(tzinfo=TIMEZONE)


def pick_top_matchups(games: list[dict], limit: int = 3) -> list[dict]:
    upcoming_games = get_upcoming_games(games)

    ranked = sorted(
        upcoming_games,
        key=lambda game: (
            -score_game_for_matchup_priority(game)[0],
            score_game_for_matchup_priority(game)[1],
        ),
    )

    return ranked[:limit]


def extract_matchup_flags(games: list[dict], limit: int = 3) -> list[str]:
    notes: list[str] = []

    top_games = pick_top_matchups(games, limit=limit)

    for idx, game in enumerate(top_games):
        away_team = clean_name(game.get("away_name"))
        home_team = clean_name(game.get("home_name"))
        away_sp = clean_name(game.get("away_probable_pitcher"))
        home_sp = clean_name(game.get("home_probable_pitcher"))
        game_time = format_et_time(game.get("game_datetime", ""))

        notes.append(
            build_matchup_line(
                away_team=away_team,
                home_team=home_team,
                away_sp=away_sp,
                home_sp=home_sp,
                game_time=game_time,
                slot_index=idx,
            )
        )

    if not notes:
        notes.append("No standout matchups were identified during this report window.")

    return notes[:limit]


def build_board_context(games: list[dict]) -> str:
    upcoming_games = get_upcoming_games(games)
    count = len(upcoming_games)

    if count >= 10:
        return "A full MLB board remains in play, putting extra emphasis on probable pitchers and pregame matchup edges."

    if count >= 5:
        return "A busy MLB evening slate keeps the focus on starting pitching and which clubs can grab early momentum."

    if count > 0:
        return "A lighter MLB board sharpens attention on a smaller group of matchups with cleaner pregame storylines."

    return "Most of the MLB value in this report window comes from games already underway or completed."


# =========================
# REAL STATCAST LAYER
# =========================

def pybaseball_available() -> bool:
    return playerid_lookup is not None and statcast_pitcher is not None


def split_player_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return "", parts[0]
    return parts[0], parts[-1]


def lookup_mlbam_id(full_name: str) -> int | None:
    if not pybaseball_available():
        return None

    first, last = split_player_name(full_name)
    if not last:
        return None

    try:
        lookup_df = playerid_lookup(last=last, first=first, fuzzy=True)
        if lookup_df is None or lookup_df.empty:
            return None

        # Prefer active/recent rows if available
        if "mlb_played_last" in lookup_df.columns:
            lookup_df = lookup_df.sort_values(by="mlb_played_last", ascending=False)

        if "key_mlbam" not in lookup_df.columns:
            return None

        for _, row in lookup_df.iterrows():
            raw_id = row.get("key_mlbam")
            if raw_id is None:
                continue
            try:
                return int(raw_id)
            except Exception:
                continue

        return None

    except Exception as exc:
        log(f"Statcast lookup failed for {full_name}: {exc}")
        return None


def safe_mean(series) -> float | None:
    try:
        cleaned = series.dropna()
        if cleaned.empty:
            return None
        return float(cleaned.mean())
    except Exception:
        return None


def safe_max(series) -> float | None:
    try:
        cleaned = series.dropna()
        if cleaned.empty:
            return None
        return float(cleaned.max())
    except Exception:
        return None


def pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100, 1)


def get_recent_pitcher_statcast_summary(full_name: str, days_back: int = 30) -> dict | None:
    if not pybaseball_available():
        return None

    player_id = lookup_mlbam_id(full_name)
    if player_id is None:
        return None

    end_date = now_et().date()
    start_date = end_date - timedelta(days=days_back)

    try:
        df = statcast_pitcher(
            start_dt=start_date.strftime("%Y-%m-%d"),
            end_dt=end_date.strftime("%Y-%m-%d"),
            player_id=player_id,
        )
    except Exception as exc:
        log(f"Statcast pull failed for {full_name}: {exc}")
        return None

    if df is None or getattr(df, "empty", True):
        return None

    pitch_count = len(df.index)

    release_speed = safe_mean(df["release_speed"]) if "release_speed" in df.columns else None
    max_velocity = safe_max(df["release_speed"]) if "release_speed" in df.columns else None
    release_spin = safe_mean(df["release_spin_rate"]) if "release_spin_rate" in df.columns else None
    extension = safe_mean(df["release_extension"]) if "release_extension" in df.columns else None

    whiff_rate = None
    if "description" in df.columns:
        descriptions = df["description"].fillna("").astype(str)
        whiffs = descriptions.isin(["swinging_strike", "swinging_strike_blocked"]).sum()
        swings = descriptions.isin([
            "swinging_strike",
            "swinging_strike_blocked",
            "foul",
            "foul_tip",
            "hit_into_play",
            "hit_into_play_no_out",
            "hit_into_play_score",
        ]).sum()
        whiff_rate = pct(int(whiffs), int(swings)) if swings > 0 else None

    return {
        "player_id": player_id,
        "pitch_count": pitch_count,
        "avg_velocity": round(release_speed, 1) if release_speed is not None else None,
        "max_velocity": round(max_velocity, 1) if max_velocity is not None else None,
        "avg_spin": round(release_spin) if release_spin is not None else None,
        "avg_extension": round(extension, 1) if extension is not None else None,
        "whiff_rate": whiff_rate,
    }


def build_statcast_pitcher_note(
    pitcher: str,
    team: str,
    opponent: str,
    game_time: str,
    summary: dict,
) -> str:
    avg_velocity = summary.get("avg_velocity")
    max_velocity = summary.get("max_velocity")
    avg_spin = summary.get("avg_spin")
    whiff_rate = summary.get("whiff_rate")
    pitch_count = summary.get("pitch_count", 0)

    traits: list[str] = []

    if avg_velocity is not None:
        if avg_velocity >= 97.0:
            traits.append(f"has averaged {avg_velocity} mph recently")
        elif avg_velocity >= 94.0:
            traits.append(f"has sat at {avg_velocity} mph over his recent Statcast sample")

    if max_velocity is not None and max_velocity >= 98.0:
        traits.append(f"has touched {max_velocity} mph")

    if avg_spin is not None and avg_spin >= 2400:
        traits.append(f"has carried an average spin rate around {avg_spin}")

    if whiff_rate is not None:
        if whiff_rate >= 30.0:
            traits.append(f"has produced a {whiff_rate}% whiff rate on swings")
        elif whiff_rate >= 24.0:
            traits.append(f"has generated a healthy {whiff_rate}% whiff rate on swings")

    if traits:
        trait_text = "; ".join(traits[:2])
        return (
            f"{pitcher} gets the ball for {team} against {opponent} at {game_time} and {trait_text}, "
            f"making him one of the stronger Statcast pitching signals on tonight’s board."
        )

    return (
        f"{pitcher} is set to start for {team} versus {opponent} at {game_time}, and his recent Statcast sample "
        f"covers {pitch_count} pitches, giving this matchup a measurable pitching signal to watch."
    )


def extract_pitcher_watch(games: list[dict], limit: int = 3) -> list[str]:
    notes: list[str] = []
    seen_pitchers: set[str] = set()

    upcoming_games = get_upcoming_games(games)

    for game in upcoming_games:
        away_team = clean_name(game.get("away_name"))
        home_team = clean_name(game.get("home_name"))
        away_sp = clean_name(game.get("away_probable_pitcher"))
        home_sp = clean_name(game.get("home_probable_pitcher"))
        game_time = format_et_time(game.get("game_datetime", ""))

        for pitcher, team, opponent in [
            (away_sp, away_team, home_team),
            (home_sp, home_team, away_team),
        ]:
            if pitcher == "Unknown" or pitcher in seen_pitchers:
                continue

            summary = get_recent_pitcher_statcast_summary(pitcher)

            if summary:
                notes.append(
                    build_statcast_pitcher_note(
                        pitcher=pitcher,
                        team=team,
                        opponent=opponent,
                        game_time=game_time,
                        summary=summary,
                    )
                )
            else:
                notes.append(
                    build_pitcher_watch_line(
                        pitcher=pitcher,
                        team=team,
                        opponent=opponent,
                        game_time=game_time,
                        slot_index=len(notes),
                    )
                )

            seen_pitchers.add(pitcher)

            if len(notes) >= limit:
                break

        if len(notes) >= limit:
            break

    if not notes:
        notes.append("No probable-pitcher signals were available during this report window.")

    return notes[:limit]


def build_advanced_fallback_report(disclaimer: str, error_message: str = "") -> str:
    lines = [
        f"MLB ADVANCED REPORT | {today_et()}",
        "",
        "STATCAST WATCH",
        "- No advanced data was available during this report window.",
        "",
        "MATCHUP FLAGS",
        "- No matchup insights were available.",
        "",
        "BOARD CONTEXT",
        "- An advanced MLB summary could not be generated.",
    ]

    if error_message:
        lines.extend([
            "",
            "ERROR",
            f"- {error_message}",
        ])

    lines.extend([
        "",
        disclaimer,
    ])

    return "\n".join(lines)