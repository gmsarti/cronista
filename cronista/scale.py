"""
scale.py — o coração graduado do sistema.

Princípio: nada é binário. Toda intensidade (afinidade, rancor, tensão,
renome, traços de caráter) é um escalar contínuo em [0, 10]. Os *resultados*
binários (houve guerra, houve casamento, forjou-se um artefato) emergem quando
um escalar cruza um limiar — nunca são gravados diretamente como fato.

MIN = 0  →  ausência total
MAX = 10 →  intensidade máxima

Este módulo NÃO tem estado de mundo nem aleatoriedade. É pura aritmética
determinística e testável.
"""
from __future__ import annotations

from dataclasses import dataclass

MIN: float = 0.0
MAX: float = 10.0


def clamp(x: float) -> float:
    """Prende um valor na faixa [0, 10]."""
    if x < MIN:
        return MIN
    if x > MAX:
        return MAX
    return float(x)


def blend(a: float, b: float, peso: float) -> float:
    """Interpola entre dois níveis. peso=0 → a, peso=1 → b."""
    peso = clamp(peso * 10) / 10  # peso também é uma fração graduada
    return clamp(a * (1 - peso) + b * peso)


def decay(x: float, taxa: float) -> float:
    """Decaimento multiplicativo por passo de tempo. taxa em [0,1)."""
    return clamp(x * (1.0 - taxa))


# Bandas descritivas: transformam o escalar em linguagem para o narrador.
# A gradação existe tanto na mecânica quanto na crônica.
_INTENSIDADE = [
    (1.0, "inexistente"),
    (2.5, "tênue"),
    (4.0, "moderada"),
    (5.5, "considerável"),
    (7.0, "forte"),
    (8.5, "intensa"),
    (10.1, "avassaladora"),
]

# Afinidade tem valência: 0 = ódio, 5 = indiferença, 10 = devoção.
_AFINIDADE = [
    (1.0, "ódio figadal"),
    (2.5, "hostilidade"),
    (4.0, "desconfiança"),
    (5.5, "indiferença"),
    (7.0, "simpatia"),
    (8.5, "afeição"),
    (10.1, "devoção"),
]

_RENOME = [
    (1.0, "desconhecido"),
    (2.5, "obscuro"),
    (4.0, "notado"),
    (5.5, "respeitado"),
    (7.0, "renomado"),
    (8.5, "ilustre"),
    (10.1, "lendário"),
]


def _band(x: float, tabela) -> str:
    x = clamp(x)
    for teto, rotulo in tabela:
        if x < teto:
            return rotulo
    return tabela[-1][1]


def descrever_intensidade(x: float) -> str:
    return _band(x, _INTENSIDADE)


def descrever_afinidade(x: float) -> str:
    return _band(x, _AFINIDADE)


def descrever_renome(x: float) -> str:
    return _band(x, _RENOME)


@dataclass(frozen=True)
class Nivel:
    """
    Objeto-valor imutável para um nível graduado. Útil quando se quer passar
    um escalar por aí com segurança (o valor já nasce preso em [0,10]) e com
    descrição embutida. O estado *mutável* das entidades usa floats crus por
    ergonomia; este tipo é para fronteiras e para o narrador.
    """
    valor: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "valor", clamp(self.valor))

    def __add__(self, delta: float) -> "Nivel":
        return Nivel(self.valor + delta)

    def __sub__(self, delta: float) -> "Nivel":
        return Nivel(self.valor - delta)

    def misturar(self, outro: "Nivel", peso: float) -> "Nivel":
        return Nivel(blend(self.valor, outro.valor, peso))

    @property
    def intensidade(self) -> str:
        return descrever_intensidade(self.valor)

    def __float__(self) -> float:
        return self.valor
