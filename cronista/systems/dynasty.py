"""Casamentos dinásticos entre civs — o elo entre linhagem e comércio."""
from __future__ import annotations

import itertools

from ..entities import Civ
from ..scale import decay
from ..world import World
from ._thresholds import PEACE_THRESHOLD, TRADE_ROUTE_THRESHOLD


class Dynasty:
    """Casamentos dinásticos entre civs — o elo entre linhagem e comércio.

    Quando duas civs comerciam forte e há pouca tensão, seus nobres se casam,
    selando com sangue o que o dinheiro começou. O parentesco [0,10]:
      - amortece a tensão com MAIS força que o comércio (sangue prende mais);
      - dá durabilidade à aliança (resiste à queda do comércio);
      - realimenta-se: filhos de uniões dinásticas entrelaçam as linhagens.

    O sangue esfria devagar entre as gerações (decaimento leve), o que motiva
    renovar os laços — e abre a fresta para a mais rara das tragédias: a
    traição do parente (tratada no Conflict)."""

    def step(self, world: World) -> None:
        civs = world.civs()
        for civ_a, civ_b in itertools.combinations(civs, 2):
            # o sangue esfria devagar se não for renovado
            if civ_a.parentesco.get(civ_b.id):
                decayed = decay(civ_a.parentesco[civ_b.id], 0.01)
                civ_a.parentesco[civ_b.id] = decayed
                civ_b.parentesco[civ_a.id] = decayed
            if civ_b.id in civ_a.at_war_with:
                continue
            com = civ_a.comercio.get(civ_b.id, 0.0)
            tensao = max(civ_a.tension.get(civ_b.id, 0), civ_b.tension.get(civ_a.id, 0))
            paren = civ_a.parentesco.get(civ_b.id, 0.0)
            # casa-se quando há comércio forte, pouca tensão e o laço não está
            # saturado; a probabilidade é graduada pelo próprio comércio.
            if com >= TRADE_ROUTE_THRESHOLD and tensao < PEACE_THRESHOLD + 2 and paren < 8:
                prob = 0.04 * (com / 10) * (1 - paren / 10)
                if world.rng.random() < prob:
                    self._marry(world, civ_a, civ_b)

    def _marry(self, world: World, civ_a: Civ, civ_b: Civ) -> None:
        na, nb = self._best_bachelor(world, civ_a), self._best_bachelor(world, civ_b)
        if not na or not nb:
            return
        world.emit("casamento_dinastico", actors=[na.id, nb.id],
                   civs=[civ_a.id, civ_b.id],
                   noivos=[na.name, nb.name],
                   caused_by=self._route_between(world, civ_a, civ_b))

    def _best_bachelor(self, world: World, civ: Civ):
        candidatos = [f for f in world.figures_of(civ.id)
                if f.spouse is None and world.year - f.born >= 16]
        # o de maior renome faz o melhor par diplomático
        return max(candidatos, key=lambda f: f.renown, default=None)

    def _route_between(self, world: World, civ_a: Civ, civ_b: Civ) -> tuple[int, ...]:
        for ev in reversed(world.log):
            if ev.kind == "rota_comercial" and set(ev.actors) == {civ_a.id, civ_b.id}:
                return (ev.id,)
        return ()
