from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings



class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    url=settings.engine_url,
    echo=True
)

session_factory = async_sessionmaker(engine)

