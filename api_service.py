# File: api_service.py (Versão 2.0 - Arquitetura Escalável)

import httpx
import logging
from typing import Optional, Dict, Any

# Configuração do logger para este módulo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [API_SERVICE] - %(message)s')

class MasterAPIClient:
    """
    Um cliente de API assíncrono e reutilizável para interagir com a Master API.
    Centraliza a lógica de autenticação, headers e tratamento de erros.
    """
    def __init__(self, token: str, base_url: str, banco: str, client_id_log: int = 0):
        """
        Inicializa o cliente com as credenciais específicas de um tenant.
        
        Args:
            token: O X-Token para autenticação.
            base_url: A URL base da API do cliente (ex: http://alternativa.net.br/api/v2).
            banco: O valor para o header 'Banco'.
            client_id_log: O ID do cliente para enriquecer os logs.
        """
        self.base_url = base_url.rstrip('/') # Garante que não haja barras extras
        self.client_id_log = client_id_log
        
        headers = {
            "X-Token": token,
            "Banco": banco,
            "Content-Type": "application/json"
        }
        
        self.client = httpx.AsyncClient(headers=headers, timeout=20.0)
        logging.info(f"Cliente API inicializado para client_id: {self.client_id_log}")

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Método privado genérico para realizar requisições."""
        url = f"{self.base_url}/{endpoint}"
        try:
            logging.info(f"Executando {method} para {url} (client_id: {self.client_id_log})")
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            
            data = response.json()
            logging.info(f"Sucesso na chamada para {url}. Status: {response.status_code}.")
            return data

        except httpx.HTTPStatusError as e:
            logging.error(
                f"Erro de Status HTTP em {url} (client_id: {self.client_id_log}): "
                f"Status {e.response.status_code} - Resposta: {e.response.text}",
                exc_info=True
            )
            return None
        except httpx.RequestError as e:
            logging.error(
                f"Erro de Requisição em {url} (client_id: {self.client_id_log}): {e}",
                exc_info=True
            )
            return None
        except Exception as e:
            logging.critical(
                f"Erro inesperado no cliente API em {url} (client_id: {self.client_id_log}): {e}",
                exc_info=True
            )
            return None
            
    # --- MÉTODOS DE API EXISTENTES E NOVOS ---

    async def get_venda(self, codigo_venda: str) -> Optional[dict]:
        """
        Busca os dados completos de uma venda específica. (Antiga função consultar_status_api)
        Endpoint: GET /venda/{codigo}
        """
        return await self._make_request("GET", f"venda/{codigo_venda}")

    async def get_cliente_by_documento(self, documento: str) -> Optional[dict]:
        """
        (NOVA FUNÇÃO ESTRATÉGICA) Busca um cliente pelo seu DocumentoFiscal (CPF/CNPJ).
        Endpoint: POST /getclientes
        """
        payload = {
            "DocumentoFiscal": {
                "Valores": [documento]
            }
        }
        return await self._make_request("POST", "getclientes", json=payload)

    async def get_produto(self, codigo_produto: str) -> Optional[dict]:
        """
        (NOVA FUNÇÃO ESTRATÉGICA) Busca dados de um produto pelo código.
        Endpoint: GET /produto/{codigo}
        """
        return await self._make_request("GET", f"produto/{codigo_produto}")
        
    async def close(self):
        """Fecha a sessão do cliente httpx. Essencial para o graceful shutdown."""
        if not self.client.is_closed:
            await self.client.aclose()
            logging.info(f"Cliente API fechado para client_id: {self.client_id_log}")