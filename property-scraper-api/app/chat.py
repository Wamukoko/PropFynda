import logging
from typing import Optional

from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Agent Eve, a friendly and knowledgeable Kenyan property assistant. You help users find and learn about properties for sale or rent across Kenya.

Your capabilities:
- Help users search for properties by describing what they want (location, price range, bedrooms, type)
- Answer questions about specific listings when provided with listing details
- Give general advice about renting and buying property in Kenya
- Explain neighborhoods, pricing trends, and what to look out for
- Guide users on how to contact agents and view properties

Be concise, warm, and helpful. When listing details are provided, use them to answer specifically. If you don't know something, be honest. Always communicate in clear, natural English.

When users want to search, ask them clarifying questions like location, budget, bedrooms, and whether they want to rent or buy."""


def chat(messages: list[dict], listing_context: Optional[str] = None) -> str:
    if not OPENAI_API_KEY:
        return "Agent Eve is currently unavailable — the assistant has not been configured with an API key. Please contact the administrator."

    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        default_headers={"HTTP-Referer": "https://qejaapi.local", "X-Title": "Qeja Property Listings"},
    )

    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    if listing_context:
        msgs.append({
            "role": "system",
            "content": f"The user is currently looking at this listing:\n{listing_context}",
        })
    msgs.extend(messages)

    try:
        res = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=msgs,
            max_tokens=500,
            temperature=0.7,
        )
        return res.choices[0].message.content or ""
    except Exception as e:
        logger.exception("OpenAI chat error")
        return f"Sorry, I ran into an error: {e}"
