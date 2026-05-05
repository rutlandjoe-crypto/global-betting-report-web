from pathlib import Path
import html
import webbrowser

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "substack_post.txt"
OUTPUT_FILE = BASE_DIR / "substack_post.html"

# =========================================================
# HELPERS
# =========================================================

def read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path.name}")

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{path.name} is empty.")

    return text


def paragraphs_to_html(text: str) -> str:
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    html_blocks = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        joined = " ".join(lines)
        escaped = html.escape(joined)

        if joined.startswith("# "):
            html_blocks.append(f"<h1>{html.escape(joined[2:].strip())}</h1>")
        elif joined.isupper() and len(joined) <= 40:
            html_blocks.append(f"<h2>{escaped}</h2>")
        else:
            html_blocks.append(f"<p>{escaped}</p>")

    return "\n".join(html_blocks)


def build_html_document(body_html: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Substack Draft</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      font-family: Georgia, serif;
      max-width: 760px;
      margin: 40px auto;
      padding: 0 20px;
      line-height: 1.65;
      color: #111;
      background: #fff;
    }}
    h1 {{
      font-size: 2rem;
      margin-bottom: 1rem;
    }}
    h2 {{
      margin-top: 2rem;
      font-size: 1.15rem;
      letter-spacing: 0.02em;
    }}
    p {{
      margin: 0 0 1rem 0;
    }}
  </style>
</head>
<body>
{body_html}
</body>
</html>
"""


def main() -> None:
    try:
        text = read_text_file(INPUT_FILE)
        body_html = paragraphs_to_html(text)
        full_html = build_html_document(body_html)

        OUTPUT_FILE.write_text(full_html, encoding="utf-8")

        print(f"Saved: {OUTPUT_FILE.name}")
        webbrowser.open(OUTPUT_FILE.resolve().as_uri())

    except Exception as e:
        print(f"substack_draft.py failed: {e}")

    footer = build_report_footer("substack")
    substack_post = report_text.strip() + "\n\n---\n\n" + footer


if __name__ == "__main__":
    main()