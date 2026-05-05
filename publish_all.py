from pathlib import Path
import subprocess
import sys

# =========================================================
# PATH SETUP
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

SCRIPTS = [
    "global_sports_report.py",
    "build_distribution.py",
    "telegram_post.py",
    "twitter_post.py",
]

# =========================================================
# HELPERS
# =========================================================

def run_script(script_name: str) -> bool:
    script_path = BASE_DIR / script_name

    if not script_path.exists():
        print(f"Missing script: {script_name}")
        return False

    print("=" * 60)
    print(f"RUNNING: {script_name}")
    print("=" * 60)

    result = subprocess.run(
        [PYTHON_EXE, str(script_path)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True
    )

    if result.stdout:
        print(result.stdout.strip())

    if result.stderr:
        print("STDERR:")
        print(result.stderr.strip())

    if result.returncode != 0:
        print(f"FAILED: {script_name} exited with code {result.returncode}")
        return False

    print(f"COMPLETED: {script_name}")
    return True

# =========================================================
# MAIN
# =========================================================

def main():
    print("Starting Global Sports Report publishing pipeline...\n")

    for script in SCRIPTS:
        success = run_script(script)
        if not success:
            print("\nPipeline stopped.")
            return

    print("\nPublishing pipeline completed successfully.")

if __name__ == "__main__":
    main()