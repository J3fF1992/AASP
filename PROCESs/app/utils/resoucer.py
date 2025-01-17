import asyncio
from pydantic import BaseModel
import unidecode
from fastapi import HTTPException, Body
from utils.logger import logger
from typing import Optional

def normalizar_valor(valor):
    """
    Normaliza o valor de texto:
    - Remove acentos.
    - Converte para minúsculas.
    - Remove caracteres especiais.
    - Remove espaços extras.
    """
    if not valor:
        return ""
    valor = unidecode(valor)  # Remove acentos
    valor = "".join(e for e in valor if e.isalnum() or e.isspace())  # Remove caracteres especiais
    return valor.strip().lower()  # Remove espaços extras e converte para minúsculas



fila_uuids = asyncio.Queue()

class UserPayload(BaseModel):
    matricula: str
    codigo_aasp: Optional[str] = None
    access_token: str
    user_uuid: str
    notion_database_id: str
    tipo: str

class UserPayloadAssociado(BaseModel):
    matricula: str    
    access_token: str
    notion_database_id: str
    tipo: str

class NotionAPIUtils:
    @staticmethod
    def normalizar_valor(valor):
        """Normaliza o valor de texto."""
        if not valor:
            return ""
        valor = unidecode.unidecode(valor)  # Remove acentos
        valor = "".join(e for e in valor if e.isalnum() or e.isspace())  # Remove caracteres especiais
        return valor.strip().lower()  # Remove espaços extras e converte para minúsculas


async def validar_payload(payload: UserPayload = Body(...)):
    """
    Valida e normaliza o payload recebido.
    """
    # Log do payload recebido
    logger.info(f"Payload recebido: {payload.dict()}")

    try:
        # Validar e normalizar os campos
        matricula = payload.matricula.strip()
        tipo = payload.tipo.strip().lower()
        codigo_aasp = payload.codigo_aasp.strip() if payload.codigo_aasp else None

        # Log do que foi processado
        logger.info(f"Valores processados - Matrícula: {matricula}, Tipo: {tipo}, Código AASP: {codigo_aasp}")

        # Validação específica
        if tipo not in ["empresa", "associado"]:
            raise HTTPException(
                status_code=422,
                detail="Tipo inválido. Valores permitidos: 'empresa', 'associado'."
            )

        if tipo == "empresa" and not codigo_aasp:
            raise HTTPException(
                status_code=422,
                detail="Para 'empresa', o campo 'codigo_aasp' é obrigatório."
            )

        return payload.dict()

    except ValidationError as ve:
        logger.error(f"Erro de validação do payload: {ve.errors()}")
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as e:
        logger.error(f"Erro inesperado ao validar payload: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
