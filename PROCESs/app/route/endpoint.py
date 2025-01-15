from fastapi import FastAPI, APIRouter, Body, Depends
from services.notion.route import processar_intimacao_empresa, processar_intimacao_associado
from utils.resoucer import UserPayload
from utils.logger import logger
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from models.db_config import get_db
import asyncio

app = FastAPI()
router = APIRouter()


@router.post("/empresa")
async def intimacao_empresa(
    payload: UserPayload = Body(...), 
    sessao: AsyncSession = Depends(get_db)
):
    logger.info(f"Recebido payload para empresa: {payload.dict()}")

    if not payload.matricula or not payload.codigo_aasp:
        logger.error("Payload inválido: Matrícula e Código AASP são obrigatórios.")
        return JSONResponse(status_code=400, content={"message": "Matrícula e Código AASP são obrigatórios para empresa."})

    # Resposta inicial
    response = JSONResponse(status_code=202, content={"message": "Processamento iniciado."})

    # Processar o payload de forma assíncrona
    async def process_payload():
        try:
            resultado = await processar_intimacao_empresa(payload, sessao)

            if "error" in resultado:
                logger.error(f"Erro no processamento para empresa: {resultado['error']}")
            else:
                logger.info(f"Processamento concluído para empresa: {resultado}")

        except Exception as e:
            logger.error(f"Erro inesperado ao processar empresa: {e}")

    asyncio.create_task(process_payload())

    return response


@router.post("/associado")
async def intimacao_associado(
    payload: UserPayload = Body(...), 
    sessao: AsyncSession = Depends(get_db)
):
    logger.info(f"Recebido payload para associado: {payload.dict()}")

    if not payload.matricula:
        logger.error("Payload inválido: Matrícula é obrigatória.")
        return JSONResponse(status_code=400, content={"message": "Matrícula é obrigatória para associado."})

    # Resposta inicial
    response = JSONResponse(status_code=202, content={"message": "Processamento iniciado."})

    # Processar o payload de forma assíncrona
    async def process_payload():
        try:
            resultado = await processar_intimacao_associado(payload, sessao)

            if "error" in resultado:
                logger.error(f"Erro no processamento para associado: {resultado['error']}")
            else:
                logger.info(f"Processamento concluído para associado: {resultado}")

        except Exception as e:
            logger.error(f"Erro inesperado ao processar associado: {e}")

    asyncio.create_task(process_payload())

    return response


app.include_router(router)
