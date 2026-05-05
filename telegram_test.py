from dotenv import load_dotenv
from pathlib import Path
import os
import requests

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

print("RAW TOKEN:", repr(token))
print("LENGTH:", len(token))

url = f"https://api.telegram.org/bot{token}/getMe"
response = requests.get(url)

print("STATUS:", response.status_code)
print("RESPONSE:", response.text)