import os
from pathlib import Path
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POST_FILE = BASE_DIR / "telegram_post.txt"


def load_post_text() -> str:
    if not POST_FILE.exists():
        raise FileNotFoundError(f"Missing file: {POST_FILE}")
    text = POST_FILE.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("telegram_post.txt is empty.")
    return text


def split_message(text: str, limit: int = 4000) -> list[str]:
    parts = []
    remaining = text.strip()

    while remaining:
        if len(remaining) <= limit:
            parts.append(remaining)
            break

        cut = remaining.rfind("\n", 0, limit)
        if cut == -1:
            cut = remaining.rfind(" ", 0, limit)
        if cut == -1:
            cut = limit

        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()

    return [p for p in parts if p]


def send_telegram_message(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN in .env")
    if not TELEGRAM_CHAT_ID:
        raise ValueError("Missing TELEGRAM_CHAT_ID in .env")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    message_parts = split_message(text)

    for index, part in enumerate(message_parts, start=1):
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": part,
        }

        response = requests.post(url, data=payload, timeout=30)

        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise RuntimeError(
                f"Telegram API error on part {index}: "
                f"{response.status_code} | {response.text}"
            )

        print(f"Sent Telegram message part {index}/{len(message_parts)}")
        footer = build_report_footer("telegram")
        telegram_post = report_text.strip() + "\n\n---\n\n" + footer


def main():
    try:
        text = load_post_text()
        send_telegram_message(text)
        print("Telegram post complete.")
    except Exception as e:
        print(f"Telegram post failed: {e}")


if __name__ == "__main__":
    main()