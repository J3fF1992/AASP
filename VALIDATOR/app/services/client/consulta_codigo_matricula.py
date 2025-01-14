from sqlalchemy.future import select
from models.db_config import SessionLocal
from models.models import User
from services.validador import NotionDatabase,NotionDatabaseClient
from utils.logger import logger

async def consultar_matriculas_vazias():
    matriculas_data = []

    async with SessionLocal() as session:
        try:
            # Consulta usuários com campos incompletos
            result = await session.execute(
                select(User).filter((User.matricula == None) | (User.codigo_aasp == None))
            )
            users_with_empty_fields = result.scalars().all()

            for associado in users_with_empty_fields:
                # Verificar se o usuário já foi processado no cache
                if associado.uuid in NotionDatabaseClient.processed_users:
                    logger.info(f"Usuário {associado.uuid} já processado. Ignorando.")
                    continue

                notion_database_result = await session.execute(
                    select(NotionDatabase).filter_by(uuid=associado.uuid)
                )
                notion_database = notion_database_result.scalar_one_or_none()

                if notion_database:
                    logger.info(f"Usuário encontrado: {associado.name}, UUID: {associado.uuid}.")
                    matriculas_data.append({
                        "banco_id": notion_database.matricula_db_id,
                        "access_token": associado.access_token,
                        "user_uuid": associado.uuid,
                    })
                else:
                    logger.warning(f"Nenhum banco do Notion associado encontrado para UUID: {associado.uuid}.")

        except Exception as e:
            logger.error(f"Erro ao consultar o banco de dados: {e}")

    return matriculas_data
