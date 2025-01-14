from fastapi import FastAPI
from route.auth_notion import router as auth_routes
import uvicorn

# Instância principal do aplicativo FastAPI
app = FastAPI(
    title="Notion Integration API",
    description="API para integração com Notion e manipulação de intimações",
    version="1.0.0"
)

# Incluindo as rotas de autenticação
app.include_router(auth_routes, tags=["Auth"])

# Endpoint raiz para verificar o status da API
@app.get("/", tags=["Health Check"])
async def root():
    """
    Endpoint para verificar se a API está funcionando corretamente.
    """
    return {"message": "Notion Integration API is running!"}

# Ponto de entrada para iniciar o servidor automaticamente
if __name__ == "__main__":
    uvicorn.run(
        "main:app",  # Refere-se ao objeto `app` neste arquivo
        host="0.0.0.0",  # Escuta em todas as interfaces de rede
        port=8000,  # Porta onde o servidor será iniciado
        reload=True  # Habilita o recarregamento automático ao alterar o código
    )