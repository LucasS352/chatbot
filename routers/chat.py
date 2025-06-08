# File: routers/chat.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from models import ChatMessage
from database import get_db, Client, Conversation, Message as DB_Message, Intent, IntentVariation
import re
import random
from datetime import datetime, timedelta
import json # <<< [NOVO] Importado para processar os botões

# Importa a função do nosso serviço de NLP
from nlp_service import find_best_intent_nlp

CONFIDENCE_THRESHOLD = 60  # Limiar de confiança

router = APIRouter()


# --- Funções de suporte (sem alterações) ---

def get_client_by_token(db: Session, token: str) -> Client:
    """Busca um cliente pelo access_token. Levanta um erro 403 se não encontrar."""
    if not token:
        raise HTTPException(status_code=403, detail="Token de acesso não fornecido.")
    
    client = db.query(Client).filter(Client.access_token == token).first()
    
    if not client:
        raise HTTPException(status_code=403, detail="Token de acesso inválido ou não autorizado.")
        
    return client

def get_or_create_conversation(db: Session, client_id: int) -> Conversation:
    """Busca uma conversa ativa recente para o cliente ou cria uma nova."""
    recent_conversation = (
        db.query(Conversation)
        .filter(Conversation.client_id == client_id)
        .order_by(Conversation.start_time.desc())
        .first()
    )
    
    if recent_conversation:
        thirty_minutes_ago = datetime.now() - timedelta(minutes=30)
        last_message_in_conv = (
            db.query(DB_Message)
            .filter(
                DB_Message.conversation_id == recent_conversation.conversation_id,
                DB_Message.timestamp > thirty_minutes_ago
            )
            .first()
        )
        if last_message_in_conv:
            print(f"Continuando conversa existente ID: {recent_conversation.conversation_id}")
            return recent_conversation
    
    print(f"Criando nova conversa para o client_id: {client_id}")
    conversation = Conversation(client_id=client_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def find_exact_match(db: Session, message: str) -> Optional[Intent]:
    """Busca um match exato da mensagem em IntentVariation."""
    message_lower = message.lower().strip()
    variation = db.query(IntentVariation).filter(IntentVariation.variation == message_lower).first()
    if variation:
        return variation.intent
    return None


@router.post("/chat")
async def chat(api_message: ChatMessage, db: Session = Depends(get_db)):
    """
    Endpoint principal do chat. Valida o token e processa a pergunta.
    """
    try:
        # 1. Validação e obtenção de dados (sem alterações)
        client = get_client_by_token(db, api_message.token)
        conversation = get_or_create_conversation(db, client.client_id)
        
        user_msg = DB_Message(
            conversation_id=conversation.conversation_id,
            sender="user",
            content=api_message.question
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        print(f"\n--- Nova Mensagem ---")
        print(f"Cliente: '{client.client_name}' (ID: {client.client_id})")
        print(f"Pergunta: '{api_message.question}'")

        # 2. Lógica de busca de intenção (sem alterações)
        found_intent = find_exact_match(db, api_message.question)
        source_of_match = "Match Exato (Confiança: 100%)"

        if not found_intent:
            found_intent, score = find_best_intent_nlp(db, api_message.question)
            print(f"Score de confiança do PLN: {score}%")
            source_of_match = f"PLN (Confiança: {score}%)"
            if score < CONFIDENCE_THRESHOLD:
                print(f"-> Confiança abaixo do limiar. Match descartado.")
                found_intent = None
        
        # --- [INÍCIO DAS MODIFICAÇÕES] ---
        
        bot_response_text_final = ""
        image_names = []
        quick_replies_data = [] # <<< [NOVO] Inicializa lista de botões

        if found_intent:
            print(f"-> Intenção determinada: '{found_intent.title}' (Fonte: {source_of_match})")
            response_full_text = found_intent.response
            
            # <<< [NOVO] Lógica para extrair os botões de resposta rápida (quick replies)
            quick_reply_pattern = r'🚀 Quick Replies: (\[.*?\])'
            qr_match = re.search(quick_reply_pattern, response_full_text, re.DOTALL)
            if qr_match:
                try:
                    # Carrega a string JSON para uma lista python
                    quick_replies_data = json.loads(qr_match.group(1))
                    # Remove a string dos botões da resposta principal
                    response_full_text = re.sub(quick_reply_pattern, '', response_full_text).strip()
                except json.JSONDecodeError:
                    print("AVISO: Erro ao decodificar JSON dos quick replies.")
                    quick_replies_data = []
            
            # Lógica existente para extrair imagens
            image_pattern = r'🖼️ Imagens relacionadas: ([^\n]+)'
            match = re.search(image_pattern, response_full_text)
            if match:
                image_names = [img.strip() for img in match.group(1).split(',')]
                response_full_text = re.sub(image_pattern, '', response_full_text).strip()
                
            # Lógica existente para escolher resposta aleatória
            possible_responses = [res.strip() for res in response_full_text.split('\n\n') if res.strip()]
            if possible_responses:
                bot_response_text_final = random.choice(possible_responses)
        else:
            print("-> Nenhuma intenção encontrada. Usando resposta padrão.")
            bot_response_text_final = "Desculpe, não tenho certeza de como ajudar. Pode reformular?"
        
        print(f"Resposta do Bot: '{bot_response_text_final}'")
        bot_msg = DB_Message(conversation_id=conversation.conversation_id, sender="bot", content=bot_response_text_final)
        db.add(bot_msg)
        db.commit()
        db.refresh(bot_msg)

        # <<< [MODIFICADO] Adiciona a lista de botões ao payload da resposta
        response_payload = { 
            "status": "success", 
            "response": bot_response_text_final, 
            "conversation_id": conversation.conversation_id, 
            "message_id": bot_msg.message_id,
            "quick_replies": quick_replies_data # Adiciona a lista (vazia ou não)
        }
        
        if image_names:
            base_image_url = "http://localhost:8000/images/"
            image_urls = [f"{base_image_url}{name}" for name in image_names]
            response_payload["images"] = image_urls
            
        return response_payload

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno: {str(e)}")

# --- [FIM DAS MODIFICAÇÕES] ---