from cronista.scale import (
    MAX, MIN, Nivel, blend, clamp, decay,
    descrever_afinidade, descrever_intensidade, descrever_renome,
)


def test_clamp_prende_nos_limites():
    assert clamp(-5) == MIN
    assert clamp(99) == MAX
    assert clamp(3.2) == 3.2


def test_blend_extremos_e_meio():
    assert blend(0, 10, 0.0) == 0
    assert blend(0, 10, 1.0) == 10
    assert blend(0, 10, 0.5) == 5


def test_decay_reduz_e_nunca_negativa():
    assert decay(10, 0.5) == 5
    assert decay(0.0, 0.9) == 0
    assert 0 <= decay(10, 0.04) <= 10


def test_bandas_sao_graduadas_nao_binarias():
    # o mesmo escalar produz rótulos distintos conforme a faixa
    assert descrever_intensidade(0.2) == "inexistente"
    assert descrever_intensidade(5.0) == "considerável"
    assert descrever_intensidade(9.9) == "avassaladora"
    assert descrever_afinidade(0.5) == "ódio figadal"
    assert descrever_afinidade(5.0) == "indiferença"
    assert descrever_afinidade(9.9) == "devoção"
    assert descrever_renome(9.9) == "lendário"


def test_nivel_e_imutavel_e_preso():
    n = Nivel(15)
    assert n.valor == 10
    n2 = n - 4
    assert n2.valor == 6
    assert float(n2) == 6
    assert n.intensidade == "avassaladora"
