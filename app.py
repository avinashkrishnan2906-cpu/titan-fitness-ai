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
# CONFIGURATION & AI CLIENT
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

# 🔄 DYNAMIC GYM PROFILE SWITCHER
# Vercel reads this to target the correct localized data variables
CURRENT_GYM_PROFILE = "we_fitness"
config_path = os.path.join(BASE_DIR, "jsons", f"{CURRENT_GYM_PROFILE}.json")

with open(faq_path, "r", encoding="utf-8") as f:
    template_data = json.load(f)

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
# VERCEL DIRECT GOOGLE INJECTION ENGINE
# ==========================================
def append_to_google_sheet(sheet_name: str, row_data: list):
    """Parses Google Service Keys securely out of Vercel Environment memory"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Pulls your raw JSON credentials string straight out of Vercel's secure environment settings
        creds_json_string = os.getenv("GOOGLE_CREDS_JSON")
        if not creds_json_string:
            print("❌ Error: GOOGLE_CREDS_JSON variable is completely missing from Vercel settings!")
            return False
            
        creds_dict = json.loads(creds_json_string)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(creds)
        
        # Target the exact sheet name sent from the frontend request payload
        workbook = gc.open(sheet_name)
        sheet = workbook.sheet1
        sheet.append_row(row_data)
        print(f"✅ Production row successfully pushed to Google Sheet: '{sheet_name}'")
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
        print(f"❌ AI Core Exception: {e}")
        return "Floor is packed! Jump straight to our registration card below to lock in your pass! 👇"

# =========================
# LIVE API ENDPOINTS
# =========================
@app.post("/chat")
def chat(req: ChatRequest):
    return {"response": get_contextual_response(req.message)}

@app.post("/save-lead")
def save_lead(data: dict):
    print(f"📡 INCOMING LEAD PAYLOAD TO VERCEL: {data}")
    
    name = data.get("name", "Unknown Name")
    phone = data.get("phone", "Unknown Phone")
    goal = data.get("goal", "General Fitness")
    
    # 📊 Grabs whatever sheet name is requested dynamically by the incoming frontend network request
    target_sheet = data.get("target_sheet_name", "We Fitness Club Data")
    
    formatted_row = [name, phone, goal]
    success = append_to_google_sheet(target_sheet, formatted_row)
    
    if success:
        return {"status": "saved", "origin": "vercel_gspread_cloud_confirmed"}
    else:
        return {"status": "cloud_error", "detail": "Check Vercel Environment configuration variables and sheet editing permissions"}

@app.get("/")
def root():
    return {"status": "online", "engine": f"{config_data.get('gym_name')} Cloud Engine v1.4"}
