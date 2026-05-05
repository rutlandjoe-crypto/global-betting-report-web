from __future__ import annotations

import html
import re
import sys
import webbrowser
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================================================
# CONFIG
# =========================================================
BASE_DIR = Path(__file__).resolve().parent

TIMEZONE = ZoneInfo("America/New_York")

# Preferred input files:
# 1) substack_post.html  -> used as-is
# 2) substack_post.txt   -> converted to HTML
INPUT_HTML = BASE_DIR / "substack_post.html"
INPUT_TEXT = BASE_DIR / "substack_post.txt"

# Output files
READY_HTML = BASE_DIR / "substack_ready.html"
PREVIEW_HTML = BASE_DIR / "substack_preview.html"

# Your Substack publication URLs
SUBSTACK_NEW_POST_URL = "https://globalsportsreport.substack.com/publish/post"
SUBSTACK_DASHBOARD_URL = "https://globalsportsreport.substack.com/publish"

DISCLAIMER = (
    "This report is an automated summary intended to support, not replace, "
    "human sports journalism."
)

# =========================================================
# HELPERS
# =========================================================
def now_et_string() -> str:
    return datetime.now(TIMEZONE).strftime("%B %d, %Y %I:%M %p ET")


def read_source() -> tuple[str, str]:
    """
    Returns:
        content, source_type
    source_type:
        "html" or "text"
    """
    if INPUT_HTML.exists():
        return INPUT_HTML.read_text(encoding="utf-8"), "html"

    if INPUT_TEXT.exists():
        return INPUT_TEXT.read_text(encoding="utf-8"), "text"

    raise FileNotFoundError(
        f"Could not find either:\n"
        f" - {INPUT_HTML.name}\n"
        f" - {INPUT_TEXT.name}"
    )


def split_title_and_body(raw_text: str) -> tuple[str, str]:
    """
    Uses first non-empty line as title, remainder as body.
    """
    lines = raw_text.replace("\r\n", "\n").split("\n")

    non_empty = [line.strip() for line in lines if line.strip()]
    if not non_empty:
        return "Global Sports Report", ""

    title = non_empty[0]

    # body starts after first matching non-empty line in original text
    title_found = False
    body_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not title_found and stripped == title:
            title_found = True
            continue
        if title_found:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return title, body


def is_section_header(line: str) -> bool:
    """
    Treat all-caps short-ish lines as section headers.
    Examples:
    SNAPSHOT
    KEY RESULTS
    NATIONAL LEAGUE
    """
    stripped = line.strip()
    if not stripped:
        return False

    if len(stripped) > 50:
        return False

    letters = re.sub(r"[^A-Za-z]", "", stripped)
    if not letters:
        return False

    return stripped == stripped.upper()


def is_bullet_like(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("- ")
        or stripped.startswith("• ")
        or stripped.startswith("* ")
        or re.match(r"^\d+\.\s+", stripped) is not None
    )


def clean_bullet(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"^[-•*]\s+", "", stripped)
    stripped = re.sub(r"^\d+\.\s+", "", stripped)
    return stripped.strip()


def paragraph_to_html(text: str) -> str:
    escaped = html.escape(text.strip())
    return f"<p>{escaped}</p>"


def list_items_to_html(items: list[str]) -> str:
    li_parts = [f"<li>{html.escape(item.strip())}</li>" for item in items if item.strip()]
    if not li_parts:
        return ""
    return "<ul>\n" + "\n".join(li_parts) + "\n</ul>"


def convert_text_body_to_html(body: str) -> str:
    """
    Very clean text -> HTML conversion for your report format.
    """
    lines = body.replace("\r\n", "\n").split("\n")
    html_parts: list[str] = []

    paragraph_buffer: list[str] = []
    list_buffer: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if paragraph_buffer:
            paragraph = " ".join(part.strip() for part in paragraph_buffer if part.strip()).strip()
            if paragraph:
                html_parts.append(paragraph_to_html(paragraph))
            paragraph_buffer = []

    def flush_list() -> None:
        nonlocal list_buffer
        if list_buffer:
            html_parts.append(list_items_to_html(list_buffer))
            list_buffer = []

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            flush_paragraph()
            flush_list()
            continue

        if is_section_header(line):
            flush_paragraph()
            flush_list()
            html_parts.append(f"<h2>{html.escape(line.title())}</h2>")
            continue

        if is_bullet_like(line):
            flush_paragraph()
            list_buffer.append(clean_bullet(line))
            continue

        # keep short label-style lines bolded if they look like "FINAL SCORES"
        # already handled above; otherwise treat as paragraph text
        flush_list()
        paragraph_buffer.append(line)

    flush_paragraph()
    flush_list()

    return "\n".join(html_parts).strip()


def ensure_disclaimer_in_html(body_html: str) -> str:
    plain = re.sub(r"<[^>]+>", " ", body_html)
    plain = re.sub(r"\s+", " ", plain).strip().lower()

    if DISCLAIMER.lower() in plain:
        return body_html

    return (
        body_html
        + "\n<hr />\n"
        + f"<p><em>{html.escape(DISCLAIMER)}</em></p>"
    )


def build_final_html(title: str, body_html: str) -> str:
    published_time = now_et_string()

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body {{
      font-family: Georgia, "Times New Roman", serif;
      max-width: 760px;
      margin: 40px auto;
      padding: 0 20px 60px;
      line-height: 1.7;
      color: #111;
      background: #fff;
    }}
    h1 {{
      font-size: 2.2rem;
      line-height: 1.2;
      margin-bottom: 0.35rem;
    }}
    .meta {{
      color: #666;
      font-size: 0.95rem;
      margin-bottom: 2rem;
    }}
    h2 {{
      margin-top: 2rem;
      margin-bottom: 0.75rem;
      font-size: 1.2rem;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    p {{
      margin: 0 0 1rem 0;
    }}
    ul {{
      margin: 0 0 1rem 1.25rem;
    }}
    li {{
      margin-bottom: 0.5rem;
    }}
    hr {{
      border: none;
      border-top: 1px solid #ddd;
      margin: 2rem 0;
    }}
    .note {{
      background: #f7f7f7;
      border: 1px solid #e5e5e5;
      padding: 14px 16px;
      border-radius: 10px;
      margin-top: 2rem;
      font-size: 0.95rem;
    }}
    code {{
      background: #f3f3f3;
      padding: 2px 6px;
      border-radius: 6px;
    }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <div class="meta">Prepared {html.escape(published_time)}</div>

  {body_html}

  <div class="note">
    Copy the article body from this page into Substack if needed.
  </div>
</body>
</html>
"""


def extract_article_body_fragment(full_html: str) -> str:
    """
    Extracts just the useful article body from preview HTML.
    """
    match = re.search(r"<body>\s*(.*?)\s*</body>", full_html, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return full_html


def save_ready_fragment(title: str, body_html: str) -> str:
    """
    Saves a fragment file that is easy to copy/paste into Substack.
    """
    fragment = (
        f"<h1>{html.escape(title)}</h1>\n"
        f"{body_html}\n"
    )
    READY_HTML.write_text(fragment, encoding="utf-8")
    return fragment


def open_in_browser(path: Path) -> None:
    webbrowser.open(path.resolve().as_uri())


def open_substack_editor() -> None:
    try:
        webbrowser.open(SUBSTACK_NEW_POST_URL)
    except Exception:
        webbrowser.open(SUBSTACK_DASHBOARD_URL)


def copy_text_to_clipboard(text: str) -> bool:
    """
    Plain-text clipboard copy for convenience.
    HTML clipboard is much more fragile on Windows, so we keep this reliable.
    """
    try:
        import tkinter  # built-in

        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        return False


# =========================================================
# MAIN
# =========================================================
def main() -> int:
    try:
        content, source_type = read_source()

        if source_type == "html":
            title = "Global Sports Report"
            body_html = content.strip()
        else:
            title, text_body = split_title_and_body(content)
            body_html = convert_text_body_to_html(text_body)

        body_html = ensure_disclaimer_in_html(body_html)

        preview_doc = build_final_html(title, body_html)
        PREVIEW_HTML.write_text(preview_doc, encoding="utf-8")

        ready_fragment = save_ready_fragment(title, body_html)

        copied = copy_text_to_clipboard(ready_fragment)

        print("✅ Substack publish prep complete.")
        print(f"✅ Preview file: {PREVIEW_HTML.name}")
        print(f"✅ Ready-to-paste HTML fragment: {READY_HTML.name}")

        if copied:
            print("✅ Ready HTML copied to clipboard as plain text.")
        else:
            print("⚠️ Clipboard copy was skipped or failed.")

        print("\nOpening preview file...")
        open_in_browser(PREVIEW_HTML)

        print("Opening Substack editor...")
        open_substack_editor()

        print("\nNext steps:")
        print("1. Review the preview in your browser.")
        print("2. In Substack, create a new post.")
        print("3. Paste the contents of substack_ready.html into the editor if needed.")
        print("4. Add subtitle / tags / social settings, then publish.")

        return 0

    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        print("\nCreate one of these files first:")
        print(f" - {INPUT_HTML.name}")
        print(f" - {INPUT_TEXT.name}")
        return 1

    except Exception as exc:
        print(f"❌ Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())