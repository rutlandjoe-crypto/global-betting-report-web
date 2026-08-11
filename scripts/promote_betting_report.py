from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


BANNED_PHRASES = (
    "books wait on prices",
    "board takes shape",
    "market takes shape",
    "lines take shape",
    "fallback",
    "generic",
    "placeholder",
)


def parse_timestamp(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("missing generated timestamp")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"unparseable generated timestamp: {text}") from exc
    if parsed.tzinfo is None:
        raise ValueError("generated timestamp has no timezone")
    return parsed.astimezone(timezone.utc)


def report_timestamp(data: dict) -> datetime:
    return parse_timestamp(data.get("generated_utc") or data.get("verified_at"))


def verified_output_count(data: dict) -> int:
    verification = data.get("verification")
    if isinstance(verification, dict):
        if (
            verification.get("status") == "verified"
            and verification.get("provider") == "Sportradar Odds Comparison Prematch v2"
        ):
            count = verification.get("total_verified_events")
            if isinstance(count, int):
                return count

    cards = data.get("homepage_cards") or []
    return sum(
        1
        for card in cards
        if isinstance(card, dict)
        and isinstance(card.get("verified_markets"), list)
        and card["verified_markets"]
    )


def load_and_validate(path: Path, not_before: datetime) -> tuple[dict, bytes]:
    if not path.is_file():
        raise ValueError(f"generated Betting report is missing: {path}")

    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"generated Betting report is malformed: {exc}") from exc

    identity = " ".join(
        str(data.get(key) or "")
        for key in ("site", "site_name", "title", "vertical")
    )
    if "betting" not in identity.lower():
        raise ValueError("generated report does not identify as Betting")
    if report_timestamp(data) < not_before:
        raise ValueError(
            "generated Betting report predates this workflow run; refusing stale output"
        )

    cards = data.get("homepage_cards") or data.get("cards") or []
    newsroom = data.get("live_newsroom") or data.get("briefing") or []
    if len(cards) < 8:
        raise ValueError(f"generated Betting report has only {len(cards)} cards")
    if len(newsroom) < 5:
        raise ValueError(
            f"generated Betting report has only {len(newsroom)} newsroom items"
        )
    if verified_output_count(data) <= 0:
        raise ValueError(
            "generated Betting report contains zero verified Sportradar output"
        )

    lowered = raw.decode("utf-8", errors="ignore").lower()
    hits = [phrase for phrase in BANNED_PHRASES if phrase in lowered]
    if hits:
        raise ValueError(
            "generated Betting report contains blocked fallback content: "
            + ", ".join(hits)
        )
    return data, raw


def write_atomic(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
        Path(temp_name).replace(path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def promote(
    source: Path,
    canonical: Path,
    not_before: datetime,
    compatibility: Path | None = None,
) -> None:
    source_data, raw = load_and_validate(source, not_before)

    if canonical.exists() and source.resolve() != canonical.resolve():
        canonical_data = json.loads(canonical.read_text(encoding="utf-8"))
        if report_timestamp(source_data) <= report_timestamp(canonical_data):
            raise ValueError(
                "generated Betting report is not newer than the canonical report"
            )

    if source.resolve() != canonical.resolve():
        write_atomic(canonical, raw)
    if canonical.read_bytes() != raw:
        raise ValueError("canonical report is not byte-identical to verified output")

    if compatibility is not None:
        write_atomic(compatibility, canonical.read_bytes())
        if compatibility.read_bytes() != canonical.read_bytes():
            raise ValueError("compatibility report does not match canonical output")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--compatibility", type=Path)
    parser.add_argument("--not-before", required=True)
    args = parser.parse_args()
    try:
        promote(
            args.source,
            args.canonical,
            parse_timestamp(args.not_before),
            args.compatibility,
        )
    except Exception as exc:
        print(f"BETTING GENERATION FAILED: {exc}")
        return 1
    print(f"Betting canonical report verified: {args.canonical}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
