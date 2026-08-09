"""
deps.py — os parâmetros de simulação e a construção do mundo.

A API é stateless: não existe mundo guardado no servidor. Cada requisição
re-simula a partir de `(seed, years, n_civs, figuras_por_civ)` — o que é sempre
consistente, porque `simulate` é determinístico.
"""
from typing import Annotated

from fastapi import Depends, Path, Query
from pydantic import BaseModel, Field

from api.config import get_settings
from cronista import World, simulate

_s = get_settings()


class SimulationParams(BaseModel):
    """Tudo que define um mundo. Mesmos valores → mesmo log, sempre.

    Sem `extra="forbid"`: como o modelo é lido da query string inteira, proibir
    extras rejeitaria os filtros próprios de cada rota (`kind`, `limit`, ...).
    """

    years: int = Field(default=_s.default_years, ge=1, le=_s.max_years)
    n_civs: int = Field(default=_s.default_n_civs, ge=1, le=_s.max_n_civs)
    figuras_por_civ: int = Field(
        default=_s.default_figuras_por_civ, ge=1, le=_s.max_figuras_por_civ
    )


def get_world(
    seed: Annotated[int, Path(ge=0, description="Semente do gerador determinístico.")],
    params: Annotated[SimulationParams, Query()],
) -> World:
    return simulate(
        seed=seed,
        years=params.years,
        n_civs=params.n_civs,
        figuras_por_civ=params.figuras_por_civ,
    )


WorldDep = Annotated[World, Depends(get_world)]
ParamsDep = Annotated[SimulationParams, Query()]
