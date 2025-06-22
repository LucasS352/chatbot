# File: migrate_intents.py
import json
import sys
import os
from sqlalchemy.orm import Session
# Importações do projeto
from database import SessionLocal, Intent, IntentVariation, engine, Base
from nlp_service import preprocess_text, get_nlp_model # << Otimização de NLU

def load_json_intents(file_path: str) -> dict:
    """Carrega o arquivo JSON com as intenções. (Sua versão, mantida por ser excelente)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            print(f"  ↳ Carregando arquivo: {file_path}")
            return json.load(file)
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {file_path}. Pulando.")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao decodificar JSON em {file_path}: {e}. Pulando.")
        return {}

def clear_existing_intents(db: Session):
    """Remove todas as intenções e variações existentes. (Sua versão, mantida por ser excelente)"""
    print("🧹 Iniciando limpeza de intenções e variações existentes...")
    try:
        num_variations_deleted = db.query(IntentVariation).delete(synchronize_session=False)
        print(f"  - {num_variations_deleted} variações marcadas para deleção.")
        
        num_intents_deleted = db.query(Intent).delete(synchronize_session=False)
        print(f"  - {num_intents_deleted} intenções marcadas para deleção.")
        
        db.commit()
        print("  - COMMIT realizado. Deleções efetivadas.")
        print("✅ Limpeza concluída.")
    except Exception as e:
        print(f"  ❌ ERRO CRÍTICO DURANTE A LIMPEZA: {e}")
        db.rollback()
        raise Exception(f"Falha ao limpar tabelas: {e}")

def migrate_intents_to_database(json_data: dict, db: Session, clear_all_data_before_migrating: bool = False):
    """
    Migra as intenções do JSON para o banco de dados SEGUINDO A NOVA ARQUITETURA.
    (Versão refatorada para performance e clareza)
    """
    if clear_all_data_before_migrating:
        try:
            clear_existing_intents(db)
        except Exception as e:
            print(f"❌ A limpeza dos dados falhou. Abortando a migração. Erro: {e}")
            return

    print("📦 Iniciando migração com a nova arquitetura...")
    
    intents_added_count = 0
    intents_skipped_count = 0
    patterns_added_count = 0

    if not json_data:
        print("⚠️ Nenhuma intenção encontrada para migrar.")
        return

    for intent_key, intent_data in json_data.items():
        print(f"\n📋 Processando intenção: '{intent_key}'")
        
        if not clear_all_data_before_migrating:
            if db.query(Intent).filter(Intent.title == intent_key).first():
                print(f"  ⚠️ Intenção '{intent_key}' já existe. Pulando.")
                intents_skipped_count += 1
                continue
        
        try:
            # --- MUDANÇA ARQUITETURAL 1: Salvar em campos estruturados ---
            main_response = intent_data.get('responses', [""])[0] 
            quick_replies_list = intent_data.get('quick_replies', [])
            images_list = intent_data.get('images', [])

            db_intent = Intent(
                title=intent_key,
                response=main_response,
                quick_replies=json.dumps(quick_replies_list, ensure_ascii=False) if quick_replies_list else None,
                images=json.dumps(images_list, ensure_ascii=False) if images_list else None
            )
            db.add(db_intent)
            intents_added_count += 1
            
            # --- MUDANÇA ARQUITETURAL 2: Pré-processar variações ('patterns') ---
            patterns = intent_data.get('patterns', [])
            if patterns:
                for pattern in patterns:
                    if pattern.strip():
                        preprocessed_pattern = preprocess_text(pattern)
                        db_variation = IntentVariation(
                            intent=db_intent,
                            variation=pattern,
                            preprocessed_variation=preprocessed_pattern
                        )
                        db.add(db_variation)
                        patterns_added_count += 1
                print(f"  ✔️ {len(patterns)} variações adicionadas e pré-processadas.")
            
        except Exception as e:
            print(f"  ❌ Erro ao processar a intenção '{intent_key}': {e}")
            db.rollback()
            print("  - Rollback da intenção atual realizado.")
            # Se a intenção já foi contada, precisamos decrementar
            if intents_added_count > 0:
                intents_added_count -= 1
            break # Pára o loop para o usuário poder corrigir o JSON

    try:
        print("\n\nFinalizando... Commitando todas as alterações no banco de dados...")
        db.commit()
        print("✅ Transação finalizada com sucesso!")
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO COMMIT FINAL: {e}")
        db.rollback()

    print(f"\n🎉 Migração concluída!")
    print(f"📊 Resumo:")
    print(f"  - {intents_added_count} novas intenções ADICIONADAS.")
    print(f"  - {intents_skipped_count} intenções PULADAS.")
    print(f"  - {patterns_added_count} variações totais ADICIONADAS e PRÉ-PROCESSADAS.")


def main():
    """Função principal que orquestra todo o processo."""
    print("🚀 Script de Migração de Intenções JSON → MySQL")
    print("==================================================")
    
    print("📋 Criando tabelas do banco de dados se não existirem...")
    Base.metadata.create_all(bind=engine)

    # --- OTIMIZAÇÃO: Carregar o modelo de NLP uma única vez ---
    print("🧠 Carregando modelo de NLP (pode levar um momento na primeira vez)...")
    get_nlp_model()
    print("   Modelo de NLP pronto para uso.")
    # --------------------------------------------------------
    
    intents_directory = "intents_sources"

    if not os.path.exists(intents_directory) or not os.path.isdir(intents_directory):
        print(f"❌ Diretório de intenções '{intents_directory}' não encontrado!")
        sys.exit(1)

    aggregated_json_data = {}
    print(f"\n🔍 Lendo arquivos JSON do diretório: '{intents_directory}'...")

    for filename in os.listdir(intents_directory):
        if filename.lower().endswith(".json"):
            file_path = os.path.join(intents_directory, filename)
            current_file_data = load_json_intents(file_path)
            for intent_key, intent_value in current_file_data.items():
                if intent_key in aggregated_json_data:
                    print(f"  ⚠️ Aviso: Intenção '{intent_key}' do arquivo '{filename}' está sobrescrevendo uma já carregada.")
                aggregated_json_data[intent_key] = intent_value
    
    if not aggregated_json_data:
        print("❌ Nenhum dado de intenção válido foi carregado dos arquivos. Nada para migrar.")
        sys.exit(1)
    
    # --- PROMPT INTERATIVO: Mantido da sua versão original ---
    clear_all_data_flag = False
    while True:
        clear_prompt_response = input("\n🤔 Deseja LIMPAR TODAS as intenções existentes antes de importar? (s/N): ").lower().strip()
        if clear_prompt_response == 's':
            clear_all_data_flag = True
            break
        elif clear_prompt_response in ('n', ''):
            clear_all_data_flag = False
            break
        else:
            print("Resposta inválida. Por favor, 's' para sim ou 'n' para não.")

    db = SessionLocal()
    try:
        migrate_intents_to_database(aggregated_json_data, db, clear_all_data_flag)
    except Exception as e:
        print(f"❌ Ocorreu um erro geral durante o processo de migração: {e}")
    finally:
        db.close()
        print("\n🔌 Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    main()