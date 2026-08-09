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
    figures_per_civ: int


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

    narration: str


class EventPageOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[EventOut]


class WorldSummaryOut(BaseModel):
    params: SimulationParamsOut
    total_events: int
    living_figures: int
    total_figures: int
    artefatos: int
    summary: str
    geopolitical_state: str


class SagaOut(BaseModel):
    """Um evento e toda a cadeia causal que o produziu."""

    event_id: int
    depth: int
    narration: str
    chain: list[NarratedEventOut]


class SagaRefOut(BaseModel):
    """Ponteiro para uma saga: o evento-folha e o tamanho da sua cadeia."""

    event_id: int
    year: int
    kind: str
    depth: int
    narration: str


class WorldLogOut(BaseModel):
    params: SimulationParamsOut
    total: int
    log: list[EventOut]
