# File: models.py
from pydantic import BaseModel

# O corpo da requisição do chat agora espera um 'token' em vez de um 'username'
class ChatMessage(BaseModel):
    token: str
    question: str