# File: main.py
# VERSÃO DE PRODUÇÃO FINAL - Carrega o modelo de IA na inicialização via lifespan.

import uvicorn
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# --- Nossas importações de módulos ---
from routers import chat
from database import engine 
from config import settings
from nlp_service import load_nlp_model # <-- Importamos a função de carregamento

# --- GERENCIADOR DE LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código a ser executado ANTES da aplicação começar a receber requisições
    print("--- Evento de Startup da Aplicação ---")
    load_nlp_model() # Carrega o pesado modelo de IA na memória
    print("--- Startup Concluído. Aplicação pronta para operar. ---")
    yield
    # Código a ser executado QUANDO a aplicação for desligada
    print("--- Evento de Shutdown da Aplicação ---")


# Cria a instância da aplicação FastAPI com o lifespan para garantir o carregamento na inicialização
app = FastAPI(title="Chatbot ERP Master", lifespan=lifespan)

# --- CONFIGURAÇÃO DO CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURAÇÃO DE ARQUIVOS ESTÁTICOS ---
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")
if os.path.exists(IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
    print(f"📁 Pasta de imagens estáticas configurada em: {IMAGES_DIR}")
else:
    print(f"⚠️ AVISO: Pasta de imagens '{IMAGES_DIR}' não foi encontrada!")

# --- INCLUSÃO DO ROTEADOR ---
app.include_router(chat.router)

# --- EXECUÇÃO DO SERVIDOR ---
if __name__ == "__main__":
    print("\n=== Iniciando Servidor do Chatbot ERP Master ===")
    print(f"Conectando ao banco de dados: {str(engine.url)}")
    print("\nIniciando servidor Uvicorn...")
    print(f"🌐 API rodando em: {settings.APP_BASE_URL}")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)