from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from utils.settings import DATABASE_URL
from sqlalchemy.ext.declarative import declarative_base
from utils.logger import logger

Base = declarative_base()
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    echo=False
)

SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with SessionLocal() as session:
        yield session

async def get_db_session():
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error(f"Erro ao obter a sessão: {e}")
    finally:
        try:
            await session.close()
        except Exception as e:
            logger.error(f"Erro ao fechar a sessão: {e}")
