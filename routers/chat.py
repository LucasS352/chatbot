# File: routers/chat.py
# VERSÃO ATUALIZADA - Inclui o handler para a funcionalidade de Consulta de Cliente.

import logging
import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime, timedelta

# Nossas importações de módulos
from models import ChatMessage
from database import get_db, Client, Conversation, Message as DB_Message, Intent
from nlp_service import find_best_intent_nlp, extract_order_code, extract_product_code, extract_document_number
from api_service import MasterAPIClient
from config import settings # Importa a configuração central

# --- CONFIGURAÇÃO ---
CONFIDENCE_THRESHOLD = 55
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
log = logging.getLogger(__name__)

router = APIRouter()

# --- FUNÇÕES DE SUPORTE ---
def get_client_by_token(db: Session, token: str) -> Client:
    """Autentica o cliente pelo token de acesso."""
    if not token:
        raise HTTPException(status_code=403, detail="Token de acesso não fornecido.")
    client = db.query(Client).filter(Client.access_token == token).first()
    if not client:
        log.warning(f"Tentativa de acesso com token inválido: {token}")
        raise HTTPException(status_code=403, detail="Token de acesso inválido ou não autorizado.")
    return client

def get_or_create_conversation(db: Session, client_id: int) -> Conversation:
    """Obtém a conversa atual ou cria uma nova se a última interação foi há mais de 30 minutos."""
    recent_conversation = db.query(Conversation).filter(Conversation.client_id == client_id).order_by(Conversation.start_time.desc()).first()
    if recent_conversation:
        thirty_minutes_ago = datetime.now() - timedelta(minutes=30)
        last_message_in_conv = db.query(DB_Message).filter(DB_Message.conversation_id == recent_conversation.conversation_id, DB_Message.timestamp > thirty_minutes_ago).order_by(DB_Message.timestamp.desc()).first()
        if last_message_in_conv:
            return recent_conversation
            
    conversation = Conversation(client_id=client_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

# --- ARQUITETURA DE HANDLERS DE INTENÇÃO ---

async def default_handler(db: Session, client: Client, intent: Intent, message: str) -> Dict[str, Any]:
    """Manipulador padrão: extrai dados estruturados do objeto Intent do banco de dados."""
    log.info(f"Usando default_handler para a intenção: '{intent.title}'")
    return {
        "text": intent.response,
        "quick_replies": json.loads(intent.quick_replies) if intent.quick_replies else [],
        "images": json.loads(intent.images) if intent.images else []
    }

async def handle_status_pedido(db: Session, client: Client, intent: Intent, message: str) -> Dict[str, Any]:
    """Manipulador para a intenção 'processo_status_pedido' que consulta a API."""
    log.info(f"Usando handle_status_pedido para a intenção: '{intent.title}'")
    codigo_venda = extract_order_code(message)
    response_data = {"text": intent.response, "quick_replies": [], "images": []}

    if not codigo_venda:
        response_data["text"] = "Não consegui identificar o código do pedido. Poderia informá-lo novamente?"
        return response_data

    if not all([client.master_api_token, client.master_api_url, client.master_api_banco]):
        response_data["text"] = "Sua empresa não possui a integração com o ERP Master configurada corretamente. Por favor, contate o suporte."
        log.error(f"Cliente {client.client_id} tentou usar API sem credenciais completas.")
        return response_data

    api_client = MasterAPIClient(
        token=client.master_api_token,
        base_url=client.master_api_url,
        banco=client.master_api_banco,
        client_id_log=client.client_id
    )
    
    try:
        api_response = await api_client.get_venda(codigo_venda)
        if api_response and "venda" in api_response and isinstance(api_response["venda"], list) and len(api_response["venda"]) > 0:
            sale_data = api_response["venda"][0]
            status = sale_data.get("DescricaoStatus", "não informado")
            data_venda_str = sale_data.get("DataVenda")
            valor_total = float(sale_data.get("ValorTotal", 0.0))
            nome_cliente = sale_data.get("EntregaNome", "cliente não informado")
            data_formatada = data_venda_str
            if data_venda_str:
                try:
                    data_obj = datetime.fromisoformat(data_venda_str)
                    data_formatada = data_obj.strftime('%d/%m/%Y')
                except (ValueError, TypeError):
                    log.warning(f"Não foi possível formatar a data: {data_venda_str}")
            response_data["text"] = (
                f"Encontrei os detalhes do pedido {codigo_venda}:\n"
                f"• Cliente: {nome_cliente}\n"
                f"• Data da Venda: {data_formatada}\n"
                f"• Valor Total:R$ {valor_total:.2f}\n"
                f"• Status Atual: {status}"
            )
        else:
            response_data["text"] = f"Não encontrei nenhum pedido com o código {codigo_venda}. Por favor, verifique o número e tente novamente."
    finally:
        await api_client.close()
        
    return response_data

async def handle_consulta_produto(db: Session, client: Client, intent: Intent, message: str) -> Dict[str, Any]:
    """Manipulador para a intenção 'consulta_produto_por_codigo' que consulta a API."""
    log.info(f"Usando handle_consulta_produto para a intenção: '{intent.title}'")
    codigo_produto = extract_product_code(message)
    response_data = {"text": intent.response, "quick_replies": [], "images": []}

    if not codigo_produto:
        response_data["text"] = "Não consegui identificar o código do produto. Poderia informá-lo novamente?"
        return response_data

    if not all([client.master_api_token, client.master_api_url, client.master_api_banco]):
        response_data["text"] = "Sua empresa não possui a integração com o ERP Master configurada corretamente."
        log.error(f"Cliente {client.client_id} tentou usar API sem credenciais completas.")
        return response_data

    api_client = MasterAPIClient(
        token=client.master_api_token,
        base_url=client.master_api_url,
        banco=client.master_api_banco,
        client_id_log=client.client_id
    )
    
    try:
        api_response = await api_client.get_produto(codigo_produto)
        product_data = None
        if isinstance(api_response, dict) and "produto" in api_response and isinstance(api_response["produto"], dict):
            product_data = api_response["produto"]
        if product_data and "Codigo" in product_data:
            nome = product_data.get("Nome", "Nome não disponível")
            preco = product_data.get("PrecoVenda", 0.0)
            estoque = product_data.get("EstoqueAtual", 0.0)
            response_data["text"] = (
                f"Aqui estão os detalhes do produto **{codigo_produto}**:\n"
                f"• **Nome:** {nome}\n"
                f"• **Preço de Venda:** R$ {float(preco):.2f}\n"
                f"• **Estoque Atual:** {float(estoque):.0f} unidades"
            )
        else:
            response_data["text"] = f"Não encontrei nenhum produto com o código {codigo_produto}. Por favor, verifique o número."
    finally:
        await api_client.close()
        
    return response_data

# --- NOVO HANDLER PARA CONSULTA DE CLIENTE ---
async def handle_consulta_cliente(db: Session, client: Client, intent: Intent, message: str) -> Dict[str, Any]:
    """Manipulador para a intenção 'consulta_cliente_por_documento' que consulta a API."""
    log.info(f"Usando handle_consulta_cliente para a intenção: '{intent.title}'")
    documento = extract_document_number(message)
    response_data = {"text": intent.response, "quick_replies": [], "images": []}

    if not documento:
        response_data["text"] = "Não consegui identificar um número de CPF ou CNPJ na sua pergunta. Poderia informar novamente?"
        return response_data
    
    api_client = MasterAPIClient(
        token=client.master_api_token,
        base_url=client.master_api_url,
        banco=client.master_api_banco,
        client_id_log=client.client_id
    )
    
    try:
        api_response = await api_client.get_cliente_by_documento(documento)
        
        if api_response and "clientes" in api_response and isinstance(api_response["clientes"], list) and api_response["clientes"]:
            client_data = api_response["clientes"][0]
            nome = client_data.get("Nome", "N/A")
            email = client_data.get("Email", "N/A")
            municipio = client_data.get("MunicipioNome", "N/A")
            response_data["text"] = (
                f"Encontrei o cadastro para o documento **{documento}**:\n"
                f"• **Nome:** {nome}\n"
                f"• **Município:** {municipio}\n"
                f"• **E-mail:** {email}"
            )
        else:
            response_data["text"] = f"Não encontrei nenhum cliente com o documento {documento}."
    finally:
        await api_client.close()
        
    return response_data

# --- ATUALIZAÇÃO DO MAPA DE INTENÇÕES PARA HANDLERS ---
INTENT_HANDLERS = {
    "processo_status_pedido": handle_status_pedido,
    "consulta_produto_por_codigo": handle_consulta_produto,
    "consulta_cliente_por_documento": handle_consulta_cliente,
}

# --- ENDPOINT PRINCIPAL DO CHAT (SEM ALTERAÇÕES) ---
@router.post("/chat", response_model=Dict[str, Any])
async def chat(api_message: ChatMessage, db: Session = Depends(get_db)):
    try:
        client = get_client_by_token(db, api_message.token)
        conversation = get_or_create_conversation(db, client.client_id)
        
        db.add(DB_Message(conversation_id=conversation.conversation_id, sender="user", content=api_message.question))
        db.commit()
        log.info(f"Cliente: '{client.client_name}', Pergunta: '{api_message.question}'")

        intent_title, score = find_best_intent_nlp(api_message.question)
        
        found_intent = None
        if intent_title and score >= CONFIDENCE_THRESHOLD:
            found_intent = db.query(Intent).filter(Intent.title == intent_title).first()
        
        if found_intent:
            log.info(f"Intenção prevista: '{found_intent.title}' com confiança de {score:.2f}%")
            handler = INTENT_HANDLERS.get(found_intent.title, default_handler)
            response_data = await handler(db, client, found_intent, api_message.question)
        else:
            log.warning(f"Nenhuma intenção encontrada ou confiança baixa ({score:.2f}). Mensagem: '{api_message.question}'")
            response_data = {
                "text": "Desculpe, não entendi bem o que você precisa. Poderia reformular a pergunta?", 
                "quick_replies": [], 
                "images": []
            }

        db.add(DB_Message(conversation_id=conversation.conversation_id, sender="bot", content=response_data["text"]))
        db.commit()
        
        return {
            "status": "success",
            "response": response_data["text"],
            "conversation_id": conversation.conversation_id,
            "quick_replies": response_data["quick_replies"],
            "images": [f"{settings.APP_BASE_URL}/images/{name}" for name in response_data["images"]]
        }

    except Exception as e:
        log.critical(f"Erro crítico não tratado no endpoint de chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocorreu um erro interno inesperado.")