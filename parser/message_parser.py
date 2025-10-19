from openai import AsyncOpenAI
from config import settings
import json


client = AsyncOpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)

async def create_request(message):

    response = await client.chat.completions.create(
        model="deepseek-chat",
        temperature=1.0,
        response_format={
            "type": "json_object"
        },
        messages=[
            {
                "role": "system",
                "content": prompt3
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






messages=[
            {
                "role": "system",
                "content": "Ты — парсер сообщений торгового чата RPG-игры. Каждое входящее сообщение может содержать информацию о покупке,"
                           " продаже или обеих операциях сразу. Формат сообщений не фиксированный, может быть написан в свободной форме,"
                           " с ошибками и сокращениями.\n\nТвоя задача — проанализировать сообщение и вернуть строго корректный JSON со следующими полями:"
                           "\n- item_name: название предмета, не должен содержать внутри себя грейд, время действия и тд, только название\n"
                           "- item_type: тип предмета, который ты должен определить сам из конеткста, есть всего два варианта: \"RESOURCE\" либо \"EQUIPMENT\"\n"
                           "- quantity: количество предметов (целое число), если количество не указано явно, то задавай значение -1\n- item_grade: грейд предмета, обычно указывается римскими "
                           "цифрами внутри квадратных скобок [] либо пишется рядом с названием без скобок, если не получается явно определить грейд, то подставь значение: \"undefined\""
                           "\n- item_duration: время действия предмета, обычно указывается рядом с названием. Если времени действия, то укажи \"undefined\"\n"
                           "- price_for_one: цена за одну штуку\n- offer_type: \"buy\" (если покупка), \"sell\" (если продажа)\n- currency: \"cookies\" или \"money\"\n\n"
                           "Если в сообщении присутствует и покупка, и продажа, верни массив объектов, каждый с отдельной операцией."
                           "\n\nВозвращай **строго JSON**, без пояснений, без лишнего текста."
            }]




prompt3 = """You are a parser for messages from a Russian-language RPG game trading chat. 
Each incoming message may contain information about buying, selling, or both operations at once. 
The messages are free-form, may contain errors, abbreviations, emojis (such as 🍪 or 💰), and non-standard formatting.

Your task is to analyze the message and you must output your answer strictly as a JSON array of objects. Do not include any explanations, comments, or text outside of the JSON. 
Each element must be a valid JSON object. The output must be a valid JSON array structure that can be parsed without modification.". 
⚠️ Do not add any explanations or extra text. The JSON must be syntactically correct.

Rules for generating data:
- item_name: the name of the item (without grade, duration, or other extra info)
- quantity:
  - if the quantity is explicitly mentioned — use that number
  - if the quantity is not mentioned — use null
- item_grade: the item's grade. This is a Roman numeral that appears in the name of an object, usually in square brackets, but can also be without them, e.g. [II], [III], [III+] or II, III, III+. Always return it in square brackets, e.g., "[I]", "[II]", "[III]". 
  If the grade cannot be determined — use "undefined"
- item_duration: the item's duration. You must output the full Russian form of time units — for example, '3ч' → '3 часа', '30м' → '30 минут'. If the time is written in English (e.g., '7d'), translate it into Russian ('7 дней'). If not specified — use "undefined"
- price_for_one: the price per unit (integer).  If the price is missing, unclear, or cannot be confidently determined, do NOT create an object for this item.
- offer_type: "buy" or "sell"
- currency: "cookies" or "money"

If a message contains both a buy and a sell operation, return an array of objects, one for each operation.

Additional instructions:
- Be conservative: if you are not confident about the value of a field (especially price or quantity), do not create an object. 
- Only include items with clear and confidently identifiable prices.
- Handle Russian text correctly — all analysis is done on the original Russian text, do not translate it.
- If you cannot find valid or reliable data, return only the text None.
- There may also be a situation where someone wants to sell or buy cookies - currency, for coins - another currency. 
 For such cases, treat it as a regular offer, where item_name is cookies.

Example:
Message: "Продам Меч рыцаря [II] - 500💰\nЛук короля III+ - 30печ.\nПродам 10 печ по 400 монет"
JSON:
[{
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


