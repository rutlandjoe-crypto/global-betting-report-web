from __future__ import annotations

import os
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


# =========================================================
# GLOBAL SPORTS REPORT - MASTER RUNNER
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "master_runner_log.txt"
LOCK_FILE = BASE_DIR / "master_runner.lock"
LAST_RUN_FILE = BASE_DIR / "last_master_runner_status.txt"

ET_ZONE = ZoneInfo("America/New_York")
PYTHON_EXE = sys.executable

# script_name, timeout_seconds, required_for_pipeline
SCRIPTS = [
    ("get_betting_odds_report.py", 300, True),
    ("build_betting_distribution.py", 180, True),
]

ALWAYS_RUN = {"get_betting_odds_report.py", "build_betting_distribution.py"}
CRITICAL_SCRIPTS = {"get_betting_odds_report.py", "build_betting_distribution.py"}
NON_CRITICAL_FAILURES = {
    "get_mlb_advanced_report.py",
    "get_nba_advanced_report.py",
    "get_nfl_report.py",
    "get_nfl_advanced_report.py",
    "get_nfl_draft_signals.py",
    "get_soccer_report.py",
    "betting_odds.py",
}

REQUIRED_OUTPUTS = [BASE_DIR / "public" / "latest_report.json"]


def et_now() -> datetime:
    return datetime.now(ET_ZONE)


def timestamp() -> str:
    return et_now().strftime("%Y-%m-%d %I:%M:%S %p ET")


def log(message: str, also_print: bool = True) -> None:
    line = f"[{timestamp()}] {message}"
    if also_print:
        print(line, flush=True)

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        if also_print:
            print(f"[{timestamp()}] WARNING: Could not write to log file.", flush=True)


def log_blank_line() -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write("\n")
    except Exception:
        pass
    print("", flush=True)


def write_divider(char: str = "=") -> None:
    log(char * 70)


def truncate_output(text: str, max_chars: int = 6000) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n...[output truncated]..."


def seconds_since_modified(path: Path) -> float | None:
    try:
        return max(0.0, datetime.now().timestamp() - path.stat().st_mtime)
    except Exception:
        return None


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining = seconds % 60
    return f"{minutes}m {remaining:.1f}s"


def write_last_run_status(
    pipeline_status: str,
    successful_scripts: list[str],
    degraded_scripts: list[str],
    failed_scripts: list[str],
    blocked_scripts: list[str],
    script_timings: dict[str, str],
) -> None:
    try:
        LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"Pipeline status: {pipeline_status}",
            f"Timestamp: {timestamp()}",
            "",
            f"Successful scripts ({len(successful_scripts)}):",
        ]

        if successful_scripts:
            for name in successful_scripts:
                duration = script_timings.get(name, "unknown")
                lines.append(f"- {name} [{duration}]")
        else:
            lines.append("- None")

        lines.extend(
            [
                "",
                f"Degraded scripts ({len(degraded_scripts)}):",
            ]
        )

        if degraded_scripts:
            for name in degraded_scripts:
                duration = script_timings.get(name, "unknown")
                lines.append(f"- {name} [{duration}]")
        else:
            lines.append("- None")

        lines.extend(
            [
                "",
                f"Failed scripts ({len(failed_scripts)}):",
            ]
        )

        if failed_scripts:
            for name in failed_scripts:
                duration = script_timings.get(name, "unknown")
                lines.append(f"- {name} [{duration}]")
        else:
            lines.append("- None")

        lines.extend(
            [
                "",
                f"Blocked/skipped scripts ({len(blocked_scripts)}):",
            ]
        )

        if blocked_scripts:
            for name in blocked_scripts:
                lines.append(f"- {name}")
        else:
            lines.append("- None")

        lines.extend(["", "Script runtimes:"])

        if script_timings:
            for name, duration in script_timings.items():
                lines.append(f"- {name}: {duration}")
        else:
            lines.append("- None")

        LAST_RUN_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"Saved last run status: {LAST_RUN_FILE}")
    except Exception as exc:
        log(f"WARNING: Could not write last run status file: {exc}")


def acquire_lock() -> bool:
    """
    Prevent overlapping runs.
    If a lock exists and is older than 6 hours, treat it as stale and remove it.
    Uses exclusive file creation to reduce race conditions.
    """
    if LOCK_FILE.exists():
        try:
            age_seconds = seconds_since_modified(LOCK_FILE)
            existing = LOCK_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            age_seconds = None
            existing = "Unknown existing lock state"

        if age_seconds is not None and age_seconds > 21600:
            log("Stale lock file detected. Removing old lock and continuing.")
            log(f"Old lock info: {existing}")
            try:
                LOCK_FILE.unlink()
            except Exception as exc:
                log(f"WARNING: Could not remove stale lock file: {exc}")
                return False
        else:
            log("Another master runner instance appears to already be running.")
            log(f"Existing lock info: {existing}")
            return False

    lock_text = (
        f"PID={os.getpid()} | STARTED={timestamp()} | "
        f"PYTHON={PYTHON_EXE} | BASE_DIR={BASE_DIR}"
    )

    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(lock_text)
        return True
    except FileExistsError:
        log("Another master runner instance grabbed the lock first.")
        return False
    except Exception as exc:
        log(f"WARNING: Failed to create lock file: {exc}")
        return False


def release_lock() -> None:
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception as exc:
        log(f"WARNING: Failed to remove lock file: {exc}")


def run_script(script_name: str, timeout_seconds: int) -> tuple[str, str, float]:
    """
    Returns:
        ("success", output, elapsed_seconds)
        ("degraded", output, elapsed_seconds)
        ("failed", output, elapsed_seconds)
    """
    script_path = BASE_DIR / script_name
    started = datetime.now().timestamp()

    if not script_path.exists():
        elapsed = datetime.now().timestamp() - started
        return ("failed", f"Script not found: {script_path}", elapsed)

    command = [PYTHON_EXE, str(script_path)]

    try:
        result = subprocess.run(
            command,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        combined_output_parts = []
        if stdout:
            combined_output_parts.append("STDOUT:\n" + stdout)
        if stderr:
            combined_output_parts.append("STDERR:\n" + stderr)

        combined_output = "\n\n".join(combined_output_parts).strip()
        elapsed = datetime.now().timestamp() - started

        if result.returncode == 0:
            return ("success", truncate_output(combined_output), elapsed)

        return (
            "failed",
            truncate_output(
                combined_output or f"{script_name} exited with return code {result.returncode}"
            ),
            elapsed,
        )

    except subprocess.TimeoutExpired as exc:
        partial_stdout = (exc.stdout or "").strip() if exc.stdout else ""
        partial_stderr = (exc.stderr or "").strip() if exc.stderr else ""

        combined_output_parts = [f"Timed out after {timeout_seconds} seconds."]
        if partial_stdout:
            combined_output_parts.append("PARTIAL STDOUT:\n" + partial_stdout)
        if partial_stderr:
            combined_output_parts.append("PARTIAL STDERR:\n" + partial_stderr)

        elapsed = datetime.now().timestamp() - started
        return ("degraded", truncate_output("\n\n".join(combined_output_parts)), elapsed)

    except Exception as exc:
        elapsed = datetime.now().timestamp() - started
        return (
            "failed",
            truncate_output(
                f"Exception while running {script_name}: {exc}\n{traceback.format_exc()}"
            ),
            elapsed,
        )


def main() -> int:
    os.chdir(BASE_DIR)

    log_blank_line()
    write_divider("=")
    log("MASTER RUNNER STARTED")
    log(f"BASE_DIR: {BASE_DIR}")
    log(f"PYTHON: {PYTHON_EXE}")
    log(f"LOG_FILE: {LOG_FILE}")
    log(f"LOCK_FILE: {LOCK_FILE}")
    log(f"LAST_RUN_FILE: {LAST_RUN_FILE}")

    if not acquire_lock():
        log("Exiting because another run is already active.")
        write_divider("=")
        return 1

    successful_scripts: list[str] = []
    degraded_scripts: list[str] = []
    failed_scripts: list[str] = []
    blocked_scripts: list[str] = []

    script_timings: dict[str, str] = {}
    required_failures: list[str] = []

    # If upstream content scripts fail, downstream builders can still run,
    # but their status may be marked degraded.
    upstream_report_issue = False

    try:
        log("BETTING BLOCK START")
        for script_name, timeout_seconds, required_for_pipeline in SCRIPTS:
            script_path = BASE_DIR / script_name

            if script_name not in ALWAYS_RUN and not script_path.exists():
                log(f"BLOCKED: {script_name} does not exist.")
                blocked_scripts.append(script_name)

                if required_for_pipeline:
                    required_failures.append(script_name)
                    upstream_report_issue = True
                continue

            log(f"START: {script_name}")

            status, output, elapsed = run_script(script_name, timeout_seconds)
            script_timings[script_name] = format_duration(elapsed)

            if output:
                log(f"OUTPUT from {script_name}:\n{output}")

            effective_status = status

            # If upstream scripts had issues, the two final builders should show degraded
            # even if they technically finish.
            if script_name in ALWAYS_RUN and status == "success" and upstream_report_issue:
                effective_status = "degraded"
                log(
                    f"DEGRADED: {script_name} completed, but earlier upstream scripts had issues."
                )

            if effective_status == "success":
                log(f"SUCCESS: {script_name} ({script_timings[script_name]})")
                successful_scripts.append(script_name)

            elif effective_status == "degraded":
                log(f"DEGRADED: {script_name} ({script_timings[script_name]})")
                degraded_scripts.append(script_name)

                if script_name not in ALWAYS_RUN:
                    upstream_report_issue = True
                    if required_for_pipeline:
                        required_failures.append(script_name)

            else:
                log(f"FAILED: {script_name} ({script_timings[script_name]})")
                failed_scripts.append(script_name)

                if script_name not in ALWAYS_RUN:
                    upstream_report_issue = True
                    if required_for_pipeline:
                        required_failures.append(script_name)

        missing_outputs = [str(path) for path in REQUIRED_OUTPUTS if not path.exists()]
        if missing_outputs:
            for path in missing_outputs:
                log(f"FAILED: required Betting output missing: {path}")
            failed_scripts.append("betting latest_report.json verification")

        log("BETTING BLOCK FINISH")

        has_critical_failure = any(name in failed_scripts for name in CRITICAL_SCRIPTS) or bool(missing_outputs)

        meaningful_failed_scripts = [
            name for name in failed_scripts if name not in NON_CRITICAL_FAILURES
        ]
        meaningful_degraded_scripts = [
            name for name in degraded_scripts if name not in NON_CRITICAL_FAILURES
        ]
        meaningful_blocked_scripts = [
            name for name in blocked_scripts if name not in NON_CRITICAL_FAILURES
        ]

        if has_critical_failure:
            pipeline_status = "FAILED"
        elif meaningful_failed_scripts or meaningful_degraded_scripts or meaningful_blocked_scripts:
            pipeline_status = "DEGRADED"
        else:
            pipeline_status = "SUCCESS"

        write_divider("-")
        log(f"PIPELINE STATUS: {pipeline_status}")
        log(f"Timestamp: {timestamp()}")
        log_blank_line()

        log(f"Successful scripts ({len(successful_scripts)}):")
        if successful_scripts:
            for name in successful_scripts:
                duration = script_timings.get(name, "unknown")
                log(f"- {name} [{duration}]")
        else:
            log("- None")

        log_blank_line()
        log(f"Degraded scripts ({len(degraded_scripts)}):")
        if degraded_scripts:
            for name in degraded_scripts:
                duration = script_timings.get(name, "unknown")
                log(f"- {name} [{duration}]")
        else:
            log("- None")

        log_blank_line()
        log(f"Failed scripts ({len(failed_scripts)}):")
        if failed_scripts:
            for name in failed_scripts:
                duration = script_timings.get(name, "unknown")
                log(f"- {name} [{duration}]")
        else:
            log("- None")

        log_blank_line()
        log(f"Blocked/skipped scripts ({len(blocked_scripts)}):")
        if blocked_scripts:
            for name in blocked_scripts:
                log(f"- {name}")
        else:
            log("- None")

        log_blank_line()
        log("Script runtimes:")
        if script_timings:
            for name, duration in script_timings.items():
                log(f"- {name}: {duration}")
        else:
            log("- None")

        if required_failures:
            log_blank_line()
            log("Required pipeline issues detected in:")
            for name in sorted(set(required_failures)):
                log(f"- {name}")

        if failed_scripts:
            log_blank_line()
            log("Failure classification:")
            for name in failed_scripts:
                if name in NON_CRITICAL_FAILURES:
                    log(f"- {name}: non-critical failure")
                elif name in CRITICAL_SCRIPTS:
                    log(f"- {name}: critical failure")
                else:
                    log(f"- {name}: standard failure")

        write_last_run_status(
            pipeline_status=pipeline_status,
            successful_scripts=successful_scripts,
            degraded_scripts=degraded_scripts,
            failed_scripts=failed_scripts,
            blocked_scripts=blocked_scripts,
            script_timings=script_timings,
        )

        write_divider("=")
        log("MASTER RUNNER FINISHED")
        write_divider("=")

        return 1 if pipeline_status == "FAILED" else 0

    finally:
        release_lock()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        log(f"FATAL ERROR IN MASTER RUNNER: {exc}")
        log(traceback.format_exc())
        release_lock()
        sys.exit(1)
