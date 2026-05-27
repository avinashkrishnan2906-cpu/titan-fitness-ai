from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
from sambanova import SambaNova
import requests
# =========================
# FASTAPI APP
# =========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# API KEY
# =========================
api_key = os.getenv("SAMBANOVA_API_KEY")

if not api_key:
    raise ValueError("❌ SAMBANOVA_API_KEY is missing")

# =========================
# SAMBANOVA CLIENT
# =========================
client = SambaNova(
    api_key=api_key,
    base_url="https://api.sambanova.ai/v1",
)

print("✅ SambaNova client initialized")

# =========================
# FILE PATHS (VERCEL SAFE)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

faq_path = os.path.join(BASE_DIR, "jsons", "faq_template.json")
config_path = os.path.join(BASE_DIR, "jsons", "titan_fitness.json")

print("📂 FAQ PATH:", faq_path)
print("📂 CONFIG PATH:", config_path)

# =========================
# LOAD JSON FILES
# =========================
with open(faq_path, "r", encoding="utf-8") as f:
    template_data = json.load(f)

with open(config_path, "r", encoding="utf-8") as f:
    config_data = json.load(f)

print("✅ JSON files loaded")

# =========================
# BUILD RESPONSES
# =========================
responses = {}

for key, value in template_data.items():
    responses[key] = value.format_map(config_data)

print("✅ Responses built")

# =========================
# REQUEST MODEL
# =========================
class ChatRequest(BaseModel):
    message: str

# =========================
# AI RESPONSE FUNCTION
# =========================
def get_response(user_input):
    keys = list(responses.keys())

    prompt = f"""
    You are a strict intent classifier.

    User question: "{user_input}"

    Choose ONLY ONE category from:
    {keys}

    Examples:
    - price, fees → membership rates
    - trainer, coach, personal training → personal training
    - trial → free trial
    - parking → parking

    Return ONLY the category name.
    """

    response = client.chat.completions.create(
        model="DeepSeek-V3.1",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        top_p=0.1
    )

    category = response.choices[0].message.content.strip().lower()

    print("🤖 AI CATEGORY:", category)

    for key in responses:
        if key.lower() in category:
            return responses[key]

    return "Sorry, I didn't understand that."

# =========================
# CHAT ENDPOINT
# =========================
@app.post("/chat")
def chat(req: ChatRequest):

    print("📩 USER MESSAGE:", req.message)

    reply = get_response(req.message)

    return {
        "response": reply
    }

@app.post("/save-lead")
def save_lead(data: dict):

    webhook_url = "https://script.google.com/macros/s/AKfycbxVXcnVB-5I_0dohGLwOIVzQpp1tqxNpGLSAJXj-JvBv6v421fQNFglhxKlr4YqF53X/exec"

    requests.post(
        webhook_url,
        json=data
    )

    return {
        "status": "saved"
    }
# =========================
# ROOT ENDPOINT
# =========================
@app.get("/")
def root():
    return {
        "message": "🚀 Titan Fitness AI Bot is running!"
    }
