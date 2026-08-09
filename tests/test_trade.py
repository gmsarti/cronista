from cronista import simulate
from cronista.entities import Civ
from cronista.systems import LIMIAR_ALIANCA, LIMIAR_ROTA


def _por_seed(fn, seeds=range(40), years=220):
    """Roda fn(world) em várias seeds e retorna a primeira que satisfaz."""
    for s in seeds:
        w = simulate(seed=s, years=years)
        if fn(w):
            return w
    return None


def test_rotas_comerciais_surgem_em_algum_mundo():
    w = _por_seed(lambda w: any(e.kind == "rota_comercial" for e in w.log))
    assert w is not None


def test_aliancas_surgem_em_algum_mundo():
    w = _por_seed(lambda w: any(e.kind == "alianca_formada" for e in w.log))
    assert w is not None


def test_alianca_exige_comercio_alto_ou_sangue():
    # a aliança é emergente: comércio forte, OU comércio decente selado por sangue.
    from cronista.systems import LIMIAR_ROTA
    for s in range(20):
        w = simulate(seed=s, years=220)
        for e in w.log:
            if e.kind == "alianca_formada":
                com = e.data["comercio"]
                paren = e.data.get("parentesco", 0)
                assert com >= LIMIAR_ALIANCA - 0.01 or (
                    com >= LIMIAR_ROTA - 0.01 and paren >= 5 - 0.01)


def test_aliados_nao_declaram_guerra_entre_si():
    # varre o log reconstruindo quem era aliado no momento de cada guerra.
    for s in range(20):
        w = simulate(seed=s, years=220)
        aliados: dict[int, set[int]] = {}
        for e in w.log:
            a = e.actors
            if e.kind == "alianca_formada":
                aliados.setdefault(a[0], set()).add(a[1])
                aliados.setdefault(a[1], set()).add(a[0])
            elif e.kind in ("alianca_rompida", "guerra_declarada"):
                aliados.get(a[0], set()).discard(a[1])
                aliados.get(a[1], set()).discard(a[0])
            if e.kind == "guerra_declarada":
                assert a[1] not in aliados.get(a[0], set())


def test_prosperidade_sobe_com_comercio():
    # num mundo mercantil, ao menos uma civ deve enriquecer acima do inicial.
    w = _por_seed(
        lambda w: any(isinstance(c, Civ) and c.prosperidade > 7 for c in w.civs())
    )
    assert w is not None


def test_comercio_e_simetrico():
    w = simulate(seed=9, years=150)
    for ca in w.civs():
        for outro_id, v in ca.comercio.items():
            outro = w.get(outro_id)
            assert abs(outro.comercio.get(ca.id, 0) - v) < 1e-9
