# dashboard.py
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case
from database import SessionLocal, Client, Conversation, Message
from pathlib import Path
import html

# --- Funções do Banco de Dados (Expandidas) ---
def get_clients(db: Session):
    return db.query(Client).order_by(Client.client_name).all()

def get_conversations(db: Session, client_id: int):
    return db.query(Conversation).filter(Conversation.client_id == client_id).order_by(Conversation.start_time.desc()).all()

def get_messages(db: Session, conversation_id: int):
    return db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp.asc()).all()

# --- NOVAS FUNÇÕES DE ANÁLISE ---
def get_unanswered_questions(db: Session):
    """Busca perguntas de usuários que o bot não soube responder."""
    # Encontra IDs de conversas onde o bot disse a frase padrão de "não sei"
    fallback_response = "Desculpe, não tenho certeza de como ajudar. Pode reformular?"
    
    # Subquery para pegar a mensagem do usuário que veio ANTES da resposta de fallback do bot
    # Esta query é um pouco mais complexa e usa funções do SQL para encontrar a mensagem anterior.
    
    # Primeiro, pegamos todas as mensagens de fallback do bot
    fallback_messages = db.query(Message).filter(Message.content == fallback_response, Message.sender == 'bot').all()
    
    unanswered_data = []
    for bot_msg in fallback_messages:
        # Para cada mensagem de fallback, encontramos a mensagem do usuário que veio logo antes na mesma conversa
        user_msg = db.query(Message)\
            .filter(Message.conversation_id == bot_msg.conversation_id, Message.timestamp < bot_msg.timestamp, Message.sender == 'user')\
            .order_by(Message.timestamp.desc())\
            .first()
        
        if user_msg:
            client_convo = db.query(Conversation).filter(Conversation.conversation_id == user_msg.conversation_id).first()
            client = db.query(Client).filter(Client.client_id == client_convo.client_id).first()
            unanswered_data.append({
                "Data": user_msg.timestamp.strftime('%d/%m/%Y'),
                "Cliente": client.client_name,
                "Pergunta Não Respondida": user_msg.content
            })
            
    return pd.DataFrame(unanswered_data)


def get_client_engagement(db: Session):
    """Calcula o engajamento e a assertividade por cliente."""
    fallback_response = "Desculpe, não tenho certeza de como ajudar. Pode reformular?"

    # Usamos func.count e func.sum do SQLAlchemy para agregar os dados
    results = db.query(
        Client.client_name,
        func.count(Conversation.conversation_id).label('total_conversations'),
        func.count(Message.message_id).label('total_messages'),
        func.sum(case((Message.sender == 'bot', 1), else_=0)).label('bot_responses'),
        func.sum(case((Message.content == fallback_response, 1), else_=0)).label('fallback_count')
    ).select_from(Client)\
    .outerjoin(Conversation, Client.client_id == Conversation.client_id)\
    .outerjoin(Message, Conversation.conversation_id == Message.conversation_id)\
    .group_by(Client.client_name)\
    .order_by(func.count(Conversation.conversation_id).desc())\
    .all()

    engagement_data = []
    for name, convos, msgs, bot_res, fallbacks in results:
        bot_res = bot_res or 0
        fallbacks = fallbacks or 0
        # Evita divisão por zero se o bot não respondeu
        assertividade = ((bot_res - fallbacks) / bot_res * 100) if bot_res > 0 else 0
        engagement_data.append({
            "Cliente": name,
            "Total de Conversas": convos,
            "Total de Mensagens": msgs,
            "Assertividade do Bot (%)": f"{assertividade:.1f}"
        })

    return pd.DataFrame(engagement_data)


# --- Função para Carregar CSS (sem alterações) ---
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Arquivo CSS '{file_name}' não encontrado.")

# --- Início da Interface do Dashboard ---

st.set_page_config(page_title="Dashboard de Análise", layout="wide")
local_css("assetsdashboard/style.css")

st.title("📊 Dashboard de Análise de Conversas do ERP Master")

db = SessionLocal()
try:
    # --- NOVO: Seção de Análise Geral ---
    st.markdown("---")
    st.header("Análise Geral de Performance")

    col1_geral, col2_geral = st.columns(2)

    with col1_geral:
        st.subheader("Engajamento por Cliente")
        df_engagement = get_client_engagement(db)
        st.dataframe(df_engagement, use_container_width=True)

    with col2_geral:
        st.subheader("Perguntas Não Respondidas pelo Bot")
        df_unanswered = get_unanswered_questions(db)
        # Usamos st.data_editor para uma visualização de tabela mais moderna
        st.data_editor(
            df_unanswered, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Pergunta Não Respondida": st.column_config.TextColumn(
                    "Pergunta Não Respondida",
                    help="As perguntas que os usuários fizeram e o bot não soube responder.",
                    width="large",
                )
            }
        )
    
    # --- Seção de Visualização de Conversa Individual ---
    st.markdown("---")
    st.header("Análise de Conversa Individual")

    all_clients = get_clients(db)
    if not all_clients:
        st.warning("Nenhum cliente encontrado no banco de dados.")
        st.stop()
    
    client_options = {client.client_name: client.client_id for client in all_clients}
    selected_client_name = st.selectbox(
        "**1. Selecione um Cliente**",
        options=list(client_options.keys())
    )

    selected_client_id = client_options[selected_client_name]
    client_conversations = get_conversations(db, selected_client_id)

    if not client_conversations:
        st.info(f"O cliente '{selected_client_name}' ainda não possui conversas registradas.")
        st.stop()

    conversation_options = {
        f"Conversa #{conv.conversation_id}  |  {conv.start_time.strftime('%d/%m/%Y às %H:%M:%S')}": conv.conversation_id 
        for conv in client_conversations
    }
    selected_conversation_label = st.selectbox(
        "**2. Selecione uma Conversa para Analisar**",
        options=list(conversation_options.keys())
    )
    
    selected_conversation_id = conversation_options[selected_conversation_label]
    messages = get_messages(db, selected_conversation_id)

    col1_convo, col2_convo = st.columns([1, 2])

    with col1_convo:
        st.subheader("Métricas da Conversa")
        total_messages = len(messages)
        user_messages_count = sum(1 for msg in messages if msg.sender == 'user')
        bot_messages_count = total_messages - user_messages_count
        
        if total_messages > 1:
            duration = messages[-1].timestamp - messages[0].timestamp
            st.metric(label="Duração da Conversa", value=str(duration).split('.')[0])
        else:
            st.metric(label="Duração da Conversa", value="N/A")

        st.metric(label="Total de Mensagens", value=total_messages)
        st.metric(label="Mensagens do Usuário", value=user_messages_count)
        st.metric(label="Respostas do Bot", value=bot_messages_count)

    with col2_convo:
        st.subheader(f"Diálogo da Conversa #{selected_conversation_id}")
        with st.container(height=600):
            for msg in messages:
                with st.chat_message(name=msg.sender, avatar="🤖" if msg.sender == 'bot' else "🧑‍💻"):
                    st.markdown(msg.content)
                    st.caption(f"_{msg.timestamp.strftime('%d/%m/%Y %H:%M:%S')}_")

finally:
    db.close()