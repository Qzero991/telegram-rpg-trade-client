from openai import AsyncOpenAI
from config import settings
from rapidfuzz import process, fuzz
import json
import re

client = AsyncOpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)


def contains_buy_sell(text: str, threshold: int = 85) -> bool:
    # Ключевые слова, которые ищем
    keywords = ["продам", "продажа", "продаю", "куплю", "скупка", "покупаю", "покупка"]
    # Разбиваем текст на слова (регулярка убирает знаки препинания)
    words = re.findall(r"\w+", text.lower())

    for kw in keywords:
        match = process.extractOne(query=kw, choices=words, scorer=fuzz.partial_ratio)
        if match and match[1] >= threshold:
            return True
    return False

async def create_request(message: str):

    if not contains_buy_sell(message):
        print("There are no 'Buy' or 'Sell' keywords in message")
        return None

    response = await client.chat.completions.create(
        model="deepseek-chat",
        temperature=0.5,
        response_format={
            "type": "json_object"
        },
        messages=[
            {
                "role": "system",
                "content": prompt5_english
            },
            {
                "role": "user",
                "content": message
            }
        ]
    )

    print(response.choices[0].message.content)

    try:
        data = json.loads(response.choices[0].message.content)
        if isinstance(data, dict) and "items" in data:
            items = data["items"]
        elif isinstance(data, dict) and "offers" in data:
            items = data["offers"]
        elif isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            print("ОШИБКА. НЕПРАВИЛЬНЫЙ ТИП ОТВЕТА ОТ НЕЙРОНКИ")
            return None
        items = [obj for obj in items if isinstance(obj['price_for_one'], int) and obj['currency'] in ("cookies", "money")]
        if items:
            return items
    except (json.JSONDecodeError, TypeError):
        print("ОШИБКА. НЕПРАВИЛЬНЫЙ ТИП ОТВЕТА ОТ НЕЙРОНКИ")
        return None


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
* **quantity** —  
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
  If it’s impossible to confidently determine whether it’s a buy or sell offer (i.e., there are no words like "куплю" or "продам" or similar) — **ignore this offer** and **do not include it in JSON**.  
  **This is extremely important.**
* **currency** — `"cookies"` (печеньки) or `"money"` (монеты).

If the message contains both buy and sell offers — return an array of objects, one for each operation.

**Additional rules:**

* Be conservative: if any field (especially price) cannot be confidently determined, do not include that item.  
* Include only items where the price is clearly defined.  
* Work directly with the Russian text — **do not translate it**.  
* If no reliable data is found, return only `None`.  
* If the user is trading **currency** (e.g., cookies for money), treat it as a normal offer where `item_name = "cookies"`.

**Example:**

Message:

Продам:
Меч рыцаря [II] - 500💰
Лук короля III+ - 30печ.
Продам 10 печ по 400з

JSON:

[
  {
    "item_name": "Меч рыцаря",
    "quantity": null,
    "item_grade": "[II]",
    "item_duration": "undefined",
    "price_for_one": 500,
    "offer_type": "sell",
    "currency": "money"
  },
  {
    "item_name": "Лук короля",
    "quantity": null,
    "item_grade": "[III+]",
    "item_duration": "undefined",
    "price_for_one": 30,
    "offer_type": "sell",
    "currency": "cookies"
  },
  {
    "item_name": "cookies",
    "quantity": 10,
    "item_grade": "undefined",
    "item_duration": "undefined",
    "price_for_one": 400,
    "offer_type": "sell",
    "currency": "money"
  }
]
"""


