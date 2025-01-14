import requests
from utils.logger import logger
from utils.settings import NOTION_VERSION
from models.schemas import NotionDatabase


def criar_pagina_pai_no_workspace(access_token: str, titulo: str, pagina_id: str):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    payload = {
        "parent": {"type": "page_id", "page_id": pagina_id},
        "properties": {
            "title": [{"type": "text", "text": {"content": titulo}}]
        }
    }
    logger.info(f"Enviando payload para criar página no workspace: {payload}")
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            page_id = response.json().get("id")
            logger.info(f"Página pai criada com sucesso no workspace! ID: {page_id}")
            return page_id
        else:
            logger.error(f"Erro ao criar página no workspace: {response.status_code} - {response.text}")
            return None
    except requests.RequestException as e:
        logger.exception(f"Erro ao conectar à API do Notion: {e}")
        return None

def listar_paginas_existentes(access_token: str, nome_busca: str = None):
    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    payload = {
        "filter": {
            "value": "page",
            "property": "object"
        }
    }
    logger.info("Buscando páginas no workspace.")
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            paginas = response.json().get("results", [])
            logger.info(f"{len(paginas)} páginas encontradas no workspace.")
            for pagina in paginas:
                propriedades = pagina.get("properties", {})
                titulo_obj = propriedades.get("title", {}).get("title", [])
                titulo = titulo_obj[0].get("text", {}).get("content") if titulo_obj else None
                if titulo == nome_busca:
                    page_id = pagina.get("id")
                    page_url = pagina.get("url")
                    logger.info(f"Página encontrada: ID: {page_id}, URL: {page_url}, Nome: {titulo}")
                    return page_id, page_url
            logger.warning(f"Nenhuma página encontrada com o nome: {nome_busca}")
            return None, None
        else:
            logger.error(f"Erro ao buscar páginas: {response.status_code} - {response.text}")
            return None, None
    except requests.RequestException as e:
        logger.exception("Erro ao buscar páginas.")
        return None, None        

def atualizar_matricula_no_banco(db, shared_uuid, matricula_id):
    notion_database = db.query(NotionDatabase).filter_by(id=shared_uuid).first()
    if notion_database:
        notion_database.matricula_db_id = matricula_id
        db.commit()
        logger.info(f"Matricula ID {matricula_id} armazenado localmente para o usuário {shared_uuid}.")
    else:
        logger.error(f"Banco de dados local para o usuário {shared_uuid} não encontrado.")
