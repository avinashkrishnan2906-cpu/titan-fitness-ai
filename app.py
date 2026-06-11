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

# ==========================================
# CONFIGURATION & API CLIENT
# ==========================================
api_key = os.getenv("SAMBANOVA_API_KEY")
if not api_key:
    raise ValueError("❌ SAMBANOVA_API_KEY is missing")

client = SambaNova(
    api_key=api_key,
    base_url="https://api.sambanova.ai/v1",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
faq_path = os.path.join(BASE_DIR, "jsons", "faq_template.json")

# 🚨 CRASH DEFENSE: Safe dynamic fallback mapping for your profile variables
gym_name = "We Fitness Center"
knowledge_base = "- RECRUITMENT: Claim your free pass on the interface card lower down."

try:
    # Attempt to load templates safely if they exist in your repository
    if os.path.exists(faq_path):
        with open(faq_path, "r", encoding="utf-8") as f:
            template_data = json.load(f)
        
        # Look for the active profile structure (Defaulting to we_fitness or falling back cleanly)
        config_path = os.path.join(BASE_DIR, "jsons", "we_fitness.json")
        if not os.path.exists(config_path):
            config_path = os.path.join(BASE_DIR, "jsons", "titan_fitness.json")
            
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            gym_name = config_data.get("gym_name", gym_name)
            
            # Formulate structural knowledge segments
            knowledge_base = ""
            for key, value in template_data.items():
                try:
                    knowledge_base += f"- {key.upper()}: {value.format_map(config_data)}\n"
                except Exception:
                    knowledge_base += f"- {key.upper()}: {value}\n"
except Exception as setup_error:
    print(f"⚠️ Safe non-blocking warning during Vercel assembly: {setup_error}")

# ==========================================
# SCHEMAS
# ==========================================
class ChatRequest(BaseModel):
    message: str

# ==========================================
# AI CONTEXTUAL ENGINE
# ==========================================
def get_contextual_response(user_input: str) -> str:
    system_instruction = f"""
    You are an elite AI Front Desk Concierge for {gym_name}. Your goal is to convert visitors into leads.
    
    Here is the exact verified knowledge base for {gym_name}:
    {knowledge_base}
    
    CRITICAL RULES:
    1. Base your answer ONLY on the verified data above.
    2. Keep answers concise, high-energy, and professional (max 2-3 sentences). Always include a gym emoji.
    3. If the user expresses explicit interest in joining, starting, pricing, or trials, end your response by encouraging them to use the free trial booking card.
    """
    try:
        # Utilizing SambaNova compatible DeepSeek model targets
        response = client.chat.completions.create(
            model="DeepSeek-R1-Distill-Llama-70B", # Production-stable designation key
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3,
            max_tokens=250
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ AI Core Engine Timeout: {e}")
        return "Welcome to the floor! Let's get you set up on the training floor right away. Use the registration pass card below to lock in your entry! 👇"

# ==========================================
# API CHANNELS & IMPLEMENTATION ENDPOINTS
# ==========================================
@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    return {"response": get_contextual_response(req.message)}

@app.post("/save-lead")
def save_lead(data: dict):
    # This single webhook URL stays the same for all your gym clients
    webhook_url = "https://script.google.com/macros/s/AKfycbxbL4n05vuelArsDMgywsHcRVlmr5FckYdb4JfvY9CD6LbwYvkyc4GyvE9npoXaR_o/exec"
    
    try:
        # Extract target_sheet sent by frontend, default to a safe fallback if missing
        target_sheet = data.get("target_sheet", "General Gym Leads")
        print(f"📡 Forwarding Payload to Dynamic Sheet [{target_sheet}]: {data}")
        
        # Send the entire dictionary (including the target sheet name) to Google
        response = requests.post(webhook_url, json=data, timeout=12, allow_redirects=True)
        print(f"📡 Google API Response: {response.status_code}")
        return {"status": "saved", "origin": "dynamic_webhook_confirmed"}
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Webhook write interface failed: {e}")
        return {"status": "error", "msg": str(e)}

@app.get("/")
def root():
    return {"status": "online", "engine": f"{gym_name} Cloud Engine v1.5"}
