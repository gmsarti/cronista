"""
systems.py — os motores da simulação.

Cada sistema tem `step(world)` e propõe eventos via `world.emit(...)`. Nenhum
sistema muta o estado diretamente. Toda decisão nasce de um escalar [0,10]:
os traços enviesam probabilidades, os acumuladores (rancor, tensão) sobem e
descem, e os *limiares* convertem gradação contínua em evento discreto.

Laços de realimentação embutidos:
  A) morte em batalha  → rancor herdado pela linhagem → tensão entre civs
                       → nova guerra → mais mortes.  (o motor trágico)
  B) feito glorioso    → renome → artefato → cobiça (tensão) → roubo → guerra.
  C) afinidade alta    → casamento → nascimento → nova figura (natalidade).
"""
from __future__ import annotations

import itertools
from typing import Protocol

from .entities import Artifact, Civ, Figure
from .scale import blend, clamp, decay
from .world import World

# ---- limiares (a "física" do mundo; graduado → evento) -----------------
MARRIAGE_THRESHOLD = 7.5       # afinidade acima disso → casam
WAR_THRESHOLD = 7.5            # tensão acima disso → guerra declarada
PEACE_THRESHOLD = 3.0          # tensão abaixo disso (ou exaustão alta) → paz
ARTIFACT_THRESHOLD = 8.0       # renome*habilidade acima disso → forja
THEFT_THRESHOLD = 6.5          # tensão + fama do artefato → tentativa de roubo
TRADE_ROUTE_THRESHOLD = 5.0    # comércio acima disso → rota comercial estabelecida
ALLIANCE_THRESHOLD = 8.0       # comércio sustentado + baixa tensão → aliança
ALLIANCE_END_THRESHOLD = 3.5   # comércio abaixo disso → aliança se desfaz

# aliases de compatibilidade — importados por tests/ (não remover sem atualizar os testes)
LIMIAR_GUERRA = WAR_THRESHOLD
LIMIAR_ROTA = TRADE_ROUTE_THRESHOLD
LIMIAR_ALIANCA = ALLIANCE_THRESHOLD


_SILABAS = ["mor", "dun", "kaz", "thal", "bre", "gol", "sef", "vint", "urd",
            "lok", "myr", "gru", "nes", "tor", "quel", "bram", "od", "sil"]
_EPITETOS = ["o Firme", "de Ferro", "o Sombrio", "Punho-Longo", "a Astuta",
             "o Rancoroso", "Olhos-de-Brasa", "o Prudente", "Mão-Torta",
             "a Indômita", "Coração-de-Pedra", "o Tecelão"]


def _random_name(rng) -> str:
    n_syllables = rng.randint(2, 3)
    return "".join(rng.choice(_SILABAS) for _ in range(n_syllables)).capitalize()


class System(Protocol):
    def step(self, world: World) -> None: ...


# ------------------------------------------------------------------------
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


# ------------------------------------------------------------------------
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


# ------------------------------------------------------------------------
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


# ------------------------------------------------------------------------
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


# ------------------------------------------------------------------------
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


# ------------------------------------------------------------------------
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
