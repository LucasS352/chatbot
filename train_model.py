import spacy
from spacy.tokens import DocBin
from sklearn.model_selection import train_test_split
import os

from database import SessionLocal, Intent, IntentVariation
from sqlalchemy.orm import joinedload

def create_spacy_docs():
    """
    Busca os dados do banco e os converte para o formato DocBin do spaCy.
    """
    print("Buscando dados do banco de dados...")
    db = SessionLocal()
    nlp = spacy.blank("pt")
    
    all_data = []
    try:
        all_labels = [intent.title for intent in db.query(Intent).all()]
        all_variations = db.query(IntentVariation).options(joinedload(IntentVariation.intent)).all()
        
        for variation in all_variations:
            if variation.intent:
                doc = nlp.make_doc(variation.variation)
                cats = {label: 0.0 for label in all_labels}
                cats[variation.intent.title] = 1.0
                doc.cats = cats
                all_data.append(doc)
    finally:
        db.close()

    if not all_data:
        print("❌ Nenhum dado encontrado para processar.")
        return

    # Dividindo os Doc objects em treino e teste
    train_docs, test_docs = train_test_split(all_data, test_size=0.2, random_state=42)
    
    # Criando os arquivos DocBin
    train_db = DocBin(docs=train_docs)
    test_db = DocBin(docs=test_docs)

    # Criando o diretório de assets se não existir
    if not os.path.exists("./assets"):
        os.makedirs("./assets")

    train_db.to_disk("./assets/train.spacy")
    test_db.to_disk("./assets/dev.spacy")
    print(f"✅ Arquivos de dados criados: {len(train_docs)} para treino, {len(test_docs)} para teste.")

def train_from_config():
    """
    Executa o treinamento usando o arquivo de configuração e os dados binários.
    """
    # Importa a função de treino da CLI do spaCy
    from spacy.cli.train import train

    print("\n--- INICIANDO TREINAMENTO A PARTIR DO ARQUIVO DE CONFIGURAÇÃO ---")
    
    # Define os caminhos para o config e os arquivos de output
    config_path = "config.cfg"
    output_path = "nlp_model" # Onde o modelo final será salvo
    
    # Argumentos para a função de treino
    # "paths.train": "./assets/train.spacy"  --> Isso diz ao spaCy onde encontrar os dados de treino,
    # sobrescrevendo qualquer valor que esteja no config.cfg
    overrides = {
        "paths.train": "./assets/train.spacy",
        "paths.dev": "./assets/dev.spacy"
    }

    # Chama a função de treino do spaCy
    train(config_path, output_path, overrides=overrides)
    print(f"\n✅ Treinamento concluído! Modelo salvo em '{output_path}'")


if __name__ == "__main__":
    create_spacy_docs()
    train_from_config()