import httpx
from utils.logger import logger
import re

async def enviar_requisicao(client, url, headers, payload, tentativas=3):
    for tentativa in range(tentativas):
        try:
            response = await client.post(url, headers=headers, json=payload)
            return response
        except httpx.RequestError as e:
            if tentativa < tentativas - 1:
                continue
            raise e

def dividir_texto_em_blocos(texto: str, limite: int = 2000) -> list:
    return [texto[i:i + limite] for i in range(0, len(texto), limite)]

def formatar_dados_para_notion(dados_json: dict) -> dict:
    def dividir_texto_em_blocos(texto: str, limite: int = 2000) -> list:
        return [texto[i:i + limite] for i in range(0, len(texto), limite)]

    publicacao = (
        f"{dados_json.get('termoReferenciaData', '')} "
        f"{dados_json.get('titulo', '')} "
        f"{dados_json.get('cabecalho', '')} "
        f"{dados_json.get('textoPublicacao', '')} "
        f"{dados_json.get('rodape', '')}"
    ).strip()

    publicacao_formatada = re.sub(r";", r"\n", publicacao)
    blocos_publicacao = dividir_texto_em_blocos(publicacao_formatada)

    publicacao_rich_text = [{"text": {"content": bloco}} for bloco in blocos_publicacao]

    return {
        "Jornal": {"title": [{"text": {"content": dados_json.get('jornal', {}).get('nomeJornal', 'Sem Nome')}}]},
        "Tratado em": {"date": {"start": dados_json.get('jornal', {}).get('dataTratamento')}},
        "Disponibilização": {"date": {"start": dados_json.get('jornal', {}).get('dataDisponibilizacao_Publicacao')}},
        "Nº do Processo": {"rich_text": [{"text": {"content": dados_json.get('numeroUnicoProcesso', 'Sem Processo')}}]},
        "Publicação": {"rich_text": publicacao_rich_text},
        "Título": {"rich_text": [{"text": {"content": dados_json.get('titulo', 'Sem Título')}}]},
        "Cabeçalho": {"rich_text": [{"text": {"content": dados_json.get('cabecalho', 'Sem Cabeçalho')}}]},
        "Rodapé": {"rich_text": [{"text": {"content": dados_json.get('rodape') or 'Sem Rodapé'}}]},
        "Nº Publicação": {"number": dados_json.get('numeroPublicacao')},
        "Nº Arquivo": {"number": dados_json.get('numeroArquivo')},
        "Cod Relacionamento": {"number": dados_json.get('codigoRelacionamento')}
    }

async def enviar_dados_para_notion(intimacoes: list, access_token: str, notion_database_id: str):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    success_count = 0
    error_count = 0
    details = []

    total = len(intimacoes)
    logger.info(f"Iniciando o envio de {total} intimações para o Notion.")

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        for index, intimacao in enumerate(intimacoes, start=1):
            try:
                logger.info(f"Processando intimação {index}/{total}...")
                dados_formatados = formatar_dados_para_notion(intimacao)
                payload = {
                    "parent": {"database_id": notion_database_id},
                    "properties": dados_formatados
                }

                response = await enviar_requisicao(client, url, headers, payload, tentativas=3)

                if response.status_code == 200:
                    success_count += 1
                    logger.info(f"Intimação {index}/{total} enviada com sucesso.")
                else:
                    details.append({
                        "index": index,
                        "status": response.status_code,
                        "response_text": response.text
                    })
                    error_count += 1
                    logger.error(f"Erro ao enviar intimação {index}/{total}: {response.status_code} - {response.text}")

            except httpx.TimeoutException:
                details.append({"index": index, "error": "Timeout na solicitação"})
                error_count += 1
                logger.error(f"Timeout ao enviar intimação {index}/{total}.")
            except httpx.RequestError as e:
                details.append({"index": index, "error": f"Erro de conexão: {str(e)}"})
                error_count += 1
                logger.error(f"Erro de conexão ao enviar intimação {index}/{total}: {str(e)}")

    logger.info(f"Envio concluído para o banco {notion_database_id}: {success_count} sucesso(s), {error_count} erro(s).")
    return {"success": success_count, "errors": error_count, "details": details}