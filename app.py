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
config_path = os.path.join(BASE_DIR, "jsons", "titan_fitness.json")

with open(faq_path, "r", encoding="utf-8") as f:
    template_data = json.load(f)

with open(config_path, "r", encoding="utf-8") as f:
    config_data = json.load(f)

knowledge_base = ""
for key, value in template_data.items():
    try:
         knowledge_base += f"- {key.upper()}: {value.format_map(config_data)}\n"
    except Exception:
         knowledge_base += f"- {key.upper()}: {value}\n"

# ==========================================
# DIRECT NATIVE GOOGLE SHEET INJECTOR
# ==========================================
def inject_lead_directly(row_data: list):
    """Bypasses macros completely to write straight to the spreadsheet workbook"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Stream credentials directly out of secure Vercel environment memory
        creds_json_string = os.getenv("GOOGLE_CREDS_JSON")
        if not creds_json_string:
            print("❌ Error: GOOGLE_CREDS_JSON environment variable is not configured on Vercel!")
            return False
            
        creds_dict = json.loads(creds_json_string)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(creds)
        
        # Target your exact active Google Spreadsheet by its text name
        workbook = gc.open("We Fitness Club Data")
        sheet = workbook.sheet1
        
        # Append data row natively
        sheet.append_row(row_data)
        print("✅ Success: Lead injected natively via gspread driver!")
        return True
    except Exception as e:
        print(f"❌ Native Sheets Driver Failure: {e}")
        return False

class ChatRequest(BaseModel):
    message: str

# =========================
# LIVE API ENDPOINTS
# =========================
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        system_instruction = f"You are an AI Front Desk Concierge. Knowledge:\n{knowledge_base}"
        response = client.chat.completions.create(
            model="DeepSeek-V3.1",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": req.message}
            ],
            temperature=0.3,
            max_tokens=250
        )
        return {"response": response.choices[0].message.content.strip()}
    except Exception:
        return {"response": "Welcome to the floor! Claim your Free Pass pass right below! 👇"}

@app.post("/save-lead")
def save_lead(data: dict):
    print(f"📡 INCOMING PAYLOAD RECEIVED: {data}")
    
    name = data.get("name", "Unknown Name")
    phone = data.get("phone", "Unknown Phone")
    goal = data.get("goal", "General Fitness")
    source = data.get("source", "we_fitness_center")
    
    # Construct row format matrix
    formatted_row = [name, phone, goal, source]
    
    # Execute native direct injection tracking pipeline
    success = inject_lead_directly(formatted_row)
    
    if success:
        return {"status": "saved", "origin": "native_gspread_confirmed"}
    else:
        raise HTTPException(status_code=502, detail="Internal Google Driver payload validation mismatch")

@app.get("/")
def root():
    return {"status": "online", "engine": "We Fitness Native Gspread Engine v2.0"}
