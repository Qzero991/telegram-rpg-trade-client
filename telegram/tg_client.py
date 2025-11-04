from telethon import TelegramClient
from config import settings


client = TelegramClient(settings.telegram_session_name, settings.telegram_api_id, settings.telegram_api_hash)


async def start_client():
    if not client.is_connected():
        await client.start()

async def run_client_forever():
    await start_client()
    await client.run_until_disconnected()


