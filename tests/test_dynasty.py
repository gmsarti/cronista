from cronista import simulate
from cronista.entities import Civ, Figure


def _busca(cond, seeds=range(40), years=240):
    for s in seeds:
        w = simulate(seed=s, years=years)
        if cond(w):
            return w
    return None


def test_casamentos_dinasticos_surgem():
    w = _busca(lambda w: any(e.kind == "casamento_dinastico" for e in w.log))
    assert w is not None


def test_casamento_dinastico_une_civs_distintas():
    for s in range(15):
        w = simulate(seed=s, years=240)
        for e in w.log:
            if e.kind == "casamento_dinastico":
                fa, fb = w.get(e.actors[0]), w.get(e.actors[1])
                assert isinstance(fa, Figure) and isinstance(fb, Figure)
                assert fa.civ != fb.civ            # é entre civs diferentes
                assert fa.spouse == fb.id and fb.spouse == fa.id


def test_parentesco_e_simetrico_e_graduado():
    for s in range(15):
        w = simulate(seed=s, years=200)
        for ca in w.civs():
            for outro, p in ca.parentesco.items():
                assert 0 <= p <= 10
                cb = w.get(outro)
                assert abs(cb.parentesco.get(ca.id, 0) - p) < 1e-9


def test_parentesco_so_existe_apos_casamento_dinastico():
    # se há sangue entre duas civs, houve um casamento dinástico entre elas.
    w = _busca(lambda w: any(c.parentesco for c in w.civs()))
    assert w is not None
    casadas = {frozenset(e.data["civs"]) for e in w.log
               if e.kind == "casamento_dinastico"}
    for ca in w.civs():
        for outro, p in ca.parentesco.items():
            if p > 0:
                assert frozenset((ca.id, outro)) in casadas


def test_traicao_rasga_alianca_e_declara_guerra():
    # a traição sempre vem em par: rompe a aliança E declara a guerra.
    w = _busca(lambda w: any(e.data.get("motivo") == "traição"
                             and e.kind == "guerra_declarada" for e in w.log))
    assert w is not None
    guerras_traicao = [e for e in w.log
                       if e.kind == "guerra_declarada"
                       and e.data.get("motivo") == "traição"]
    rupturas_traicao = [e for e in w.log
                        if e.kind == "alianca_rompida"
                        and e.data.get("motivo") == "traição"]
    assert len(rupturas_traicao) >= len(guerras_traicao) > 0


def test_fratricidio_encadeia_ate_a_traicao():
    # uma morte fratricida deve estar causalmente ligada a uma guerra.
    from cronista import causal_subtree
    w = _busca(lambda w: any(e.kind == "morte" and e.data.get("traicao")
                             for e in w.log))
    assert w is not None
    kin = [e for e in w.log if e.kind == "morte" and e.data.get("traicao")]
    cadeia = causal_subtree(w, kin[0].id)
    assert any(e.kind == "guerra_declarada" for e in cadeia)


def test_determinismo_com_dinastia():
    a = simulate(seed=13, years=200)
    b = simulate(seed=13, years=200)
    assert [e.to_dict() for e in a.log] == [e.to_dict() for e in b.log]
