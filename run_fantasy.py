from __future__ import annotations

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

TIMEZONE = ZoneInfo("America/New_York")
DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, human sports journalism."
)


def now_et() -> datetime:
    return datetime.now(TIMEZONE)


def et_now() -> str:
    return now_et().strftime("%Y-%m-%d %I:%M:%S %p ET")


def report_date() -> str:
    return now_et().strftime("%Y-%m-%d")


def log(message: str) -> None:
    print(f"[{et_now()}] {message}", flush=True)


def build_fallback_report(reason: str) -> str:
    return f"""FANTASY REPORT | {report_date()}

Across the fantasy landscape, usable data was unavailable during this report window.

SNAPSHOT
No fantasy updates were available at this time.

FALLBACK NOTE
Fantasy automation used a fallback report because: {reason}

{DISCLAIMER}
""".strip()


def write_fallback(reason: str) -> None:
    fallback = build_fallback_report(reason)
    OUTPUT_PATH.write_text(fallback + "\n", encoding="utf-8")
    log(f"Fallback fantasy report written: {OUTPUT_PATH.name}")


def file_has_content(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


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
            timeout=90,
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if stdout:
            log("Fantasy script stdout:")
            for line in stdout.splitlines():
                print(line, flush=True)

        if stderr:
            log("Fantasy script stderr:")
            for line in stderr.splitlines():
                print(line, flush=True)

        if result.returncode != 0:
            log(f"ERROR: Fantasy report script failed with code {result.returncode}")
            write_fallback(f"source script exited with code {result.returncode}")
            return False

        if file_has_content(OUTPUT_PATH):
            log(f"{OUTPUT_PATH.name} created by source script ({OUTPUT_PATH.stat().st_size} bytes)")
            log("Fantasy report complete")
            return True

        if stdout:
            OUTPUT_PATH.write_text(stdout + "\n", encoding="utf-8")
            log(f"Saved: {OUTPUT_PATH.name}")
            log(f"Fantasy report complete ({len(stdout)} chars)")
            return True

        log("WARNING: Script ran but produced no report output")
        write_fallback("source script returned no output")
        return False

    except subprocess.TimeoutExpired:
        log("ERROR: Fantasy report build timed out after 90 seconds")
        write_fallback("source script timed out after 90 seconds")
        return False

    except Exception as exc:
        log(f"ERROR: Unexpected failure in run_fantasy.py -> {exc}")
        write_fallback(f"unexpected wrapper error: {exc}")
        return False


if __name__ == "__main__":
    success = run_fantasy_report()
    sys.exit(0 if success else 1)