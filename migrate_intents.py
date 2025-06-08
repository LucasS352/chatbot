# File: migrate_intents.py - VERSÃO CORRIGIDA
import json
import sys
import os
from sqlalchemy.orm import Session
from database import SessionLocal, Intent, IntentVariation, engine, Base # Seus módulos database.py

def load_json_intents(file_path: str) -> dict:
    """Carrega o arquivo JSON com as intenções"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            print(f"  ↳ Carregando arquivo: {file_path}")
            return json.load(file)
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {file_path}. Pulando este arquivo.")
        return {} 
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao decodificar JSON em {file_path}: {e}. Pulando este arquivo.")
        return {}

def clear_existing_intents(db: Session):
    """Remove todas as intenções e variações existentes. Levanta exceção em caso de falha."""
    print("🧹 Iniciando limpeza de intenções e variações existentes...")
    try:
        # Deletar variações primeiro por causa da dependência da chave estrangeira
        num_variations_deleted = db.query(IntentVariation).delete(synchronize_session=False)
        print(f"  - {num_variations_deleted} variações de intenção marcadas para deleção.")
        
        num_intents_deleted = db.query(Intent).delete(synchronize_session=False)
        print(f"  - {num_intents_deleted} intenções marcadas para deleção.")
        
        db.commit()
        print("  - COMMIT realizado. Deleções efetivadas no banco de dados.")
        print("✅ Limpeza de intenções e variações existentes concluída.")
    except Exception as e:
        print(f"  ❌ ERRO CRÍTICO DURANTE A LIMPEZA DAS TABELAS: {e}")
        print("  - Tentando reverter transação...")
        db.rollback()
        print("  - Rollback realizado.")
        raise Exception(f"Falha ao limpar tabelas existentes: {e}")


def migrate_intents_to_database(json_data: dict, db: Session, clear_all_data_before_migrating: bool = False):
    """
    Migra as intenções do JSON para o banco de dados.
    """
    
    if clear_all_data_before_migrating:
        try:
            clear_existing_intents(db)
        except Exception as e:
            print(f"❌ A limpeza dos dados falhou. Abortando a migração. Erro detalhado acima.")
            return

    print("📦 Iniciando migração/verificação das intenções...")
    
    total_intents_in_json = len(json_data)
    intents_added_count = 0
    intents_skipped_count = 0
    patterns_added_count = 0
    
    if not json_data:
        print("⚠️ Nenhuma intenção encontrada nos arquivos JSON para migrar.")
        return

    for intent_key, intent_data in json_data.items():
        print(f"\n📋 Processando intenção do JSON: '{intent_key}'")
        
        if not clear_all_data_before_migrating:
            existing_intent = db.query(Intent).filter(Intent.title == intent_key).first()
            if existing_intent:
                print(f"  ⚠️ Intenção '{intent_key}' já existe no banco de dados com ID: {existing_intent.intent_id}. Pulando inserção.")
                intents_skipped_count += 1
                continue
        
        # --- Preparar a string de resposta (concatenando múltiplas respostas, info de imagens e quick replies) ---
        responses = intent_data.get('responses', [])
        response_text = "\n\n".join(responses) if isinstance(responses, list) else str(responses)
        
        images = intent_data.get('images', [])
        if images:
            image_text = "\n\n🖼️ Imagens relacionadas: " + ", ".join(images)
            response_text += image_text

        # [INÍCIO DA CORREÇÃO] - Adicionar a lógica dos quick replies
        quick_replies = intent_data.get('quick_replies', [])
        if quick_replies:
            # Converte a lista de botões para uma string JSON compacta e com acentos corretos
            qr_json_string = json.dumps(quick_replies, separators=(',', ':'), ensure_ascii=False)
            # Anexa ao texto final no formato esperado pelo backend
            response_text += f"\n\n🚀 Quick Replies: {qr_json_string}"
        # [FIM DA CORREÇÃO]
            
        try:
            print(f"  ➕ Tentando adicionar nova intenção: '{intent_key}'")
            db_intent = Intent(
                title=intent_key,
                response=response_text # Agora 'response_text' contém os botões!
            )
            db.add(db_intent)
            db.commit()
            db.refresh(db_intent)
            
            print(f"  	✅ Intenção '{intent_key}' ADICIONADA com ID: {db_intent.intent_id}")
            intents_added_count += 1
            
            current_intent_patterns_added = 0
            patterns = intent_data.get('patterns', [])
            if patterns:
                for pattern in patterns:
                    if pattern.strip():
                        db_variation = IntentVariation(
                            intent_id=db_intent.intent_id,
                            variation=pattern.lower().strip()
                        )
                        db.add(db_variation)
                        current_intent_patterns_added += 1
                
                if current_intent_patterns_added > 0:
                    db.commit()
                print(f"  	📝 {current_intent_patterns_added} padrões/variações adicionados para '{intent_key}'.")
                patterns_added_count += current_intent_patterns_added
            
        except Exception as e:
            print(f"  ❌ Erro ao processar/adicionar a intenção '{intent_key}': {e}")
            print("  - Tentando reverter a adição desta intenção específica...")
            db.rollback()
            print("  - Rollback da intenção atual realizado.")
    
    print(f"\n🎉 Migração concluída!")
    print(f"📊 Resumo:")
    print(f"   - {total_intents_in_json} intenções encontradas nos arquivos JSON.")
    print(f"   - {intents_added_count} novas intenções foram ADICIONADAS ao banco.")
    print(f"   - {intents_skipped_count} intenções foram PULADAS (pois já existiam e não estava no modo de limpeza total).")
    print(f"   - {patterns_added_count} padrões/variações totais foram ADICIONADOS para as novas intenções.")


def main():
    """Função principal"""
    print("🚀 Script de Migração de Intenções JSON → MySQL")
    print("==================================================")
    
    print("📋 Criando tabelas do banco de dados se não existirem...")
    Base.metadata.create_all(bind=engine)
    
    intents_directory = "intents_sources"

    if not os.path.exists(intents_directory) or not os.path.isdir(intents_directory):
        print(f"❌ Diretório de intenções '{intents_directory}' não encontrado!")
        sys.exit(1)

    aggregated_json_data = {}
    print(f"\n🔍 Lendo arquivos JSON do diretório: '{intents_directory}'...")

    found_json_files = False
    for filename in os.listdir(intents_directory):
        if filename.lower().endswith(".json"):
            found_json_files = True
            file_path = os.path.join(intents_directory, filename)
            current_file_data = load_json_intents(file_path)
            
            for intent_key, intent_value in current_file_data.items():
                if intent_key in aggregated_json_data:
                    print(f"  	⚠️  Aviso: Intenção '{intent_key}' do arquivo '{filename}' está sobrescrevendo uma intenção com o mesmo nome já carregada de outro arquivo.")
                aggregated_json_data[intent_key] = intent_value
    
    if not found_json_files:
        print(f"❌ Nenhum arquivo .json foi encontrado no diretório '{intents_directory}'. Nada para migrar.")
        sys.exit(1) 
    
    if not aggregated_json_data:
        print("❌ Nenhum dado de intenção válido foi carregado dos arquivos JSON. Nada para migrar.")
        sys.exit(1)
    
    clear_all_data_flag = False
    while True:
        clear_prompt_response = input("\n🤔 Deseja limpar TODAS as intenções e variações existentes no banco de dados antes de importar as novas? (s/N): ").lower().strip()
        if clear_prompt_response == 's':
            clear_all_data_flag = True
            break
        elif clear_prompt_response == 'n' or clear_prompt_response == '':
            clear_all_data_flag = False
            break
        else:
            print("Resposta inválida. Por favor, digite 's' para sim ou 'n' para não (ou pressione Enter para 'n').")

    print(f"\n📚 Total de {len(aggregated_json_data)} intenções únicas agregadas dos arquivos JSON para processar.")
    if clear_all_data_flag:
        print("   (Modo de operação: LIMPAR TUDO e depois inserir)")
    else:
        print("   (Modo de operação: INSERIR SE NÃO EXISTIR PELO TÍTULO)")
        
    db = SessionLocal()
    try:
        migrate_intents_to_database(aggregated_json_data, db, clear_all_data_flag)
    except Exception as e:
        print(f"❌ Ocorreu um erro geral durante o processo de migração: {e}")
    finally:
        db.close()
        print("🔌 Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    main()