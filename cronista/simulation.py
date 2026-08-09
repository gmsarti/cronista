"""
simulation.py — o driver.

Semeia o mundo, cria as civilizações fundadoras e roda o loop anual:
para cada ano, cada sistema propõe eventos. Determinístico: a mesma seed
produz exatamente o mesmo log.
"""
from __future__ import annotations

from .entities import Civ, Figure, Site
from .scale import clamp
from .systems import Bonds, Conflict, Demography, Dynasty, Renown, Trade, _random_name
from .world import World

_CIV_NAMES = ["Casa de Bramgol", "Clã Thalvint", "Reino de Kazmyr",
              "Aliança de Nesod", "Ducado de Urdlok"]


def seed_world(world: World, n_civs: int, figures_per_civ: int) -> None:
    rng = world.rng
    for i in range(n_civs):
        site = world.add(Site(id=world.new_id(),
                              name="Fortaleza " + _random_name(rng)))
        # temperament em [0,1]: perto de 0 → mercador, perto de 1 → saqueador.
        # belligerence e mercantilism saem daqui (anti-correlacionados, com ruído),
        # de modo que cada civ nasce um arquétipo — mas nada é rígido.
        temperament = rng.random()
        belligerence = clamp(1 + 9 * temperament + rng.uniform(-1.5, 1.5))
        mercantilism = clamp(1 + 9 * (1 - temperament) + rng.uniform(-1.5, 1.5))
        civ = world.add(Civ(
            id=world.new_id(),
            name=_CIV_NAMES[i % len(_CIV_NAMES)],
            site=site.id,
            population=rng.uniform(80, 160),
            belligerence=belligerence,
            mercantilism=mercantilism,
            prosperidade=clamp(rng.uniform(3, 6)),
        ))
        for _ in range(figures_per_civ):
            world.add(Figure(
                id=world.new_id(),
                name=_random_name(rng),
                born=-rng.randint(16, 40),   # já adultos na fundação
                civ=civ.id,
                ambition=clamp(rng.uniform(1, 10)),
                courage=clamp(rng.uniform(1, 10)),
                cunning=clamp(rng.uniform(1, 10)),
                renown=clamp(rng.uniform(1, 4)),
            ))


def simulate(
    seed: int = 42,
    years: int = 180,
    n_civs: int = 5,
    figures_per_civ: int = 6,
) -> World:
    world = World(seed=seed)
    seed_world(world, n_civs, figures_per_civ)
    systems = [Demography(), Bonds(), Renown(), Trade(), Dynasty(), Conflict()]
    for year in range(years):
        world.year = year
        for system in systems:
            system.step(world)
    return world
