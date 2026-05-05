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

# Platform toggles
ENABLE_TELEGRAM = os.getenv("ENABLE_TELEGRAM", "true").strip().lower() == "true"
ENABLE_TWITTER = os.getenv("ENABLE_TWITTER", "true").strip().lower() == "true"
ENABLE_SUBSTACK = os.getenv("ENABLE_SUBSTACK", "true").strip().lower() == "true"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Twitter / X
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "").strip()
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "").strip()
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
TWITTER_ACCESS_SECRET = (
    os.getenv("TWITTER_ACCESS_SECRET", "").strip()
    or os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "").strip()
)
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "").strip()

# Branding
X_HANDLE = os.getenv("GSR_X_HANDLE", "@GlobalSportsRep").strip()
SUBSTACK_URL = os.getenv(
    "GSR_SUBSTACK_URL",
    "https://globalsportsreport.substack.com/"
).strip()

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
    "error:",
    "exception:",
]


# =========================================================
# LOGGING
# =========================================================

def timestamp_et() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %I:%M:%S %p %Z")


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
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("generated:"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def collapse_duplicate_disclaimer(text: str) -> str:
    pattern = re.escape(DISCLAIMER)
    matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
    if len(matches) <= 1:
        return text

    first = matches[0]
    first_text = text[first.start():first.end()]
    text_without_duplicates = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    return f"{text_without_duplicates}\n\n{first_text}"


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

    if "GLOBAL SPORTS REPORT" not in text.upper():
        log("Warning: report does not contain 'GLOBAL SPORTS REPORT' header.")

    if len(text) < 250:
        fail("Report is too short to distribute safely.")


# =========================================================
# CONTENT BUILDERS
# =========================================================

def get_title_line(report_text: str) -> str:
    for line in report_text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return "GLOBAL SPORTS REPORT"


def get_headline_block(report_text: str) -> str:
    lines = [line.rstrip() for line in report_text.splitlines()]
    headline_idx = None

    for i, line in enumerate(lines):
        if line.strip().upper() == "HEADLINE":
            headline_idx = i
            break

    if headline_idx is None:
        return ""

    collected = []
    for line in lines[headline_idx + 1:]:
        stripped = line.strip()
        if not stripped:
            if collected:
                break
            continue
        if stripped.isupper() and len(stripped) < 40:
            break
        collected.append(stripped)

    return " ".join(collected).strip()


def get_key_results(report_text: str, max_items: int = 4) -> List[str]:
    lines = [line.rstrip() for line in report_text.splitlines()]
    start_idx = None

    for i, line in enumerate(lines):
        if line.strip().upper() in {"KEY RESULTS", "KEY STORYLINES"}:
            start_idx = i
            break

    if start_idx is None:
        return []

    items: List[str] = []
    for line in lines[start_idx + 1:]:
        stripped = line.strip()
        if not stripped:
            if items:
                break
            continue
        if stripped.isupper() and len(stripped) < 40:
            break
        if stripped.startswith("•"):
            items.append(stripped.lstrip("•").strip())
        elif re.match(r"^\d+\.", stripped):
            items.append(re.sub(r"^\d+\.\s*", "", stripped))
        else:
            if items:
                break

    return items[:max_items]


def build_telegram_post(report_text: str) -> str:
    title = get_title_line(report_text)
    headline = get_headline_block(report_text)
    key_results = get_key_results(report_text, max_items=4)

    parts: List[str] = [title]

    if headline:
        parts.append(headline)

    if key_results:
        bullet_block = "\n".join(f"• {item}" for item in key_results)
        parts.append(bullet_block)

    parts.append(DISCLAIMER)
    parts.append(f"Read more: {SUBSTACK_URL}")
    parts.append(f"Follow on X: {X_HANDLE}")

    return "\n\n".join(part for part in parts if part.strip()).strip()


def build_substack_html(report_text: str) -> str:
    safe_text = html.escape(report_text)
    safe_text = safe_text.replace("\n\n", "</p><p>").replace("\n", "<br>")

    footer = (
        f"<hr>"
        f"<p><em>{html.escape(DISCLAIMER)}</em></p>"
        f"<p>Follow Global Sports Report on X: "
        f"<a href='https://x.com/{html.escape(X_HANDLE.lstrip('@'))}'>{html.escape(X_HANDLE)}</a></p>"
        f"<p>Read more at <a href='{html.escape(SUBSTACK_URL)}'>{html.escape(SUBSTACK_URL)}</a></p>"
    )

    return f"<p>{safe_text}</p>{footer}"


def build_twitter_intro(report_text: str) -> str:
    title = get_title_line(report_text)
    headline = get_headline_block(report_text)
    key_results = get_key_results(report_text, max_items=3)

    lines: List[str] = [title]

    if headline:
        lines.append(headline)

    if key_results:
        for item in key_results:
            lines.append(f"• {item}")

    lines.append(f"{X_HANDLE}")
    return "\n".join(lines).strip()


def split_thread(text: str, max_len: int = 275) -> List[str]:
    text = normalize_text(text)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []

    current = ""
    for para in paragraphs:
        candidate = para if not current else f"{current}\n\n{para}"
        if len(candidate) <= max_len:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(para) <= max_len:
            current = para
            continue

        # Hard split long paragraphs by sentence first
        sentence_parts = re.split(r"(?<=[.!?])\s+", para)
        temp = ""
        for sentence in sentence_parts:
            candidate_sentence = sentence if not temp else f"{temp} {sentence}"
            if len(candidate_sentence) <= max_len:
                temp = candidate_sentence
            else:
                if temp:
                    chunks.append(temp)
                if len(sentence) <= max_len:
                    temp = sentence
                else:
                    # final hard split by character
                    for i in range(0, len(sentence), max_len):
                        chunks.append(sentence[i:i + max_len].strip())
                    temp = ""
        if temp:
            current = temp

    if current:
        chunks.append(current)

    total = len(chunks)
    numbered: List[str] = []

    for i, chunk in enumerate(chunks, start=1):
        prefix = f"{i}/{total} "
        allowed = max_len - len(prefix)
        numbered.append(prefix + chunk[:allowed].rstrip())

    return numbered


def build_twitter_thread(report_text: str) -> List[str]:
    intro = build_twitter_intro(report_text)

    body_sections = []
    lines = [line.rstrip() for line in report_text.splitlines()]
    capture = False
    for line in lines:
        stripped = line.strip()

        if stripped.upper() in {"KEY RESULTS", "KEY STORYLINES", "HEADLINE"}:
            capture = False
            continue

        if stripped.upper() == "SNAPSHOT":
            capture = True

        if capture and stripped:
            body_sections.append(stripped)

    body_text = "\n\n".join(body_sections[:12]).strip()

    thread_source = f"{intro}\n\n{body_text}\n\n{DISCLAIMER}\n{SUBSTACK_URL}"
    parts = split_thread(thread_source, max_len=275)

    # Keep thread length reasonable
    return parts[:8]


# =========================================================
# DEDUPE / HASH
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

    save_text_file(SUBSTACK_POST_FILE, html_content)

    if SUBSTACK_PUBLISH_SCRIPT:
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
    else:
        log("No Substack publish script configured. Saved HTML-ready file only.")


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