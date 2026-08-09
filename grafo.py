"""
grafo.py — o log como grafo causal, estático e animado.

Cada evento é um nó; cada aresta `caused_by` liga a causa ao efeito. O eixo X é
o ano, então o grafo se lê da esquerda para a direita como uma linha do tempo.

    python grafo.py                         # PNG + GIF da seed 42, 180 anos
    python grafo.py --seed 7 --years 120
    python grafo.py --kinds guerra_declarada,batalha,paz,morte
    python grafo.py --legends-only          # só os eventos com cadeia causal

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
EVENT_COLORS: dict[str, str] = {
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
GRAY = "#b0b0b0"


def build_graph(world: World, kinds: set[str] | None = None) -> nx.DiGraph:
    """O log vira um DiGraph: nó = evento, aresta = causa → efeito."""
    graph = nx.DiGraph()
    for ev in world.log:
        if kinds and ev.kind not in kinds:
            continue
        graph.add_node(ev.id, year=ev.year, kind=ev.kind, prosa=render_event(world, ev))
    for ev in world.log:
        if ev.id not in graph:
            continue
        for parent_id in ev.caused_by:
            if parent_id in graph:
                graph.add_edge(parent_id, ev.id)
    return graph


def temporal_layout(graph: nx.DiGraph) -> dict[int, tuple[float, float]]:
    """X = ano, Y = posição dentro do ano (empilhada e centrada)."""
    by_year: dict[int, list[int]] = {}
    for node_id, attrs in graph.nodes(data=True):
        by_year.setdefault(attrs["year"], []).append(node_id)

    pos: dict[int, tuple[float, float]] = {}
    for year, node_ids in by_year.items():
        node_ids.sort()
        offset = (len(node_ids) - 1) / 2
        for i, node_id in enumerate(node_ids):
            pos[node_id] = (float(year), i - offset)
    return pos


def _legend(graph: nx.DiGraph) -> list[Line2D]:
    present_kinds = {attrs["kind"] for _, attrs in graph.nodes(data=True)}
    return [
        Line2D([], [], marker="o", linestyle="", markersize=7,
               color=EVENT_COLORS.get(k, GRAY), label=k)
        for k in sorted(present_kinds)
    ]


def _configure_year_axis(ax, graph: nx.DiGraph) -> None:
    """Marca a década no eixo X e apaga o eixo Y, que é só empilhamento.

    Precisa rodar *depois* dos `nx.draw_networkx_*`: eles desligam os rótulos
    dos eixos, então `bottom`/`labelbottom` são religados aqui na mão.
    """
    years = [attrs["year"] for _, attrs in graph.nodes(data=True)]
    start, end = min(years) // 10 * 10, max(years) + 10
    ax.set_xticks(range(start, end, 10))
    ax.tick_params(axis="x", bottom=True, labelbottom=True,
                   labelsize=8, colors="#555555")
    ax.get_yaxis().set_visible(False)


def _node_colors(graph: nx.DiGraph, node_ids: list[int]) -> list[str]:
    return [EVENT_COLORS.get(graph.nodes[n]["kind"], GRAY) for n in node_ids]


def _node_sizes(graph: nx.DiGraph, node_ids: list[int]) -> list[float]:
    """Nós com descendência causal aparecem maiores — são os que geram lenda."""
    return [18 + 22 * min(graph.out_degree(n) + graph.in_degree(n), 6) for n in node_ids]


def draw_static(graph: nx.DiGraph, pos: dict, seed: int, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(20, 9))
    node_ids = list(graph.nodes)
    nx.draw_networkx_edges(graph, pos, ax=ax, edge_color="#00000030",
                           arrows=False, width=0.6)
    nx.draw_networkx_nodes(graph, pos, ax=ax, nodelist=node_ids,
                           node_color=_node_colors(graph, node_ids),
                           node_size=_node_sizes(graph, node_ids), linewidths=0)
    ax.set_title(f"Grafo causal do mundo seed={seed} — "
                 f"{graph.number_of_nodes()} eventos, {graph.number_of_edges()} arestas causais")
    ax.set_xlabel("ano")
    _configure_year_axis(ax, graph)
    ax.legend(handles=_legend(graph), loc="upper left", ncol=2, fontsize=8, framealpha=0.9)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=110)
    plt.close(fig)


def animate(graph: nx.DiGraph, pos: dict, seed: int, output_path: Path, fps: int) -> None:
    """Um quadro por ano: o grafo cresce, e o ano corrente pisca em destaque."""
    years = sorted({attrs["year"] for _, attrs in graph.nodes(data=True)})
    up_to_year: dict[int, list[int]] = {}
    for year in years:
        up_to_year[year] = [n for n, attrs in graph.nodes(data=True) if attrs["year"] <= year]

    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    fig, ax = plt.subplots(figsize=(20, 9))

    def frame(year: int) -> None:
        ax.clear()
        visible_nodes = up_to_year[year]
        sub = graph.subgraph(visible_nodes)
        new_nodes = [n for n in visible_nodes if graph.nodes[n]["year"] == year]
        old_nodes = [n for n in visible_nodes if graph.nodes[n]["year"] != year]

        nx.draw_networkx_edges(sub, pos, ax=ax, edge_color="#00000028",
                               arrows=False, width=0.6)
        if old_nodes:
            nx.draw_networkx_nodes(sub, pos, ax=ax, nodelist=old_nodes,
                                   node_color=_node_colors(graph, old_nodes),
                                   node_size=_node_sizes(graph, old_nodes),
                                   alpha=0.55, linewidths=0)
        if new_nodes:
            nx.draw_networkx_nodes(sub, pos, ax=ax, nodelist=new_nodes,
                                   node_color=_node_colors(graph, new_nodes),
                                   node_size=[t * 2.4 for t in _node_sizes(graph, new_nodes)],
                                   edgecolors="black", linewidths=0.8)

        ax.set_xlim(min(xs) - 3, max(xs) + 3)
        ax.set_ylim(min(ys) - 2, max(ys) + 2)
        ax.set_title(f"seed={seed} — ano {year:>4} | {len(visible_nodes)} eventos acumulados "
                     f"| {len(new_nodes)} neste ano")
        ax.set_xlabel("ano")
        ax.get_yaxis().set_visible(False)
        ax.legend(handles=_legend(graph), loc="upper left", ncol=2,
                  fontsize=8, framealpha=0.9)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)

    anim = FuncAnimation(fig, frame, frames=years, interval=1000 // fps)
    anim.save(output_path, writer=PillowWriter(fps=fps))
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualiza o log do cronista como grafo causal.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--years", type=int, default=180)
    parser.add_argument("--kinds", type=str, default="",
                   help="lista separada por vírgula; vazio = todos os tipos")
    parser.add_argument("--legends-only", action="store_true",
                   help="descarta eventos isolados, sem causa nem consequência")
    parser.add_argument("--saida", type=Path, default=Path("docs"))
    parser.add_argument("--fps", type=int, default=6)
    parser.add_argument("--no-gif", action="store_true", help="gera só o PNG")
    args = parser.parse_args()

    kinds = {k.strip() for k in args.kinds.split(",") if k.strip()} or None
    world = simulate(seed=args.seed, years=args.years)
    graph = build_graph(world, kinds)

    if args.legends_only:
        graph = graph.subgraph([n for n in graph if graph.degree(n) > 0]).copy()

    pos = temporal_layout(graph)
    args.saida.mkdir(parents=True, exist_ok=True)
    print(f"grafo: {graph.number_of_nodes()} nós, {graph.number_of_edges()} arestas")

    png = args.saida / f"grafo_seed{args.seed}.png"
    draw_static(graph, pos, args.seed, png)
    print(f"  {png}")

    if not args.no_gif:
        gif = args.saida / f"grafo_seed{args.seed}.gif"
        animate(graph, pos, args.seed, gif, args.fps)
        print(f"  {gif}")


if __name__ == "__main__":
    main()
