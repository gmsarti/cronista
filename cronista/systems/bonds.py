"""Relações intra-civ."""
from __future__ import annotations

import itertools

from ..scale import blend, clamp
from ..world import World
from ._thresholds import MARRIAGE_THRESHOLD


class Bonds:
    """Relações intra-civ. Afinidade é um escalar que desliza; ao cruzar o
    limiar, vira casamento (LAÇO C)."""

    def step(self, world: World) -> None:
        rng = world.rng
        for civ in world.civs():
            vivos = [f for f in world.figures_of(civ.id) if f.spouse is None]
            rng.shuffle(vivos)
            for a, b in itertools.combinations(vivos[:8], 2):
                # afinidade puxa para a semelhança de caráter (com ruído)
                base = a.affinity.get(b.id, 5.0)
                sim = 10 - (abs(a.ambition - b.ambition) + abs(a.courage - b.courage)) / 2
                nova = clamp(blend(base, sim, 0.25) + rng.uniform(-1, 1))
                a.affinity[b.id] = nova
                b.affinity[a.id] = nova
                if (nova >= MARRIAGE_THRESHOLD
                        and a.spouse is None and b.spouse is None
                        and world.year - a.born >= 16 and world.year - b.born >= 16):
                    a.spouse, b.spouse = b.id, a.id
                    world.emit("casamento", actors=[a.id, b.id],
                               afinidade=round(nova, 1))
