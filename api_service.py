# api_service.py (Versão Final e Completa)
import httpx
from typing import Optional

async def consultar_status_api(codigo_venda: str, token: str, base_url: str) -> Optional[dict]:
    """
    Consulta uma API externa para obter os dados de uma venda específica.
    Recebe a URL base dinamicamente para suportar múltiplos clientes.
    """
    # Monta a URL completa para o endpoint desejado
    url = f"{base_url}/venda/{codigo_venda}"
    
    # Prepara o header da requisição com o token de autorização
    headers = {
        "X-Token": token,
        "Banco": "MasterSite" 
    }
    
    print(f"[API Service] Consultando API: GET {url}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=20.0)
            response.raise_for_status()
            
            print(f"[API Service] Sucesso! Status: {response.status_code}")
            return response.json()

        except httpx.HTTPStatusError as e:
            print(f"ERRO de status da API: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"ERRO de requisição para a API: {e}")
            return None