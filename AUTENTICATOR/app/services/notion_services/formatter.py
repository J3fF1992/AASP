import httpx
from sqlalchemy.orm import Session
from utils.logger import logger


def formatar_dados_para_notion(dados_json: dict) -> dict:
    def formatar_data(data: str) -> str:
        return data if data else None

    publicacao = (
        f"{dados_json.get('termoReferenciaData', '')} "
        f"{dados_json.get('titulo', '')} "
        f"{dados_json.get('cabecalho', '')} "
        f"{dados_json.get('textoPublicacao', '')} "
        f"{dados_json.get('rodape', '')}"
    ).strip()

    return {
        "Jornal": {"title": [{"text": {"content": dados_json.get('jornal', {}).get('nomeJornal', 'Sem Nome')}}]},
        "Tratado em": {"date": {"start": formatar_data(dados_json.get('jornal', {}).get('dataTratamento'))}},
        "Disponibilização": {"date": {"start": formatar_data(dados_json.get('jornal', {}).get('dataDisponibilizacao_Publicacao'))}},
        "Nº do Processo": {"rich_text": [{"text": {"content": dados_json.get('numeroUnicoProcesso', 'Sem Processo')}}]},
        "Publicação": {"rich_text": [{"text": {"content": publicacao}}]},
        "Nº Publicação": {"number": dados_json.get('numeroPublicacao')},
        "Nº Arquivo": {"number": dados_json.get('numeroArquivo')},
        "Cod Relacionamento": {"number": dados_json.get('codigoRelacionamento')},
        "Título": {"rich_text": [{"text": {"content": dados_json.get('titulo', 'Sem Título')}}]},
        "Cabeçalho": {"rich_text": [{"text": {"content": dados_json.get('cabecalho', 'Sem Cabeçalho')}}]},
        "Rodapé": {"rich_text": [{"text": {"content": dados_json.get('rodape', 'Sem Rodapé')}}]}
    }


async def enviar_dados_para_notion(
    user_uuid: str,
    intimacoes: list,
    access_token: str,
    notion_database_id: str,
    db: Session
):
    logger.debug(f"Usuário: {user_uuid}, DEFAULT_DATABASE_ID={notion_database_id}")
    # logger.debug(f"Usuário: {user_uuid}, ACCESS_TOKEN={access_token}, DEFAULT_DATABASE_ID={notion_database_id}")

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
                logger.error(f"Intimação {index}: Dados não formatados corretamente.")
                error_count += 1
                error_details.append({"index": index, "error": "Dados não formatados corretamente"})
                continue

            payload = {
                "parent": {"database_id": notion_database_id},
                "properties": dados_formatados
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    logger.info(f"Intimação {index}: Dados enviados com sucesso ao Notion.")
                    success_count += 1
                    success_details.append({"index": index, "response": response.json()})
                else:
                    logger.error(f"Intimação {index}: Erro ao enviar dados ({response.status_code}): {response.text}")
                    error_count += 1
                    error_details.append({
                        "index": index,
                        "status_code": response.status_code,
                        "response": response.text
                    })

        except Exception as e:
            logger.exception(f"Intimação {index}: Erro ao processar intimação: {str(e)}")
            error_count += 1
            error_details.append({"index": index, "error": str(e)})

    logger.info(f"Envio concluído: {success_count} enviados com sucesso, {error_count} erros.")

    return {
        "success": success_count,
        "errors": error_count,
        "details": {
            "success": success_details,
            "errors": error_details
        }
    }
