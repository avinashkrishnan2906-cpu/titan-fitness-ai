from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
from sambanova import SambaNova
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
# CONFIGURATION, CORE DIRECTORIES & AI ENGINE
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

# 🔄 THE DYNAMIC PROFILE SWITCH: Toggle between "we_fitness" or "369_beast" here
CURRENT_GYM_PROFILE = "we_fitness"
config_path = os.path.join(BASE_DIR, "jsons", f"{CURRENT_GYM_PROFILE}.json")

with open(faq_path, "r", encoding="utf-8") as f:
    template_data = json.load(f)

# Fallback patch if file is missing during quick testing
if os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
else:
    config_data = {"gym_name": "We Fitness Center"}

knowledge_base = ""
for key, value in template_data.items():
    try:
        formatted_value = value.format_map(config_data)
        knowledge_base += f"- {key.upper()}: {formatted_value}\n"
    except Exception:
        knowledge_base += f"- {key.upper()}: {value}\n"

# ==========================================
# GOOGLE SHEETS DIRECT INJECTION ENGINE
# ==========================================
def append_to_google_sheet(sheet_name: str, row_data: list):
    """Bypasses macros entirely to inject rows directly into any Google Sheet by name"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Looks for your standard Google service account key file in your backend folder
        creds_path = os.path.join(BASE_DIR, "creds.json") 
        if not os.path.exists(creds_path):
            print("❌ Error: 'creds.json' service account file missing from backend folder!")
            return False
            
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        gc = gspread.authorize(creds)
        
        # Opens whatever sheet name is requested dynamically by the user payload
        workbook = gc.open(sheet_name)
        sheet = workbook.sheet1
        sheet.append_row(row_data)
        print(f"✅ Row successfully injected into sheet: '{sheet_name}'")
        return True
    except Exception as e:
        print(f"❌ Direct Google Sheets Write Failure: {e}")
        return False

class ChatRequest(BaseModel):
    message: str

def get_contextual_response(user_input: str) -> str:
    gym_name = config_data.get("gym_name", "We Fitness Center")
    system_instruction = f"""
    You are an elite AI Front Desk Concierge for {gym_name}. Your goal is to convert visitors into leads.
    Here is the exact verified knowledge base for {gym_name}:
    {knowledge_base}
    CRITICAL RULES:
    1. Base your answer ONLY on the verified data above.
    2. Keep answers concise, high-energy, and professional (max 2-3 sentences). Always include a gym emoji.
    """
    try:
        response = client.chat.completions.create(
            model="DeepSeek-V3.1",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3,
            max_tokens=250
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Floor is packed! Jump straight to our registration card below to lock in your pass! 👇"

# =========================
# LIVE API ENDPOINTS
# =========================
@app.post("/chat")
def chat(req: ChatRequest):
    return {"response": get_contextual_response(req.message)}

@app.post("/save-lead")
def save_lead(data: dict):
    print(f"📡 INCOMING LEAD PAYLOAD: {data}")
    
    # Safely extract user fields
    name = data.get("name", "Unknown Name")
    phone = data.get("phone", "Unknown Phone")
    goal = data.get("goal", "General Fitness")
    
    # Target sheet parsed dynamically from user request or matched directly to your variable
    target_sheet = data.get("target_sheet_name", "We Fitness Club Data")
    
    # Prepare row format
    formatted_row = [name, phone, goal]
    
    # Fire direct spreadsheet injection
    success = append_to_google_sheet(target_sheet, formatted_row)
    
    if success:
        return {"status": "saved", "origin": "direct_gspread_confirmed"}
    else:
        return {"status": "local_error", "detail": "Verify creds.json sharing permissions"}

@app.get("/")
def root():
    return {"status": "online", "engine": f"{config_data.get('gym_name')} Engine v1.3"}
