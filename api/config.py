"""
config.py — configuração da API.

Os tetos (`max_*`) existem porque a API é stateless: cada requisição re-simula
o mundo do zero, então o custo de uma request é proporcional a
`years * n_civs * figures_per_civ`. Sem teto, uma única chamada poderia pedir
100.000 anos e travar o processo.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CRONISTA_", env_file=".env")

    app_name: str = "cronista"
    app_version: str = "0.1.0"

    default_years: int = 180
    default_n_civs: int = 5
    default_figures_per_civ: int = 6

    max_years: int = 1000
    max_n_civs: int = 20
    max_figures_per_civ: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
