import asyncio
import logging
from config import settings
from logic.items_init import items_in_file_renew
from logic.messages_handler import run_messages_handler


# Logging setup
logging.basicConfig(
    level=logging.DEBUG,  # change to DEBUG for detailed logs
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

logger.info("Application startup initiated")



if __name__ == "__main__":
    try:
        logger.info("Starting async event loop...")

        if settings.app_mode == "collector":
            logger.info("Running in ITEMS COLLECTOR mode")
            asyncio.run(items_in_file_renew())

        elif settings.app_mode == "worker":
            logger.info("Running in TRADE WORKER mode")
            asyncio.run(run_messages_handler())

        else:
            raise ValueError(f"Unknown APP_MODE: {settings.app_mode}")

    except KeyboardInterrupt:
        logger.warning("🛑 Application stopped manually (Ctrl+C)")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        logger.info("Application terminated")

