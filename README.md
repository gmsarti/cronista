# cronista

Um *Dwarf-Fortress-Legends* em miniatura: um gerador determinístico de história,
event-sourced e **graduado**.

Dois invariantes sustentam o projeto:

- **Nada é binário.** Toda intensidade — afinidade, rancor, tensão, renome,
  traços de caráter — é um escalar contínuo em `[0, 10]`. Os resultados discretos
  (houve guerra, houve casamento, forjou-se um artefato) *emergem* quando um
  escalar cruza um limiar; nunca são gravados como fato.
- **O log é a verdade.** Os sistemas apenas *propõem* eventos via `world.emit(...)`;
  todo efeito colateral vive nos handlers de `World`. A camada de leitura
  (`chronicle.py` e a API) nunca muta o mundo — ela reconstrói a lenda seguindo
  as arestas `caused_by`.

A mesma seed produz exatamente o mesmo log. Toda aleatoriedade passa por
`World.rng = random.Random(seed)`, sem estado global.

## Estrutura

```
cronista/        domínio puro (sem nenhuma dependência web)
  scale.py       núcleo graduado: clamp, blend, decay, bandas descritivas
  events.py      o Event imutável, com atores e pais causais
  entities.py    estado mutável com identidade: Figure, Civ, Site, Artifact
  world.py       o estado ativo + o log append-only; emit() e seus handlers
  systems.py     os motores: Demography, Bonds, Renown, Trade, Dynasty, Conflict
  simulation.py  o driver: seed_world() e simulate()
  chronicle.py   ler o log de volta e contar a lenda
api/             camada HTTP (FastAPI), somente leitura
tests/           pytest
docs/            análise, roadmap e diagramas mermaid
demo.py          CLI
```

## Instalação

```bash
uv sync --extra dev        # ou: pip install -e ".[dev]"
```

Requer Python 3.13+.

## Uso

### CLI

```bash
python demo.py [seed] [anos]     # padrão: 42 180
```

Roda uma história e imprime o resumo, o estado geopolítico final e as três
maiores sagas.

### API

```bash
uvicorn api.main:create_app --factory --reload
```

Documentação interativa em `http://127.0.0.1:8000/docs`.

A API é **stateless**: não há mundo guardado no servidor. Cada requisição
re-simula a partir dos parâmetros `(seed, years, n_civs, figuras_por_civ)`, o que
é sempre consistente porque a simulação é determinística.

| Método | Rota                                    | O que retorna                                  |
| ------ | --------------------------------------- | ---------------------------------------------- |
| `GET`  | `/health`                               | status do serviço                              |
| `GET`  | `/worlds/{seed}`                        | resumo e estado geopolítico do mundo           |
| `GET`  | `/worlds/{seed}/events`                 | log paginado, com filtros                      |
| `GET`  | `/worlds/{seed}/events/{event_id}`      | um evento e sua prosa                          |
| `GET`  | `/worlds/{seed}/events/{event_id}/saga` | a cadeia causal que produziu o evento          |
| `GET`  | `/worlds/{seed}/sagas`                  | as maiores lendas do mundo                     |
| `GET`  | `/worlds/{seed}/log`                    | o log completo, cru                            |

Exemplos:

```bash
curl "http://127.0.0.1:8000/worlds/42?years=180"
curl "http://127.0.0.1:8000/worlds/42/events?kind=batalha&limit=10"
curl "http://127.0.0.1:8000/worlds/42/sagas?top=3"
```

## Testes

```bash
pytest
```

Os testes de integração (`test_trade.py`, `test_dynasty.py`) varrem dezenas de
seeds até encontrar um mundo que exiba o fenômeno emergente sob teste — são
lentos por natureza.

## Documentação

[`docs/analise_e_roadmap.md`](docs/analise_e_roadmap.md) mapeia os cinco laços de
realimentação do sistema, compara com Dwarf Fortress e descreve o roadmap.
Os diagramas estão em [`docs/arquitetura.mermaid`](docs/arquitetura.mermaid) e
[`docs/lacos_de_realimentacao.mermaid`](docs/lacos_de_realimentacao.mermaid).
