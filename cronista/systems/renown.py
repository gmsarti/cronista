"""Feitos → renome → artefatos (LAÇO B, primeira metade)."""
from __future__ import annotations

from ..entities import Artifact
from ..scale import clamp
from ..world import World
from ._names import _random_name
from ._thresholds import ARTIFACT_THRESHOLD


class Renown:
    """Feitos → renome → artefatos (LAÇO B, primeira metade)."""

    def step(self, world: World) -> None:
        rng = world.rng
        for figure in world.figures():
            # ambição corrói/eleva o renome lentamente; feitos vêm de batalhas
            figure.renown = clamp(figure.renown + rng.uniform(-0.1, 0.15) + figure.ambition * 0.01)
            potencial = (figure.renown + figure.cunning) / 2
            if potencial >= ARTIFACT_THRESHOLD and rng.random() < 0.05:
                art = Artifact(
                    id=world.new_id(),
                    name="o " + _random_name(rng),
                    forged=world.year,
                    creator=figure.id,
                    civ=figure.civ,
                    fame=clamp(potencial + rng.uniform(-1, 1)),
                    holder_civ=figure.civ,
                )
                world.add(art)
                figure.renown = clamp(figure.renown + 1.0)
                world.emit("artefato_forjado", actors=[figure.id],
                           artifact=art.id, name=art.name,
                           fama=round(art.fame, 1))
