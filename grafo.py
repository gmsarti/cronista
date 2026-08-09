"""
grafo.py — o log como grafo causal, estático e animado.

Cada evento é um nó; cada aresta `caused_by` liga a causa ao efeito. O eixo X é
o ano, então o grafo se lê da esquerda para a direita como uma linha do tempo.

    python grafo.py                         # PNG + GIF da seed 42, 180 anos
    python grafo.py --seed 7 --anos 120
    python grafo.py --kinds guerra_declarada,batalha,paz,morte
    python grafo.py --so-lendas             # só os eventos com cadeia causal

Requer o extra de visualização: `uv sync --extra viz`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.lines import Line2D

from cronista import simulate
from cronista.chronicle import render_event
from cronista.world import World

# uma cor por tipo de evento — quem não estiver aqui cai no cinza
CORES: dict[str, str] = {
    "nascimento": "#7fb069",
    "morte": "#4a4a4a",
    "casamento": "#e0a3c4",
    "casamento_dinastico": "#c2185b",
    "guerra_declarada": "#e85d04",
    "batalha": "#c1121f",
    "paz": "#457b9d",
    "alianca_formada": "#2a9d8f",
    "alianca_rompida": "#9d4edd",
    "rota_comercial": "#e9c46a",
    "artefato_forjado": "#f4a261",
    "artefato_roubado": "#8a5a44",
}
CINZA = "#b0b0b0"


def construir_grafo(world: World, kinds: set[str] | None = None) -> nx.DiGraph:
    """O log vira um DiGraph: nó = evento, aresta = causa → efeito."""
    g = nx.DiGraph()
    for ev in world.log:
        if kinds and ev.kind not in kinds:
            continue
        g.add_node(ev.id, year=ev.year, kind=ev.kind, prosa=render_event(world, ev))
    for ev in world.log:
        if ev.id not in g:
            continue
        for pai in ev.caused_by:
            if pai in g:
                g.add_edge(pai, ev.id)
    return g


def layout_temporal(g: nx.DiGraph) -> dict[int, tuple[float, float]]:
    """X = ano, Y = posição dentro do ano (empilhada e centrada)."""
    por_ano: dict[int, list[int]] = {}
    for n, dados in g.nodes(data=True):
        por_ano.setdefault(dados["year"], []).append(n)

    pos: dict[int, tuple[float, float]] = {}
    for ano, nos in por_ano.items():
        nos.sort()
        deslocamento = (len(nos) - 1) / 2
        for i, n in enumerate(nos):
            pos[n] = (float(ano), i - deslocamento)
    return pos


def _legenda(g: nx.DiGraph) -> list[Line2D]:
    presentes = {d["kind"] for _, d in g.nodes(data=True)}
    return [
        Line2D([], [], marker="o", linestyle="", markersize=7,
               color=CORES.get(k, CINZA), label=k)
        for k in sorted(presentes)
    ]


def _eixo_dos_anos(ax, g: nx.DiGraph) -> None:
    """Marca a década no eixo X e apaga o eixo Y, que é só empilhamento.

    Precisa rodar *depois* dos `nx.draw_networkx_*`: eles desligam os rótulos
    dos eixos, então `bottom`/`labelbottom` são religados aqui na mão.
    """
    anos = [d["year"] for _, d in g.nodes(data=True)]
    inicio, fim = min(anos) // 10 * 10, max(anos) + 10
    ax.set_xticks(range(inicio, fim, 10))
    ax.tick_params(axis="x", bottom=True, labelbottom=True,
                   labelsize=8, colors="#555555")
    ax.get_yaxis().set_visible(False)


def _cores_dos_nos(g: nx.DiGraph, nos: list[int]) -> list[str]:
    return [CORES.get(g.nodes[n]["kind"], CINZA) for n in nos]


def _tamanhos(g: nx.DiGraph, nos: list[int]) -> list[float]:
    """Nós com descendência causal aparecem maiores — são os que geram lenda."""
    return [18 + 22 * min(g.out_degree(n) + g.in_degree(n), 6) for n in nos]


def desenhar_estatico(g: nx.DiGraph, pos: dict, seed: int, saida: Path) -> None:
    fig, ax = plt.subplots(figsize=(20, 9))
    nos = list(g.nodes)
    nx.draw_networkx_edges(g, pos, ax=ax, edge_color="#00000030",
                           arrows=False, width=0.6)
    nx.draw_networkx_nodes(g, pos, ax=ax, nodelist=nos,
                           node_color=_cores_dos_nos(g, nos),
                           node_size=_tamanhos(g, nos), linewidths=0)
    ax.set_title(f"Grafo causal do mundo seed={seed} — "
                 f"{g.number_of_nodes()} eventos, {g.number_of_edges()} arestas causais")
    ax.set_xlabel("ano")
    _eixo_dos_anos(ax, g)
    ax.legend(handles=_legenda(g), loc="upper left", ncol=2, fontsize=8, framealpha=0.9)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    fig.tight_layout()
    fig.savefig(saida, dpi=110)
    plt.close(fig)


def animar(g: nx.DiGraph, pos: dict, seed: int, saida: Path, fps: int) -> None:
    """Um quadro por ano: o grafo cresce, e o ano corrente pisca em destaque."""
    anos = sorted({d["year"] for _, d in g.nodes(data=True)})
    ate_o_ano: dict[int, list[int]] = {}
    for ano in anos:
        ate_o_ano[ano] = [n for n, d in g.nodes(data=True) if d["year"] <= ano]

    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    fig, ax = plt.subplots(figsize=(20, 9))

    def quadro(ano: int) -> None:
        ax.clear()
        visiveis = ate_o_ano[ano]
        sub = g.subgraph(visiveis)
        novos = [n for n in visiveis if g.nodes[n]["year"] == ano]
        antigos = [n for n in visiveis if g.nodes[n]["year"] != ano]

        nx.draw_networkx_edges(sub, pos, ax=ax, edge_color="#00000028",
                               arrows=False, width=0.6)
        if antigos:
            nx.draw_networkx_nodes(sub, pos, ax=ax, nodelist=antigos,
                                   node_color=_cores_dos_nos(g, antigos),
                                   node_size=_tamanhos(g, antigos),
                                   alpha=0.55, linewidths=0)
        if novos:
            nx.draw_networkx_nodes(sub, pos, ax=ax, nodelist=novos,
                                   node_color=_cores_dos_nos(g, novos),
                                   node_size=[t * 2.4 for t in _tamanhos(g, novos)],
                                   edgecolors="black", linewidths=0.8)

        ax.set_xlim(min(xs) - 3, max(xs) + 3)
        ax.set_ylim(min(ys) - 2, max(ys) + 2)
        ax.set_title(f"seed={seed} — ano {ano:>4} | {len(visiveis)} eventos acumulados "
                     f"| {len(novos)} neste ano")
        ax.set_xlabel("ano")
        ax.get_yaxis().set_visible(False)
        ax.legend(handles=_legenda(g), loc="upper left", ncol=2,
                  fontsize=8, framealpha=0.9)
        for lado in ("top", "right", "left"):
            ax.spines[lado].set_visible(False)

    anim = FuncAnimation(fig, quadro, frames=anos, interval=1000 // fps)
    anim.save(saida, writer=PillowWriter(fps=fps))
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser(description="Visualiza o log do cronista como grafo causal.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--anos", type=int, default=180)
    p.add_argument("--kinds", type=str, default="",
                   help="lista separada por vírgula; vazio = todos os tipos")
    p.add_argument("--so-lendas", action="store_true",
                   help="descarta eventos isolados, sem causa nem consequência")
    p.add_argument("--saida", type=Path, default=Path("docs"))
    p.add_argument("--fps", type=int, default=6)
    p.add_argument("--sem-gif", action="store_true", help="gera só o PNG")
    args = p.parse_args()

    kinds = {k.strip() for k in args.kinds.split(",") if k.strip()} or None
    world = simulate(seed=args.seed, years=args.anos)
    g = construir_grafo(world, kinds)

    if args.so_lendas:
        g = g.subgraph([n for n in g if g.degree(n) > 0]).copy()

    pos = layout_temporal(g)
    args.saida.mkdir(parents=True, exist_ok=True)
    print(f"grafo: {g.number_of_nodes()} nós, {g.number_of_edges()} arestas")

    png = args.saida / f"grafo_seed{args.seed}.png"
    desenhar_estatico(g, pos, args.seed, png)
    print(f"  {png}")

    if not args.sem_gif:
        gif = args.saida / f"grafo_seed{args.seed}.gif"
        animar(g, pos, args.seed, gif, args.fps)
        print(f"  {gif}")


if __name__ == "__main__":
    main()
