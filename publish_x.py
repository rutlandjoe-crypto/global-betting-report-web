import os
from pathlib import Path

from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("X_API_KEY", "").strip()
API_SECRET = os.getenv("X_API_SECRET", "").strip()
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "").strip()
ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "").strip()

THREAD_FILE = BASE_DIR / "dist" / "x" / "global_x_thread.txt"
POST_URL = "https://api.x.com/2/tweets"


def load_thread_posts() -> list[str]:
    if not THREAD_FILE.exists():
        raise FileNotFoundError(f"Missing thread file: {THREAD_FILE}")

    raw = THREAD_FILE.read_text(encoding="utf-8")
    posts = [part.strip() for part in raw.split("\n\n---\n\n") if part.strip()]

    if not posts:
        raise ValueError("No thread posts found in the X distribution file.")

    return posts


def get_client() -> OAuth1Session:
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        raise ValueError("Missing one or more X API credentials in .env")

    return OAuth1Session(
        API_KEY,
        client_secret=API_SECRET,
        resource_owner_key=ACCESS_TOKEN,
        resource_owner_secret=ACCESS_TOKEN_SECRET,
    )


def create_post(client: OAuth1Session, text: str, reply_to_id: str | None = None) -> str:
    payload = {"text": text}
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

    response = client.post(POST_URL, json=payload)

    if response.status_code not in (200, 201):
        raise RuntimeError(f"X post failed: {response.status_code} | {response.text}")

    data = response.json()
    return data["data"]["id"]


def publish_thread() -> list[str]:
    posts = load_thread_posts()
    client = get_client()

    posted_ids: list[str] = []
    previous_id = None

    for post in posts:
        tweet_id = create_post(client, post, reply_to_id=previous_id)
        posted_ids.append(tweet_id)
        previous_id = tweet_id

    return posted_ids


def main() -> None:
    ids = publish_thread()
    print(f"✅ Posted X thread successfully ({len(ids)} posts)")


if __name__ == "__main__":
    main()