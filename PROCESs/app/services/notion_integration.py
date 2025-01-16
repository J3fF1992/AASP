import httpx
from utils.logger import logger
import re
from sqlalchemy.dialects.postgresql import insert
import datetime
from models.models import UltimaIntimacaoProcessada
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio



async def atualizar_ultima_data(sessao: AsyncSession, usuario_uuid: str, nova_ultima_data: datetime):
    """Atualiza ou cria o registro da última data processada após o término."""
    try:
        # Certificar que `nova_ultima_data` é do tipo datetime
        if isinstance(nova_ultima_data, str):
            nova_ultima_data = datetime.fromisoformat(nova_ultima_data)

        # Remover milissegundos usando regex
        nova_ultima_data_str = re.sub(r'\.\d+', '', nova_ultima_data.isoformat())
        nova_ultima_data = datetime.datetime.fromisoformat(nova_ultima_data_str)

        stmt = insert(UltimaIntimacaoProcessada).values(
            usuario_uuid=usuario_uuid,
            ultima_data_processada=nova_ultima_data
        ).on_conflict_do_update(
            index_elements=['usuario_uuid'],  # Coluna que define o conflito
            set_={'ultima_data_processada': nova_ultima_data}  # Valor a ser atualizado
        )

        await sessao.execute(stmt)
        await sessao.commit()
        logger.info(f"Última data processada atualizada para {usuario_uuid}: {nova_ultima_data}")

    except Exception as e:
        logger.error(f"Erro ao atualizar última data processada para {usuario_uuid}: {e}")


# async def enviar_requisicao(client, url, headers, payload, tentativas=3):
#     for tentativa in range(tentativas):
#         try:
#             response = await client.post(url, headers=headers, json=payload)
#             return response
#         except httpx.RequestError as e:
#             if tentativa < tentativas - 1:
#                 continue
#             raise e


async def enviar_requisicao(client, url, headers, payload, tentativas=3):
    """
    Envia uma única requisição ao Notion, com tentativa em caso de falha.
    """
    for tentativa in range(1, tentativas + 1):
        try:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response
            logger.error(f"Tentativa {tentativa} falhou com código {response.status_code}: {response.text}")
        except httpx.RequestError as e:
            logger.error(f"Tentativa {tentativa} falhou devido a erro de conexão: {e}")
        await asyncio.sleep(1)  # Atraso entre tentativas
    raise Exception(f"Falha ao enviar após {tentativas} tentativas.")


async def enviar_dados_para_notion(intimacoes: list, access_token: str, notion_database_id: str):
    MAX_CONCURRENT_REQUESTS = 5
    """
    Envia múltiplas intimações para o Notion de forma paralela.
    """
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    total = len(intimacoes)
    logger.info(f"Iniciando o envio de {total} intimações para o Notion.")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def enviar_intimacao(index, intimacao):
        """
        Envia uma única intimação para o Notion.
        """
        async with semaphore:
            try:
                logger.info(f"Processando intimação {index + 1}/{total}...")
                dados_formatados = formatar_dados_para_notion(intimacao)
                payload = {
                    "parent": {"database_id": notion_database_id},
                    "properties": dados_formatados
                }
                async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                    response = await enviar_requisicao(client, url, headers, payload, tentativas=3)
                logger.info(f"Intimação {index + 1}/{total} enviada com sucesso.")
                return {"index": index, "success": True}
            except Exception as e:
                logger.error(f"Erro ao enviar intimação {index + 1}/{total}: {str(e)}")
                return {"index": index, "success": False, "error": str(e)}

    # Cria tarefas para todas as intimações
    tasks = [enviar_intimacao(index, intimacao) for index, intimacao in enumerate(intimacoes)]
    
    # Executa todas as tarefas simultaneamente
    resultados = await asyncio.gather(*tasks)

    # Resumo de sucessos e falhas
    success_count = sum(1 for r in resultados if r.get("success"))
    error_count = total - success_count
    logger.info(f"Envio concluído para o banco {notion_database_id}: {success_count} sucesso(s), {error_count} erro(s).")

    return {"success": success_count, "errors": error_count, "details": resultados}


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

# async def enviar_dados_para_notion(intimacoes: list, access_token: str, notion_database_id: str):
#     url = "https://api.notion.com/v1/pages"
#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json",
#         "Notion-Version": "2022-06-28"
#     }

#     success_count = 0
#     error_count = 0
#     details = []

#     total = len(intimacoes)
#     logger.info(f"Iniciando o envio de {total} intimações para o Notion.")

#     async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
#         for index, intimacao in enumerate(intimacoes, start=1):
#             try:
#                 logger.info(f"Processando intimação {index}/{total}...")
#                 dados_formatados = formatar_dados_para_notion(intimacao)
#                 payload = {
#                     "parent": {"database_id": notion_database_id},
#                     "properties": dados_formatados
#                 }

#                 response = await enviar_requisicao(client, url, headers, payload, tentativas=3)

#                 if response.status_code == 200:
#                     success_count += 1
#                     logger.info(f"Intimação {index}/{total} enviada com sucesso.")
#                 else:
#                     details.append({
#                         "index": index,
#                         "status": response.status_code,
#                         "response_text": response.text
#                     })
#                     error_count += 1
#                     logger.error(f"Erro ao enviar intimação {index}/{total}: {response.status_code} - {response.text}")

#             except httpx.TimeoutException:
#                 details.append({"index": index, "error": "Timeout na solicitação"})
#                 error_count += 1
#                 logger.error(f"Timeout ao enviar intimação {index}/{total}.")
#             except httpx.RequestError as e:
#                 details.append({"index": index, "error": f"Erro de conexão: {str(e)}"})
#                 error_count += 1
#                 logger.error(f"Erro de conexão ao enviar intimação {index}/{total}: {str(e)}")

#     logger.info(f"Envio concluído para o banco {notion_database_id}: {success_count} sucesso(s), {error_count} erro(s).")
#     return {"success": success_count, "errors": error_count, "details": details}