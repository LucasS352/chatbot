# File: main.py
import uvicorn
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Importa os módulos do seu projeto
from routers import chat
import database

# Cria a instância da aplicação FastAPI
app = FastAPI(title="Chatbot ERP Master")

# --- CONFIGURAÇÃO DO CORS ---
# Esta seção deve vir ANTES de incluir os roteadores e montar os arquivos estáticos.

# Lista de origens que têm permissão para fazer requisições à sua API
origins = [
    "http://localhost",          # Origem do seu XAMPP (porta 80 padrão)
    "http://localhost:8080",     # Origem se você usar o servidor simples do Python
    "http://127.0.0.1",          # Endereço IP local alternativo
    "http://127.0.0.1:8080",     # Alternativa para o servidor do Python
    "null"                       # Permite testes abrindo o arquivo HTML localmente (file://)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Usa a lista específica de origens permitidas
    allow_credentials=True,
    allow_methods=["*"],         # Permite todos os métodos (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],         # Permite todos os cabeçalhos
)
# --- FIM DA CONFIGURAÇÃO CORS ---

# --- CONFIGURAÇÃO DE ARQUIVOS ESTÁTICOS ---
# Define o caminho absoluto para a pasta 'images'
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")

if os.path.exists(IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
    print(f"📁 Pasta de imagens estáticas configurada em: {IMAGES_DIR}")
else:
    print(f"⚠️ AVISO: Pasta de imagens '{IMAGES_DIR}' não foi encontrada!")

# --- INCLUSÃO DO ROTEADOR ---
# Inclui as rotas definidas no arquivo routers/chat.py
app.include_router(chat.router)


# --- EXECUÇÃO DO SERVIDOR (PARA DESENVOLVIMENTO) ---
if __name__ == "__main__":
    print("\n=== Iniciando Servidor do Chatbot ERP Master ===")
    
    # Descomente a linha abaixo apenas se precisar recriar as tabelas do zero na inicialização
    # print("Verificando/Criando tabelas do banco de dados...")
    # database.Base.metadata.create_all(bind=database.engine)
    
    print(f"Conectando ao banco de dados: {str(database.engine.url)}")
    print("\nIniciando servidor Uvicorn...")
    print("🌐 API rodando em: http://127.0.0.1:8000")
    print("✓ Frontend deve ser acessado via servidor web (ex: http://localhost/chatbot/)")
    print("-" * 50)
    
    # O host '0.0.0.0' torna a API acessível na sua rede local, não apenas em localhost
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)