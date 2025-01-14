from fastapi import APIRouter, HTTPException
from services.notion_services.create_database import criar_banco_de_dados, criar_banco_matricula
from services.notion_services.create_page import listar_paginas_existentes, criar_pagina_pai_no_workspace
from models.db_config import engine
from utils.logger import logger
from models.schemas import NotionDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.responses import RedirectResponse
import random
import httpx

router = APIRouter()
HTTP_TIMEOUT = 30.0

async def run_notion_process(access_token: str, user_id: int, email: str = None, user_name: str = None):
    logger.info(f"Iniciando processo de criação no Notion para usuário ID: {user_id} (Email: {email}).")

    async with AsyncSession(engine) as db:
        try:
            timeout = httpx.Timeout(HTTP_TIMEOUT)
            async with httpx.AsyncClient(timeout=timeout) as client:

                logger.info("Buscando páginas existentes no workspace.")
                pagina_id, pagina_url = listar_paginas_existentes(access_token, nome_busca="TESTE")

                if not pagina_id:
                    logger.warning("Página 'TESTE' não encontrada no workspace.")
                    raise HTTPException(status_code=404, detail="Página 'TESTE' não encontrada no workspace.")

                logger.info(f"Página encontrada: ID={pagina_id}, URL={pagina_url}. Criando página pai.")
                nova_pagina_id = criar_pagina_pai_no_workspace(access_token, "AASP - Consulta de processos", pagina_id)

                if not nova_pagina_id:
                    logger.error("Erro ao criar a página pai no workspace.")
                    raise HTTPException(status_code=500, detail="Erro ao criar página pai no workspace.")

                logger.info(f"Página pai criada com sucesso: ID={nova_pagina_id}.")

                random_number = str(random.randint(1000, 9999))
                unique_email = f"{email}{random_number}"

                logger.info("Iniciando a criação do banco de dados no Notion.")
                banco_id, banco_url = await criar_banco_de_dados(
                    access_token=access_token,
                    page_id=nova_pagina_id,
                    nome_banco="Banco de Dados - Consultar processos",
                    user_id=user_id,
                    db=db,
                    email=unique_email,
                    user_name=user_name,
                )

                if banco_id:
                    banco_id_clean = banco_id.replace("-", "")
                    logger.info(f"Banco de dados criado no Notion: ID={banco_id_clean}, URL={banco_url}.")

                    result = await db.execute(select(NotionDatabase).filter(NotionDatabase.uuid == user_id))
                    notion_database = result.scalar_one_or_none()

                    if notion_database:
                        notion_database.notion_database_id = banco_id_clean
                        await db.commit()
                        logger.info(f"Banco de dados (ID={banco_id_clean}) armazenado no banco local.")

                logger.info("Criando banco de matrículas no Notion.")
                banco_matricula = await criar_banco_matricula(parent_id=nova_pagina_id, access_token=access_token)

                if not banco_matricula:
                    logger.error("Banco de matrículas não foi criado.")
                    raise HTTPException(status_code=500, detail="Erro ao criar banco de matrículas no Notion.")

                matricula_id = banco_matricula["id"].replace("-", "")
                logger.info(f"Banco de matrículas criado: ID={matricula_id}, URL={banco_matricula['url']}.")

                if notion_database:
                    notion_database.matricula_db_id = matricula_id
                    await db.commit()
                    logger.info(f"Banco de matrículas (ID={matricula_id}) armazenado no banco local.")

                logger.info(f"Processo concluído com sucesso. Redirecionando para: {banco_matricula['url']}.")
                return RedirectResponse(url=banco_matricula['url'], status_code=303)

        except HTTPException as e:
            logger.error(f"Erro HTTP durante o processo: {e.detail}")
            raise

        except httpx.ReadTimeout:
            logger.error(f"Erro de timeout na comunicação com o Notion. Timeout configurado: {HTTP_TIMEOUT} segundos.")
            raise HTTPException(status_code=504, detail="Erro de timeout na comunicação com o Notion.")

        except Exception as e:
            logger.exception("Erro inesperado durante o processo de criação no Notion.")
            raise HTTPException(status_code=500, detail="Erro no fluxo de criação no Notion.")