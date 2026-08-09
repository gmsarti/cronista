"""
simulation.py — o driver.

Semeia o mundo, cria as civilizações fundadoras e roda o loop anual:
para cada ano, cada sistema propõe eventos. Determinístico: a mesma seed
produz exatamente o mesmo log.
"""
from __future__ import annotations

from .entities import Civ, Figure, Site
from .scale import clamp
from .systems import Bonds, Conflict, Demography, Dynasty, Renown, Trade, _nome_proprio
from .world import World

_CIV_NOMES = ["Casa de Bramgol", "Clã Thalvint", "Reino de Kazmyr",
              "Aliança de Nesod", "Ducado de Urdlok"]


def seed_world(world: World, n_civs: int, figuras_por_civ: int) -> None:
    rng = world.rng
    for i in range(n_civs):
        site = world.add(Site(id=world.new_id(),
                              name="Fortaleza " + _nome_proprio(rng)))
        # temperamento em [0,1]: perto de 0 → mercador, perto de 1 → saqueador.
        # belicosidade e mercantilismo saem daqui (anti-correlacionados, com ruído),
        # de modo que cada civ nasce um arquétipo — mas nada é rígido.
        temperamento = rng.random()
        belic = clamp(1 + 9 * temperamento + rng.uniform(-1.5, 1.5))
        merc = clamp(1 + 9 * (1 - temperamento) + rng.uniform(-1.5, 1.5))
        civ = world.add(Civ(
            id=world.new_id(),
            name=_CIV_NOMES[i % len(_CIV_NOMES)],
            site=site.id,
            populacao=rng.uniform(80, 160),
            belicosidade=belic,
            mercantilismo=merc,
            prosperidade=clamp(rng.uniform(3, 6)),
        ))
        for _ in range(figuras_por_civ):
            world.add(Figure(
                id=world.new_id(),
                name=_nome_proprio(rng),
                born=-rng.randint(16, 40),   # já adultos na fundação
                civ=civ.id,
                ambicao=clamp(rng.uniform(1, 10)),
                valor=clamp(rng.uniform(1, 10)),
                astucia=clamp(rng.uniform(1, 10)),
                renome=clamp(rng.uniform(1, 4)),
            ))


def simulate(
    seed: int = 42,
    years: int = 180,
    n_civs: int = 5,
    figuras_por_civ: int = 6,
) -> World:
    world = World(seed=seed)
    seed_world(world, n_civs, figuras_por_civ)
    systems = [Demography(), Bonds(), Renown(), Trade(), Dynasty(), Conflict()]
    for year in range(years):
        world.year = year
        for system in systems:
            system.step(world)
    return world
