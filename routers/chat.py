# File: routers/chat.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from models import ChatMessage
from database import get_db, Client, Conversation, Message as DB_Message, Intent, IntentVariation # Client importado, User removido
import re
import random
from datetime import datetime, timedelta

# Importa a função do nosso serviço de NLP
from nlp_service import find_best_intent_nlp

CONFIDENCE_THRESHOLD = 60  # Limiar de confiança

router = APIRouter()


# --- INÍCIO DAS NOVAS FUNÇÕES E MODIFICAÇÕES ---

def get_client_by_token(db: Session, token: str) -> Client:
    """Busca um cliente pelo access_token. Levanta um erro 403 se não encontrar."""
    if not token:
        raise HTTPException(status_code=403, detail="Token de acesso não fornecido.")
        
    client = db.query(Client).filter(Client.access_token == token).first()
    
    if not client:
        # O erro 403 (Forbidden) é apropriado aqui, pois o acesso é negado
        raise HTTPException(status_code=403, detail="Token de acesso inválido ou não autorizado.")
        
    return client

# A função get_or_create_conversation agora usa client_id
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

# Função find_exact_match permanece a mesma
def find_exact_match(db: Session, message: str) -> Optional[Intent]:
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
        # 1. Valida o token e obtém o cliente
        client = get_client_by_token(db, api_message.token)
        
        # 2. Obtém ou cria a conversa para o cliente validado
        conversation = get_or_create_conversation(db, client.client_id)
        
        # 3. Salva a mensagem do usuário
        user_msg = DB_Message(
            conversation_id=conversation.conversation_id,
            sender="user", # Podemos manter "user" ou usar o nome do cliente
            content=api_message.question
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        print(f"\n--- Nova Mensagem ---")
        print(f"Cliente: '{client.client_name}' (ID: {client.client_id})")
        print(f"Pergunta: '{api_message.question}'")

        # 4. Lógica de busca de intenção (híbrida)
        found_intent = find_exact_match(db, api_message.question)
        source_of_match = "Match Exato (Confiança: 100%)"

        if not found_intent:
            found_intent, score = find_best_intent_nlp(db, api_message.question)
            print(f"Score de confiança do PLN: {score}%")
            source_of_match = f"PLN (Confiança: {score}%)"
            if score < CONFIDENCE_THRESHOLD:
                print(f"-> Confiança abaixo do limiar. Match descartado.")
                found_intent = None
        
        # O resto da lógica para processar a resposta e retornar permanece o mesmo...
        # ...

        bot_response_text_final = ""
        image_names = []
        if found_intent:
            print(f"-> Intenção determinada: '{found_intent.title}' (Fonte: {source_of_match})")
            response_full_text = found_intent.response
            # ... (Lógica de extrair imagens e escolher resposta aleatória)
            image_pattern = r'🖼️ Imagens relacionadas: ([^\n]+)'
            match = re.search(image_pattern, response_full_text)
            if match:
                image_names = [img.strip() for img in match.group(1).split(',')]
                response_full_text = re.sub(image_pattern, '', response_full_text).strip()
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
        response_payload = { "status": "success", "response": bot_response_text_final, "conversation_id": conversation.conversation_id, "message_id": bot_msg.message_id }
        if image_names:
            base_image_url = "http://localhost:8000/images/"
            image_urls = [f"{base_image_url}{name}" for name in image_names]
            response_payload["images"] = image_urls
        return response_payload

    except HTTPException:
        # Re-levanta exceções HTTP (como o 403 de token inválido) para que o FastAPI as retorne corretamente
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno: {str(e)}")


# Os endpoints GET não são mais úteis com 'user_id', precisariam ser adaptados para 'client_id' ou outra forma
# Por enquanto, vou deixá-los comentados para não causar erros.
# @router.get("/conversations/{user_id}") ...
# @router.get("/conversations/{conversation_id}/messages") ...