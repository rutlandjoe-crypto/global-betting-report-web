import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# =========================================================
# PATH / ENV
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

TELEGRAM_POST_FILE = Path(
    os.getenv("TELEGRAM_OUTPUT_FILE", BASE_DIR / "telegram_post.txt")
)

REQUEST_TIMEOUT = 20


# =========================================================
# HELPERS
# =========================================================
def read_telegram_post() -> str:
    if not TELEGRAM_POST_FILE.exists():
        raise FileNotFoundError(
            f"Telegram post file not found: {TELEGRAM_POST_FILE}"
        )

    text = TELEGRAM_POST_FILE.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("Telegram post file is empty.")

    return text


def validate_env() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN in .env")

    if not TELEGRAM_CHAT_ID:
        raise ValueError("Missing TELEGRAM_CHAT_ID in .env")


def split_message(text: str, max_len: int = 3500) -> list[str]:
    """
    Split long Telegram text into safe chunks.
    Keeps breaks on paragraph boundaries when possible.
    """
    if len(text) <= max_len:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_len:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(para) <= max_len:
            current = para
            continue

        # hard wrap oversized paragraph
        words = para.split()
        part = ""

        for word in words:
            candidate = f"{part} {word}".strip() if part else word
            if len(candidate) <= max_len:
                part = candidate
            else:
                if part:
                    chunks.append(part)
                part = word

        if part:
            current = part

    if current:
        chunks.append(current)

    return chunks


# =========================================================
# TELEGRAM API
# =========================================================
def send_telegram_message(text: str) -> dict:
    """
    Sends one Telegram message using Bot API sendMessage.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }

    response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")

    return data


def send_telegram_post() -> list[dict]:
    validate_env()
    text = read_telegram_post()
    chunks = split_message(text)

    results = []
    for chunk in chunks:
        results.append(send_telegram_message(chunk))

    return results


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    try:
        results = send_telegram_post()
        print("✅ Telegram post sent successfully.")
        print(f"Messages sent: {len(results)}")
    except Exception as exc:
        print("❌ Telegram send failed.")
        print(f"Error: {exc}")