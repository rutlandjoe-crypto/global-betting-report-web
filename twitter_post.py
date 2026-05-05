from pathlib import Path
import os
import time

from dotenv import load_dotenv
import requests
from requests_oauthlib import OAuth1

# =========================================================
# SETUP
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

THREAD_FILE = BASE_DIR / "twitter_thread.txt"
X_POST_URL = "https://api.x.com/2/tweets"

MAX_TWEETS = 8
MAX_CHARS = 270

# Load credentials
X_API_KEY = os.getenv("TWITTER_API_KEY")
X_API_SECRET = os.getenv("TWITTER_API_SECRET")
X_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# =========================================================
# VALIDATE ENV
# =========================================================

def validate_env():
    required = {
        "TWITTER_API_KEY": X_API_KEY,
        "TWITTER_API_SECRET": X_API_SECRET,
        "TWITTER_ACCESS_TOKEN": X_ACCESS_TOKEN,
        "TWITTER_ACCESS_TOKEN_SECRET": X_ACCESS_TOKEN_SECRET,
    }

    missing = [k for k, v in required.items() if not v]

    if missing:
        raise ValueError(f"Missing credentials in .env: {', '.join(missing)}")

# =========================================================
# AUTH
# =========================================================

def get_auth():
    return OAuth1(
        X_API_KEY,
        X_API_SECRET,
        X_ACCESS_TOKEN,
        X_ACCESS_TOKEN_SECRET
    )

# =========================================================
# THREAD BUILDING
# =========================================================

def normalize_text(raw: str) -> str:
    return raw.replace("\r\n", "\n").strip()

def split_manual_parts(raw: str):
    """
    If twitter_thread.txt uses explicit separators, respect them:
    Tweet 1

    ---

    Tweet 2
    """
    parts = [p.strip() for p in raw.split("\n\n---\n\n") if p.strip()]
    return parts

def compact_lines_into_thread(raw: str, max_tweets=8, max_chars=270):
    """
    Convert a long text file into a compact X thread.

    Rules:
    - ignore blank lines
    - combine multiple lines into each tweet
    - keep each tweet under max_chars
    - cap thread at max_tweets
    - add numbering automatically
    """
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        raise ValueError("twitter_thread.txt is empty.")

    chunks = []
    current = ""

    for line in lines:
        candidate = f"{current}\n{line}".strip() if current else line

        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = line

    if current:
        chunks.append(current)

    if not chunks:
        raise ValueError("No tweet parts found.")

    # If too many chunks, merge overflow into final tweet
    if len(chunks) > max_tweets:
        kept = chunks[:max_tweets - 1]
        overflow = chunks[max_tweets - 1:]

        final_chunk = "\n".join(overflow)
        if len(final_chunk) > max_chars:
            final_chunk = final_chunk[:max_chars - 3].rstrip() + "..."

        kept.append(final_chunk)
        chunks = kept

    total = len(chunks)
    numbered = []

    for i, chunk in enumerate(chunks, start=1):
        prefix = f"{i}/{total} "
        allowed = max_chars - len(prefix)

        if len(chunk) > allowed:
            chunk = chunk[:allowed - 3].rstrip() + "..."

        numbered.append(prefix + chunk)

    return numbered

def load_thread_parts():
    if not THREAD_FILE.exists():
        raise FileNotFoundError(f"Missing file: {THREAD_FILE}")

    raw = normalize_text(THREAD_FILE.read_text(encoding="utf-8"))

    if not raw:
        raise ValueError("twitter_thread.txt is empty.")

    # If you manually separated tweets with ---, preserve that
    if "\n\n---\n\n" in raw:
        manual_parts = split_manual_parts(raw)

        if len(manual_parts) > MAX_TWEETS:
            manual_parts = manual_parts[:MAX_TWEETS]

        total = len(manual_parts)
        numbered = []

        for i, part in enumerate(manual_parts, start=1):
            prefix = f"{i}/{total} "
            allowed = MAX_CHARS - len(prefix)

            if len(part) > allowed:
                part = part[:allowed - 3].rstrip() + "..."

            numbered.append(prefix + part)

        return numbered

    # Otherwise auto-compact the file into a tighter thread
    return compact_lines_into_thread(raw, max_tweets=MAX_TWEETS, max_chars=MAX_CHARS)

# =========================================================
# POST TWEET
# =========================================================

def post_tweet(text, reply_to=None):
    payload = {"text": text}

    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}

    response = requests.post(
        X_POST_URL,
        auth=get_auth(),
        json=payload,
        timeout=30
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(f"X API error: {response.status_code} | {response.text}")

    data = response.json()
    tweet_id = data.get("data", {}).get("id")

    if not tweet_id:
        raise RuntimeError("No tweet ID returned.")

    return tweet_id

# =========================================================
# MAIN
# =========================================================

def main():
    validate_env()
    parts = load_thread_parts()

    previous_id = None

    for i, part in enumerate(parts, start=1):
        tweet_id = post_tweet(part, previous_id)
        previous_id = tweet_id

        print(f"Posted tweet {i}/{len(parts)}")
        time.sleep(1)

    print("X thread posted successfully.")

# =========================================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAILED: {e}")
        raise