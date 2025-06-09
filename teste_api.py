# teste_api.py - Versão Final de Validação (Endpoint /venda/{codigo})
import requests

# --- DADOS VALIDADOS ---
URL_BASE = "http://wapalternativa02.dalla.srv.br:2099/root"
SEU_TOKEN_FUNCIONAL = "3R215TWJLYwrjGlC8ht7e68srMtAwm6K6kg8kY8An"
CODIGO_DA_VENDA_ESPECIFICA = "178241" # O "Nº Venda" que sabemos que existe
# --------------------

# Monta a URL para o endpoint de UMA VENDA ESPECÍFICA
url_completa = f"{URL_BASE}/venda/{CODIGO_DA_VENDA_ESPECIFICA}"

# Para buscar um item específico, geralmente só o token é necessário no header
headers = {
    "X-Token": SEU_TOKEN_FUNCIONAL,
    "Banco": "MasterSite" # Vamos manter este por segurança
}

print(f"Tentando acessar venda específica: GET {url_completa}")
print(f"Com os headers: {headers}")

try:
    response = requests.get(url_completa, headers=headers, timeout=20)

    print(f"\n--- Resultado ---")
    print(f"Código de Status HTTP: {response.status_code}")
    print("Resposta do Servidor:")
    
    try:
        print(response.json())
    except requests.exceptions.JSONDecodeError:
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"\nOcorreu um erro de conexão: {e}")