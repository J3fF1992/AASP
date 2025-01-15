from fastapi import FastAPI
import asyncio
from utils.logger import logger
from models.db_config import SessionLocal
from services.client.consulta_codigo_matricula import consultar_matriculas_vazias
from services.validador import NotionDatabaseClient
import os

SEMAPHORE_LIMIT = 10

async def lifespan(app: FastAPI):
    """Configurações executadas durante o ciclo de vida da aplicação."""
    logger.info("Iniciando a API...")
    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

    async def loop_principal():
        try:
            while True:
                matriculas_data = await consultar_matriculas_vazias()

                if not matriculas_data:
                    logger.info("Nenhum dado encontrado para processamento. Aguardando próximo ciclo.")
                    await asyncio.sleep(10)
                    continue

                async with SessionLocal() as session:
                    tasks = [
                        processar_tarefa(data, session, semaphore)
                        for data in matriculas_data
                    ]

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for data, result in zip(matriculas_data, results):
                        if isinstance(result, Exception):
                            logger.error(f"Erro ao processar {data['user_uuid']}: {result}")
                        else:
                            logger.info(f"Processamento bem-sucedido para {data['user_uuid']}.")
                await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Erro no loop principal: {e}")

    try:
        logger.info("Configurando loop principal.")
        app.state.loop_task = asyncio.create_task(loop_principal())
        yield
    except Exception as e:
        logger.error(f"Erro no lifespan: {e}")
    finally:
        logger.info("Encerrando a API. Cancelando loop principal.")
        app.state.loop_task.cancel()
        try:
            await app.state.loop_task
        except asyncio.CancelledError:
            logger.info("Loop principal foi encerrado com sucesso.")

async def processar_tarefa(data, session, semaphore):
    async with semaphore:
        try:
            client = NotionDatabaseClient(
                database_id=data["banco_id"],
                access_token=data["access_token"],
                session=session,
            )
            await client.processar_associado(data["user_uuid"])
        except Exception as e:
            logger.error(f"Erro ao processar {data['user_uuid']}: {e}")

# Instância do FastAPI
app = FastAPI(
    title="Notion Integration API",
    description="API para integração com Notion e manipulação de intimações",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,  # Registrar o manipulador de ciclo de vida
)

if __name__ == "__main__":
    import uvicorn

    HOST = os.getenv("APP_HOST", "127.0.0.1")
    PORT = int(os.getenv("APP_PORT", 3002))
    RELOAD = os.getenv("APP_RELOAD", "true").lower() == "true"

    uvicorn.run("main:app", host=HOST, port=PORT, reload=RELOAD)