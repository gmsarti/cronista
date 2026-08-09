from cronista import simulate, causal_subtree
from cronista.scale import decay
from cronista.systems import LIMIAR_GUERRA
from cronista.world import World
from cronista.entities import Figure, Civ


def test_determinismo_mesma_seed_mesmo_log():
    a = simulate(seed=7, years=120)
    b = simulate(seed=7, years=120)
    assert len(a.log) == len(b.log)
    assert [e.to_dict() for e in a.log] == [e.to_dict() for e in b.log]


def test_seeds_diferentes_divergem():
    a = simulate(seed=1, years=120)
    b = simulate(seed=2, years=120)
    assert [e.kind for e in a.log] != [e.kind for e in b.log]


def test_mundo_gera_historia():
    w = simulate(seed=42, years=180)
    kinds = {e.kind for e in w.log}
    assert "nascimento" in kinds
    assert "morte" in kinds
    # com 4 civs e 180 anos, é esperado algum conflito
    assert kinds & {"guerra_declarada", "batalha"}


def test_mortos_ficam_mortos_e_log_e_consistente():
    w = simulate(seed=42, years=180)
    mortes = [e for e in w.log if e.kind == "morte"]
    for ev in mortes:
        f = w.get(ev.actors[0])
        assert isinstance(f, Figure)
        assert not f.alive
        assert f.died is not None


def test_guerra_so_ocorre_acima_do_limiar():
    # a guerra é emergente: nunca é gravada sem tensão suficiente por trás.
    w = simulate(seed=3, years=200)
    for ev in w.log:
        if ev.kind == "guerra_declarada":
            assert ev.data["tensao"] >= LIMIAR_GUERRA - 0.01


def test_guerra_de_vinganca_encadeia_ate_uma_morte():
    # LAÇO A: uma guerra de vingança (não de aliança) aponta para mortes.
    w = simulate(seed=42, years=220)
    vinganca = [e for e in w.log
                if e.kind == "guerra_declarada"
                and e.caused_by
                and e.data.get("motivo") != "aliança"]
    if vinganca:
        cadeia = causal_subtree(w, vinganca[0].id)
        assert any(e.kind == "morte" for e in cadeia)


def test_guerra_de_bloco_encadeia_ate_outra_guerra():
    # LAÇO do bloco: uma guerra por aliança aponta para a guerra que a puxou.
    w = simulate(seed=9, years=220)
    bloco = [e for e in w.log if e.data.get("motivo") == "aliança"]
    assert bloco, "esperava ao menos uma guerra de bloco na seed 9"
    cadeia = causal_subtree(w, bloco[0].id)
    assert sum(1 for e in cadeia if e.kind == "guerra_declarada") >= 2


def test_rancor_decai_com_o_tempo():
    # sem novos agravos, o rancor esfria — gradação, não flag permanente.
    r = 10.0
    for _ in range(50):
        r = decay(r, 0.04)
    assert r < 2.0


def test_ids_de_evento_sao_unicos_e_crescentes():
    w = simulate(seed=9, years=100)
    ids = [e.id for e in w.log]
    assert len(ids) == len(set(ids))
    assert ids == sorted(ids)


def test_causal_subtree_inclui_o_proprio_evento():
    w = simulate(seed=42, years=150)
    ev = w.log[-1]
    sub = causal_subtree(w, ev.id)
    assert ev in sub
    # ordenado cronologicamente
    anos = [e.year for e in sub]
    assert anos == sorted(anos)
