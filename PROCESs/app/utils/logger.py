import logging
import os

# Definir o nível de log a partir da variável de ambiente ou usar "INFO" como padrão
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Criar um handler de saída padrão (console)
console_handler = logging.StreamHandler()

# Definir um formatter personalizado para incluir o status e outras informações
formatter = logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Associar o formatter ao handler
console_handler.setFormatter(formatter)

# Configurar o logger principal
logger = logging.getLogger(__name__)
logger.setLevel(log_level)
logger.addHandler(console_handler)

# Adicionar um exemplo de função para logar status
def log_status(status: str, mensagem: str, detalhes: dict = None):
    """
    Loga informações detalhadas de status.
    
    Args:
        status (str): Sucesso ou erro.
        mensagem (str): Mensagem descritiva do evento.
        detalhes (dict, optional): Detalhes adicionais para o log.
    """
    log_message = f"Status: {status.upper()} - {mensagem}"
    if detalhes:
        log_message += f" | Detalhes: {detalhes}"

    if status.lower() == "sucesso":
        logger.info(log_message)
    else:
        logger.error(log_message)
