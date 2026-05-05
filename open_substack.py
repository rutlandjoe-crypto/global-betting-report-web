import os
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SUBSTACK_URL = os.getenv("GSR_SUBSTACK_URL", "https://globalsportsreport.substack.com").strip()

TITLE_FILE = BASE_DIR / "dist" / "substack" / "substack_title.txt"
BODY_FILE = BASE_DIR / "dist" / "substack" / "global_substack.md"


def main() -> None:
    if not TITLE_FILE.exists():
        raise FileNotFoundError(f"Missing title file: {TITLE_FILE}")

    if not BODY_FILE.exists():
        raise FileNotFoundError(f"Missing body file: {BODY_FILE}")

    title = TITLE_FILE.read_text(encoding="utf-8").strip()
    body = BODY_FILE.read_text(encoding="utf-8").strip()

    print("=" * 60)
    print("SUBSTACK TITLE")
    print(title)
    print("=" * 60)
    print("SUBSTACK BODY PREVIEW")
    print(body[:2000] + ("\n..." if len(body) > 2000 else ""))
    print("=" * 60)
    print(f"Full body file: {BODY_FILE}")

    # Open publication homepage and generic Substack web entry point
    webbrowser.open(SUBSTACK_URL)
    webbrowser.open("https://substack.com/home")

    # Optional clipboard support
    try:
        import pyperclip  # pip install pyperclip
        pyperclip.copy(body)
        print("✅ Substack body copied to clipboard")
    except Exception:
        print("ℹ️ Clipboard copy skipped (install pyperclip if you want this).")


if __name__ == "__main__":
    main()