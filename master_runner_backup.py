import os
import sys
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = os.getenv("REPORT_TIMEZONE", "America/Denver")
GLOBAL_REPORT_FILE = "global_sports_report.txt"

SPORT_SCRIPTS = [
    ("NBA", "get_nba_report.py", "nba_report.txt"),
    ("MLB", "get_mlb_report.py", "mlb_report.txt"),
    ("NHL", "get_nhl_report.py", "nhl_report.txt"),
    ("NFL", "get_nfl_report.py", "nfl_report.txt"),
    ("SOCCER", "get_soccer_report.py", "soccer_report.txt"),
    ("FANTASY", "get_fantasy_report.py", "fantasy_report.txt"),
    ("BETTING", "get_betting_odds_report.py", "betting_odds_report.txt"),
]

SECTION_SEPARATOR = "\n" + "=" * 80 + "\n"


def now_local():
    return datetime.now(ZoneInfo(TIMEZONE))


def run_script(script):
    if not os.path.exists(script):
        print(f"⚠ Skipping missing script: {script}")
        return False

    print(f"▶ Running {script}")

    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"❌ Error running {script}")
            print(result.stderr)
            return False

        return True

    except Exception as e:
        print(f"❌ Crash running {script}: {e}")
        return False


def read_report(file):
    if not os.path.exists(file):
        return None

    try:
        with open(file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return None


def build_header(now):
    return "\n".join([
        f"Global Sports Report | {now.strftime('%Y-%m-%d')}",
        "",
        "A consolidated multi-sport briefing built from automated reporting systems.",
        "",
        "This report is an automated summary designed to support, not replace, human journalism.",
        "",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    ])


def main():
    now = now_local()

    print("\n🏁 MASTER RUNNER STARTING\n")

    sections = []
    status_notes = []

    for name, script, report_file in SPORT_SCRIPTS:
        print(f"\n--- {name} ---")

        run_ok = run_script(script)
        report_text = read_report(report_file)

        if not run_ok:
            status_notes.append(f"{name}: script failed")
            continue

        if not report_text:
            status_notes.append(f"{name}: no data")
            continue

        sections.append(f"{name}\n\n{report_text}")
        print(f"✅ {name} added")

    final_report = build_header(now)

    if sections:
        final_report += "\n\n" + SECTION_SEPARATOR.join(sections)

    if status_notes:
        final_report += "\n\n" + SECTION_SEPARATOR
        final_report += "\nREPORT STATUS\n\n"
        for note in status_notes:
            final_report += f"- {note}\n"

    try:
        with open(GLOBAL_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(final_report)

        print(f"\n✅ FINAL REPORT CREATED: {GLOBAL_REPORT_FILE}")

    except Exception as e:
        print(f"\n❌ WRITE ERROR: {e}")

    print("\n🏆 DONE\n")


if __name__ == "__main__":
    main()