from fastapi import APIRouter, HTTPException, Request
import requests
import base64
from services.run_notion import run_notion_process
from utils.settings import REDIRECT_URI, NOTION_CLIENT_SECRET, NOTION_CLIENT_ID
import uuid
from utils.logger import logger
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

auth_lock = asyncio.Lock()
token_store = {}
router = APIRouter()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.RequestException),
)
def obter_access_token(payload, headers):
    token_url = "https://api.notion.com/v1/oauth/token"
    response = requests.post(token_url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

@router.get("/oauth/callback")
async def oauth_redirect(request: Request):
    logger.info("Requisição recebida no endpoint /oauth/callback.")
    
    async with auth_lock:
        logger.info("Obtendo lock para evitar concorrência na autenticação.")
        
        code = request.query_params.get("code")
        if not code:
            logger.error("Código de autorização não fornecido.")
            raise HTTPException(status_code=400, detail="Código de autorização não fornecido.")
        
        client_data = f"{NOTION_CLIENT_ID}:{NOTION_CLIENT_SECRET}"
        encoded_client_data = base64.b64encode(client_data.encode("utf-8")).decode("utf-8")
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_client_data}"
        }

        try:            
            token_data = obter_access_token(payload, headers)
            # logger.info(f"Resposta da API de OAuth: {token_data}")
            
            access_token = token_data.get("access_token")
            owner = token_data.get("owner", {})
            user_data = owner.get("user", {})
            name = user_data.get("name")
            email = user_data.get("person", {}).get("email")

            if not access_token:
                logger.error("Access token não encontrado na resposta da API.")
                raise HTTPException(status_code=400, detail="Access token não encontrado.")
            
            user_uuid = str(uuid.uuid4())
            formatted_uuid = user_uuid.replace("-", "")
            token_store[formatted_uuid] = access_token
            logger.info(f"Access token armazenado com sucesso para o usuário {formatted_uuid}.")

            return await run_notion_process(access_token, formatted_uuid, email, name)
        except requests.RequestException as e:
            logger.exception("Erro ao conectar com a API do Notion.")
            raise HTTPException(status_code=500, detail="Erro de comunicação com a API do Notion.")
        finally:
            logger.info("Lock liberado para novas requisições.")