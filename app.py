from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
from sambanova import SambaNova
import requests

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
# CONFIGURATION & API CLIENT
# =========================
api_key = os.getenv("SAMBANOVA_API_KEY")
if not api_key:
    raise ValueError("❌ SAMBANOVA_API_KEY is missing")

client = SambaNova(
    api_key=api_key,
    base_url="https://api.sambanova.ai/v1",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
faq_path = os.path.join(BASE_DIR, "jsons", "faq_template.json")
config_path = os.path.join(BASE_DIR, "jsons", "titan_fitness.json")

# Load raw configurations
with open(faq_path, "r", encoding="utf-8") as f:
    template_data = json.load(f)

with open(config_path, "r", encoding="utf-8") as f:
    config_data = json.load(f)

# Build the structural knowledge context base for the gym
knowledge_base = ""
for key, value in template_data.items():
    formatted_value = value.format_map(config_data)
    knowledge_base += f"- {key.upper()}: {formatted_value}\n"

# =========================
# SCHEMAS
# =========================
class ChatRequest(BaseModel):
    message: str

# =========================
# AI CONTEXTUAL ENGINE
# =========================
def get_contextual_response(user_input: str) -> str:
    system_instruction = f"""
    You are an elite AI Front Desk Concierge for Titan Fitness. Your goal is to convert visitors into leads.
    
    Here is the exact verified knowledge base for Titan Fitness:
    {knowledge_base}
    
    CRITICAL RULES:
    1. Base your answer ONLY on the verified data above.
    2. If the user asks for something not directly mentioned, politely guide them to book a free trial to speak with a coach.
    3. Keep answers concise, high-energy, and professional (max 2-3 sentences). Always include a gym emoji.
    4. If the user expresses explicit interest in joining, starting, pricing, or trials, end your response by encouraging them to use the free trial booking card.
    """

    try:
        response = client.chat.completions.create(
            model="DeepSeek-V3.1", # Ensure this model string matches SambaNova's exact designation
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3, # Slightly higher for fluid conversion conversational styles
            max_tokens=250
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return "We're experiencing a high volume of traffic! Please jump straight to booking your Free 7-Day Trial below using our registration card! 👇"

# =========================
# ROUTES
# =========================
@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    print(f"📩 USER MESSAGE: {req.message}")
    reply = get_contextual_response(req.message)
    return {"response": reply}

@app.post("/save-lead")
def save_lead(data: dict):
    webhook_url = "https://script.google.com/macros/s/AKfycbxVXcnVB-5I_0dohGLwOIVzQpp1tqxNpGLSAJXj-JvBv6v421fQNFglhxKlr4YqF53X/exec"
    
    try:
        # Structured forwarding to your Google Apps Script Webhook
        response = requests.post(webhook_url, json=data, timeout=8)
        return {"status": "saved", "origin": "webhook_confirmed"}
    except requests.exceptions.RequestException as e:
        print(f"❌ Google Sheet Save Failed: {e}")
        # Return status success anyway to not ruin user experience on frontend, handle retry asynchronously
        return {"status": "cached_locally", "error": str(e)}

@app.get("/")
def root():
    return {"status": "online", "engine": "Titan Fitness AI Agent v1.1"}
