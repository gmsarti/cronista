"""
world.py — o estado ativo e o log.

O World guarda entidades (estado "dobrado") e o log append-only (a verdade).
`emit()` cria um evento, aplica seus efeitos ao estado e o registra. A camada
de sistemas nunca muta o estado diretamente: ela *propõe* eventos, e todo o
efeito colateral vive nos handlers de `apply`.
"""
from __future__ import annotations

import json
import random
from typing import Any, Iterable

from .entities import Artifact, Civ, Figure, Site
from .events import Event
from .scale import clamp


class World:
    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed)
        self.seed = seed
        self.year = 0
        self.entities: dict[int, Any] = {}
        self.log: list[Event] = []
        self._next_id = 1

    # ---- identidade -----------------------------------------------------
    def new_id(self) -> int:
        i = self._next_id
        self._next_id += 1
        return i

    def add(self, entity: Any) -> Any:
        self.entities[entity.id] = entity
        return entity

    # ---- consultas ------------------------------------------------------
    def figures(self, alive_only: bool = True) -> list[Figure]:
        out = [e for e in self.entities.values() if isinstance(e, Figure)]
        return [f for f in out if f.alive] if alive_only else out

    def civs(self) -> list[Civ]:
        return [e for e in self.entities.values() if isinstance(e, Civ)]

    def artifacts(self) -> list[Artifact]:
        return [e for e in self.entities.values() if isinstance(e, Artifact)]

    def figures_of(self, civ_id: int, alive_only: bool = True) -> list[Figure]:
        return [f for f in self.figures(alive_only) if f.civ == civ_id]

    def get(self, eid: int) -> Any:
        return self.entities.get(eid)

    def name_of(self, eid: int) -> str:
        e = self.entities.get(eid)
        return getattr(e, "name", f"#{eid}") if e else f"#{eid}"

    # ---- emissão de eventos --------------------------------------------
    def emit(
        self,
        kind: str,
        actors: Iterable[int] = (),
        site: int | None = None,
        caused_by: Iterable[int] = (),
        **data: Any,
    ) -> Event:
        ev = Event(
            id=self.new_id(),
            year=self.year,
            kind=kind,
            actors=tuple(actors),
            site=site,
            caused_by=tuple(caused_by),
            data=dict(data),
        )
        self._apply(ev)
        self.log.append(ev)
        return ev

    # ---- handlers (todo efeito colateral vive aqui) --------------------
    def _apply(self, ev: Event) -> None:
        handler = getattr(self, f"_on_{ev.kind}", None)
        if handler:
            handler(ev)

    def _on_morte(self, ev: Event) -> None:
        f = self.get(ev.actors[0])
        if isinstance(f, Figure) and f.alive:
            f.died = ev.year

    def _on_guerra_declarada(self, ev: Event) -> None:
        a, b = ev.actors[0], ev.actors[1]
        ca, cb = self.get(a), self.get(b)
        if isinstance(ca, Civ) and isinstance(cb, Civ):
            ca.em_guerra_com.add(b)
            cb.em_guerra_com.add(a)
            ca.guerra_evento[b] = ev.id
            cb.guerra_evento[a] = ev.id
            # a guerra rompe qualquer aliança e faz o comércio ruir
            ca.aliados.discard(b)
            cb.aliados.discard(a)

    def _on_alianca_formada(self, ev: Event) -> None:
        a, b = ev.actors[0], ev.actors[1]
        ca, cb = self.get(a), self.get(b)
        if isinstance(ca, Civ) and isinstance(cb, Civ):
            ca.aliados.add(b)
            cb.aliados.add(a)
            ca.alianca_evento[b] = ev.id
            cb.alianca_evento[a] = ev.id

    def _on_alianca_rompida(self, ev: Event) -> None:
        a, b = ev.actors[0], ev.actors[1]
        ca, cb = self.get(a), self.get(b)
        if isinstance(ca, Civ) and isinstance(cb, Civ):
            ca.aliados.discard(b)
            cb.aliados.discard(a)

    def _on_casamento_dinastico(self, ev: Event) -> None:
        fa, fb = self.get(ev.actors[0]), self.get(ev.actors[1])
        if isinstance(fa, Figure):
            fa.spouse = ev.actors[1]
        if isinstance(fb, Figure):
            fb.spouse = ev.actors[0]
        ca, cb = self.get(ev.data["civs"][0]), self.get(ev.data["civs"][1])
        if isinstance(ca, Civ) and isinstance(cb, Civ):
            from .scale import clamp
            boost = 3.0
            ca.parentesco[cb.id] = clamp(ca.parentesco.get(cb.id, 0) + boost)
            cb.parentesco[ca.id] = clamp(cb.parentesco.get(ca.id, 0) + boost)

    def _on_paz(self, ev: Event) -> None:
        a, b = ev.actors[0], ev.actors[1]
        ca, cb = self.get(a), self.get(b)
        if isinstance(ca, Civ) and isinstance(cb, Civ):
            ca.em_guerra_com.discard(b)
            cb.em_guerra_com.discard(a)
            # a paz alivia parte da tensão e da exaustão
            ca.tensao[b] = clamp(ca.tensao.get(b, 0) * 0.4)
            cb.tensao[a] = clamp(cb.tensao.get(a, 0) * 0.4)
            ca.exausto = clamp(ca.exausto * 0.3)
            cb.exausto = clamp(cb.exausto * 0.3)

    def _on_artefato_roubado(self, ev: Event) -> None:
        art = self.get(ev.data["artifact"])
        if isinstance(art, Artifact):
            art.holder_civ = ev.data["thief_civ"]

    # ---- serialização ---------------------------------------------------
    def dump_log(self) -> str:
        return json.dumps([e.to_dict() for e in self.log], ensure_ascii=False, indent=2)
