import json
from openai import OpenAI
# Load template
with open(r"E:\ai_chatbot_business\jsons\faq_template.json", "r") as f:
    template_data = json.load(f)

# Load client config
with open(r"E:\ai_chatbot_business\jsons\titan_fitness.json", "r") as f:
    config_data = json.load(f)

# Generate final responses
responses = {}
for key, value in template_data.items():
    responses[key] = value.format(**config_data)

def get_response(user_input):
    user_input = user_input.lower()

    for key in responses:
        if key in user_input:
            return responses[key]

    return "Sorry, I didn't understand that. Can you rephrase?"

# Chat loop
print("🤖 Gym AI Bot is running (type 'exit' to quit)\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        break

    reply = get_response(user_input)
    print("Bot:", reply)