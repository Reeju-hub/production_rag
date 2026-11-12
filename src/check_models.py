import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

print("🔍 Fetching Active Gemini Models directly from Google...\n")
print("✅ YEH HAIN TUMHARE LIYE AVAILABLE MODELS:\n")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print("⚠️ Error:", e)