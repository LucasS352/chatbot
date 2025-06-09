# File: nlp_service.py
import spacy
from fuzzywuzzy import fuzz
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from database import Intent, IntentVariation
import re

# A variável global para o modelo começa como None.
NLP_MODEL = None

def get_nlp_model():
    """
    Carrega o modelo spaCy na primeira vez que é chamado e o armazena na
    variável global NLP_MODEL. Nas chamadas seguintes, apenas retorna o modelo já carregado.
    """
    global NLP_MODEL
    if NLP_MODEL is None:
        print("[NLP Service] Carregando modelo spaCy 'pt_core_news_sm' pela primeira vez...")
        try:
            NLP_MODEL = spacy.load("pt_core_news_sm")
            print("[NLP Service] Modelo spaCy carregado com sucesso.")
        except OSError:
            print("ERRO: Modelo 'pt_core_news_sm' não encontrado. Tentando baixar...")
            from spacy.cli import download
            download("pt_core_news_sm")
            NLP_MODEL = spacy.load("pt_core_news_sm")
            print("[NLP Service] Modelo baixado e carregado com sucesso.")
    return NLP_MODEL

def preprocess_text(text: str) -> str:
    """Limpa e normaliza o texto: remove stopwords, pontuação e aplica lematização."""
    nlp = get_nlp_model() # Pega o modelo (carrega apenas se for a 1ª vez)
    doc = nlp(text.lower())
    tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct and token.text.strip()]
    return " ".join(tokens)

def find_best_intent_nlp(db: Session, question: str) -> Tuple[Optional[Intent], int]:
    """Usa PLN para encontrar a melhor intenção para a pergunta no banco de dados."""
    if not question:
        return None, 0

    preprocessed_question = preprocess_text(question)
    if not preprocessed_question:
        return None, 0

    variations = db.query(IntentVariation).all()
    
    best_score = 0
    best_intent = None

    for variation in variations:
        preprocessed_variation = preprocess_text(variation.variation)
        if not preprocessed_variation:
            continue
        score = fuzz.token_sort_ratio(preprocessed_question, preprocessed_variation)
        if score > best_score:
            best_score = score
            best_intent = variation.intent

    return best_intent, best_score

def extract_order_code(text: str) -> Optional[str]:
    """
    Extrai um código de venda (uma sequência de 5 ou 6 dígitos) do texto.
    A expressão \b garante que estamos pegando um número "inteiro" e não parte de um número maior.
    """
    match = re.search(r'\b\d{1,9}\b', text)
    if match:
        return match.group(0)
    return None