import asyncio
import os
from fastapi import FastAPI
from route.endpoint import router as process_routes
from models.db_config import engine, Base
from utils.logger import logger
from utils.resoucer import fila_uuids

# Configuração de trabalhadores
MAX_WORKERS = 3  # Número máximo de trabalhadores

app = FastAPI()

# Função do trabalhador
async def worker(worker_id: int):
    """Trabalhador que consome itens da fila de UUIDs."""
    logger.info(f"[Trabalhador {worker_id}] Iniciado e aguardando tarefas...")
    while True:
        user_uuid = await fila_uuids.get()
        try:
            logger.info(f"[Trabalhador {worker_id}] Processando UUID: {user_uuid}")
            await asyncio.sleep(2)  # Simulação de processamento
            logger.info(f"[Trabalhador {worker_id}] UUID {user_uuid} processado com sucesso")
        except Exception as e:
            logger.error(f"[Trabalhador {worker_id}] Erro ao processar UUID {user_uuid}: {e}")
        finally:
            fila_uuids.task_done()

# Ciclo de vida da aplicação
async def lifespan(app: FastAPI):
    logger.info("Iniciando a API...")

    # Inicializar o banco de dados
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Banco de dados inicializado com sucesso.")

    # Inicializar os trabalhadores
    logger.info(f"Iniciando {MAX_WORKERS} trabalhadores...")
    for i in range(MAX_WORKERS):
        asyncio.create_task(worker(i))

    yield

    # Finalizar recursos
    logger.info("Encerrando a API...")
    await engine.dispose()
    logger.info("Conexão com o banco de dados encerrada.")

# Inicialização do FastAPI
app = FastAPI(
    title="Notion Integration API",
    description="API para integração com Notion e manipulação de intimações",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Registrar os roteadores
app.include_router(process_routes, tags=["Processos empresa"])

# Healthcheck
@app.get("/healthcheck", tags=["Status"])
async def healthcheck():
    logger.info("Healthcheck chamado.")
    return {"status": "ok", "message": "Serviço operando normalmente"}

if __name__ == "__main__":
    import uvicorn

    HOST = os.getenv("APP_HOST", "127.0.0.1")
    PORT = int(os.getenv("APP_PORT", 8003))#8003))
    RELOAD = os.getenv("APP_RELOAD", "true").lower() == "true"

    uvicorn.run("main:app", host=HOST, port=PORT, reload=RELOAD)
