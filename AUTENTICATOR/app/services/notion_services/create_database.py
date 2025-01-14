from fastapi import HTTPException
from pydantic import BaseModel, Field
import httpx
from utils.logger import logger
from utils.settings import NOTION_VERSION
from services.notion_services.formatter import formatar_dados_para_notion
from sqlalchemy.orm import Session
from models.schemas import NotionDatabase, User
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

class IntimacaoRequest(BaseModel):
    matricula: str = Field(..., example="33F27778582844DE9BD8C465BD603CF2")
    dia: int = Field(..., ge=1, le=31, example=4)
    mes: int = Field(..., ge=1, le=12, example=12)
    ano: int = Field(..., ge=1900, le=2100, example=2024)

async def consultar_banco(access_token: str, database_id: str):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers)
            if response.status_code == 200:
                return response.json().get("results", [])
            else:
                logger.error(f"Erro ao consultar o banco: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail="Erro ao consultar banco de dados.")
    except httpx.RequestError as e:
        logger.exception(f"Erro ao conectar ao banco: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
async def criar_banco_de_dados(
    access_token: str, page_id: str, nome_banco: str, user_id: str, db: AsyncSession, email: str, user_name: str
):
    logger.info(f"Iniciando criação de banco de dados. Page ID: {page_id}, Nome do Banco: {nome_banco}, User ID: {user_id}")
    shared_uuid = user_id if user_id else str(uuid.uuid4()).replace("-", "")

    try:
        logger.info(f"Verificando existência do usuário no banco local. User UUID: {shared_uuid}")
        result = await db.execute(select(User).filter(User.uuid == shared_uuid))
        usuario = result.scalar_one_or_none()

        if not usuario:
            logger.info(f"Usuário não encontrado no banco local. Criando novo usuário. Email: {email}, Nome: {user_name}")
            novo_usuario = User(uuid=shared_uuid, name=user_name, email=email, access_token=access_token)
            db.add(novo_usuario)
            await db.commit()
            usuario = novo_usuario

        url = "https://api.notion.com/v1/databases"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }
        payload = {
            "parent": {"type": "page_id", "page_id": page_id},
            "title": [{"type": "text", "text": {"content": nome_banco}}],
            "properties": {
                "Jornal": {"title": {}},
                "Tratado em": {"date": {}},
                "Disponibilização": {"date": {}},
                "Nº do Processo": {"rich_text": {}},
                "Publicação": {"rich_text": {}},
                "Nº Publicação": {"number": {}},
                "Nº Arquivo": {"number": {}},
                "Cod Relacionamento": {"number": {}},
                "Título": {"rich_text": {}},
                "Cabeçalho": {"rich_text": {}},
                "Rodapé": {"rich_text": {}},
            },
        }

        logger.info(f"Enviando payload para criar banco de dados no Notion. Payload: {payload}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                logger.info("Banco de dados criado com sucesso no Notion.")
                database = response.json()
                database_id = database.get("id")
                database_url = database.get("url")
                formatted_database_id = database_id.replace("-", "")

                result = await db.execute(select(NotionDatabase).filter(NotionDatabase.uuid == shared_uuid))
                existente = result.scalar_one_or_none()

                if existente:
                    logger.info(f"Atualizando banco local com o ID do banco criado. Banco ID: {formatted_database_id}")
                    existente.notion_database_id = formatted_database_id
                    await db.commit()
                else:
                    logger.info(f"Criando novo registro de banco no banco local. Banco ID: {formatted_database_id}")
                    novo_banco = NotionDatabase(
                        uuid=shared_uuid,
                        notion_database_id=formatted_database_id,
                        matricula_db_id=formatted_database_id,
                    )
                    db.add(novo_banco)
                    await db.commit()

                return database_id, database_url

            else:
                logger.error(f"Erro ao criar banco de dados no Notion. Status Code: {response.status_code}, Response: {response.text}")
                raise HTTPException(status_code=500, detail="Erro ao criar banco no Notion.")

    except httpx.RequestError as e:
        logger.exception(f"Erro de conexão ao criar banco no Notion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
async def enviar_dados_para_notion(
    user_uuid: str, intimacoes: list, access_token: str, notion_database_id: str, db: Session
):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    success_count = 0
    error_count = 0
    success_details = []
    error_details = []
    for index, intimacao in enumerate(intimacoes, start=1):
        try:
            dados_formatados = formatar_dados_para_notion(intimacao)
            if not dados_formatados:
                error_count += 1
                error_details.append({"index": index, "error": "Dados não formatados corretamente"})
                continue
            payload = {"parent": {"database_id": notion_database_id}, "properties": dados_formatados}
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    success_count += 1
                    success_details.append({"index": index, "response": response.json()})
                else:
                    error_count += 1
                    error_details.append({"index": index, "status_code": response.status_code, "response": response.text})
        except Exception as e:
            error_count += 1
            error_details.append({"index": index, "error": str(e)})
    return {
        "success": success_count,
        "errors": error_count,
        "details": {"success": success_details, "errors": error_details}
    }

async def criar_banco_matricula(parent_id: str, access_token: str):
    url = "https://api.notion.com/v1/databases"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = {
        "parent": {"type": "page_id", "page_id": parent_id},
        "title": [{"type": "text", "text": {"content": "Configurações de acesso"}}],
        "properties": {
            "Dados do usuario": {"title": {}},
            "Tipo": {"rich_text": {}},
            "Chave de Acesso": {"rich_text": {}},
            "Código AASP": {"rich_text": {}}
        }
    }

    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return {"id": data["id"], "url": data["url"]}
            else:
                logger.error(f"Erro ao criar banco de dados: {response.status_code} - {response.text}")
                return None
        except httpx.RequestError as e:
            logger.exception("Erro durante a solicitação:")
            return None