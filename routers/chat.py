from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from models import ChatMessage
from database import get_db, Client, Conversation, Message as DB_Message, Intent, IntentVariation
import re
import random
import json

from nlp_service import find_best_intent_nlp, extract_order_code
from api_service import consultar_status_api

CONFIDENCE_THRESHOLD = 60
router = APIRouter()

# --- Funções de suporte (sem alterações) ---
def get_client_by_token(db: Session, token: str) -> Client:
    if not token:
        raise HTTPException(status_code=403, detail="Token de acesso não fornecido.")
    client = db.query(Client).filter(Client.access_token == token).first()
    if not client:
        raise HTTPException(status_code=403, detail="Token de acesso inválido ou não autorizado.")
    return client

def get_or_create_conversation(db: Session, client_id: int) -> Conversation:
    recent_conversation = db.query(Conversation).filter(Conversation.client_id == client_id).order_by(Conversation.start_time.desc()).first()
    if recent_conversation:
        thirty_minutes_ago = datetime.now() - timedelta(minutes=30)
        last_message_in_conv = db.query(DB_Message).filter(DB_Message.conversation_id == recent_conversation.conversation_id, DB_Message.timestamp > thirty_minutes_ago).first()
        if last_message_in_conv:
            return recent_conversation
    conversation = Conversation(client_id=client_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def find_exact_match(db: Session, message: str) -> Optional[Intent]:
    message_lower = message.lower().strip()
    variation = db.query(IntentVariation).filter(IntentVariation.variation == message_lower).first()
    if variation:
        return variation.intent
    return None

# --- Endpoint Principal do Chat ---
@router.post("/chat")
async def chat(api_message: ChatMessage, db: Session = Depends(get_db)):
    try:
        client = get_client_by_token(db, api_message.token)
        conversation = get_or_create_conversation(db, client.client_id)
        
        user_msg = DB_Message(conversation_id=conversation.conversation_id, sender="user", content=api_message.question)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        print(f"\n--- Nova Mensagem ---\nCliente: '{client.client_name}'\nPergunta: '{api_message.question}'")

        found_intent = find_exact_match(db, api_message.question)
        if not found_intent:
            found_intent, score = find_best_intent_nlp(db, api_message.question)
            if not found_intent or score < CONFIDENCE_THRESHOLD:
                found_intent = None
        
        bot_response_text_final = ""
        image_names = []
        quick_replies_data = []

        if found_intent:
            print(f"-> Intenção determinada: '{found_intent.title}'")

            # <<< LÓGICA FINAL E CORRIGIDA >>>
            # Primeiro, trata a intenção especial de status de pedido
            if found_intent.title == 'processo_status_pedido':
                codigo_extraido = extract_order_code(api_message.question)
                
                if codigo_extraido:
                    if client.master_api_token and client.master_api_url:
                        api_response = await consultar_status_api(
                            codigo_venda=codigo_extraido, token=client.master_api_token, base_url=client.master_api_url
                        )
                        if api_response and 'venda' in api_response and api_response['venda']:
                            status_pedido = api_response['venda'][0].get("DescricaoStatus", "Status não informado")
                            bot_response_text_final = f"O status do seu pedido {codigo_extraido} é: {status_pedido}."
                        elif api_response is not None:
                            bot_response_text_final = f"Consultei o sistema, mas não encontrei nenhum pedido com o código {codigo_extraido}."
                        else:
                            bot_response_text_final = "Tive um problema ao me comunicar com os sistemas do ERP."
                    else:
                        bot_response_text_final = "Sua empresa não tem a configuração de API completa (URL ou Token).Contate o suporte para realizar a integração"
                else:
                    # Decodifica o JSON para pegar a mensagem de "código não encontrado"
                    responses_dict = json.loads(found_intent.response.replace("'", '"'))
                    bot_response_text_final = responses_dict.get('code_not_found', "Por favor, informe o código do seu pedido.")
            
            # Se não for a intenção de status, executa a lógica padrão
            else:
                response_full_text = found_intent.response
                
                # Extrai quick replies
                quick_reply_pattern = r'🚀 Quick Replies: (\[.*?\])'
                qr_match = re.search(quick_reply_pattern, response_full_text, re.DOTALL)
                if qr_match:
                    try:
                        quick_replies_data = json.loads(qr_match.group(1))
                        response_full_text = re.sub(quick_reply_pattern, '', response_full_text).strip()
                    except json.JSONDecodeError:
                        print("AVISO: Erro ao decodificar JSON dos quick replies.")
                
                # Extrai imagens
                image_pattern = r'🖼️ Imagens relacionadas: (.*?)$'
                img_match = re.search(image_pattern, response_full_text, re.DOTALL)
                if img_match:
                    image_list_str = img_match.group(1)
                    image_names = [name.strip() for name in image_list_str.split(',') if name.strip()]
                    response_full_text = re.sub(image_pattern, '', response_full_text).strip()

                # Define o texto da resposta
                possible_responses = [res.strip() for res in response_full_text.split('\n\n') if res.strip()]
                if possible_responses:
                    bot_response_text_final = random.choice(possible_responses)
                elif not quick_replies_data and not image_names: # Apenas se não houver NADA, usa o texto completo
                    bot_response_text_final = response_full_text

        else:
            bot_response_text_final = "Desculpe, não tenho certeza de como ajudar."
        
        # Etapa final: Salvar e retornar
        print(f"Resposta do Bot: '{bot_response_text_final}'")
        bot_msg = DB_Message(conversation_id=conversation.conversation_id, sender="bot", content=bot_response_text_final)
        db.add(bot_msg)
        db.commit()
        db.refresh(bot_msg)

        response_payload = { "status": "success", "response": bot_response_text_final, "conversation_id": conversation.conversation_id, "message_id": bot_msg.message_id, "quick_replies": quick_replies_data }
        if image_names:
            response_payload["images"] = [f"http://localhost:8000/images/{name}" for name in image_names]
            
        return response_payload

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno: {str(e)}")