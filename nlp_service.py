# File: nlp_service.py
# VERSÃO CORRIGIDA - Preparado para carregamento na inicialização da API (lifespan).

import spacy
from typing import Optional, Tuple
import re

MODEL_PATH = "nlp_model" 
NLP_MODEL = None # O modelo começará como None e será preenchido na inicialização.

def load_nlp_model():
    """
    Função que carrega o modelo de NLP na variável global.
    Esta função deve ser chamada UMA VEZ durante a inicialização da API.
    """
    global NLP_MODEL
    if NLP_MODEL is None:
        try:
            print(f"[NLP Service] Iniciando o carregamento do modelo customizado de '{MODEL_PATH}'...")
            NLP_MODEL = spacy.load(MODEL_PATH)
            print("[NLP Service] ✅ Modelo customizado carregado com sucesso na memória.")
        except OSError:
            print(f"ERRO CRÍTICO: Modelo não encontrado em '{MODEL_PATH}'.")
            print("Execute 'python train_model.py' para criar o modelo antes de iniciar a API.")
            raise
            
def find_best_intent_nlp(question: str) -> Tuple[Optional[str], float]:
    """
    Usa o modelo de classificação de texto (textcat) JÁ CARREGADO para prever a intenção.
    """
    if not NLP_MODEL:
        # Este erro só acontecerá se a aplicação tentar rodar sem o modelo carregado.
        raise RuntimeError("O modelo de NLP não foi carregado. Verifique o evento de inicialização da API.")
    
    if not question:
        return None, 0.0

    doc = NLP_MODEL(question.lower())
    
    if not doc.cats:
        return None, 0.0

    best_intent_title = max(doc.cats, key=doc.cats.get)
    confidence_score = doc.cats[best_intent_title]
    
    return best_intent_title, confidence_score * 100

def extract_order_code(text: str) -> Optional[str]:
    """Extrai um código numérico do texto."""
    match = re.search(r'\b\d{1,9}\b', text)
    if match:
        return match.group(0)
    return None

def extract_product_code(text: str) -> Optional[str]:
    """Extrai um código de produto (assumindo ser uma sequência de dígitos) do texto."""
    match = re.search(r'\b\d{1,9}\b', text)
    if match:
        return match.group(0)
    return None

def extract_document_number(text: str) -> Optional[str]:
    """Extrai um número de CPF ou CNPJ de uma string, com ou sem pontuação."""
    match = re.search(r'\b(\d{11}|\d{14})\b', text.replace('.', '').replace('/', '').replace('-', ''))
    if match:
        return match.group(0)
    return None

def preprocess_text(text: str) -> str:
    """Função de pré-processamento usada pelo script de migração."""
    nlp = spacy.load("pt_core_news_sm")
    doc = nlp(text.lower())
    tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct and token.text.strip()]
    return " ".join(tokens)