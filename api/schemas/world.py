"""
world.py — os modelos de resposta da API. Espelham o domínio, sem lógica.
"""
from typing import Any

from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    status: str
    app: str
    version: str


class SimulationParamsOut(BaseModel):
    """Ecoa os parâmetros que geraram o mundo — reproduzir é só repeti-los."""

    seed: int
    years: int
    n_civs: int
    figuras_por_civ: int


class EventOut(BaseModel):
    """Espelha `cronista.events.Event`."""

    id: int
    year: int
    kind: str
    actors: list[int] = Field(default_factory=list)
    site: int | None = None
    caused_by: list[int] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class NarratedEventOut(EventOut):
    """Um evento acompanhado da prosa que o narra."""

    prosa: str


class EventPageOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[EventOut]


class WorldSummaryOut(BaseModel):
    params: SimulationParamsOut
    total_eventos: int
    figuras_vivas: int
    figuras_total: int
    artefatos: int
    resumo: str
    estado_geopolitico: str


class SagaOut(BaseModel):
    """Um evento e toda a cadeia causal que o produziu."""

    event_id: int
    profundidade: int
    prosa: str
    cadeia: list[NarratedEventOut]


class SagaRefOut(BaseModel):
    """Ponteiro para uma saga: o evento-folha e o tamanho da sua cadeia."""

    event_id: int
    year: int
    kind: str
    profundidade: int
    prosa: str


class WorldLogOut(BaseModel):
    params: SimulationParamsOut
    total: int
    log: list[EventOut]
