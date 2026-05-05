import subprocess
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
TIMEZONE = ZoneInfo("America/New_York")

SCRIPTS = [
    "get_mlb_report.py",
    "get_nba_report.py",
    "get_nhl_report.py",
    "get_soccer_report.py",
    "global_report.py",
    "build_distribution.py",
    "send_to_telegram.py",
]


def now_et() -> str:
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %I:%M:%S %p ET")


def run_script(script_name: str) -> bool:
    script_path = BASE_DIR / script_name

    if not script_path.exists():
        print(f"❌ Missing file: {script_name}")
        return False

    print("")
    print("=" * 60)
    print(f"▶ Running: {script_name}")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.stdout.strip():
        print(result.stdout)

    if result.returncode != 0:
        print(f"❌ Failed: {script_name}")
        if result.stderr.strip():
            print(result.stderr)
        return False

    if result.stderr.strip():
        print(result.stderr)

    print(f"✅ Finished: {script_name}")
    return True


def main() -> None:
    print("")
    print("GLOBAL SPORTS REPORT — DAILY RUN")
    print(f"Start time: {now_et()}")

    passed = []
    failed = []

    for script in SCRIPTS:
        ok = run_script(script)
        if ok:
            passed.append(script)
        else:
            failed.append(script)

    print("")
    print("=" * 60)
    print("RUN SUMMARY")
    print("=" * 60)
    print(f"Completed: {len(passed)}")
    for item in passed:
        print(f"  ✅ {item}")

    print(f"Failed: {len(failed)}")
    for item in failed:
        print(f"  ❌ {item}")

    print("")
    print(f"End time: {now_et()}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()