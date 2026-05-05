from pathlib import Path
from dotenv import load_dotenv
import os
import requests

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

print("TOKEN OK:", bool(token))
print("TOKEN START:", token[:10])
print("TOKEN END:", token[-6:])

url = f"https://api.telegram.org/bot{token}/getUpdates"
response = requests.get(url, timeout=30)

print("STATUS:", response.status_code)
print("RESPONSE:", response.text)