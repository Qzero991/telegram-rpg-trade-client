import asyncio
from config import settings
from telethon import TelegramClient, events
from telegram.tg_client import client

from database.queries import insert_message_data

async def trade_group_listener(offer_message_queue=None):

    @client.on(events.NewMessage(chats='me',incoming=True, outgoing=True))
    async def group_handler(event):
        await offer_message_queue.put(event)
        print(event.raw_text)