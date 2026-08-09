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
LIMIAR_CASAMENTO = 7.5      # afinidade acima disso → casam
LIMIAR_GUERRA = 7.5         # tensão acima disso → guerra declarada
LIMIAR_PAZ = 3.0            # tensão abaixo disso (ou exaustão alta) → paz
LIMIAR_ARTEFATO = 8.0       # renome*habilidade acima disso → forja
LIMIAR_ROUBO = 6.5          # tensão + fama do artefato → tentativa de roubo
LIMIAR_ROTA = 5.0           # comércio acima disso → rota comercial estabelecida
LIMIAR_ALIANCA = 8.0        # comércio sustentado + baixa tensão → aliança
LIMIAR_FIM_ALIANCA = 3.5    # comércio abaixo disso → aliança se desfaz


_SILABAS = ["mor", "dun", "kaz", "thal", "bre", "gol", "sef", "vint", "urd",
            "lok", "myr", "gru", "nes", "tor", "quel", "bram", "od", "sil"]
_EPITETOS = ["o Firme", "de Ferro", "o Sombrio", "Punho-Longo", "a Astuta",
             "o Rancoroso", "Olhos-de-Brasa", "o Prudente", "Mão-Torta",
             "a Indômita", "Coração-de-Pedra", "o Tecelão"]


def _nome_proprio(rng) -> str:
    n = rng.randint(2, 3)
    return "".join(rng.choice(_SILABAS) for _ in range(n)).capitalize()


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
            p = 0.002 + max(0, idade - 45) * 0.010
            if idade > 80:
                p += 0.08
            if rng.random() < min(p, 0.9):
                world.emit("morte", actors=[f.id], causa="idade", idade=idade,
                           renome=round(f.renome, 1))

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
            name=_nome_proprio(rng),
            born=world.year,
            civ=civ.id,
            ambicao=clamp(blend(p1.ambicao, p2.ambicao, 0.5) + rng.uniform(-2, 2)),
            valor=clamp(blend(p1.valor, p2.valor, 0.5) + rng.uniform(-2, 2)),
            astucia=clamp(blend(p1.astucia, p2.astucia, 0.5) + rng.uniform(-2, 2)),
            parents=(p1.id, p2.id),
        )
        # LAÇO A (herança de rancor): a criança nasce carregando parte das
        # mágoas dos pais — graduada, não copiada inteira.
        for alvo, r in {**p1.rancor, **p2.rancor}.items():
            herdado = 0.6 * max(p1.rancor.get(alvo, 0), p2.rancor.get(alvo, 0))
            if herdado > 0.5:
                child.rancor[alvo] = clamp(herdado)
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
                base = a.afinidade.get(b.id, 5.0)
                sim = 10 - (abs(a.ambicao - b.ambicao) + abs(a.valor - b.valor)) / 2
                nova = clamp(blend(base, sim, 0.25) + rng.uniform(-1, 1))
                a.afinidade[b.id] = nova
                b.afinidade[a.id] = nova
                if (nova >= LIMIAR_CASAMENTO
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
        for f in world.figures():
            # ambição corrói/eleva o renome lentamente; feitos vêm de batalhas
            f.renome = clamp(f.renome + rng.uniform(-0.1, 0.15) + f.ambicao * 0.01)
            potencial = (f.renome + f.astucia) / 2
            if potencial >= LIMIAR_ARTEFATO and rng.random() < 0.05:
                art = Artifact(
                    id=world.new_id(),
                    name="o " + _nome_proprio(rng),
                    forged=world.year,
                    creator=f.id,
                    civ=f.civ,
                    fama=clamp(potencial + rng.uniform(-1, 1)),
                    holder_civ=f.civ,
                )
                world.add(art)
                f.renome = clamp(f.renome + 1.0)
                world.emit("artefato_forjado", actors=[f.id],
                           artifact=art.id, name=art.name,
                           fama=round(art.fama, 1))


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
        self._mover_comercio(world, civs)
        self._atualizar_prosperidade(world, civs)
        self._formar_alliancas(world, civs)

    def _mover_comercio(self, world: World, civs: list[Civ]) -> None:
        for ca, cb in itertools.combinations(civs, 2):
            c = ca.comercio.get(cb.id, 0.0)
            em_guerra = cb.id in ca.em_guerra_com
            if em_guerra:
                novo = decay(c, 0.5)      # a guerra estrangula as rotas
            else:
                tensao = max(ca.tensao.get(cb.id, 0), cb.tensao.get(ca.id, 0))
                # o comércio busca um alvo: apetite mercantil + riqueza, menos
                # atrito E menos a belicosidade do par (saqueadores repelem sócios).
                alvo = clamp((ca.mercantilismo + cb.mercantilismo) / 2
                             + (ca.prosperidade + cb.prosperidade) / 5
                             - tensao * 0.8
                             - max(ca.belicosidade, cb.belicosidade) * 0.30)
                novo = clamp(blend(c, alvo, 0.15))
            # graduado → evento: uma rota nasce ou se rompe ao cruzar o limiar
            if c < LIMIAR_ROTA <= novo:
                world.emit("rota_comercial", actors=[ca.id, cb.id],
                           volume=round(novo, 1))
            elif novo < LIMIAR_ROTA <= c and em_guerra:
                world.emit("comercio_rompido", actors=[ca.id, cb.id],
                           caused_by=self._causa_guerra(ca, cb))
            ca.comercio[cb.id] = novo
            cb.comercio[ca.id] = novo

    def _atualizar_prosperidade(self, world: World, civs: list[Civ]) -> None:
        for civ in civs:
            volume = sum(civ.comercio.values())
            alvo = clamp(2.0 + volume * 0.35 + civ.populacao * 0.008)
            if civ.em_guerra_com:
                alvo = clamp(alvo - 2.5)     # a guerra empobrece
            civ.prosperidade = clamp(blend(civ.prosperidade, alvo, 0.1))

    def _formar_alliancas(self, world: World, civs: list[Civ]) -> None:
        for ca, cb in itertools.combinations(civs, 2):
            c = ca.comercio.get(cb.id, 0.0)
            paren = ca.parentesco.get(cb.id, 0.0)
            aliados = cb.id in ca.aliados
            tensao = max(ca.tensao.get(cb.id, 0), cb.tensao.get(ca.id, 0))
            em_guerra = cb.id in ca.em_guerra_com
            # a aliança nasce de comércio forte OU de comércio decente selado por sangue
            elegivel = c >= LIMIAR_ALIANCA or (c >= LIMIAR_ROTA and paren >= 5)
            if not aliados and not em_guerra and elegivel and tensao < LIMIAR_PAZ + 2:
                world.emit("alianca_formada", actors=[ca.id, cb.id],
                           comercio=round(c, 1), parentesco=round(paren, 1),
                           caused_by=self._rota_entre(world, ca, cb))
            # a aliança só se desfaz quando comércio E sangue minguam
            elif aliados and c < LIMIAR_FIM_ALIANCA and paren < LIMIAR_FIM_ALIANCA:
                world.emit("alianca_rompida", actors=[ca.id, cb.id],
                           comercio=round(c, 1))

    def _causa_guerra(self, ca: Civ, cb: Civ) -> tuple[int, ...]:
        gid = ca.guerra_evento.get(cb.id)
        return (gid,) if gid else ()

    def _rota_entre(self, world: World, ca: Civ, cb: Civ) -> tuple[int, ...]:
        # aponta a aliança para a rota comercial que a tornou possível
        for ev in reversed(world.log):
            if ev.kind == "rota_comercial" and set(ev.actors) == {ca.id, cb.id}:
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
        for ca, cb in itertools.combinations(civs, 2):
            # o sangue esfria devagar se não for renovado
            if ca.parentesco.get(cb.id):
                p = decay(ca.parentesco[cb.id], 0.01)
                ca.parentesco[cb.id] = p
                cb.parentesco[ca.id] = p
            if cb.id in ca.em_guerra_com:
                continue
            com = ca.comercio.get(cb.id, 0.0)
            tensao = max(ca.tensao.get(cb.id, 0), cb.tensao.get(ca.id, 0))
            paren = ca.parentesco.get(cb.id, 0.0)
            # casa-se quando há comércio forte, pouca tensão e o laço não está
            # saturado; a probabilidade é graduada pelo próprio comércio.
            if com >= LIMIAR_ROTA and tensao < LIMIAR_PAZ + 2 and paren < 8:
                prob = 0.04 * (com / 10) * (1 - paren / 10)
                if world.rng.random() < prob:
                    self._casar(world, ca, cb)

    def _casar(self, world: World, ca: Civ, cb: Civ) -> None:
        na, nb = self._melhor_solteiro(world, ca), self._melhor_solteiro(world, cb)
        if not na or not nb:
            return
        world.emit("casamento_dinastico", actors=[na.id, nb.id],
                   civs=[ca.id, cb.id],
                   noivos=[na.name, nb.name],
                   caused_by=self._rota_entre(world, ca, cb))

    def _melhor_solteiro(self, world: World, civ: Civ):
        cand = [f for f in world.figures_of(civ.id)
                if f.spouse is None and world.year - f.born >= 16]
        # o de maior renome faz o melhor par diplomático
        return max(cand, key=lambda f: f.renome, default=None)

    def _rota_entre(self, world: World, ca: Civ, cb: Civ) -> tuple[int, ...]:
        for ev in reversed(world.log):
            if ev.kind == "rota_comercial" and set(ev.actors) == {ca.id, cb.id}:
                return (ev.id,)
        return ()


# ------------------------------------------------------------------------
class Conflict:
    """O motor trágico. Tensão entre civs acumula de rancores, belicosidade e
    cobiça por artefatos; ao cruzar LIMIAR_GUERRA vira guerra. A guerra gera
    batalhas → mortes → NOVOS rancores → mais tensão (LAÇO A fecha aqui).
    A exaustão e o decaimento puxam de volta para a paz."""

    def step(self, world: World) -> None:
        civs = world.civs()
        self._acumular_tensao(world, civs)
        self._talvez_roubo(world, civs)      # LAÇO B, segunda metade
        self._talvez_traicao(world, civs)    # ruptura do sangue (rara, trágica)
        self._declarar_guerras(world, civs)
        self._travar_batalhas(world, civs)
        self._talvez_paz(world, civs)

    # -- tensão sobe e desce ---------------------------------------------
    def _acumular_tensao(self, world: World, civs: list[Civ]) -> None:
        for ca, cb in itertools.permutations(civs, 2):
            t = ca.tensao.get(cb.id, 0.0)
            vivos = world.figures_of(ca.id)
            # pressão de rancor: soma dos rancores dos vivos de ca contra cb
            rancor = sum(f.rancor.get(cb.id, 0) for f in vivos)
            # a faísca inicial: um líder ambicioso numa civ belicosa começa
            # guerras mesmo sem histórico de sangue.
            ambicao_lider = max((f.ambicao for f in vivos), default=0.0)
            # cobiça: a riqueza do vizinho tenta os belicosos (comércio de 2 gumes)
            inveja = 0.02 * cb.prosperidade * (ca.belicosidade / 10)
            # interdependência: o que se lucra com cb desestimula atacá-lo
            laco = 0.06 * ca.comercio.get(cb.id, 0.0)
            # sangue prende mais que dinheiro: o parentesco amortece mais forte
            sangue = 0.09 * ca.parentesco.get(cb.id, 0.0)
            pressao = (0.045 * ca.belicosidade
                       + 0.006 * ambicao_lider
                       + 0.015 * min(rancor, 30)
                       + inveja
                       - laco
                       - sangue)
            if cb.id in ca.em_guerra_com:
                pressao += 0.3
            t = clamp(t + pressao)
            t = decay(t, 0.04)          # tudo esfria um pouco a cada ano
            ca.tensao[cb.id] = t

    # -- LAÇO B: cobiça por artefato vira roubo, que reacende a tensão ----
    def _talvez_traicao(self, world: World, civs: list[Civ]) -> None:
        """A ruptura do sangue: um nobre ambicioso demais rompe a aliança e
        ataca os próprios sogros por poder. Rara — a mais escura das guerras,
        e a que gera as mágoas mais fundas. É movida pelo indivíduo: basta uma
        alma ambiciosa o bastante numa casa ligada por sangue a outra."""
        rng = world.rng
        for ca in civs:
            for bid in list(ca.aliados):
                cb = world.get(bid)
                if not isinstance(cb, Civ):
                    continue
                if ca.parentesco.get(bid, 0) < 3:
                    continue          # é preciso haver sangue para traí-lo
                vivos = world.figures_of(ca.id)
                traidor = max(vivos, key=lambda f: f.ambicao, default=None)
                if traidor is None or traidor.ambicao < 8:
                    continue
                # a probabilidade cresce com a ambição do traidor e a belicosidade da casa
                prob = 0.016 * (traidor.ambicao / 10) * (0.5 + ca.belicosidade / 20)
                if rng.random() < prob:
                    world.emit("alianca_rompida", actors=[ca.id, bid],
                               comercio=round(ca.comercio.get(bid, 0), 1),
                               motivo="traição")
                    ev = world.emit("guerra_declarada", actors=[ca.id, bid],
                                    actor_traidor=traidor.id,
                                    traidor_nome=traidor.name,
                                    tensao=9.0, motivo="traição")
                    # o sangue rompido incendeia a tensão e apaga o parentesco,
                    # senão a guerra faria as pazes antes da primeira batalha.
                    ca.tensao[bid] = 9.0
                    cb.tensao[ca.id] = 9.0
                    ca.parentesco[bid] = clamp(ca.parentesco.get(bid, 0) * 0.1)
                    cb.parentesco[ca.id] = clamp(cb.parentesco.get(ca.id, 0) * 0.1)
                    self._arrastar_aliados(world, ca, cb, ev)

    # -- LAÇO B: cobiça por artefato vira roubo, que reacende a tensão ----
    def _talvez_roubo(self, world: World, civs: list[Civ]) -> None:
        rng = world.rng
        for art in world.artifacts():
            dono = art.holder_civ
            if dono is None:
                continue
            for cb in civs:
                if cb.id == dono:
                    continue
                cobica = (cb.tensao.get(dono, 0) + art.fama) / 2
                if cobica >= LIMIAR_ROUBO and rng.random() < 0.03:
                    ev = world.emit("artefato_roubado", actors=[cb.id, dono],
                                    artifact=art.id, thief_civ=cb.id,
                                    name=art.name)
                    # o roubo é uma afronta: injeta tensão nos dois sentidos
                    d = world.get(dono)
                    d.tensao[cb.id] = clamp(d.tensao.get(cb.id, 0) + 3.5)
                    self._semear_rancor(world, victim_civ=dono, enemy_civ=cb.id,
                                        peso=2.0, cause=ev.id)
                    break

    # -- graduado → evento: declaração de guerra -------------------------
    def _declarar_guerras(self, world: World, civs: list[Civ]) -> None:
        for ca, cb in itertools.combinations(civs, 2):
            if cb.id in ca.em_guerra_com:
                continue
            if cb.id in ca.aliados:
                continue                      # aliados não se atacam
            t = max(ca.tensao.get(cb.id, 0), cb.tensao.get(ca.id, 0))
            if t >= LIMIAR_GUERRA:
                causas = self._eventos_de_rancor(world, ca, cb)
                ev = world.emit("guerra_declarada", actors=[ca.id, cb.id],
                                caused_by=causas, tensao=round(t, 1))
                self._arrastar_aliados(world, ca, cb, ev)

    def _arrastar_aliados(self, world: World, ca: Civ, cb: Civ, guerra) -> None:
        """LAÇO do bloco: um aliado leal pode ser arrastado para a guerra do
        parceiro. A lealdade é graduada pelo volume de comércio; a probabilidade
        vem daí. É o que transforma rixas bilaterais em guerras de bloco."""
        rng = world.rng
        atacado, agressor = cb, ca
        for aliado_id in list(atacado.aliados):
            aliado = world.get(aliado_id)
            if not isinstance(aliado, Civ):
                continue
            if agressor.id in (aliado.aliados | aliado.em_guerra_com):
                continue
            if aliado.id == agressor.id:
                continue
            lealdade = aliado.comercio.get(atacado.id, 0.0)   # [0,10]
            if rng.random() < lealdade / 15.0:                # até ~67% se comércio máximo
                world.emit("guerra_declarada", actors=[aliado.id, agressor.id],
                           caused_by=[guerra.id], tensao=8.5,
                           motivo="aliança")
                # a entrada na guerra vem com atrito real, senão a paz vem já
                aliado.tensao[agressor.id] = max(aliado.tensao.get(agressor.id, 0), 8.5)
                agressor.tensao[aliado.id] = max(agressor.tensao.get(aliado.id, 0), 8.5)

    def _travar_batalhas(self, world: World, civs: list[Civ]) -> None:
        rng = world.rng
        vistos: set[frozenset] = set()
        for ca in civs:
            for bid in list(ca.em_guerra_com):
                par = frozenset((ca.id, bid))
                if par in vistos:
                    continue
                vistos.add(par)
                cb = world.get(bid)
                if not isinstance(cb, Civ):
                    continue
                if rng.random() < 0.55:
                    self._batalha(world, ca, cb)
                    ca.exausto = clamp(ca.exausto + rng.uniform(0.5, 1.5))
                    cb.exausto = clamp(cb.exausto + rng.uniform(0.5, 1.5))

    def _batalha(self, world: World, ca: Civ, cb: Civ) -> None:
        rng = world.rng
        fa = self._forca(world, ca)
        fb = self._forca(world, cb)
        total = fa + fb + 1e-6
        # vencedor probabilístico, proporcional à força (não determinístico-duro)
        vencedor, perdedor = (ca, cb) if rng.random() < fa / total else (cb, ca)
        margem = abs(fa - fb) / total   # [0,1], quão decisiva
        # baixas na plebe do perdedor, graduadas pela margem
        baixas = clamp(2 + margem * 6)
        perdedor.populacao = max(10.0, perdedor.populacao - baixas * 3)
        # a batalha aponta causalmente para a guerra que a gerou
        guerra_id = ca.guerra_evento.get(cb.id)
        causa_guerra = [guerra_id] if guerra_id else []

        mortos = []
        for f in world.figures_of(perdedor.id):
            # figuras de baixo valor caem primeiro; alto valor resiste
            risco = 0.05 + margem * 0.10 - f.valor * 0.004
            if rng.random() < max(0.01, risco):
                mortos.append(f)

        ev = world.emit("batalha", actors=[vencedor.id, perdedor.id],
                        caused_by=causa_guerra,
                        vencedor=vencedor.id, margem=round(margem, 2),
                        baixas=round(baixas, 1),
                        mortos=[m.id for m in mortos])

        # renome para um algoz do lado vencedor
        vivos_venc = world.figures_of(vencedor.id)
        algoz = max(vivos_venc, key=lambda x: x.valor, default=None)
        if algoz:
            algoz.renome = clamp(algoz.renome + 0.5 + margem)

        # LAÇO A: cada morte semeia rancor na linhagem/civ do morto
        for m in mortos:
            # traição de sangue: o morto tem parentes vivos na civ que o matou —
            # cônjuge, pai/mãe ou filho, frutos de uniões dinásticas. Tombar pela
            # mão do próprio sangue é a mais funda das mágoas.
            traicao = self._tem_sangue_em(world, m, vencedor.id)
            world.emit("morte", actors=[m.id], causa="batalha",
                       caused_by=[ev.id], contra=vencedor.id,
                       renome=round(m.renome, 1), traicao=bool(traicao))
            peso = 1.0 + m.renome * 0.15
            if traicao:
                perdedor.parentesco[vencedor.id] = clamp(
                    perdedor.parentesco.get(vencedor.id, 0) * 0.2)
                vencedor.parentesco[perdedor.id] = clamp(
                    vencedor.parentesco.get(perdedor.id, 0) * 0.2)
                peso *= 2.0          # a mágoa do fratricídio é redobrada
            self._semear_rancor(world, victim_civ=perdedor.id,
                                enemy_civ=vencedor.id,
                                peso=peso, cause=ev.id, foco=m)

    # -- paz: quando a tensão esfria ou a exaustão pesa demais -----------
    def _talvez_paz(self, world: World, civs: list[Civ]) -> None:
        vistos: set[frozenset] = set()
        for ca in civs:
            for bid in list(ca.em_guerra_com):
                par = frozenset((ca.id, bid))
                if par in vistos:
                    continue
                vistos.add(par)
                cb = world.get(bid)
                if not isinstance(cb, Civ):
                    continue
                t = max(ca.tensao.get(bid, 0), cb.tensao.get(ca.id, 0))
                cansaco = max(ca.exausto, cb.exausto)
                if t <= LIMIAR_PAZ or cansaco >= 8.5:
                    world.emit("paz", actors=[ca.id, cb.id],
                               tensao=round(t, 1), exaustao=round(cansaco, 1))

    # -- utilitários ------------------------------------------------------
    def _tem_sangue_em(self, world: World, figura: Figure, civ_id: int) -> bool:
        """A figura tem parente próximo vivo na civ dada? (cônjuge, pai/mãe, filho)"""
        proximos = list(figura.parents) + list(figura.children)
        if figura.spouse is not None:
            proximos.append(figura.spouse)
        for pid in proximos:
            p = world.get(pid)
            if isinstance(p, Figure) and p.alive and p.civ == civ_id:
                return True
        return False

    def _forca(self, world: World, civ: Civ) -> float:
        return (civ.populacao * 0.1
                + civ.prosperidade * 1.5          # riqueza equipa tropas
                + sum(f.valor for f in world.figures_of(civ.id)))

    def _semear_rancor(self, world, victim_civ, enemy_civ, peso, cause, foco=None):
        alvos = world.figures_of(victim_civ)
        if foco is not None:
            # parentes do morto guardam rancor mais forte
            parentes = set(foco.children) | set(foco.parents)
            if foco.spouse:
                parentes.add(foco.spouse)
        else:
            parentes = set()
        for f in alvos:
            base = f.rancor.get(enemy_civ, 0.0)
            ganho = peso * (2.0 if f.id in parentes else 0.4)
            f.rancor[enemy_civ] = clamp(base + ganho)

    def _eventos_de_rancor(self, world, ca, cb, janela=40, maximo=3):
        # amarra a declaração de guerra às mortes recentes que a motivaram.
        # O rancor que acende a guerra pode estar de QUALQUER um dos dois lados.
        def rancor_de(civ, alvo):
            return max((f.rancor.get(alvo.id, 0) for f in world.figures_of(civ.id)),
                       default=0.0)

        limite_ano = world.year - janela
        causas = []
        # se ca guarda rancor de cb, as mortes de gente de ca pela mão de cb contam
        for atacante, vitima in ((ca, cb), (cb, ca)):
            if rancor_de(atacante, vitima) > 4:
                for ev in reversed(world.log):
                    if ev.year < limite_ano:
                        break
                    if (ev.kind == "morte"
                            and ev.data.get("causa") == "batalha"
                            and ev.data.get("contra") == vitima.id):
                        causas.append(ev.id)
                    if len(causas) >= maximo:
                        break
        return tuple(sorted(set(causas)))
