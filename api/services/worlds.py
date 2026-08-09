"""
worlds.py — traduz o mundo simulado para os modelos de resposta.

Camada de leitura: nada aqui muta o `World`. Toda a interpretação já existe em
`cronista.chronicle` — este módulo apenas orquestra e serializa.
"""
from api.deps import SimulationParams
from api.schemas.world import (
    EventOut,
    EventPageOut,
    NarratedEventOut,
    SagaOut,
    SagaRefOut,
    SimulationParamsOut,
    WorldLogOut,
    WorldSummaryOut,
)
from cronista.chronicle import (
    biggest_sagas,
    causal_subtree,
    index_log,
    render_event,
    render_saga,
    summarize,
    world_state,
)
from cronista.events import Event
from cronista.world import World


def _to_out(ev: Event) -> EventOut:
    return EventOut(**ev.to_dict())


def _narrated(world: World, ev: Event) -> NarratedEventOut:
    return NarratedEventOut(**ev.to_dict(), narration=render_event(world, ev))


def params_out(seed: int, params: SimulationParams) -> SimulationParamsOut:
    return SimulationParamsOut(seed=seed, **params.model_dump())


def build_summary(world: World, seed: int, params: SimulationParams) -> WorldSummaryOut:
    return WorldSummaryOut(
        params=params_out(seed, params),
        total_events=len(world.log),
        living_figures=len(world.figures()),
        total_figures=len(world.figures(alive_only=False)),
        artefatos=len(world.artifacts()),
        summary=summarize(world),
        geopolitical_state=world_state(world),
    )


def filter_events(
    world: World,
    kind: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    actor: int | None = None,
) -> list[Event]:
    events = world.log
    if kind is not None:
        events = [e for e in events if e.kind == kind]
    if year_from is not None:
        events = [e for e in events if e.year >= year_from]
    if year_to is not None:
        events = [e for e in events if e.year <= year_to]
    if actor is not None:
        events = [e for e in events if actor in e.actors]
    return list(events)


def build_event_page(
    world: World,
    limit: int,
    offset: int,
    kind: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    actor: int | None = None,
) -> EventPageOut:
    events = filter_events(world, kind, year_from, year_to, actor)
    window = events[offset : offset + limit]
    return EventPageOut(
        total=len(events),
        limit=limit,
        offset=offset,
        items=[_to_out(e) for e in window],
    )


def find_event(world: World, event_id: int) -> Event | None:
    return index_log(world).get(event_id)


def build_narrated_event(world: World, ev: Event) -> NarratedEventOut:
    return _narrated(world, ev)


def build_saga(world: World, event_id: int) -> SagaOut:
    chain = causal_subtree(world, event_id)
    return SagaOut(
        event_id=event_id,
        depth=len(chain),
        narration=render_saga(world, event_id),
        chain=[_narrated(world, e) for e in chain],
    )


def build_biggest_sagas(world: World, top: int) -> list[SagaRefOut]:
    return [
        SagaRefOut(
            event_id=ev.id,
            year=ev.year,
            kind=ev.kind,
            depth=len(causal_subtree(world, ev.id)),
            narration=render_event(world, ev),
        )
        for ev in biggest_sagas(world, top=top)
    ]


def build_log(world: World, seed: int, params: SimulationParams) -> WorldLogOut:
    return WorldLogOut(
        params=params_out(seed, params),
        total=len(world.log),
        log=[_to_out(e) for e in world.log],
    )
