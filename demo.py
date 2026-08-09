"""
demo.py — roda uma história e narra as maiores lendas.

    python demo.py [seed] [years]
"""
import sys

from cronista import simulate, summarize, biggest_sagas, render_saga, world_state
from cronista.chronicle import render_event


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 180

    world = simulate(seed=seed, years=years)

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
    dynastic_marriages = [e for e in world.log if e.kind == "casamento_dinastico"]
    kin_slayings = [e for e in world.log
                    if e.kind == "morte" and e.data.get("traicao")]
    betrayal_wars = [e for e in world.log
                     if e.kind == "guerra_declarada" and e.data.get("motivo") == "traição"]
    if dynastic_marriages or betrayal_wars:
        print("-" * 68)
        print("O SANGUE E O COMÉRCIO (arcos dinásticos)\n")
        for event in dynastic_marriages:
            print("  ♦ " + render_event(world, event))
        for event in betrayal_wars:
            print("  ⚔ " + render_event(world, event))
        for event in kin_slayings:
            print("\n  A mais funda das mágoas:")
            print(render_saga(world, event.id))
        print()

    print("-" * 68)
    print("Últimos acontecimentos do mundo:\n")
    for event in world.log[-8:]:
        print("  " + render_event(world, event))


if __name__ == "__main__":
    main()
