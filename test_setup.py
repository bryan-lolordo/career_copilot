from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()
client = OpenAI()

print("✅ Environment loaded successfully.")
print(f"OpenAI API key found: {'OPENAI_API_KEY' in os.environ}")

# Quick test call
try:
    resp = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": "Hello from Career Copilot!"}]
    )
    print("✅ OpenAI response:", resp.choices[0].message.content)
except Exception as e:
    print("❌ OpenAI test failed:", e)
