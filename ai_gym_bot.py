from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from sambanova import SambaNova

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# SambaNova client
client = SambaNova(
    api_key="8e68104c-f6ec-4718-9cba-d1e6ebfe7909",
    base_url="https://api.sambanova.ai/v1",
)

# Load files
with open(r"E:\ai_chatbot_business\jsons\faq_template.json", "r", encoding="utf-8") as f:
    template_data = json.load(f)

with open(r"E:\ai_chatbot_business\jsons\titan_fitness.json", "r", encoding="utf-8") as f:
    config_data = json.load(f)

# Build responses
responses = {}
for key, value in template_data.items():
    responses[key] = value.format_map(config_data)

# Request model
class ChatRequest(BaseModel):
    message: str


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
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        top_p=0.1
    )

    category = response.choices[0].message.content.strip().lower()

    for key in responses:
        if key in category:
            return responses[key]

    return "Sorry, I didn't understand that."


@app.post("/chat")
def chat(req: ChatRequest):
    reply = get_response(req.message)
    return {"response": reply}