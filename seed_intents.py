from database import SessionLocal, Intent, IntentVariation

db = SessionLocal()

# Criando uma intenção
intent = Intent(
    title="Emitir Nota Fiscal",
    response="Para emitir uma nota fiscal, vá em Vendas > Notas Fiscais > Nova Nota."
)
db.add(intent)
db.commit()
db.refresh(intent)

# Adicionando variações dessa intenção
variacoes = [
    "como emitir nota fiscal",
    "quero gerar uma nota",
    "fazer nota fiscal",
    "nota fiscal de produto",
    "emitir nf"
]

for texto in variacoes:
    var = IntentVariation(intent_id=intent.intent_id, variation=texto)
    db.add(var)

db.commit()
db.close()