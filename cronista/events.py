"""
events.py — o log é a verdade.

Um Event é imutável, datado, com atores e *pais causais*. O estado do mundo é
um fold sobre a lista de eventos; a "história" nunca é gravada — ela emerge
quando se lê o log de volta e se seguem as arestas `caused_by`.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(frozen=True)
class Event:
    id: int
    year: int
    kind: str                      # "nascimento", "guerra_declarada", "batalha"...
    actors: tuple[int, ...] = ()   # ids de figuras/civs envolvidas
    site: int | None = None
    caused_by: tuple[int, ...] = ()  # ids de eventos anteriores → grafo causal
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["actors"] = list(self.actors)
        d["caused_by"] = list(self.caused_by)
        return d
