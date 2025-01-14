# Usar a imagem base do Python
FROM python:3.9-slim

# Define o diretório de trabalho no container
WORKDIR /app

# Copia os arquivos de dependências
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos os arquivos do projeto para o container
COPY . .

# Expor a porta 8080
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
