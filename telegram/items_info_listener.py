import asyncio
from config import settings
from telethon import events
from telegram.tg_client import client
from parser.items_parser import items_info_parser
import re


async def items_listener(items_type_and_id_queue, async_flag):

    @client.on(events.NewMessage(chats=settings.items_info_group_id,incoming=True))
    async def items_info_handler(event):
        await items_info_parser(event, items_type_and_id_queue, async_flag)



