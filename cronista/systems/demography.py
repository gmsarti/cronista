"""Nascimento (via casais), envelhecimento e morte."""
from __future__ import annotations

from ..entities import Civ, Figure
from ..scale import blend, clamp
from ..world import World
from ._names import _random_name


class Demography:
    """Nascimento (via casais), envelhecimento e morte. Escalar-chave: idade
    empurra a probabilidade de morte; renome e valor não protegem para sempre."""

    MAX_NOTAVEIS_POR_CIV = 14

    def step(self, world: World) -> None:
        rng = world.rng
        # mortes naturais: prob cresce com a idade
        for f in world.figures():
            idade = world.year - f.born
            death_prob = 0.002 + max(0, idade - 45) * 0.010
            if idade > 80:
                death_prob += 0.08
            if rng.random() < min(death_prob, 0.9):
                world.emit("morte", actors=[f.id], causa="idade", idade=idade,
                           renome=round(f.renown, 1))

        # nascimentos: casais com afinidade consolidada geram herdeiros
        for civ in world.civs():
            vivos = world.figures_of(civ.id)
            if len(vivos) >= self.MAX_NOTAVEIS_POR_CIV:
                continue
            for f in vivos:
                if f.spouse is None:
                    continue
                mae = world.get(f.spouse)
                if not (isinstance(mae, Figure) and mae.alive):
                    continue
                if f.id > mae.id:  # cada casal considerado uma vez
                    continue
                if world.year - f.born > 55 or world.year - mae.born > 50:
                    continue
                if rng.random() < 0.10:
                    self._nascer(world, civ, f, mae)

    def _nascer(self, world: World, civ: Civ, p1: Figure, p2: Figure) -> None:
        rng = world.rng
        child = Figure(
            id=world.new_id(),
            name=_random_name(rng),
            born=world.year,
            civ=civ.id,
            ambition=clamp(blend(p1.ambition, p2.ambition, 0.5) + rng.uniform(-2, 2)),
            courage=clamp(blend(p1.courage, p2.courage, 0.5) + rng.uniform(-2, 2)),
            cunning=clamp(blend(p1.cunning, p2.cunning, 0.5) + rng.uniform(-2, 2)),
            parents=(p1.id, p2.id),
        )
        # LAÇO A (herança de rancor): a criança nasce carregando parte das
        # mágoas dos pais — graduada, não copiada inteira.
        for alvo, r in {**p1.grudges, **p2.grudges}.items():
            herdado = 0.6 * max(p1.grudges.get(alvo, 0), p2.grudges.get(alvo, 0))
            if herdado > 0.5:
                child.grudges[alvo] = clamp(herdado)
        world.add(child)
        p1.children.append(child.id)
        p2.children.append(child.id)
        world.emit("nascimento", actors=[child.id, p1.id, p2.id],
                   name=child.name)
