import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def run_script(script_name):
    try:
        print(f"\n▶ Running {script_name}...")
        result = subprocess.run(
            ["python", script_name],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print("⚠️ Error output:")
            print(result.stderr)

        if result.returncode == 0:
            print(f"✅ Finished {script_name}")
        else:
            print(f"❌ {script_name} exited with code {result.returncode}")

    except Exception as e:
        print(f"❌ Failed to run {script_name}: {e}")


def main():
    print("🚀 GLOBAL SPORTS REPORT — MORNING PIPELINE\n")

    # 1. League reports
    run_script("get_mlb_report.py")
    run_script("get_nba_report.py")
    run_script("get_nhl_report.py")
    run_script("get_soccer_report.py")

    # 2. Global report builder
    run_script("global_report.py")

    # 3. Premium Substack builder
    run_script("build_substack.py")

    # 4. Platform distribution builder
    run_script("build_distribution.py")

    print("\n🎯 ALL OUTPUTS READY")
    print("→ substack_post.txt")
    print("→ twitter_thread.txt")
    print("→ telegram_post.txt")
    print("\nYou’re ready to publish.")


if __name__ == "__main__":
    main()