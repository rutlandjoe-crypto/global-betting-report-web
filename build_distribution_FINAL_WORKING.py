from __future__ import annotations

import hashlib
import html
import os
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

try:
    import tweepy
except ImportError:
    tweepy = None


# =========================================================
# PATHS / ENV
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

GLOBAL_REPORT_FILE = BASE_DIR / "global_sports_report.txt"
TELEGRAM_POST_FILE = BASE_DIR / "telegram_post.txt"
TWITTER_THREAD_FILE = BASE_DIR / "twitter_thread.txt"
SUBSTACK_POST_FILE = BASE_DIR / "substack_post.html"
THREAD_HASH_FILE = BASE_DIR / ".last_twitter_hash.txt"

SUBSTACK_PUBLISH_SCRIPT = os.getenv("SUBSTACK_PUBLISH_SCRIPT", "").strip()

ENABLE_TELEGRAM = os.getenv("ENABLE_TELEGRAM", "true").strip().lower() == "true"
ENABLE_TWITTER = os.getenv("ENABLE_TWITTER", "true").strip().lower() == "true"
ENABLE_SUBSTACK = os.getenv("ENABLE_SUBSTACK", "true").strip().lower() == "true"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "").strip()
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "").strip()
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
TWITTER_ACCESS_SECRET = (
    os.getenv("TWITTER_ACCESS_SECRET", "").strip()
    or os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "").strip()
)
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "").strip()

X_HANDLE = os.getenv("GSR_X_HANDLE", "@GlobalSportsRep").strip()
SUBSTACK_URL = os.getenv(
    "GSR_SUBSTACK_URL",
    "https://globalsportsreport.substack.com/"
).strip()

LOG_TIMEZONE = ZoneInfo("America/New_York")

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, "
    "human sports journalism."
)

BROKEN_PATTERNS = [
    "could not load",
    "unexpected error",
    "traceback",
    "fatal error",
    "missing api key",
    "exception:",
]


# =========================================================
# LOGGING
# =========================================================

def timestamp_et() -> str:
    return datetime.now(LOG_TIMEZONE).strftime("%Y-%m-%d %I:%M:%S %p %Z")


def log(message: str) -> None:
    print(f"[{timestamp_et()}] {message}")


def fail(message: str, exit_code: int = 1) -> None:
    log(f"FATAL ERROR: {message}")
    sys.exit(exit_code)


# =========================================================
# TEXT HELPERS
# =========================================================

def fix_encoding(text: str) -> str:
    return (
        text.replace("â€™", "’")
        .replace("â€˜", "‘")
        .replace("â€œ", "“")
        .replace("â€\x9d", "”")
        .replace("â€”", "—")
        .replace("â€“", "–")
        .replace("â€¢", "•")
        .replace("\ufeff", "")
    )


def normalize_text(text: str) -> str:
    text = fix_encoding(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_generated_lines(text: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        if line.strip().lower().startswith("generated:"):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def collapse_duplicate_disclaimer(text: str) -> str:
    lines = text.splitlines()
    cleaned = []
    seen = False

    for line in lines:
        if line.strip().lower() == DISCLAIMER.lower():
            if seen:
                continue
            seen = True
        cleaned.append(line)

    return "\n".join(cleaned).strip()


def ensure_disclaimer(text: str) -> str:
    if DISCLAIMER.lower() in text.lower():
        return collapse_duplicate_disclaimer(text)
    return f"{text.strip()}\n\n{DISCLAIMER}"


def clean_report(text: str) -> str:
    text = normalize_text(text)
    text = remove_generated_lines(text)
    text = ensure_disclaimer(text)
    text = collapse_duplicate_disclaimer(text)
    return text.strip()


# =========================================================
# FILE HELPERS
# =========================================================

def read_text_file(path: Path) -> str:
    if not path.exists():
        fail(f"Missing file: {path.name}")
    return path.read_text(encoding="utf-8", errors="replace")


def save_text_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    log(f"Saved: {path.name}")


# =========================================================
# VALIDATION
# =========================================================

def validate_report(text: str) -> None:
    if not text.strip():
        fail("Report is empty.")

    lower_text = text.lower()

    for bad in BROKEN_PATTERNS:
        if bad in lower_text:
            fail(f"Report appears broken or incomplete: found '{bad}'.")

    if len(text) < 250:
        fail("Report is too short to distribute safely.")


# =========================================================
# CONTENT HELPERS
# =========================================================

def get_title_line(report_text: str) -> str:
    for line in report_text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return "GLOBAL SPORTS REPORT"


def get_section_block(report_text: str, section_name: str) -> List[str]:
    lines = report_text.splitlines()
    collected: List[str] = []
    in_section = False

    for line in lines:
        stripped = line.strip()

        if stripped.upper() == section_name.upper():
            in_section = True
            continue

        if in_section:
            if stripped and stripped.isupper() and stripped != stripped.lower():
                break
            collected.append(line)

    return [line.strip() for line in collected if line.strip()]


def get_headline_block(report_text: str) -> str:
    lines = get_section_block(report_text, "HEADLINE")
    return " ".join(lines).strip()


def get_key_results(report_text: str, max_items: int = 4) -> List[str]:
    section_lines = get_section_block(report_text, "KEY RESULTS")
    if not section_lines:
        section_lines = get_section_block(report_text, "KEY STORYLINES")

    items: List[str] = []
    for line in section_lines:
        stripped = line.strip()
        if stripped.startswith("•"):
            items.append(stripped.lstrip("•").strip())
        elif re.match(r"^\d+\.", stripped):
            items.append(re.sub(r"^\d+\.\s*", "", stripped))
        elif stripped:
            items.append(stripped)

    return items[:max_items]


# =========================================================
# PLATFORM BUILDERS
# =========================================================

def build_telegram_post(report_text: str) -> str:
    title = get_title_line(report_text)
    headline = get_headline_block(report_text)
    key_results = get_key_results(report_text, max_items=4)

    parts: List[str] = [title]

    if headline:
        parts.append(headline)

    if key_results:
        parts.append("\n".join(f"• {item}" for item in key_results))

    parts.append(DISCLAIMER)
    parts.append(f"Read more: {SUBSTACK_URL}")
    parts.append(f"Follow on X: {X_HANDLE}")

    return "\n\n".join(part for part in parts if part.strip()).strip()


def build_substack_html(report_text: str) -> str:
    safe_text = html.escape(report_text)
    paragraphs = safe_text.split("\n\n")
    html_body = "".join(
        f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs if p.strip()
    )

    footer = (
        "<hr>"
        f"<p><em>{html.escape(DISCLAIMER)}</em></p>"
        f"<p>Follow Global Sports Report on X: "
        f"<a href='https://x.com/{html.escape(X_HANDLE.lstrip('@'))}'>{html.escape(X_HANDLE)}</a></p>"
        f"<p>Read more at <a href='{html.escape(SUBSTACK_URL)}'>{html.escape(SUBSTACK_URL)}</a></p>"
    )

    return html_body + footer


def build_twitter_intro(report_text: str) -> str:
    title = get_title_line(report_text)
    headline = get_headline_block(report_text)
    key_results = get_key_results(report_text, max_items=3)

    lines: List[str] = [title]

    if headline:
        lines.append(headline)

    for item in key_results:
        lines.append(f"• {item}")

    return "\n".join(lines).strip()


def split_thread(text: str, max_len: int = 275) -> List[str]:
    text = normalize_text(text)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    raw_chunks: List[str] = []

    current = ""

    for para in paragraphs:
        candidate = para if not current else f"{current}\n\n{para}"

        if len(candidate) <= max_len:
            current = candidate
            continue

        if current:
            raw_chunks.append(current)
            current = ""

        if len(para) <= max_len:
            current = para
            continue

        sentences = re.split(r"(?<=[.!?])\s+", para)
        sentence_chunk = ""

        for sentence in sentences:
            sentence_candidate = sentence if not sentence_chunk else f"{sentence_chunk} {sentence}"

            if len(sentence_candidate) <= max_len:
                sentence_chunk = sentence_candidate
            else:
                if sentence_chunk:
                    raw_chunks.append(sentence_chunk)

                if len(sentence) <= max_len:
                    sentence_chunk = sentence
                else:
                    for i in range(0, len(sentence), max_len):
                        raw_chunks.append(sentence[i:i + max_len].strip())
                    sentence_chunk = ""

        if sentence_chunk:
            current = sentence_chunk

    if current:
        raw_chunks.append(current)

    total = len(raw_chunks)
    numbered_chunks: List[str] = []

    for i, chunk in enumerate(raw_chunks, start=1):
        prefix = f"{i}/{total} "
        allowed_len = max_len - len(prefix)
        numbered_chunks.append(prefix + chunk[:allowed_len].rstrip())

    return numbered_chunks


def build_twitter_thread(report_text: str) -> List[str]:
    intro = build_twitter_intro(report_text)

    body_lines: List[str] = []
    capture = False

    for line in report_text.splitlines():
        stripped = line.strip()

        if stripped.upper() in {"HEADLINE", "KEY RESULTS", "KEY STORYLINES"}:
            capture = False
            continue

        if stripped.upper() == "SNAPSHOT":
            capture = True

        if capture and stripped:
            body_lines.append(stripped)

    body_text = "\n\n".join(body_lines[:12]).strip()

    thread_source = (
        f"{intro}\n\n"
        f"{body_text}\n\n"
        f"{DISCLAIMER}\n"
        f"{SUBSTACK_URL}"
    )

    return split_thread(thread_source, max_len=275)[:8]


# =========================================================
# HASH / DUPLICATE PROTECTION
# =========================================================

def compute_hash(parts: List[str]) -> str:
    joined = "\n||\n".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def should_post_thread(parts: List[str]) -> Tuple[bool, str]:
    new_hash = compute_hash(parts)

    if THREAD_HASH_FILE.exists():
        old_hash = THREAD_HASH_FILE.read_text(encoding="utf-8").strip()
        if old_hash == new_hash:
            return False, new_hash

    return True, new_hash


def save_thread_hash(thread_hash: str) -> None:
    THREAD_HASH_FILE.write_text(thread_hash, encoding="utf-8")


# =========================================================
# TELEGRAM
# =========================================================

def send_telegram_message(text: str) -> None:
    if not ENABLE_TELEGRAM:
        log("Telegram disabled by config.")
        return

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("Telegram credentials missing. Skipping Telegram send.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": False,
    }

    response = requests.post(url, data=payload, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"Telegram send failed: {response.status_code} {response.text}"
        )

    log("Telegram post sent successfully.")


# =========================================================
# TWITTER / X
# =========================================================

def get_twitter_client() -> Optional["tweepy.Client"]:
    if not ENABLE_TWITTER:
        log("Twitter disabled by config.")
        return None

    if tweepy is None:
        log("tweepy is not installed. Run: pip install tweepy")
        return None

    required = [
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_SECRET,
    ]

    if not all(required):
        log("Twitter credentials missing. Skipping Twitter send.")
        return None

    return tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET,
        bearer_token=TWITTER_BEARER_TOKEN or None,
        wait_on_rate_limit=True,
    )


def post_twitter_thread(parts: List[str]) -> None:
    client = get_twitter_client()
    if client is None:
        return

    should_post, new_hash = should_post_thread(parts)
    if not should_post:
        log("Twitter thread unchanged. Skipping duplicate post.")
        return

    previous_tweet_id = None

    for idx, part in enumerate(parts, start=1):
        if previous_tweet_id is None:
            response = client.create_tweet(text=part)
        else:
            response = client.create_tweet(
                text=part,
                in_reply_to_tweet_id=previous_tweet_id
            )

        previous_tweet_id = response.data["id"]
        log(f"Posted tweet {idx}/{len(parts)}")

    save_thread_hash(new_hash)
    log("Twitter thread posted successfully.")


# =========================================================
# SUBSTACK
# =========================================================

def publish_to_substack_if_configured(html_content: str) -> None:
    if not ENABLE_SUBSTACK:
        log("Substack disabled by config.")
        return

    if not SUBSTACK_PUBLISH_SCRIPT:
        log("No Substack publish script configured. Saved HTML-ready file only.")
        return

    script_path = Path(SUBSTACK_PUBLISH_SCRIPT)

    if not script_path.exists():
        log("Substack publish script path does not exist. Saved HTML only.")
        return

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), str(SUBSTACK_POST_FILE)],
            cwd=script_path.parent,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.stdout.strip():
            print(result.stdout)

        if result.returncode != 0:
            if result.stderr.strip():
                print(result.stderr)
            raise RuntimeError("Substack publish script failed.")

        log("Substack publish script completed successfully.")
    except Exception as exc:
        raise RuntimeError(f"Substack publish failed: {exc}") from exc


# =========================================================
# MAIN
# =========================================================

def main() -> None:
    log("Starting build_distribution.py")

    report_raw = read_text_file(GLOBAL_REPORT_FILE)
    report_text = clean_report(report_raw)
    validate_report(report_text)

    telegram_post = build_telegram_post(report_text)
    twitter_parts = build_twitter_thread(report_text)
    twitter_thread_text = "\n\n".join(twitter_parts)
    substack_html = build_substack_html(report_text)

    save_text_file(TELEGRAM_POST_FILE, telegram_post)
    save_text_file(TWITTER_THREAD_FILE, twitter_thread_text)
    save_text_file(SUBSTACK_POST_FILE, substack_html)

    send_telegram_message(telegram_post)
    post_twitter_thread(twitter_parts)
    publish_to_substack_if_configured(substack_html)

    log("Distribution build complete.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(str(exc))