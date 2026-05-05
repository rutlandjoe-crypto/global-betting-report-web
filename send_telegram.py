import os
from pathlib import Path
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL = os.getenv("TELEGRAM_CHANNEL")
POST_FILE = BASE_DIR / "telegram_post.txt"

MAX_LEN = 3900  # safe limit under Telegram max message size


def chunk_text(text: str, max_len: int = MAX_LEN) -> list[str]:
    text = text.strip()
    if len(text) <= max_len:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > max_len:
        split_at = remaining.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = remaining.rfind(" ", 0, max_len)
        if split_at == -1:
            split_at = max_len

        chunk = remaining[:split_at].strip()
        if chunk:
            chunks.append(chunk)

        remaining = remaining[split_at:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


def send_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHANNEL,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    print(response.status_code)
    print(response.text)

    if response.status_code != 200:
        raise RuntimeError(f"Telegram send failed: {response.text}")


def send() -> None:
    if not TOKEN:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN in .env")

    if not CHANNEL:
        raise ValueError("Missing TELEGRAM_CHANNEL in .env")

    if not POST_FILE.exists():
        raise FileNotFoundError("telegram_post.txt not found")

    text = POST_FILE.read_text(encoding="utf-8").strip()
    chunks = chunk_text(text)

    total = len(chunks)

    for i, chunk in enumerate(chunks, start=1):
        if total > 1:
            header = f"Global Sports Report ({i}/{total})\n\n"
            send_message(header + chunk)
        else:
            send_message(chunk)


if __name__ == "__main__":
    send()