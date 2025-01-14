import asyncio
from app.models.db_config import Base, engine

async def recreate_tables():
    print("Recriando tabelas no banco de dados...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Tabelas recriadas com sucesso!")

if __name__ == "__main__":
    asyncio.run(recreate_tables())
