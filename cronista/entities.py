"""
entities.py — estado mutável, com identidade.

Regra de ouro: toda intensidade é um escalar em [0, 10], nunca um booleano.
- traços de caráter (ambição, valor, astúcia): quem é a figura.
- afinidade: dict figura→[0,10], valência (0 ódio ... 10 devoção).
- rancor: dict alvo→[0,10], acumula com perdas, decai com o tempo, herda-se.
- tensão (nas civs): dict civ→[0,10], sobe até cruzar limiar → guerra.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Figure:
    id: int
    name: str
    born: int
    civ: int
    # traços de caráter — escalares [0,10] que enviesam probabilidades
    ambicao: float = 5.0
    valor: float = 5.0
    astucia: float = 5.0
    # estado dinâmico
    renome: float = 1.0
    died: int | None = None
    parents: tuple[int, ...] = ()
    children: list[int] = field(default_factory=list)
    # relações graduadas (nunca True/False)
    afinidade: dict[int, float] = field(default_factory=dict)   # outra_figura → [0,10]
    rancor: dict[int, float] = field(default_factory=dict)      # civ_alvo → [0,10]
    spouse: int | None = None

    @property
    def alive(self) -> bool:
        return self.died is None


@dataclass
class Civ:
    id: int
    name: str
    site: int
    populacao: float = 100.0          # plebe abstrata (pool de recrutamento/natalidade)
    belicosidade: float = 5.0         # traço cultural [0,10] — tendência à guerra
    mercantilismo: float = 5.0        # traço cultural [0,10] — tendência ao comércio
    prosperidade: float = 5.0         # riqueza dinâmica [0,10]; cresce com comércio, cai na guerra
    # tensão graduada com outras civs — o motor da guerra
    tensao: dict[int, float] = field(default_factory=dict)      # outra_civ → [0,10]
    # comércio graduado — o contrapeso: interdependência que amortece a guerra
    comercio: dict[int, float] = field(default_factory=dict)    # outra_civ → [0,10]
    # parentesco dinástico — laço de sangue que amortece ainda mais e dá durabilidade
    parentesco: dict[int, float] = field(default_factory=dict)  # outra_civ → [0,10]
    em_guerra_com: set[int] = field(default_factory=set)        # resultado emergente do limiar
    aliados: set[int] = field(default_factory=set)              # emergente do comércio sustentado
    guerra_evento: dict[int, int] = field(default_factory=dict)  # civ_inimiga → id da declaração
    alianca_evento: dict[int, int] = field(default_factory=dict) # civ_aliada → id da aliança
    exausto: float = 0.0              # fadiga de guerra [0,10], empurra para a paz


@dataclass
class Site:
    id: int
    name: str
    kind: str = "fortaleza"


@dataclass
class Artifact:
    id: int
    name: str
    forged: int
    creator: int          # figura
    civ: int
    fama: float = 5.0     # [0,10]
    holder_civ: int | None = None   # quem o detém agora (muda em roubos/saques)
