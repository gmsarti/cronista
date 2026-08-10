"""O contrapeso econômico entre civs."""
from __future__ import annotations

import itertools

from ..entities import Civ
from ..scale import blend, clamp, decay
from ..world import World
from ._thresholds import (
    ALLIANCE_END_THRESHOLD,
    ALLIANCE_THRESHOLD,
    PEACE_THRESHOLD,
    TRADE_ROUTE_THRESHOLD,
)


class Trade:
    """O contrapeso. Comércio é um escalar [0,10] entre civs que cresce na paz
    (puxado pelo mercantilismo e pela prosperidade mútua) e rui na guerra.

    Três efeitos, todos graduados:
      - alimenta a PROSPERIDADE (que por sua vez realimenta o comércio);
      - AMORTECE a tensão (interdependência: quem lucra com você hesita em
        atacar) — o efeito é aplicado no Conflict;
      - quando sustentado e sem atrito, cristaliza numa ALIANÇA (limiar).

    De dois gumes: a prosperidade que o comércio gera também atiça a cobiça de
    vizinhos belicosos (efeito aplicado no Conflict). Riqueza compra paz com os
    sócios e inveja dos de fora.
    """

    def step(self, world: World) -> None:
        civs = world.civs()
        self._update_trade(world, civs)
        self._update_prosperity(world, civs)
        self._form_alliances(world, civs)

    def _update_trade(self, world: World, civs: list[Civ]) -> None:
        for civ_a, civ_b in itertools.combinations(civs, 2):
            trade_level = civ_a.comercio.get(civ_b.id, 0.0)
            em_guerra = civ_b.id in civ_a.at_war_with
            if em_guerra:
                novo = decay(trade_level, 0.5)      # a guerra estrangula as rotas
            else:
                tensao = max(civ_a.tension.get(civ_b.id, 0), civ_b.tension.get(civ_a.id, 0))
                # o comércio busca um alvo: apetite mercantil + riqueza, menos
                # atrito E menos a belicosidade do par (saqueadores repelem sócios).
                alvo = clamp((civ_a.mercantilism + civ_b.mercantilism) / 2
                             + (civ_a.prosperidade + civ_b.prosperidade) / 5
                             - tensao * 0.8
                             - max(civ_a.belligerence, civ_b.belligerence) * 0.30)
                novo = clamp(blend(trade_level, alvo, 0.15))
            # graduado → evento: uma rota nasce ou se rompe ao cruzar o limiar
            if trade_level < TRADE_ROUTE_THRESHOLD <= novo:
                world.emit("rota_comercial", actors=[civ_a.id, civ_b.id],
                           volume=round(novo, 1))
            elif novo < TRADE_ROUTE_THRESHOLD <= trade_level and em_guerra:
                world.emit("comercio_rompido", actors=[civ_a.id, civ_b.id],
                           caused_by=self._war_cause(civ_a, civ_b))
            civ_a.comercio[civ_b.id] = novo
            civ_b.comercio[civ_a.id] = novo

    def _update_prosperity(self, world: World, civs: list[Civ]) -> None:
        for civ in civs:
            volume = sum(civ.comercio.values())
            alvo = clamp(2.0 + volume * 0.35 + civ.population * 0.008)
            if civ.at_war_with:
                alvo = clamp(alvo - 2.5)     # a guerra empobrece
            civ.prosperidade = clamp(blend(civ.prosperidade, alvo, 0.1))

    def _form_alliances(self, world: World, civs: list[Civ]) -> None:
        for civ_a, civ_b in itertools.combinations(civs, 2):
            trade_level = civ_a.comercio.get(civ_b.id, 0.0)
            kinship = civ_a.parentesco.get(civ_b.id, 0.0)
            aliados = civ_b.id in civ_a.allies
            tensao = max(civ_a.tension.get(civ_b.id, 0), civ_b.tension.get(civ_a.id, 0))
            em_guerra = civ_b.id in civ_a.at_war_with
            # a aliança nasce de comércio forte OU de comércio decente selado por sangue
            elegivel = (trade_level >= ALLIANCE_THRESHOLD
                        or (trade_level >= TRADE_ROUTE_THRESHOLD and kinship >= 5))
            if not aliados and not em_guerra and elegivel and tensao < PEACE_THRESHOLD + 2:
                world.emit("alianca_formada", actors=[civ_a.id, civ_b.id],
                           comercio=round(trade_level, 1), parentesco=round(kinship, 1),
                           caused_by=self._route_between(world, civ_a, civ_b))
            # a aliança só se desfaz quando comércio E sangue minguam
            elif (aliados and trade_level < ALLIANCE_END_THRESHOLD
                  and kinship < ALLIANCE_END_THRESHOLD):
                world.emit("alianca_rompida", actors=[civ_a.id, civ_b.id],
                           comercio=round(trade_level, 1))

    def _war_cause(self, civ_a: Civ, civ_b: Civ) -> tuple[int, ...]:
        gid = civ_a.war_event_by_civ.get(civ_b.id)
        return (gid,) if gid else ()

    def _route_between(self, world: World, civ_a: Civ, civ_b: Civ) -> tuple[int, ...]:
        # aponta a aliança para a rota comercial que a tornou possível
        for ev in reversed(world.log):
            if ev.kind == "rota_comercial" and set(ev.actors) == {civ_a.id, civ_b.id}:
                return (ev.id,)
        return ()
