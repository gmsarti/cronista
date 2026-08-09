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
    visto: set[int] = set()
    ordem: list[Event] = []

    def visit(eid: int) -> None:
        if eid in visto or eid not in idx:
            return
        visto.add(eid)
        ev = idx[eid]
        for pai in ev.caused_by:
            visit(pai)
        ordem.append(ev)

    visit(event_id)
    ordem.sort(key=lambda e: (e.year, e.id))
    return ordem


# ---- renderização de um evento isolado ---------------------------------
def render_event(world: World, ev: Event) -> str:
    n = world.name_of
    y = f"Ano {ev.year:>3}"
    d = ev.data

    if ev.kind == "nascimento":
        return f"{y}: nasce {d.get('name', n(ev.actors[0]))}, de {n(ev.actors[1])} e {n(ev.actors[2])}."

    if ev.kind == "casamento":
        afin = descrever_intensidade(d.get("afinidade", 5))
        return f"{y}: {n(ev.actors[0])} e {n(ev.actors[1])} se unem — uma afinidade {afin}."

    if ev.kind == "morte":
        causa = d.get("causa", "?")
        renome = descrever_renome(d.get("renome", 1))
        quem = f"{n(ev.actors[0])}, {renome}," if renome != "desconhecido" else n(ev.actors[0])
        if causa == "batalha":
            if d.get("traicao"):
                return f"{y}: tomba {quem} pela mão dos próprios sogros de {n(d.get('contra'))} — o sangue foi traído."
            return f"{y}: tomba em batalha {quem} sob os golpes de {n(d.get('contra'))}."
        return f"{y}: morre {quem} aos {d.get('idade', '?')} anos."

    if ev.kind == "casamento_dinastico":
        noivos = d.get("noivos", [n(ev.actors[0]), n(ev.actors[1])])
        c1, c2 = d.get("civs", ev.actors)
        return f"{y}: casamento dinástico une {noivos[0]} ({n(c1)}) e {noivos[1]} ({n(c2)}) — o sangue sela o comércio."

    if ev.kind == "artefato_forjado":
        fama = descrever_intensidade(d.get("fama", 5))
        return f"{y}: {n(ev.actors[0])} forja {d.get('name')}, artefato de fama {fama}."

    if ev.kind == "artefato_roubado":
        return f"{y}: {n(ev.actors[0])} rouba {d.get('name')} das mãos de {n(ev.actors[1])} — uma afronta."

    if ev.kind == "rota_comercial":
        vol = descrever_intensidade(d.get("volume", 5))
        return f"{y}: abre-se uma rota comercial entre {n(ev.actors[0])} e {n(ev.actors[1])} — trocas de intensidade {vol}."

    if ev.kind == "comercio_rompido":
        return f"{y}: as rotas entre {n(ev.actors[0])} e {n(ev.actors[1])} se fecham — a guerra estrangula o comércio."

    if ev.kind == "alianca_formada":
        com = descrever_intensidade(d.get("comercio", 8))
        return f"{y}: {n(ev.actors[0])} e {n(ev.actors[1])} selam aliança, cimentada por um comércio {com}."

    if ev.kind == "alianca_rompida":
        return f"{y}: desfaz-se a aliança entre {n(ev.actors[0])} e {n(ev.actors[1])} — o comércio minguou."

    if ev.kind == "guerra_declarada":
        t = descrever_intensidade(d.get("tensao", 8))
        if d.get("motivo") == "traição":
            traidor = d.get("traidor_nome")
            quem = f"{traidor}, de {n(ev.actors[0])}," if traidor else n(ev.actors[0])
            return f"{y}: {quem} trai o sangue e marcha contra {n(ev.actors[1])} — a aliança é rasgada."
        if d.get("motivo") == "aliança":
            return f"{y}: {n(ev.actors[0])} entra na guerra contra {n(ev.actors[1])} para honrar uma aliança."
        return f"{y}: {n(ev.actors[0])} declara guerra a {n(ev.actors[1])} — a tensão era {t}."

    if ev.kind == "batalha":
        venc = n(d.get("vencedor"))
        perd = n(ev.actors[0] if ev.actors[1] == d.get("vencedor") else ev.actors[1])
        n_mortos = len(d.get("mortos", []))
        decisiva = "esmagadora" if d.get("margem", 0) > 0.5 else "renhida"
        cauda = f" ({n_mortos} figuras notáveis caem)" if n_mortos else ""
        return f"{y}: batalha {decisiva} — {venc} prevalece sobre {perd}{cauda}."

    if ev.kind == "paz":
        return f"{y}: {n(ev.actors[0])} e {n(ev.actors[1])} firmam a paz, exaustos."

    return f"{y}: {ev.kind} {list(ev.actors)}"


# ---- a saga: um evento e toda a sua cadeia causal ----------------------
def render_saga(world: World, event_id: int) -> str:
    cadeia = causal_subtree(world, event_id)
    linhas = [render_event(world, e) for e in cadeia]
    return "\n".join(f"  {'└─ ' if i == len(linhas)-1 else '├─ '}{l}"
                     for i, l in enumerate(linhas))


# ---- panorama ----------------------------------------------------------
def summarize(world: World) -> str:
    from collections import Counter
    c = Counter(e.kind for e in world.log)
    vivos = len(world.figures())
    total = len(world.figures(alive_only=False))
    linhas = [
        f"Mundo (seed={world.seed}) após {world.year+1} anos:",
        f"  eventos registrados : {len(world.log)}",
        f"  figuras (vivas/total): {vivos}/{total}",
        f"  artefatos forjados  : {len(world.artifacts())}",
        "  contagem por tipo   : " + ", ".join(f"{k}={v}" for k, v in c.most_common()),
    ]
    return "\n".join(linhas)


def _arquetipo(civ) -> str:
    if civ.mercantilismo - civ.belicosidade > 2:
        return "mercantil"
    if civ.belicosidade - civ.mercantilismo > 2:
        return "belicosa"
    return "ambivalente"


def world_state(world: World) -> str:
    """O mapa geopolítico ao fim: arquétipo, riqueza e blocos de aliança.
    Mostra o resultado do cabo de guerra entre o comércio e o conflito.
    Aliados ligados por sangue (parentesco) vêm marcados com ♦."""
    from .scale import descrever_intensidade
    linhas = ["Estado geopolítico ao fim da crônica:"]
    for civ in sorted(world.civs(), key=lambda c: c.prosperidade, reverse=True):
        alias = []
        for a in sorted(civ.aliados):
            marca = "♦" if civ.parentesco.get(a, 0) >= 3 else ""
            alias.append(world.name_of(a) + marca)
        aliados = ", ".join(alias) or "—"
        prosp = descrever_intensidade(civ.prosperidade)
        linhas.append(
            f"  {civ.name:<20} [{_arquetipo(civ):^12}] "
            f"riqueza {prosp:<12} bel={civ.belicosidade:.0f} merc={civ.mercantilismo:.0f} "
            f"| aliados: {aliados}"
        )
    linhas.append("  (♦ = aliança selada por casamento dinástico)")
    return "\n".join(linhas)


def biggest_sagas(world: World,
                  kinds=("guerra_declarada", "batalha", "alianca_formada",
                         "casamento_dinastico"),
                  top=3):
    """Escolhe as cadeias causais mais profundas — as melhores lendas para
    narrar — evitando sobreposição (não repete três batalhas da mesma guerra)."""
    candidatos = [e for e in world.log if e.kind in kinds]
    candidatos.sort(key=lambda e: (len(causal_subtree(world, e.id)), e.id),
                    reverse=True)
    # uma lenda por "guerra-raiz": a declaração de guerra mais antiga da cadeia.
    melhor_por_raiz: dict[int, Event] = {}
    for ev in candidatos:
        sub = causal_subtree(world, ev.id)
        guerras = [e for e in sub if e.kind == "guerra_declarada"]
        raiz = guerras[0].id if guerras else ev.id
        if raiz not in melhor_por_raiz:
            melhor_por_raiz[raiz] = ev   # candidatos já vêm do mais profundo
    escolhidas = sorted(melhor_por_raiz.values(),
                        key=lambda e: len(causal_subtree(world, e.id)),
                        reverse=True)
    return escolhidas[:top]
