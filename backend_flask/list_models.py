import os, requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY")

url = "https://generativelanguage.googleapis.com/v1beta/models"
r = requests.get(url, headers={"x-goog-api-key": key})
print("status:", r.status_code)
print(r.text[:2000])