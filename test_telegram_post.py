from pathlib import Path
from footer_utils import build_report_footer

BASE_DIR = Path(__file__).resolve().parent
REPORT_FILE = BASE_DIR / "global_sports_report.txt"


def load_report_text() -> str:
    if not REPORT_FILE.exists():
        return "No report found yet. Run your report generator first."
    return REPORT_FILE.read_text(encoding="utf-8").strip()


def build_telegram_preview(report_text: str) -> str:
    footer = build_report_footer("telegram")
    return f"{report_text}\n\n---\n\n{footer}"


def main():
    report_text = load_report_text()
    telegram_post = build_telegram_preview(report_text)

    print("\n===== TELEGRAM POST PREVIEW =====\n")
    print(telegram_post)
    print("\n===== POST METRICS =====")
    print(f"Characters: {len(telegram_post)}")

    if len(telegram_post) > 4096:
        print("WARNING: Telegram message may be too long.")
    else:
        print("OK: Telegram length looks safe.")

    print("\n===== END PREVIEW =====\n")


if __name__ == "__main__":
    main()