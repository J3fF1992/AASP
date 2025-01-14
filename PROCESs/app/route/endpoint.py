from fastapi import FastAPI, APIRouter,Body
from services.notion.route import processar_intimacao_empresa, processar_intimacao_associado
from utils.resoucer import UserPayload
from utils.logger import logger
from fastapi.responses import JSONResponse
import asyncio

app = FastAPI()
router = APIRouter()


@router.post("/empresa")
async def intimacao_empresa(payload: UserPayload = Body(...)):
    logger.info(f"Recebido payload para empresa: {payload.dict()}")

    if not payload.matricula or not payload.codigo_aasp:
        logger.error("Payload inválido: Matrícula e Código AASP são obrigatórios.")
        return JSONResponse(status_code=400, content={"message": "Matrícula e Código AASP são obrigatórios para empresa."})

    # Return initial response immediately
    response = JSONResponse(status_code=202, content={"message": "Processamento iniciado."})
    
    # Process the payload asynchronously
    async def process_payload():
        try:
            resultado = await processar_intimacao_empresa(payload)

            if "error" in resultado:
                logger.error(f"Erro no processamento para empresa: {resultado['error']}")
            else:
                logger.info(f"Processamento concluído para empresa: {resultado}")

        except Exception as e:
            logger.error(f"Erro inesperado ao processar empresa: {e}")

    asyncio.create_task(process_payload())

    return response


@router.post("/associado")
async def intimacao_empresa(payload: UserPayload = Body(...)):
    logger.info(f"Recebido payload para associado: {payload.dict()}")

    if not payload.matricula:
        logger.error("Payload inválido: Matrícula é obrigatórios.")
        return JSONResponse(status_code=400, content={"message": "Matrícula é obrigatórios para associado."})

    # Return initial response immediately
    response = JSONResponse(status_code=202, content={"message": "Processamento iniciado."})
    
    # Process the payload asynchronously
    async def process_payload():
        try:
            resultado = await processar_intimacao_associado(payload)

            if "error" in resultado:
                logger.error(f"Erro no processamento para empresa: {resultado['error']}")
            else:
                logger.info(f"Processamento concluído para associado: {resultado}")

        except Exception as e:
            logger.error(f"Erro inesperado ao processar associado: {e}")

    asyncio.create_task(process_payload())

    return response