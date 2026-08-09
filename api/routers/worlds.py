"""
worlds.py — as rotas do mundo. Todas somente leitura: a API nunca muta o log.

`seed` é path param; os demais parâmetros de simulação são query params
(ver `api.deps.SimulationParams`).
"""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from api.deps import ParamsDep, WorldDep
from api.schemas.world import (
    EventPageOut,
    NarratedEventOut,
    SagaOut,
    SagaRefOut,
    WorldLogOut,
    WorldSummaryOut,
)
from api.services import worlds as service

router = APIRouter(prefix="/worlds", tags=["worlds"])

SeedPath = Annotated[int, Path(ge=0, description="Semente do gerador determinístico.")]
EventIdPath = Annotated[int, Path(ge=1, description="Id de um evento do log.")]


@router.get("/{seed}", response_model=WorldSummaryOut)
def get_world_summary(seed: SeedPath, world: WorldDep, params: ParamsDep) -> WorldSummaryOut:
    """Resumo do mundo e o mapa geopolítico ao fim da crônica."""
    return service.build_summary(world, seed, params)


@router.get("/{seed}/events", response_model=EventPageOut)
def list_events(
    seed: SeedPath,
    world: WorldDep,
    kind: Annotated[str | None, Query(description="Filtra por tipo de evento.")] = None,
    year_from: Annotated[int | None, Query(ge=0)] = None,
    year_to: Annotated[int | None, Query(ge=0)] = None,
    actor: Annotated[int | None, Query(ge=1, description="Id de figura ou civ.")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EventPageOut:
    """O log em ordem cronológica, paginado e filtrável."""
    return service.build_event_page(world, limit, offset, kind, year_from, year_to, actor)


@router.get("/{seed}/events/{event_id}", response_model=NarratedEventOut)
def get_event(seed: SeedPath, event_id: EventIdPath, world: WorldDep) -> NarratedEventOut:
    """Um evento e a prosa que o narra."""
    ev = service.find_event(world, event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail=f"Evento {event_id} não existe neste mundo.")
    return service.build_narrated_event(world, ev)


@router.get("/{seed}/events/{event_id}/saga", response_model=SagaOut)
def get_event_saga(seed: SeedPath, event_id: EventIdPath, world: WorldDep) -> SagaOut:
    """A cadeia causal completa que produziu o evento, seguindo `caused_by`."""
    if service.find_event(world, event_id) is None:
        raise HTTPException(status_code=404, detail=f"Evento {event_id} não existe neste mundo.")
    return service.build_saga(world, event_id)


@router.get("/{seed}/sagas", response_model=list[SagaRefOut])
def list_biggest_sagas(
    seed: SeedPath,
    world: WorldDep,
    top: Annotated[int, Query(ge=1, le=20)] = 3,
) -> list[SagaRefOut]:
    """As cadeias causais mais profundas — as melhores lendas do mundo."""
    return service.build_biggest_sagas(world, top)


@router.get("/{seed}/log", response_model=WorldLogOut)
def get_log(seed: SeedPath, world: WorldDep, params: ParamsDep) -> WorldLogOut:
    """O log completo, cru."""
    return service.build_log(world, seed, params)
