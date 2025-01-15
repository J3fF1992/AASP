import asyncio
from utils.resoucer import UserPayload
from datetime import datetime, timedelta
from services.notion.lote import obter_dados_para_lote
from services.notion_integration import enviar_dados_para_notion
from utils.logger import logger
from services.notion.lote import obter_dados_para_lote_associado
from services.notion_integration import atualizar_ultima_data

async def processar_intimacao_associado(payload: UserPayload, sessao):
    try:
        matricula = payload.matricula
        access_token = payload.access_token
        notion_database_id = payload.notion_database_id
        user_uuid = payload.user_uuid

        logger.info(f"Iniciando processamento para Matrícula: {matricula}")

        hoje = datetime.now()
        datas = [
            {"dia": (hoje - timedelta(days=i)).day,
             "mes": (hoje - timedelta(days=i)).month,
             "ano": (hoje - timedelta(days=i)).year}
            for i in range(1, 30)
        ]

        periodos = [datas[i:i + 5] for i in range(0, len(datas), 5)]
        semaphore = asyncio.Semaphore(3)

        async def processar_periodo(periodo):
            async with semaphore:
                return await obter_dados_para_lote_associado(matricula, periodo)

        tasks = [processar_periodo(periodo) for periodo in periodos]
        resultados = await asyncio.gather(*tasks)

        intimações_para_enviar = [
            intimacao
            for resultado in resultados
            for intimacao in resultado["intimacoes"]
        ]

        if intimações_para_enviar:
            await enviar_dados_para_notion(
                intimacoes=intimações_para_enviar,
                access_token=access_token,
                notion_database_id=notion_database_id
            )

            ultima_data = max(
                datetime.fromisoformat(intimacao['jornal']['dataTratamento'])
                for intimacao in intimações_para_enviar
            )
            await atualizar_ultima_data(sessao, user_uuid, ultima_data)

        logger.info(f"Processamento concluído para Matrícula: {matricula}")
        return {
            "message": f"Processamento concluído para Matrícula: {matricula}",
            "sucessos": len(intimações_para_enviar)
        }

    except Exception as e:
        logger.error(f"Erro ao processar Matrícula {matricula}: {e}", exc_info=True)
        return {"error": f"Erro ao processar Matrícula {matricula}: {str(e)}"}



async def processar_intimacao_empresa(payload: UserPayload,sessao):
    try:
        matricula = payload.matricula
        codigo_aasp = payload.codigo_aasp
        access_token = payload.access_token
        notion_database_id = payload.notion_database_id

        logger.info(f"Iniciando processamento para Matrícula: {matricula}, Código: {codigo_aasp}")

        hoje = datetime.now()
        datas = [
            {"dia": (hoje - timedelta(days=i)).day,
             "mes": (hoje - timedelta(days=i)).month,
             "ano": (hoje - timedelta(days=i)).year}
            for i in range(1, 2)
        ]

        # Dividir as datas em períodos de 5 dias
        periodos = [datas[i:i + 5] for i in range(0, len(datas), 5)]

        semaphore = asyncio.Semaphore(3)  # Limitar o número de tarefas simultâneas

        async def processar_periodo(periodo):
            async with semaphore:
                return await obter_dados_para_lote(matricula, codigo_aasp, periodo)

        tasks = [processar_periodo(periodo) for periodo in periodos]
        resultados = await asyncio.gather(*tasks)

        intimações_para_enviar = [
            intimacao
            for resultado in resultados
            for intimacao in resultado["intimacoes"]
        ]

        erros = [
            erro
            for resultado in resultados
            for erro in resultado["erros"]
        ]

        # Enviar dados em lote para o Notion
        if intimações_para_enviar:
            await enviar_dados_para_notion(
                intimacoes=intimações_para_enviar,
                access_token=access_token,
                notion_database_id=notion_database_id
            )

        logger.info(f"Processamento concluído para Matrícula: {matricula}, Código: {codigo_aasp}")
        return {
            "message": f"Processamento concluído para Matrícula: {matricula}, Código: {codigo_aasp}",
            "detalhes": {
                "dias_processados": len(datas),
                "periodos_processados": len(periodos),
                "sucessos": len(intimações_para_enviar),
                "erros": len(erros),
                "erros_detalhados": erros,
                "periodo": periodos
            }
        }

    except Exception as e:
        logger.error(f"Erro ao processar Matrícula {matricula}, Código {codigo_aasp}: {e}", exc_info=True)
        return {"error": f"Erro ao processar Matrícula {matricula}, Código {codigo_aasp}: {str(e)}"}
