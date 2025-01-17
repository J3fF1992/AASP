import logging
import os

# Configuração do nível de log global
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Formatação personalizada
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Configuração do handler para console
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
console_handler.setFormatter(formatter)

# Configuração do handler para arquivo (opcional)
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(log_level)
file_handler.setFormatter(formatter)

# Configuração do logger principal
logger = logging.getLogger(__name__)  # Cria um logger com o nome do módulo
logger.setLevel(log_level)

# Evitar adicionar handlers duplicados
if not logger.hasHandlers():
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# Configuração de logs para reduzir ruídos do SQLAlchemy
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

logging.getLogger("httpx").setLevel(logging.WARNING)


logger.info("Configuração de logs inicializada.")
