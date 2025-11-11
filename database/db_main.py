import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

logger = logging.getLogger(__name__)

# Base ORM class
class Base(DeclarativeBase):
    pass

# Async DB engine
engine = create_async_engine(
    url=settings.engine_url,
    echo=True # show SQL queries in console (disable in prod)
)
logger.info(f"Async engine created for {settings.engine_url}")

# Async session factory
session_factory = async_sessionmaker(engine)
logger.info("Async session factory initialized")


