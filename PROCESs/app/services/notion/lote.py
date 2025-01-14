
from utils.logger import logger
from services.request_intimation import obter_dados_intimacao_associado
from services.request_intimation import obter_dados_intimacao



async def obter_dados_para_lote_associado(matricula, datas):
    try:
        logger.info(f"Obtendo dados para o período {datas[0]} até {datas[-1]} (Matrícula: {matricula})")
        intimações_agrupadas = []
        erros = []

        for data in datas:
            try:
                dados = await obter_dados_intimacao_associado(matricula, data)
                if dados and "intimacoes" in dados:
                    intimações_agrupadas.extend(dados.get("intimacoes", []))
                elif "error" in dados:
                    erros.append({"data": data, "detalhes": dados.get('error', 'Erro desconhecido')})
            except Exception as e:
                logger.error(f"Erro ao obter dados para {data}: {e}", exc_info=True)
                erros.append({"data": data, "detalhes": str(e)})

        return {"intimacoes": intimações_agrupadas, "erros": erros}

    except Exception as e:
        logger.error(f"Erro inesperado ao processar período {datas}: {e}", exc_info=True)
        raise


async def obter_dados_para_lote(matricula, codigo_aasp, datas):
    try:
        logger.info(f"Obtendo dados para o período {datas[0]} até {datas[-1]} (Matrícula: {matricula}, Código: {codigo_aasp})")
        intimações_agrupadas = []
        erros = []

        for data in datas:
            try:
                dados = await obter_dados_intimacao(matricula, codigo_aasp, data)
                if dados and "intimacoes" in dados:
                    intimações_agrupadas.extend(dados.get("intimacoes", []))
                elif "error" in dados:
                    erros.append({"data": data, "detalhes": dados.get('error', 'Erro desconhecido')})
            except Exception as e:
                logger.error(f"Erro ao obter dados para {data}: {e}", exc_info=True)
                erros.append({"data": data, "detalhes": str(e)})

        return {"intimacoes": intimações_agrupadas, "erros": erros}

    except Exception as e:
        logger.error(f"Erro inesperado ao processar período {datas}: {e}", exc_info=True)
        raise