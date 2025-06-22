from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import json

class Settings(BaseSettings):
    # Campos que serão carregados diretamente do .env
    DATABASE_URL: str
    APP_BASE_URL: str = "http://localhost:8000"
    
    # Definimos o campo com o tipo final que desejamos: uma lista de strings.
    CORS_ORIGINS: List[str]

    # Este é um "validador" do Pydantic. Ele nos permite transformar o dado ANTES que ele seja validado.
    @field_validator("CORS_ORIGINS", mode='before')
    @classmethod
    def _parse_cors_origins_json(cls, v: str) -> List[str]:
        """
        Este validador intercepta a string do .env (ex: '["url1", "url2"]')
        e a transforma na lista Python que o campo CORS_ORIGINS espera.
        """
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("A variável CORS_ORIGINS no arquivo .env não é um JSON de lista válido.")
        return v # Se por acaso já for uma lista, apenas a retorna.

    class Config:
        env_file = ".env"
        case_sensitive = False

# Cria uma instância única das configurações para ser usada em todo o projeto
settings = Settings()