from pydantic import BaseModel, Field
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from utils.logger import logger
from models.models import User
from sqlalchemy.future import select
from datetime import datetime


class IntimacaoRequest(BaseModel):
    matricula: str = Field(..., example="33F27778582844DE9BD8C465BD603CF2")
    dia: int = Field(..., ge=1, le=31, example=4)
    mes: int = Field(..., ge=1, le=12, example=12)
    ano: int = Field(..., ge=1900, le=2100, example=2024)

def validar_data(dia: int, mes: int, ano: int) -> bool:
    try:
        datetime(year=ano, month=mes, day=dia)
        logger.info(f"Data validada com sucesso: {dia}/{mes}/{ano}")
        return True
    except ValueError:
        logger.error(f"Data inválida fornecida: {dia}/{mes}/{ano}")
        return False

async def obter_credenciais_do_usuario(user_uuid: str, db: AsyncSession):
    try:
        result = await db.execute(select(User).where(User.uuid == user_uuid))
        user = result.scalars().first()
        if not user:
            logger.error(f"Usuário não encontrado: {user_uuid}")
            raise ValueError("Usuário não encontrado")
        notion_database_id = user.notion_databases[0].notion_database_id if user.notion_databases else None
        return user.access_token, notion_database_id
    except Exception as e:
        logger.error(f"Erro ao obter credenciais do usuário: {e}")
        raise

async def obter_dados_intimacao(matricula: str, codigo: str, data: dict) -> dict:
    try:
        # Formatar a data no formato dia%2Fmes%2Fano
        data_formatada = f"{data['dia']:02d}%2F{data['mes']:02d}%2F{data['ano']}"
        url = f"http://intimacaoapi.aasp.org.br/api/Empresa/intimacao?chave={matricula}&codigoPessoaAssociado={codigo}&data={data_formatada}"

        logger.info(f"Requisição para {url}")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            logger.error(f"Erro na API: {response.status_code}")
            return {"error": f"Erro na API: {response.status_code}"}
    except Exception as e:
        logger.error(f"Erro de conexão: {str(e)}")
        return {"error": str(e)}
    
async def obter_dados_intimacao_associado(matricula: str, data: dict) -> dict:
    try:
        # Formatar a data no formato dia%2Fmes%2Fano
        data_formatada = f"{data['dia']:02d}%2F{data['mes']:02d}%2F{data['ano']}"
        url = f"https://intimacaoapi.aasp.org.br/api/Associado/intimacao/json?chave={matricula}&data={data_formatada}&diferencial=false"
        

        logger.info(f"Requisição para {url}")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            logger.error(f"Erro na API: {response.status_code}")
            return {"error": f"Erro na API: {response.status_code}"}
    except Exception as e:
        logger.error(f"Erro de conexão: {str(e)}")
        return {"error": str(e)}

    

def formatar_dados_para_notion(dados_json: dict) -> dict:
    def formatar_data(data: str) -> str:
        return data if data else None

    jornal_nome = dados_json.get('jornal', {}).get('nomeJornal', None) or "Sem Nome"
    publicacao = (
        f"{dados_json.get('termoReferenciaData', '')} "
        f"{dados_json.get('titulo', '')} "
        f"{dados_json.get('cabecalho', '')} "
        f"{dados_json.get('textoPublicacao', '')} "
        f"{dados_json.get('rodape', '')}"
    ).strip()

    return {
        "Jornal": {"title": [{"text": {"content": jornal_nome}}]},
        "Tratado em": {"date": {"start": formatar_data(dados_json.get('jornal', {}).get('dataTratamento'))}},
        "Disponibilização": {"date": {"start": formatar_data(dados_json.get('jornal', {}).get('dataDisponibilizacao_Publicacao'))}},
        "Nº do Processo": {"rich_text": [{"text": {"content": dados_json.get('numeroUnicoProcesso', 'Sem Processo')}}]},
        "Publicação": {"rich_text": [{"text": {"content": publicacao}}]},
        "Nº Publicação": {"number": dados_json.get('numeroPublicacao') or 0},
        "Nº Arquivo": {"number": dados_json.get('numeroArquivo') or 0},
        "Cod Relacionamento": {"number": dados_json.get('codigoRelacionamento') or 0},
        "Título": {"rich_text": [{"text": {"content": dados_json.get('titulo', 'Sem Título')}}]},
        "Cabeçalho": {"rich_text": [{"text": {"content": dados_json.get('cabecalho', 'Sem Cabeçalho')}}]},
        "Rodapé": {"rich_text": [{"text": {"content": dados_json.get('rodape') or 'Sem Rodapé'}}]}
    }