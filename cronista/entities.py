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
    ambition: float = 5.0
    courage: float = 5.0
    cunning: float = 5.0
    # estado dinâmico
    renown: float = 1.0
    died: int | None = None
    parents: tuple[int, ...] = ()
    children: list[int] = field(default_factory=list)
    # relações graduadas (nunca True/False)
    affinity: dict[int, float] = field(default_factory=dict)    # outra_figura → [0,10]
    grudges: dict[int, float] = field(default_factory=dict)     # civ_alvo → [0,10]
    spouse: int | None = None

    @property
    def alive(self) -> bool:
        return self.died is None


@dataclass
class Civ:
    id: int
    name: str
    site: int
    population: float = 100.0         # plebe abstrata (pool de recrutamento/natalidade)
    belligerence: float = 5.0         # traço cultural [0,10] — tendência à guerra
    mercantilism: float = 5.0         # traço cultural [0,10] — tendência ao comércio
    prosperidade: float = 5.0         # riqueza dinâmica [0,10]; cresce com comércio, cai na guerra
    # tensão graduada com outras civs — o motor da guerra
    tension: dict[int, float] = field(default_factory=dict)     # outra_civ → [0,10]
    # comércio graduado — o contrapeso: interdependência que amortece a guerra
    comercio: dict[int, float] = field(default_factory=dict)    # outra_civ → [0,10]
    # parentesco dinástico — laço de sangue que amortece ainda mais e dá durabilidade
    parentesco: dict[int, float] = field(default_factory=dict)  # outra_civ → [0,10]
    at_war_with: set[int] = field(default_factory=set)          # resultado emergente do limiar
    allies: set[int] = field(default_factory=set)               # emergente do comércio sustentado
    war_event_by_civ: dict[int, int] = field(default_factory=dict)  # civ_inimiga → id declaração
    alliance_event_by_civ: dict[int, int] = field(default_factory=dict)  # civ_aliada → id aliança
    exhaustion: float = 0.0           # fadiga de guerra [0,10], empurra para a paz


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
    fame: float = 5.0     # [0,10]
    holder_civ: int | None = None   # quem o detém agora (muda em roubos/saques)
