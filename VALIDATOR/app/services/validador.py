import httpx
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy.future import select
from unidecode import unidecode
from models.models import NotionDatabase, User
from utils.settings import DATABASE_URL, NOTION_API_VERSION
from utils.logger import logger
import asyncio


# Configuração do SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

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

class NotionAPIUtils:
    @staticmethod
    async def consultar_dados(database_id, access_token):
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_API_VERSION,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                logger.info("Dados do banco recuperados com sucesso.")
                return data.get("results", [])
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro HTTP: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.exception(f"Erro durante a solicitação: {e}")
                return None

    @staticmethod
    def validar_dados(results):
        if not results:
            logger.warning("Nenhum registro encontrado no banco.")
            return False, [], [], []

        logger.info("Validando registros...")
        matriculas, codigos_aasp, tipos = [], [], []

        for item in results:
            properties = item.get("properties", {})

            # Validação e normalização da Chave de Acesso
            matricula = properties.get("Chave de Acesso", {}).get("rich_text", [])
            valor_matricula = (
                matricula[0].get("text", {}).get("content", "Não preenchido") if matricula else "Não preenchido"
            )
            matriculas.append(normalizar_valor(valor_matricula))

            # Validação e normalização do Código AASP
            codigo_aasp = properties.get("Código AASP", {}).get("rich_text", [])
            valor_codigo_aasp = (
                codigo_aasp[0].get("text", {}).get("content", "") if codigo_aasp else ""
            )
            codigos_aasp.append(normalizar_valor(valor_codigo_aasp))

            # Validação e normalização do Tipo
            tipo = properties.get("Tipo", {}).get("rich_text", [])
            valor_tipo = (
                tipo[0].get("text", {}).get("content", "Não preenchido") if tipo else "Não preenchido"
            )
            tipos.append(normalizar_valor(valor_tipo))

            # Validação dos valores
            if (valor_matricula == "Não preenchido" or
                valor_tipo not in ["empresa", "associado"] or
                (valor_tipo == "empresa" and not valor_codigo_aasp)):
                logger.info(f"Registro ID: {item.get('id')} ainda está com campos faltantes.")
                return False, matriculas, codigos_aasp, tipos

        logger.info("Todos os registros possuem Matrícula, Código AASP e Tipo válidos.")
        return True, matriculas, codigos_aasp, tipos

class NotionDatabaseClient:
    processed_users = set()  # Cache em memória para armazenar usuários processados

    def __init__(self, database_id, access_token, session):
        self.database_id = database_id
        self.access_token = access_token
        self.session = session

    async def enviar_para_api_externa(self, payload, endpoint):
        """
        Envia os dados para a API externa e verifica sucesso com base no status HTTP.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload)
                if 200 <= response.status_code < 300:
                    logger.info(f"Dados enviados com sucesso para o endpoint: {endpoint}")
                    return True
                else:
                    logger.warning(f"Falha ao enviar dados. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            logger.error(f"Erro ao enviar dados para API externa: {e}")
        return False

    async def processar_associado(self, user_uuid):
        """Processa o associado, verifica cache e atualiza banco de dados."""
        if user_uuid in self.processed_users:
            logger.info(f"Usuário {user_uuid} já processado. Ignorando.")
            return

        try:
            # Buscar e validar dados no Notion
            logger.info(f"Consultando dados no Notion para o usuário {user_uuid}...")
            results = await NotionAPIUtils.consultar_dados(self.database_id, self.access_token)
            all_valid, matriculas, codigos_aasp, tipos = NotionAPIUtils.validar_dados(results)

            if not all_valid:
                logger.warning(f"Dados incompletos para o usuário {user_uuid}. Ignorando.")
                return

            # Atualizar banco de dados
            async with self.session.begin():
                user = (await self.session.execute(
                    select(User).filter_by(uuid=user_uuid)
                )).scalars().first()

                if not user:
                    logger.error(f"Usuário {user_uuid} não encontrado.")
                    return

                user.matricula = matriculas[0]
                user.codigo_aasp = codigos_aasp[0] if tipos[0] == "empresa" else None
                user.tipo = tipos[0]

            # Buscar NotionDatabase
            notion_record = (await self.session.execute(
                select(NotionDatabase).filter_by(matricula_db_id=self.database_id)
            )).scalar_one_or_none()

            if not notion_record:
                logger.error(f"NotionDatabase não encontrado para ID {self.database_id}")
                return

            # Preparar payload
            payload = {
                "matricula": user.matricula,
                "access_token": self.access_token,
                "notion_database_id": notion_record.notion_database_id,
                "tipo": user.tipo,
            }
            if user.tipo == "empresa":
                payload["codigo_aasp"] = user.codigo_aasp
                endpoint = "http://localhost:8003/empresa"
            else:
                endpoint = "http://localhost:8003/associado"

            logger.info(f"Enviando payload para {endpoint}: {payload}")

            # Enviar para o endpoint
            if await self.enviar_para_api_externa(payload, endpoint):
                self.processed_users.add(user_uuid)
                logger.info(f"Usuário {user_uuid} processado com sucesso.")
            else:
                logger.warning(f"Falha ao processar usuário {user_uuid}.")

        except Exception as e:
            logger.error(f"Erro ao processar usuário {user_uuid}: {e}")
            self.processed_users.add(user_uuid)  # Evitar loops infinitos em caso de erro
