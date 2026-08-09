"""
main.py — a aplicação.

    uvicorn api.main:create_app --factory --reload

Sem estado global e sem lifespan: não há nada para inicializar. Cada requisição
re-simula o mundo a partir da seed.
"""
from fastapi import FastAPI

from api.config import get_settings
from api.routers import health, worlds


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Gerador determinístico de história event-sourced. "
            "A API é stateless: cada requisição re-simula o mundo a partir de "
            "(seed, years, n_civs, figuras_por_civ)."
        ),
    )
    app.include_router(health.router)
    app.include_router(worlds.router)
    return app


app = create_app()
