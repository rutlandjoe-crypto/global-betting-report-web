from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable
LOG_TIMEZONE = ZoneInfo("America/New_York")

# Set to True if you want the runner to stop immediately
# when a required script fails.
STOP_ON_REQUIRED_FAILURE = False

# Set to True if you want missing output files to count as failure.
CHECK_OUTPUT_FILES = True


# =========================================================
# SCRIPT PIPELINE
# =========================================================
# Edit this list only if you add/remove report scripts.
# "required": True means it matters more to the pipeline.
# "output": file expected from that script, if applicable.

SCRIPTS = [
    {
        "name": "NBA report",
        "script": "get_nba_report.py",
        "required": False,
        "output": "nba_report.txt",
    },
    {
        "name": "MLB report",
        "script": "get_mlb_report.py",
        "required": False,
        "output": "mlb_report.txt",
    },
    {
        "name": "NHL report",
        "script": "get_nhl_report.py",
        "required": False,
        "output": "nhl_report.txt",
    },
    {
        "name": "NFL report",
        "script": "get_nfl_report.py",
        "required": False,
        "output": "nfl_report.txt",
    },
    {
        "name": "Soccer report",
        "script": "get_soccer_report.py",
        "required": False,
        "output": "soccer_report.txt",
    },
    {
        "name": "Global sports report",
        "script": "global_sports_report.py",
        "required": True,
        "output": "global_sports_report.txt",
    },
    {
        "name": "Distribution build",
        "script": "build_distribution.py",
        "required": True,
        "output": None,
    },
]


# =========================================================
# LOGGING
# =========================================================

def timestamp_et() -> str:
    return datetime.now(LOG_TIMEZONE).strftime("%Y-%m-%d %I:%M:%S %p %Z")


def log(message: str) -> None:
    print(f"[{timestamp_et()}] {message}")


# =========================================================
# HELPERS
# =========================================================

def file_exists_nonempty(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def run_script(script_name: str) -> tuple[bool, str]:
    script_path = BASE_DIR / script_name

    if not script_path.exists():
        return False, f"Missing script: {script_name}"

    try:
        result = subprocess.run(
            [PYTHON_EXE, str(script_path)],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if stdout:
            print(stdout)

        if stderr:
            print(stderr)

        if result.returncode != 0:
            return False, f"{script_name} exited with code {result.returncode}"

        return True, f"{script_name} completed successfully."

    except Exception as exc:
        return False, f"{script_name} failed to run: {exc}"


def validate_output(output_name: str | None) -> tuple[bool, str]:
    if not output_name or not CHECK_OUTPUT_FILES:
        return True, "No output check required."

    output_path = BASE_DIR / output_name

    if not file_exists_nonempty(output_path):
        return False, f"Expected output missing or empty: {output_name}"

    return True, f"Verified output: {output_name}"


# =========================================================
# MAIN
# =========================================================

def main() -> None:
    log("MASTER RUNNER STARTED")

    successes = []
    failures = []

    for item in SCRIPTS:
        name = item["name"]
        script = item["script"]
        required = item["required"]
        output = item["output"]

        log(f"Starting: {name} ({script})")

        ok, message = run_script(script)

        if ok:
            log(message)

            output_ok, output_message = validate_output(output)
            if output_ok:
                log(output_message)
                successes.append(name)
            else:
                log(f"WARNING: {output_message}")
                failures.append(f"{name} -> {output_message}")

                if required and STOP_ON_REQUIRED_FAILURE:
                    log("Stopping pipeline because a required output check failed.")
                    break
        else:
            log(f"ERROR: {message}")
            failures.append(f"{name} -> {message}")

            if required and STOP_ON_REQUIRED_FAILURE:
                log("Stopping pipeline because a required script failed.")
                break

        print("-" * 60)

    log("MASTER RUNNER FINISHED")
    log(f"Successful stages: {len(successes)}")
    log(f"Failed stages: {len(failures)}")

    if successes:
        log("SUCCESS LIST:")
        for item in successes:
            log(f"  - {item}")

    if failures:
        log("FAILURE LIST:")
        for item in failures:
            log(f"  - {item}")


if __name__ == "__main__":
    main()