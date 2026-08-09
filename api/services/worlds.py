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
    return NarratedEventOut(**ev.to_dict(), prosa=render_event(world, ev))


def params_out(seed: int, params: SimulationParams) -> SimulationParamsOut:
    return SimulationParamsOut(seed=seed, **params.model_dump())


def build_summary(world: World, seed: int, params: SimulationParams) -> WorldSummaryOut:
    return WorldSummaryOut(
        params=params_out(seed, params),
        total_eventos=len(world.log),
        figuras_vivas=len(world.figures()),
        figuras_total=len(world.figures(alive_only=False)),
        artefatos=len(world.artifacts()),
        resumo=summarize(world),
        estado_geopolitico=world_state(world),
    )


def filter_events(
    world: World,
    kind: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    actor: int | None = None,
) -> list[Event]:
    eventos = world.log
    if kind is not None:
        eventos = [e for e in eventos if e.kind == kind]
    if year_from is not None:
        eventos = [e for e in eventos if e.year >= year_from]
    if year_to is not None:
        eventos = [e for e in eventos if e.year <= year_to]
    if actor is not None:
        eventos = [e for e in eventos if actor in e.actors]
    return list(eventos)


def build_event_page(
    world: World,
    limit: int,
    offset: int,
    kind: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    actor: int | None = None,
) -> EventPageOut:
    eventos = filter_events(world, kind, year_from, year_to, actor)
    janela = eventos[offset : offset + limit]
    return EventPageOut(
        total=len(eventos),
        limit=limit,
        offset=offset,
        items=[_to_out(e) for e in janela],
    )


def find_event(world: World, event_id: int) -> Event | None:
    return index_log(world).get(event_id)


def build_narrated_event(world: World, ev: Event) -> NarratedEventOut:
    return _narrated(world, ev)


def build_saga(world: World, event_id: int) -> SagaOut:
    cadeia = causal_subtree(world, event_id)
    return SagaOut(
        event_id=event_id,
        profundidade=len(cadeia),
        prosa=render_saga(world, event_id),
        cadeia=[_narrated(world, e) for e in cadeia],
    )


def build_biggest_sagas(world: World, top: int) -> list[SagaRefOut]:
    return [
        SagaRefOut(
            event_id=ev.id,
            year=ev.year,
            kind=ev.kind,
            profundidade=len(causal_subtree(world, ev.id)),
            prosa=render_event(world, ev),
        )
        for ev in biggest_sagas(world, top=top)
    ]


def build_log(world: World, seed: int, params: SimulationParams) -> WorldLogOut:
    return WorldLogOut(
        params=params_out(seed, params),
        total=len(world.log),
        log=[_to_out(e) for e in world.log],
    )
