# File: database.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Sua string de conexão com o banco de dados.
DATABASE_URL = "mysql+pymysql://root:@localhost:3306/pract"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- INÍCIO DAS MODIFICAÇÕES ---

# NOVO MODELO: Para a nova tabela 'clients'
class Client(Base):
    __tablename__ = "clients"

    client_id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(255), unique=True, nullable=False)
    access_token = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    # Um cliente pode ter muitas conversas
    conversations = relationship("Conversation", back_populates="client")

# MODELO ATUALIZADO: A tabela 'conversations' agora se relaciona com 'clients'
class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.client_id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, server_default=func.now())

    # A conversa pertence a um cliente
    client = relationship("Client", back_populates="conversations")
    # A conversa tem muitas mensagens
    messages = relationship("Message", back_populates="conversation")

# MODELO ANTIGO ATUALIZADO: A tabela 'users' não se relaciona mais diretamente com 'conversations'
# No futuro, ela poderia se relacionar com 'clients' (um cliente ter múltiplos usuários)
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Removido o relacionamento direto com 'conversations'
    # conversations = relationship("Conversation", back_populates="user")


# MODELOS SEM ALTERAÇÃO (Message, Intent, IntentVariation)
class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id", ondelete="CASCADE"))
    sender = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
    
class Intent(Base):
    __tablename__ = "intents"

    intent_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    response = Column(Text, nullable=False)

    variations = relationship("IntentVariation", back_populates="intent", cascade="all, delete-orphan")

class IntentVariation(Base):
    __tablename__ = "intent_variations"

    variation_id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(Integer, ForeignKey("intents.intent_id", ondelete="CASCADE"))
    variation = Column(Text, nullable=False)

    intent = relationship("Intent", back_populates="variations")

# --- FIM DAS MODIFICAÇÕES ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()