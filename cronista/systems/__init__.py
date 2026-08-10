"""
systems — os motores da simulação.

Cada sistema tem `step(world)` e propõe eventos via `world.emit(...)`. Nenhum
sistema muta o estado diretamente. Toda decisão nasce de um escalar [0,10]:
os traços enviesam probabilidades, os acumuladores (rancor, tensão) sobem e
descem, e os *limiares* convertem gradação contínua em evento discreto.

Laços de realimentação embutidos:
  A) morte em batalha  → rancor herdado pela linhagem → tensão entre civs
                       → nova guerra → mais mortes.  (o motor trágico)
  B) feito glorioso    → renome → artefato → cobiça (tensão) → roubo → guerra.
  C) afinidade alta    → casamento → nascimento → nova figura (natalidade).

Um sistema por arquivo: demography, bonds, renown, trade, dynasty, conflict.
"""
from __future__ import annotations

from typing import Protocol

from ..world import World
from ._names import _random_name
from ._thresholds import (
    ALLIANCE_END_THRESHOLD,
    ALLIANCE_THRESHOLD,
    ARTIFACT_THRESHOLD,
    LIMIAR_ALIANCA,
    LIMIAR_GUERRA,
    LIMIAR_ROTA,
    MARRIAGE_THRESHOLD,
    PEACE_THRESHOLD,
    THEFT_THRESHOLD,
    TRADE_ROUTE_THRESHOLD,
    WAR_THRESHOLD,
)
from .bonds import Bonds
from .conflict import Conflict
from .demography import Demography
from .dynasty import Dynasty
from .renown import Renown
from .trade import Trade


class System(Protocol):
    def step(self, world: World) -> None: ...


__all__ = [
    "System",
    "Demography",
    "Bonds",
    "Renown",
    "Trade",
    "Dynasty",
    "Conflict",
    "_random_name",
    "MARRIAGE_THRESHOLD",
    "WAR_THRESHOLD",
    "PEACE_THRESHOLD",
    "ARTIFACT_THRESHOLD",
    "THEFT_THRESHOLD",
    "TRADE_ROUTE_THRESHOLD",
    "ALLIANCE_THRESHOLD",
    "ALLIANCE_END_THRESHOLD",
    "LIMIAR_GUERRA",
    "LIMIAR_ROTA",
    "LIMIAR_ALIANCA",
]
