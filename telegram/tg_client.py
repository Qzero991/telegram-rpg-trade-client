from telethon import TelegramClient
from config import settings
import asyncio

client = TelegramClient(settings.telegram_session_name, settings.telegram_api_id, settings.telegram_api_hash)


async def start_client():
    if not client.is_connected():
        await client.start()

async def run_client_forever():
    await start_client()
    await client.run_until_disconnected()



















# async def tg_client_connection():
#     client = TelegramClient(settings.telegram_session_name, settings.telegram_api_id, settings.telegram_api_hash)
#     await client.start()
#
# async def listener(queue=None):
#     client = TelegramClient(settings.telegram_session_name, settings.telegram_api_id, settings.telegram_api_hash)
#     await client.start()
#
#     @client.on(events.NewMessage(chats=settings.trade_group_id,incoming=True, outgoing=True))
#     async def my_event_handler(event):
#         await queue.put(event)
#         print(event.raw_text)
#
#     await client.run_until_disconnected()

