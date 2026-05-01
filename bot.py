import os
from groq import Groq
from config import GROQ_API_KEY, MODEL_NAME, MAX_HISTORY, HANDOFF_PHRASE

client = Groq(api_key=GROQ_API_KEY)

chat_histories = {}


def load_business_info(business_id):
    filename = f"{business_id}.txt"
    filepath = os.path.join("businesses", filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No business file found for: {business_id}")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def build_system_prompt(business_info):
    return f"""You are a helpful and friendly customer support assistant.

Here is everything you know about this business:
---
{business_info}
---

Your rules:
1. Only answer questions using the business info above.
2. Be warm and friendly, like a helpful shopkeeper.
3. Keep answers short — 2 to 3 sentences max.
4. If you don't know the answer from the info above, reply with exactly this phrase:
   "{HANDOFF_PHRASE}"
   Nothing else. Just that phrase.
5. Never make up prices, timings, or anything not written above.
"""


def get_reply(message, session_id, business_id):
    business_info = load_business_info(business_id)

    # Get existing history or start fresh
    history = chat_histories.get(session_id, [])
    recent_history = history[-MAX_HISTORY:]

    # Build messages list — system prompt + history + new message
    messages = (
        [{"role": "system", "content": build_system_prompt(business_info)}]
        + recent_history
        + [{"role": "user", "content": message}]
    )

    # Call Groq API
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.4,
        max_tokens=300,
    )

    reply = response.choices[0].message.content.strip()

    # Save to history
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    chat_histories[session_id].append({"role": "user",      "content": message})
    chat_histories[session_id].append({"role": "assistant", "content": reply})

    needs_handoff = (reply == HANDOFF_PHRASE)

    return {"reply": reply, "needs_handoff": needs_handoff}


def clear_history(session_id):
    if session_id in chat_histories:
        del chat_histories[session_id]