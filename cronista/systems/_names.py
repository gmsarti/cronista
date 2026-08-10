"""Geração de nomes aleatórios para figuras e artefatos."""
from __future__ import annotations

_SILABAS = ["mor", "dun", "kaz", "thal", "bre", "gol", "sef", "vint", "urd",
            "lok", "myr", "gru", "nes", "tor", "quel", "bram", "od", "sil"]
_EPITETOS = ["o Firme", "de Ferro", "o Sombrio", "Punho-Longo", "a Astuta",
             "o Rancoroso", "Olhos-de-Brasa", "o Prudente", "Mão-Torta",
             "a Indômita", "Coração-de-Pedra", "o Tecelão"]


def _random_name(rng) -> str:
    n_syllables = rng.randint(2, 3)
    return "".join(rng.choice(_SILABAS) for _ in range(n_syllables)).capitalize()
