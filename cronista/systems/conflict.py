"""O motor trágico: tensão, guerra, batalha, rancor e paz."""
from __future__ import annotations

import itertools

from ..entities import Civ, Figure
from ..scale import clamp, decay
from ..world import World
from ._thresholds import PEACE_THRESHOLD, THEFT_THRESHOLD, WAR_THRESHOLD


class Conflict:
    """O motor trágico. Tensão entre civs acumula de rancores, belicosidade e
    cobiça por artefatos; ao cruzar WAR_THRESHOLD vira guerra. A guerra gera
    batalhas → mortes → NOVOS rancores → mais tensão (LAÇO A fecha aqui).
    A exaustão e o decaimento puxam de volta para a paz."""

    def step(self, world: World) -> None:
        civs = world.civs()
        self._accumulate_tension(world, civs)
        self._maybe_theft(world, civs)       # LAÇO B, segunda metade
        self._maybe_betrayal(world, civs)    # ruptura do sangue (rara, trágica)
        self._declare_wars(world, civs)
        self._wage_battles(world, civs)
        self._maybe_peace(world, civs)

    # -- tensão sobe e desce ---------------------------------------------
    def _accumulate_tension(self, world: World, civs: list[Civ]) -> None:
        for civ_a, civ_b in itertools.permutations(civs, 2):
            tension_level = civ_a.tension.get(civ_b.id, 0.0)
            vivos = world.figures_of(civ_a.id)
            # pressão de rancor: soma dos rancores dos vivos de civ_a contra civ_b
            rancor = sum(f.grudges.get(civ_b.id, 0) for f in vivos)
            # a faísca inicial: um líder ambicioso numa civ belicosa começa
            # guerras mesmo sem histórico de sangue.
            ambicao_lider = max((f.ambition for f in vivos), default=0.0)
            # cobiça: a riqueza do vizinho tenta os belicosos (comércio de 2 gumes)
            inveja = 0.02 * civ_b.prosperidade * (civ_a.belligerence / 10)
            # interdependência: o que se lucra com civ_b desestimula atacá-lo
            laco = 0.06 * civ_a.comercio.get(civ_b.id, 0.0)
            # sangue prende mais que dinheiro: o parentesco amortece mais forte
            sangue = 0.09 * civ_a.parentesco.get(civ_b.id, 0.0)
            pressao = (0.045 * civ_a.belligerence
                       + 0.006 * ambicao_lider
                       + 0.015 * min(rancor, 30)
                       + inveja
                       - laco
                       - sangue)
            if civ_b.id in civ_a.at_war_with:
                pressao += 0.3
            tension_level = clamp(tension_level + pressao)
            tension_level = decay(tension_level, 0.04)      # tudo esfria um pouco a cada ano
            civ_a.tension[civ_b.id] = tension_level

    # -- LAÇO B: cobiça por artefato vira roubo, que reacende a tensão ----
    def _maybe_betrayal(self, world: World, civs: list[Civ]) -> None:
        """A ruptura do sangue: um nobre ambicioso demais rompe a aliança e
        ataca os próprios sogros por poder. Rara — a mais escura das guerras,
        e a que gera as mágoas mais fundas. É movida pelo indivíduo: basta uma
        alma ambiciosa o bastante numa casa ligada por sangue a outra."""
        rng = world.rng
        for civ_a in civs:
            for ally_id in list(civ_a.allies):
                civ_b = world.get(ally_id)
                if not isinstance(civ_b, Civ):
                    continue
                if civ_a.parentesco.get(ally_id, 0) < 3:
                    continue          # é preciso haver sangue para traí-lo
                vivos = world.figures_of(civ_a.id)
                traidor = max(vivos, key=lambda f: f.ambition, default=None)
                if traidor is None or traidor.ambition < 8:
                    continue
                # a probabilidade cresce com a ambição do traidor e a belicosidade da casa
                prob = 0.016 * (traidor.ambition / 10) * (0.5 + civ_a.belligerence / 20)
                if rng.random() < prob:
                    world.emit("alianca_rompida", actors=[civ_a.id, ally_id],
                               comercio=round(civ_a.comercio.get(ally_id, 0), 1),
                               motivo="traição")
                    ev = world.emit("guerra_declarada", actors=[civ_a.id, ally_id],
                                    actor_traidor=traidor.id,
                                    traidor_nome=traidor.name,
                                    tensao=9.0, motivo="traição")
                    # o sangue rompido incendeia a tensão e apaga o parentesco,
                    # senão a guerra faria as pazes antes da primeira batalha.
                    civ_a.tension[ally_id] = 9.0
                    civ_b.tension[civ_a.id] = 9.0
                    civ_a.parentesco[ally_id] = clamp(civ_a.parentesco.get(ally_id, 0) * 0.1)
                    civ_b.parentesco[civ_a.id] = clamp(civ_b.parentesco.get(civ_a.id, 0) * 0.1)
                    self._drag_allies_in(world, civ_a, civ_b, ev)

    # -- LAÇO B: cobiça por artefato vira roubo, que reacende a tensão ----
    def _maybe_theft(self, world: World, civs: list[Civ]) -> None:
        rng = world.rng
        for art in world.artifacts():
            dono = art.holder_civ
            if dono is None:
                continue
            for civ_b in civs:
                if civ_b.id == dono:
                    continue
                cobica = (civ_b.tension.get(dono, 0) + art.fame) / 2
                if cobica >= THEFT_THRESHOLD and rng.random() < 0.03:
                    ev = world.emit("artefato_roubado", actors=[civ_b.id, dono],
                                    artifact=art.id, thief_civ=civ_b.id,
                                    name=art.name)
                    # o roubo é uma afronta: injeta tensão nos dois sentidos
                    d = world.get(dono)
                    d.tension[civ_b.id] = clamp(d.tension.get(civ_b.id, 0) + 3.5)
                    self._sow_grudge(world, victim_civ=dono, enemy_civ=civ_b.id,
                                        weight=2.0, cause=ev.id)
                    break

    # -- graduado → evento: declaração de guerra -------------------------
    def _declare_wars(self, world: World, civs: list[Civ]) -> None:
        for civ_a, civ_b in itertools.combinations(civs, 2):
            if civ_b.id in civ_a.at_war_with:
                continue
            if civ_b.id in civ_a.allies:
                continue                      # aliados não se atacam
            tension_level = max(civ_a.tension.get(civ_b.id, 0), civ_b.tension.get(civ_a.id, 0))
            if tension_level >= WAR_THRESHOLD:
                causas = self._grudge_events(world, civ_a, civ_b)
                ev = world.emit("guerra_declarada", actors=[civ_a.id, civ_b.id],
                                caused_by=causas, tensao=round(tension_level, 1))
                self._drag_allies_in(world, civ_a, civ_b, ev)

    def _drag_allies_in(self, world: World, civ_a: Civ, civ_b: Civ, guerra) -> None:
        """LAÇO do bloco: um aliado leal pode ser arrastado para a guerra do
        parceiro. A lealdade é graduada pelo volume de comércio; a probabilidade
        vem daí. É o que transforma rixas bilaterais em guerras de bloco."""
        rng = world.rng
        atacado, agressor = civ_b, civ_a
        for aliado_id in list(atacado.allies):
            aliado = world.get(aliado_id)
            if not isinstance(aliado, Civ):
                continue
            if agressor.id in (aliado.allies | aliado.at_war_with):
                continue
            if aliado.id == agressor.id:
                continue
            lealdade = aliado.comercio.get(atacado.id, 0.0)   # [0,10]
            if rng.random() < lealdade / 15.0:                # até ~67% se comércio máximo
                world.emit("guerra_declarada", actors=[aliado.id, agressor.id],
                           caused_by=[guerra.id], tensao=8.5,
                           motivo="aliança")
                # a entrada na guerra vem com atrito real, senão a paz vem já
                aliado.tension[agressor.id] = max(aliado.tension.get(agressor.id, 0), 8.5)
                agressor.tension[aliado.id] = max(agressor.tension.get(aliado.id, 0), 8.5)

    def _wage_battles(self, world: World, civs: list[Civ]) -> None:
        rng = world.rng
        vistos: set[frozenset] = set()
        for civ_a in civs:
            for enemy_id in list(civ_a.at_war_with):
                par = frozenset((civ_a.id, enemy_id))
                if par in vistos:
                    continue
                vistos.add(par)
                civ_b = world.get(enemy_id)
                if not isinstance(civ_b, Civ):
                    continue
                if rng.random() < 0.55:
                    self._fight_battle(world, civ_a, civ_b)
                    civ_a.exhaustion = clamp(civ_a.exhaustion + rng.uniform(0.5, 1.5))
                    civ_b.exhaustion = clamp(civ_b.exhaustion + rng.uniform(0.5, 1.5))

    def _fight_battle(self, world: World, civ_a: Civ, civ_b: Civ) -> None:
        rng = world.rng
        strength_a = self._military_strength(world, civ_a)
        strength_b = self._military_strength(world, civ_b)
        total = strength_a + strength_b + 1e-6
        # vencedor probabilístico, proporcional à força (não determinístico-duro)
        vencedor, perdedor = (civ_a, civ_b) if rng.random() < strength_a / total else (civ_b, civ_a)
        margem = abs(strength_a - strength_b) / total   # [0,1], quão decisiva
        # baixas na plebe do perdedor, graduadas pela margem
        baixas = clamp(2 + margem * 6)
        perdedor.population = max(10.0, perdedor.population - baixas * 3)
        # a batalha aponta causalmente para a guerra que a gerou
        guerra_id = civ_a.war_event_by_civ.get(civ_b.id)
        causa_guerra = [guerra_id] if guerra_id else []

        mortos = []
        for f in world.figures_of(perdedor.id):
            # figuras de baixo valor caem primeiro; alto valor resiste
            risco = 0.05 + margem * 0.10 - f.courage * 0.004
            if rng.random() < max(0.01, risco):
                mortos.append(f)

        ev = world.emit("batalha", actors=[vencedor.id, perdedor.id],
                        caused_by=causa_guerra,
                        vencedor=vencedor.id, margem=round(margem, 2),
                        baixas=round(baixas, 1),
                        mortos=[m.id for m in mortos])

        # renome para um algoz do lado vencedor
        vivos_venc = world.figures_of(vencedor.id)
        algoz = max(vivos_venc, key=lambda x: x.courage, default=None)
        if algoz:
            algoz.renown = clamp(algoz.renown + 0.5 + margem)

        # LAÇO A: cada morte semeia rancor na linhagem/civ do morto
        for m in mortos:
            # traição de sangue: o morto tem parentes vivos na civ que o matou —
            # cônjuge, pai/mãe ou filho, frutos de uniões dinásticas. Tombar pela
            # mão do próprio sangue é a mais funda das mágoas.
            traicao = self._has_kin_in(world, m, vencedor.id)
            world.emit("morte", actors=[m.id], causa="batalha",
                       caused_by=[ev.id], contra=vencedor.id,
                       renome=round(m.renown, 1), traicao=bool(traicao))
            weight = 1.0 + m.renown * 0.15
            if traicao:
                perdedor.parentesco[vencedor.id] = clamp(
                    perdedor.parentesco.get(vencedor.id, 0) * 0.2)
                vencedor.parentesco[perdedor.id] = clamp(
                    vencedor.parentesco.get(perdedor.id, 0) * 0.2)
                weight *= 2.0          # a mágoa do fratricídio é redobrada
            self._sow_grudge(world, victim_civ=perdedor.id,
                                enemy_civ=vencedor.id,
                                weight=weight, cause=ev.id, focus=m)

    # -- paz: quando a tensão esfria ou a exaustão pesa demais -----------
    def _maybe_peace(self, world: World, civs: list[Civ]) -> None:
        vistos: set[frozenset] = set()
        for civ_a in civs:
            for enemy_id in list(civ_a.at_war_with):
                par = frozenset((civ_a.id, enemy_id))
                if par in vistos:
                    continue
                vistos.add(par)
                civ_b = world.get(enemy_id)
                if not isinstance(civ_b, Civ):
                    continue
                tension_level = max(civ_a.tension.get(enemy_id, 0), civ_b.tension.get(civ_a.id, 0))
                cansaco = max(civ_a.exhaustion, civ_b.exhaustion)
                if tension_level <= PEACE_THRESHOLD or cansaco >= 8.5:
                    world.emit("paz", actors=[civ_a.id, civ_b.id],
                               tensao=round(tension_level, 1), exaustao=round(cansaco, 1))

    # -- utilitários ------------------------------------------------------
    def _has_kin_in(self, world: World, figura: Figure, civ_id: int) -> bool:
        """A figura tem parente próximo vivo na civ dada? (cônjuge, pai/mãe, filho)"""
        proximos = list(figura.parents) + list(figura.children)
        if figura.spouse is not None:
            proximos.append(figura.spouse)
        for pid in proximos:
            p = world.get(pid)
            if isinstance(p, Figure) and p.alive and p.civ == civ_id:
                return True
        return False

    def _military_strength(self, world: World, civ: Civ) -> float:
        return (civ.population * 0.1
                + civ.prosperidade * 1.5          # riqueza equipa tropas
                + sum(f.courage for f in world.figures_of(civ.id)))

    def _sow_grudge(self, world, victim_civ, enemy_civ, weight, cause, focus=None):
        alvos = world.figures_of(victim_civ)
        if focus is not None:
            # parentes do morto guardam rancor mais forte
            parentes = set(focus.children) | set(focus.parents)
            if focus.spouse:
                parentes.add(focus.spouse)
        else:
            parentes = set()
        for f in alvos:
            base = f.grudges.get(enemy_civ, 0.0)
            ganho = weight * (2.0 if f.id in parentes else 0.4)
            f.grudges[enemy_civ] = clamp(base + ganho)

    def _grudge_events(self, world, civ_a, civ_b, window=40, max_count=3):
        # amarra a declaração de guerra às mortes recentes que a motivaram.
        # O rancor que acende a guerra pode estar de QUALQUER um dos dois lados.
        def rancor_de(civ, alvo):
            return max((f.grudges.get(alvo.id, 0) for f in world.figures_of(civ.id)),
                       default=0.0)

        limite_ano = world.year - window
        causas = []
        # se civ_a guarda rancor de civ_b, as mortes de gente de civ_a pela mão de civ_b contam
        for atacante, vitima in ((civ_a, civ_b), (civ_b, civ_a)):
            if rancor_de(atacante, vitima) > 4:
                for ev in reversed(world.log):
                    if ev.year < limite_ano:
                        break
                    if (ev.kind == "morte"
                            and ev.data.get("causa") == "batalha"
                            and ev.data.get("contra") == vitima.id):
                        causas.append(ev.id)
                    if len(causas) >= max_count:
                        break
        return tuple(sorted(set(causas)))
