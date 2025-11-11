import logging
from telethon import TelegramClient
from config import settings

# ---------------- Logging ----------------
logger = logging.getLogger(__name__)

# ----------- Telegram client initialization -----------
client = TelegramClient(
    settings.telegram_session_name,
    settings.telegram_api_id,
    settings.telegram_api_hash
)


async def start_client():
    """Starts Telegram client if not connected."""
    if not client.is_connected():
        await client.start()
        logger.info("Telegram client started.")
    else:
        logger.debug("Telegram client already connected.")


async def run_client_forever():
    """Runs client until disconnected."""
    await start_client()
    logger.info("Telegram client running...")
    await client.run_until_disconnected()
    logger.warning("Telegram client disconnected.")



