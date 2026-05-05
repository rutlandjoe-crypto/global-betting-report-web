import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
OUTPUT_PATH = BASE_DIR / "fantasy_report.txt"
SOURCE_SCRIPT = BASE_DIR / "get_fantasy_report.py"

load_dotenv(dotenv_path=ENV_PATH)

ET = ZoneInfo("America/New_York")

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, "
    "human sports journalism."
)


def et_now() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d %I:%M:%S %p ET")


def report_date() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def log(message: str) -> None:
    print(f"[{et_now()}] {message}", flush=True)


def fix_spacing(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", text)
    text = re.sub(r"(?<=[0-9])(?=[A-Za-z])", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_text(value, fallback="") -> str:
    if value is None:
        return fallback

    text = str(value)

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2014": "—",
        "\u2013": "–",
        "\xa0": " ",
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€”": "—",
        "â€“": "–",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text if text else fallback


def clean_output_line(text: str) -> str:
    return fix_spacing(clean_text(text, fallback=""))


def normalize_report_text(text: str) -> str:
    if not text:
        return ""

    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = text.splitlines()

    cleaned_lines: list[str] = []
    blank_count = 0

    for line in raw_lines:
        if line.strip():
            cleaned_lines.append(clean_output_line(line))
            blank_count = 0
        else:
            blank_count += 1
            if blank_count <= 1:
                cleaned_lines.append("")

    return "\n".join(cleaned_lines).strip()


def build_fallback_report(reason: str) -> str:
    fallback = f"""FANTASY REPORT | {report_date()}

Across the fantasy landscape, usable data was unavailable during this report window.

SNAPSHOT
No fantasy updates were available at this time.

FALLBACK NOTE
Fantasy automation used a fallback report because: {reason}

{DISCLAIMER}
"""
    return normalize_report_text(fallback)


def write_report(text: str) -> None:
    normalized = normalize_report_text(text)
    OUTPUT_PATH.write_text(normalized + "\n", encoding="utf-8")
    log(f"Saved: {OUTPUT_PATH.name}")


def write_fallback(reason: str) -> None:
    fallback = build_fallback_report(reason)
    OUTPUT_PATH.write_text(fallback + "\n", encoding="utf-8")
    log(f"Fallback fantasy report written: {OUTPUT_PATH.name}")


def file_has_content(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def output_file_is_meaningful(path: Path) -> bool:
    if not file_has_content(path):
        return False

    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return False

    if len(text) < 25:
        return False

    weak_patterns = [
        "no report available",
        "report unavailable",
        "data unavailable",
        "coming soon",
    ]

    lower = text.lower()
    return not any(pattern in lower for pattern in weak_patterns)


def normalize_existing_output_file() -> None:
    if not file_has_content(OUTPUT_PATH):
        return

    try:
        current = OUTPUT_PATH.read_text(encoding="utf-8", errors="replace")
        cleaned = normalize_report_text(current)
        OUTPUT_PATH.write_text(cleaned + "\n", encoding="utf-8")
        log(f"Normalized existing output file: {OUTPUT_PATH.name}")
    except Exception as exc:
        log(f"WARNING: Could not normalize existing fantasy report: {exc}")


def run_fantasy_report() -> bool:
    if not SOURCE_SCRIPT.exists():
        log(f"ERROR: Missing script: {SOURCE_SCRIPT.name}")
        write_fallback("source fantasy script missing")
        return False

    try:
        log("Starting fantasy report build...")

        result = subprocess.run(
            [sys.executable, str(SOURCE_SCRIPT)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if stdout:
            log("Fantasy script stdout:")
            for line in stdout.splitlines():
                print(clean_output_line(line), flush=True)

        if stderr:
            log("Fantasy script stderr:")
            for line in stderr.splitlines():
                print(clean_output_line(line), flush=True)

        if result.returncode != 0:
            log(f"ERROR: Fantasy report script failed with code {result.returncode}")
            write_fallback(f"source script exited with code {result.returncode}")
            return False

        if output_file_is_meaningful(OUTPUT_PATH):
            normalize_existing_output_file()
            log(f"{OUTPUT_PATH.name} created by source script ({OUTPUT_PATH.stat().st_size} bytes)")
            log("Fantasy report complete")
            return True

        if stdout:
            write_report(stdout)
            log(f"Fantasy report complete ({len(stdout)} chars)")
            return True

        log("WARNING: Script ran but produced no report output")
        write_fallback("source script returned no output")
        return False

    except subprocess.TimeoutExpired:
        log("ERROR: Fantasy report build timed out after 60 seconds")
        write_fallback("source script timed out after 60 seconds")
        return False
    except Exception as exc:
        log(f"ERROR: Unexpected failure in run_fantasy.py -> {exc}")
        write_fallback(f"unexpected wrapper error: {exc}")
        return False


if __name__ == "__main__":
    success = run_fantasy_report()
    sys.exit(0 if success else 1)