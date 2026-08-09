"""
demo.py — roda uma história e narra as maiores lendas.

    python demo.py [seed] [anos]
"""
import sys

from cronista import simulate, summarize, biggest_sagas, render_saga, world_state
from cronista.chronicle import render_event


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    anos = int(sys.argv[2]) if len(sys.argv) > 2 else 180

    world = simulate(seed=seed, years=anos)

    print("=" * 68)
    print(summarize(world))
    print("=" * 68)
    print(world_state(world))
    print("=" * 68)

    print("\nAS MAIORES LENDAS (evento + toda a sua cadeia causal)\n")
    for ev in biggest_sagas(world, top=3):
        print("▓ " + render_event(world, ev))
        print(render_saga(world, ev.id))
        print()

    # destaque para o arco dinástico: casamento → aliança → traição → fratricídio
    dinastia = [e for e in world.log if e.kind == "casamento_dinastico"]
    fratricidios = [e for e in world.log
                    if e.kind == "morte" and e.data.get("traicao")]
    traicoes = [e for e in world.log
                if e.kind == "guerra_declarada" and e.data.get("motivo") == "traição"]
    if dinastia or traicoes:
        print("-" * 68)
        print("O SANGUE E O COMÉRCIO (arcos dinásticos)\n")
        for e in dinastia:
            print("  ♦ " + render_event(world, e))
        for e in traicoes:
            print("  ⚔ " + render_event(world, e))
        for e in fratricidios:
            print("\n  A mais funda das mágoas:")
            print(render_saga(world, e.id))
        print()

    print("-" * 68)
    print("Últimos acontecimentos do mundo:\n")
    for ev in world.log[-8:]:
        print("  " + render_event(world, ev))


if __name__ == "__main__":
    main()
