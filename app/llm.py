import logging
import httpx
import json
import re
from typing import List, Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)
logger.debug(f"OPENROUTER_API_KEY set: {'Yes' if settings.OPENROUTER_API_KEY else 'No'}")


async def call_openrouter(system_prompt: str, user_prompt: str) -> str:
    """
    Sends a request to OpenRouter API and returns the string response.
    """
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        logger.warning("OPENROUTER_API_KEY is not configured. Returning mock response.")
        if "intent" in system_prompt.lower():
            return json.dumps({
                "intent": "product_search",
                "keywords": "aspirateur",
                "price_limit": None
            })
        return "Aslema! N3tether, l'API key mta3 OpenRouter mch mrigla. Najem n3awnek fi 7aja okhra?"

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://equip-home.tn",
        "X-Title": "Tunisian E-commerce Chatbot"
    }

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }

    logger.info(f"Calling OpenRouter with model: {settings.OPENROUTER_MODEL}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            res_data = response.json()
            return res_data['choices'][0]['message']['content'].strip()
        except Exception as e:
            logger.error(f"OpenRouter API call failed: {e}")
            raise e


def extract_json(text: str) -> dict:
    """
    Attempts to extract and parse JSON from a response string.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError("Could not extract valid JSON from response")


async def detect_intent_and_extract(message: str) -> dict:
    """
    Analyzes the user's message in Tunisian Derja, French or Arabic
    to detect their intent, search keywords (translated to French), and price limit.
    """
    system_prompt = (
        "You are an AI assistant analyzing customer messages for a Tunisian e-commerce store.\n"
        "Your task is to classify the user's intent and extract search parameters.\n\n"
        "Classify intent into one of these categories:\n"
        "1. 'product_search': User wants to find a specific product (e.g. 'nlawej 3la aspirateur', 'fama microonde?').\n"
        "2. 'price_inquiry': User asks specifically about a product's price (e.g. '9adeh soum el ventilateur?', 'aspirateur b9adech?').\n"
        "3. 'recommendation': User asks for recommendations or ideas (e.g. 'chneya a7sen ventilateur 3andkom?', 'ansahni b egouttoir behi').\n"
        "4. 'faq': User asks about delivery, payment terms, shop location, returns (e.g. 'kifech l livraison?', 'kifech ndfa3?', 'fin jeyin?').\n"
        "5. 'smalltalk': Greetings, thank yous, goodbye, or general talk (e.g. 'aslema', 'salam', 'ya3tikom saha').\n\n"
        "Extract:\n"
        "- 'keywords': Search keywords translated into French or standard English (e.g. if they say 'aspirateur', keywords='aspirateur'; 'tawa9e3 s7an' -> keywords='egouttoir vaisselle'). Keep keywords simple and focused on nouns.\n"
        "- 'price_limit': The maximum price (number only) in TND if they mention a budget (e.g. 'a9al men 100dt' -> 100, 'b 50dt' -> 50). Otherwise, null.\n\n"
        "You must respond ONLY with a JSON object in this format (no conversational filler):\n"
        "{\n"
        "  \"intent\": \"product_search | price_inquiry | recommendation | faq | smalltalk\",\n"
        "  \"keywords\": \"extracted french/english keywords or empty string\",\n"
        "  \"price_limit\": float or null\n"
        "}"
    )

    try:
        response_text = await call_openrouter(system_prompt, f"User message: '{message}'")
        parsed = extract_json(response_text)
        valid_intents = ["product_search", "price_inquiry", "recommendation", "faq", "smalltalk"]
        if parsed.get("intent") not in valid_intents:
            parsed["intent"] = "smalltalk"
        return parsed
    except Exception as e:
        logger.error(f"Error in intent detection: {e}")
        return {
            "intent": "product_search",
            "keywords": message,
            "price_limit": None
        }


async def generate_response(
    message: str,
    intent: str,
    products: List[Any]
) -> str:
    """
    Generates a natural chat response in Tunisian Derja based on intent and retrieved products.
    """
    system_prompt = (
        "You are a sales assistant for a Tunisian e-commerce store.\n"
        "Always respond in friendly, concise, and natural Tunisian dialect (Derja).\n"
        "Your tone should be polite and welcoming (e.g., use words like 'Aslema', 'Marhba bik', 'Aychik').\n"
        "Follow these rules based on the user's intent and data provided:\n\n"
        "1. Respond in Tunisian Arabic (Derja) written in Latin/Franco letters (e.g., 'aslema', 'soum', 'livraison') or Arabic letters, matching the user's input style if possible.\n"
        "2. Do NOT hallucinate products or invent prices. ONLY use the provided product list.\n"
        "3. Always include the price of products in TND if available (e.g. '99.90 TND').\n"
        "4. Always suggest/include the product link if available.\n"
        "5. Keep the response short and conversational (1-3 sentences).\n\n"
        "Store FAQ Context for reference:\n"
        "- Delivery (Livraison): All over Tunisia (toute la Tunisie), price is 7 TND, delivery time is 2 to 3 business days.\n"
        "- Payment (Paiement): Cash on delivery (Paiement a la livraison) or credit card online.\n"
        "- Availability: If no product is found matching, politely explain that we don't have it in stock currently.\n"
    )

    product_context = ""
    if products:
        product_context = "Here are the matching products in our store database:\n"
        for p in products:
            price_val = f"{p.price} TND" if p.price else (p.price_str or "Non specifie")
            product_context += (
                f"- ID: {p.id}\n"
                f"  Title: {p.title}\n"
                f"  Price: {price_val}\n"
                f"  Link: {p.link}\n"
                f"  Description: {p.description or 'No description'}\n"
                f"  Availability: {p.availability or 'In Stock'}\n\n"
            )
    else:
        product_context = "No products matched the search keywords in our database.\n"

    user_prompt = (
        f"User Message: '{message}'\n"
        f"Detected Intent: {intent}\n"
        f"Product Context:\n{product_context}\n"
        "Please generate a response in Tunisian Derja."
    )

    try:
        response_text = await call_openrouter(system_prompt, user_prompt)
        return response_text
    except Exception as e:
        logger.error(f"Error in response generation: {e}")
        return "Aslema! N3tether mennik, fama mochkla sghira fil system. Najem n3awnek fi 7aja okhra?"
