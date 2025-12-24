import logging
import json
import re
from rapidfuzz import process, fuzz
from openai import AsyncOpenAI
from config import settings

# Logging
logger = logging.getLogger(__name__)

# OpenAI (DeepSeek) client
client = AsyncOpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url
)


# Checks if message contains 'buy' or 'sell' keywords with fuzzy matching.
def contains_buy_sell(text: str, threshold: int = 85) -> bool:
    keywords = ["продам", "продажа", "продаю", "куплю", "скупка", "покупаю", "покупка"]
    words = re.findall(r"\w+", text.lower())

    for kw in keywords:
        match = process.extractOne(query=kw, choices=words, scorer=fuzz.partial_ratio)
        if match and match[1] >= threshold:
            return True
    return False


# Sends message to DeepSeek model and parses response into structured JSON.
async def create_request(message: str):

    if not contains_buy_sell(message):
        logger.debug("No buy/sell keywords found in message — skipping.")
        return None

    logger.info("Sending message to DeepSeek model for parsing...")

    response = await client.chat.completions.create(
        model="deepseek-chat",
        temperature=1.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt5_english},
            {"role": "user", "content": message}
        ]
    )

    content = response.choices[0].message.content
    logger.info(f"Model raw response: {content}...")

    try:
        data = json.loads(content)

        # Normalize model response
        if isinstance(data, dict) and "items" in data:
            items = data["items"]
        elif isinstance(data, dict) and "offers" in data:
            items = data["offers"]
        elif isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            logger.error("Invalid JSON structure from model.")
            return None

        # Filter valid items
        items = [
            obj for obj in items
            if isinstance(obj.get("price_for_one"), int)
            and obj.get("currency") in ("cookies", "money")
        ]

        if items:
            logger.info(f"Parsed {len(items)} valid offers from message.")
            return items
        else:
            logger.warning("No valid items found in model response.")
            return None

    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse model response: {e}")
        return None


# System Prompt
prompt5_english = """
You are a parser for trade messages from a Russian-language RPG game chat.  
Each incoming message may contain information about buying, selling, or both at the same time.  
Messages are written in free form and may include typos, abbreviations, emojis (like 🍪 or 💰), and unusual formatting.

Your task is to analyze the message and return the result **strictly as a JSON array of objects**.  
Do not include any explanations, comments, or text outside of the JSON.  
Each element must be a valid JSON object.  
The entire output must be a fully valid JSON structure that can be parsed without any changes.

**Data generation rules:**

* **item_name** — the name of the item (without grade, duration, or unnecessary details).  
* **quantity** —  the quantity of item
  * if the quantity is explicitly mentioned — use that number,  
  * if not mentioned — use `null`.
* **item_grade** — the item’s grade. It’s usually a Roman numeral, often in brackets, like `[II]`, `[III]`, `[III+]`, or written without brackets like `II`, `III+`.  
  It can also appear as `т2`, `т3+`, etc., which correspond to `[II]`, `[III+]`.  
  Always return the grade in the bracket format, e.g. `[I]`, `[II]`, `[III]`.  
  If it’s impossible to determine — use `"undefined"`.
* **item_duration** — the duration of the item. Return the full form of the time units in **Russian**.  
  Examples:  
  `3ч` → `3 часа`, `30м` → `30 минут`, `7d` → `7 дней`.  
  If no duration is specified — use `"undefined"`.
* **price_for_one** — the price per item (integer).  
  If the price is missing, unclear, or cannot be confidently determined — **do not create an object** for this item.
* **offer_type** — `"buy"` or `"sell"`.  
  If it’s impossible to confidently determine whether it’s a buy or sell offer — **ignore this offer**.
* **currency** — `"cookies"` (печеньки) or `"money"` (монеты).

If the message contains both buy and sell offers — return an array of objects, one for each operation.

**Additional rules:**

* Be conservative: if any field (especially price) cannot be confidently determined, do not include that item.  
* Include only items where the price is clearly defined.  
* Work directly with the Russian text — **do not translate it**.  
* If no reliable data is found, return only `None`.  
* If the user is trading **currency** (e.g., cookies for money), treat it as a normal offer where `item_name = "cookies"`.
"""



