from config import settings
from telethon import events
from telegram.tg_client import client

async def trade_group_listener(offer_message_queue=None):

    @client.on(events.NewMessage(chats=settings.trade_group_id,incoming=True, outgoing=True))
    async def group_handler(event):
        print(event.raw_text)
        await offer_message_queue.put(event)