"""
chronicle.py — ler o log de volta e contar a lenda.

Duas funções centrais:
  - `causal_subtree`: dado um evento, retorna todos os seus ancestrais causais
    (a saga que o produziu), seguindo as arestas `caused_by`.
  - `render_*`: transforma eventos em prosa. Usa as bandas graduadas de scale.py
    para escolher a linguagem — a gradação da mecânica reverbera na narração.

Esta camada NUNCA muta o estado. É pura interpretação. Trocar estes templates
por uma chamada de LLM (passando a subárvore causal como contexto) é o próximo
passo natural — a separação já está pronta.
"""
from __future__ import annotations

from .events import Event
from .scale import descrever_intensidade, descrever_renome
from .world import World


def index_log(world: World) -> dict[int, Event]:
    return {e.id: e for e in world.log}


def causal_subtree(world: World, event_id: int) -> list[Event]:
    """Todos os ancestrais causais de um evento, em ordem cronológica."""
    idx = index_log(world)
    visited: set[int] = set()
    ordered: list[Event] = []

    def visit(eid: int) -> None:
        if eid in visited or eid not in idx:
            return
        visited.add(eid)
        ev = idx[eid]
        for parent_id in ev.caused_by:
            visit(parent_id)
        ordered.append(ev)

    visit(event_id)
    ordered.sort(key=lambda e: (e.year, e.id))
    return ordered


# ---- renderização de um evento isolado ---------------------------------
def render_event(world: World, ev: Event) -> str:
    name_of = world.name_of
    year_label = f"Ano {ev.year:>3}"
    event_data = ev.data

    actor_a = name_of(ev.actors[0]) if ev.actors else None
    actor_b = name_of(ev.actors[1]) if len(ev.actors) > 1 else None

    if ev.kind == "nascimento":
        child_name = event_data.get("name", actor_a)
        parent_c = name_of(ev.actors[2])
        return f"{year_label}: nasce {child_name}, de {actor_b} e {parent_c}."

    if ev.kind == "casamento":
        affinity_label = descrever_intensidade(event_data.get("afinidade", 5))
        return f"{year_label}: {actor_a} e {actor_b} se unem — uma afinidade {affinity_label}."

    if ev.kind == "morte":
        causa = event_data.get("causa", "?")
        renome = descrever_renome(event_data.get("renome", 1))
        quem = f"{actor_a}, {renome}," if renome != "desconhecido" else actor_a
        contra = name_of(event_data.get("contra"))
        if causa == "batalha":
            if event_data.get("traicao"):
                return (f"{year_label}: tomba {quem} pela mão dos próprios sogros de {contra}"
                        " — o sangue foi traído.")
            return f"{year_label}: tomba em batalha {quem} sob os golpes de {contra}."
        return f"{year_label}: morre {quem} aos {event_data.get('idade', '?')} anos."

    if ev.kind == "casamento_dinastico":
        noivos = event_data.get("noivos", [actor_a, actor_b])
        civ_a_id, civ_b_id = event_data.get("civs", ev.actors)
        civ_a, civ_b = name_of(civ_a_id), name_of(civ_b_id)
        return (f"{year_label}: casamento dinástico une {noivos[0]} ({civ_a}) e "
                f"{noivos[1]} ({civ_b}) — o sangue sela o comércio.")

    if ev.kind == "artefato_forjado":
        fame_label = descrever_intensidade(event_data.get("fama", 5))
        return (f"{year_label}: {actor_a} forja {event_data.get('name')}, "
                f"artefato de fama {fame_label}.")

    if ev.kind == "artefato_roubado":
        return (f"{year_label}: {actor_a} rouba {event_data.get('name')} das mãos de {actor_b}"
                " — uma afronta.")

    if ev.kind == "rota_comercial":
        volume_label = descrever_intensidade(event_data.get("volume", 5))
        return (f"{year_label}: abre-se uma rota comercial entre {actor_a} e {actor_b}"
                f" — trocas de intensidade {volume_label}.")

    if ev.kind == "comercio_rompido":
        return (f"{year_label}: as rotas entre {actor_a} e {actor_b} se fecham"
                " — a guerra estrangula o comércio.")

    if ev.kind == "alianca_formada":
        trade_label = descrever_intensidade(event_data.get("comercio", 8))
        return (f"{year_label}: {actor_a} e {actor_b} selam aliança, "
                f"cimentada por um comércio {trade_label}.")

    if ev.kind == "alianca_rompida":
        return (f"{year_label}: desfaz-se a aliança entre {actor_a} e {actor_b}"
                " — o comércio minguou.")

    if ev.kind == "guerra_declarada":
        tension_label = descrever_intensidade(event_data.get("tensao", 8))
        if event_data.get("motivo") == "traição":
            traidor = event_data.get("traidor_nome")
            quem = f"{traidor}, de {actor_a}," if traidor else actor_a
            return (f"{year_label}: {quem} trai o sangue e marcha contra {actor_b}"
                    " — a aliança é rasgada.")
        if event_data.get("motivo") == "aliança":
            return (f"{year_label}: {actor_a} entra na guerra contra {actor_b} "
                    "para honrar uma aliança.")
        return f"{year_label}: {actor_a} declara guerra a {actor_b} — a tensão era {tension_label}."

    if ev.kind == "batalha":
        winner_name = name_of(event_data.get("vencedor"))
        loser_id = ev.actors[0] if ev.actors[1] == event_data.get("vencedor") else ev.actors[1]
        loser_name = name_of(loser_id)
        dead_count = len(event_data.get("mortos", []))
        decisiva = "esmagadora" if event_data.get("margem", 0) > 0.5 else "renhida"
        cauda = f" ({dead_count} figuras notáveis caem)" if dead_count else ""
        return (f"{year_label}: batalha {decisiva} — {winner_name} prevalece sobre {loser_name}"
                f"{cauda}.")

    if ev.kind == "paz":
        return f"{year_label}: {actor_a} e {actor_b} firmam a paz, exaustos."

    return f"{year_label}: {ev.kind} {list(ev.actors)}"


# ---- a saga: um evento e toda a sua cadeia causal ----------------------
def render_saga(world: World, event_id: int) -> str:
    chain = causal_subtree(world, event_id)
    lines = [render_event(world, e) for e in chain]
    return "\n".join(f"  {'└─ ' if i == len(lines)-1 else '├─ '}{line}"
                     for i, line in enumerate(lines))


# ---- panorama ----------------------------------------------------------
def summarize(world: World) -> str:
    from collections import Counter
    kind_counts = Counter(e.kind for e in world.log)
    alive_count = len(world.figures())
    total_count = len(world.figures(alive_only=False))
    lines = [
        f"Mundo (seed={world.seed}) após {world.year+1} anos:",
        f"  eventos registrados : {len(world.log)}",
        f"  figuras (vivas/total): {alive_count}/{total_count}",
        f"  artefatos forjados  : {len(world.artifacts())}",
        "  contagem por tipo   : " + ", ".join(f"{k}={v}" for k, v in kind_counts.most_common()),
    ]
    return "\n".join(lines)


def _archetype(civ) -> str:
    if civ.mercantilism - civ.belligerence > 2:
        return "mercantil"
    if civ.belligerence - civ.mercantilism > 2:
        return "belicosa"
    return "ambivalente"


def world_state(world: World) -> str:
    """O mapa geopolítico ao fim: arquétipo, riqueza e blocos de aliança.
    Mostra o resultado do cabo de guerra entre o comércio e o conflito.
    Aliados ligados por sangue (parentesco) vêm marcados com ♦."""
    from .scale import descrever_intensidade
    lines = ["Estado geopolítico ao fim da crônica:"]
    for civ in sorted(world.civs(), key=lambda c: c.prosperidade, reverse=True):
        allies_display = []
        for ally_id in sorted(civ.allies):
            marca = "♦" if civ.parentesco.get(ally_id, 0) >= 3 else ""
            allies_display.append(world.name_of(ally_id) + marca)
        allies_joined = ", ".join(allies_display) or "—"
        prosp = descrever_intensidade(civ.prosperidade)
        lines.append(
            f"  {civ.name:<20} [{_archetype(civ):^12}] "
            f"riqueza {prosp:<12} bel={civ.belligerence:.0f} merc={civ.mercantilism:.0f} "
            f"| aliados: {allies_joined}"
        )
    lines.append("  (♦ = aliança selada por casamento dinástico)")
    return "\n".join(lines)


def biggest_sagas(world: World,
                  kinds=("guerra_declarada", "batalha", "alianca_formada",
                         "casamento_dinastico"),
                  top=3):
    """Escolhe as cadeias causais mais profundas — as melhores lendas para
    narrar — evitando sobreposição (não repete três batalhas da mesma guerra)."""
    candidates = [e for e in world.log if e.kind in kinds]
    candidates.sort(key=lambda e: (len(causal_subtree(world, e.id)), e.id),
                    reverse=True)
    # uma lenda por "guerra-raiz": a declaração de guerra mais antiga da cadeia.
    best_by_root_war: dict[int, Event] = {}
    for ev in candidates:
        subtree = causal_subtree(world, ev.id)
        wars = [e for e in subtree if e.kind == "guerra_declarada"]
        root_id = wars[0].id if wars else ev.id
        if root_id not in best_by_root_war:
            best_by_root_war[root_id] = ev   # candidates já vêm do mais profundo
    chosen = sorted(best_by_root_war.values(),
                    key=lambda e: len(causal_subtree(world, e.id)),
                    reverse=True)
    return chosen[:top]
