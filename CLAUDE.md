# CLAUDE.md — GUIDELINES

Guia para agentes de IA que vão trabalhar neste projeto. Leia antes de criar ou modificar qualquer coisa.

> Este arquivo é um guia operacional **e** template — as seções abaixo da linha divisória precisam ser preenchidas ou removidas na primeira interação com o projeto (inclusive essa linha).

## Antes de Começar

Antes de iniciar qualquer implementação, verifique a branch atual. Evite trabalhar em `main`, `staging` ou `develop`, crie uma nova branch seguindo as convenções em [commit-rules.md](commit-rules.md).

**Tasks pontuais** (uma implementação focada que termina em um ciclo): todo commit exige autorização. Mesmo que já tenha commitado várias vezes na mesma sessão, **nunca assuma que a autorização se repete**. Após cada implementação, rode as validações (lint, testes) e pergunte sobre o commit.

**Tasks longas e complexas** (múltiplas etapas com validações intermediárias): se necessário, comite as evoluções ao longo da implementação e, ao concluir tudo, pergunte sobre o push e o PR u siga as reras estipuladas para isso.

## Filosofia

**KISS — Keep It Simple, Stupid.** Toda decisão de código deve favorecer a solução mais simples que resolve o problema. Não adicione abstrações, configurabilidade ou generalização antecipada. Prefira nomes claros, estrutura óbvia e comentários onde a lógica não é autoevidente a soluções "inteligentes" que exigem decifração.

Regras práticas que derivam disso:

- Prefira **funções a classes** — só use classes quando houver estado real a manter
- Funções devem ser **sempre tipadas** (parâmetros e retorno)
- Use **early return** para evitar aninhamento desnecessário
- **Código mínimo que resolve o problema. Nada especulativo.**

**Toque só o que precisa. Limpe só a sua bagunça.** Esta é uma regra de escopo, não de estilo. Altere apenas o que é necessário para cumprir a tarefa. Não refatore código adjacente, não renomeie variáveis fora do problema, não faça "melhorias" oportunistas ("já que estou aqui", "esse nome está ruim", "esse trecho pode ser mais elegante" — não). Se você introduziu algo, você organiza. O resto fica como estava.

**Seja honesto — nunca invente.** Se não sabe, diga diretamente e aponte o que precisa verificar. Se está em dúvida, consulte a fonte (código, documentação, testes) antes de afirmar. Nunca entregue uma resposta plausível no lugar de uma correta.

**Não assuma — pergunte.** Se durante a implementação bater em um problema que não tem certeza de como resolver, pare e pergunte. Não adivinhe o caminho. Descreva o bloqueio, mostre as opções se houver, e deixe o time decidir.

**Tente antes de interromper — mas saiba a hora de parar.** Se uma tentativa falhar e a correção não exigir tocar em nada fora do escopo da tarefa, tente novamente. Até 2-3 tentativas são aceitáveis sem avisar. Depois disso, pare.

**Quando travar de verdade — pare e explique.** Interrompa imediatamente (sem esperar o limite de tentativas) se o bloqueio for externo à tarefa:

- precisa alterar arquivo ou módulo fora do escopo
- depende de algo fora do seu controle (config, variável de ambiente, serviço, permissão)
- exige uma decisão de design que impacta outras partes do sistema
- a tentativa quebrou código que já funcionava

Ao parar: descreva o bloqueio e sugira 1-2 opções de caminho. Sem histórico de tentativas — direto ao ponto. Deixe o time decidir. **Exceção:** ao iniciar uma tarefa, pergunte ao usuário se prefere ser notificado a cada bloqueio ou se quer que você tente resolver de forma autônoma até o fim — e siga a preferência declarada durante toda aquela sessão.

**Ao concluir uma implementação planejada — registre o resultado.** Escreva um resumo curto do que foi feito e se houve desvios do plano. Exemplo com desvio: "Previa reusar uma função existente, mas o contexto não tinha os dados necessários — criada uma função paralela para manter a mesma lógica sem acoplamento desnecessário."

## Como Manter Este Arquivo

Este `CLAUDE.md` é o índice global do projeto — contém só o que vale para **todo** o código. Regras técnicas de um módulo específico, exemplos de implementação, anatomia de rotas ou schemas ficam no `CLAUDE.md` interno daquela pasta. Não coloque aqui: exemplos de código, detalhes de implementação, padrões de um módulo específico. Se a informação só faz sentido dentro de `src/modules/users/`, ela pertence ao `src/modules/users/CLAUDE.md`.

**Estrutura de sub-CLAUDEs:**

```
CLAUDE.md                          ← este arquivo (regras globais)
src/
  modules/
    <modulo>/
      CLAUDE.md                    ← regras, padrões e exemplos do módulo
  <outra-camada>/
    CLAUDE.md                      ← se a camada tiver padrões próprios
```

Crie um sub-CLAUDE quando um módulo ou camada tiver padrões que desviam do global ou que precisam de exemplos para serem seguidos corretamente. Mantenha-o atualizado — um sub-CLAUDE desatualizado é pior que nenhum.

**Sub-CLAUDEs existentes:**

_Liste aqui os sub-CLAUDEs do projeto. Mantenha atualizado conforme novos forem criados._

<!-- ex:
- `src/modules/users/CLAUDE.md` — regras do módulo de usuários
- `src/modules/auth/CLAUDE.md` — regras de autenticação
-->

**Arquivos auxiliares na raiz:**

Além dos sub-CLAUDEs por módulo, a raiz do projeto pode conter arquivos `.md` com regras pontuais e focadas (ex: `commit-rules.md`, `security.md`, `migration-guide.md`). Esses arquivos não substituem o `CLAUDE.md` global — complementam com detalhe que não cabe aqui. Liste-os na seção **Arquivos Auxiliares** abaixo da linha divisória e mantenha a lista atualizada.

**Regras deste arquivo:**

- Máximo de **200 linhas** — se ultrapassar, mova conteúdo para o sub-CLAUDE correto
- Regras de uma camada específica → `CLAUDE.md` daquela pasta; regras globais → seção **Regras Globais** ou **O que NÃO Fazer**, sem exemplo de código
- Nunca adicione blocos de código longos neste arquivo — inclua no sub-CLAUDE correto e coloque aqui apenas um link
- **Antes de planejar:** consulte o `CLAUDE.md` de cada módulo, service ou camada que será modificada — esses arquivos contêm regras e padrões específicos que o plano deve respeitar

---

> **Template:** preencha as seções abaixo para cada projeto.

## Arquivos Auxiliares

_Liste aqui todos os arquivos `.md` auxiliares da raiz do projeto e o que cada um contém._

- [`commit-rules.md`](commit-rules.md) — regras de commit, branch, push e PR

<!-- ex:
- [`security.md`](security.md) — autenticação, rate limiting, CORS e validação de entrada
- [`testing-guide.md`](testing-guide.md) — estratégia e padrões de testes
- [`migration-guide.md`](migration-guide.md) — como criar e rodar migrations
-->

## Arquitetura em Uma Linha

_Descreva: framework + ORM/banco + autenticação + estrutura de pastas principal._

<!-- ex: Fastify 5 + Drizzle ORM + PostgreSQL + Clerk Auth — módulos por domínio em `src/modules/` -->

**Módulos:** _liste os módulos de domínio do projeto_

<!-- ex: `auth`, `users`, `roles`, `notifications` -->

## Mapa de Arquivos Críticos

_Liste os arquivos de entrada e configuração mais importantes._

<!-- ex:
- `src/app.ts` — registra plugins e rotas
- `src/config/env.ts` — validação de variáveis de ambiente
-->

## Como Adicionar uma Feature

_Descreva o fluxo padrão para adicionar uma feature no projeto._

<!-- ex:
1. **Schemas** — validações de entrada
2. **Service** — lógica de negócio
3. **Routes** — handlers HTTP + documentação OpenAPI
4. **Registrar** — adicionar ao entrypoint
5. **Migration** — consultar guia antes de gerar
6. **Testes** — cobrir service e/ou routes
-->

## Como Rodar o Projeto

_Descreva os comandos essenciais para setup e desenvolvimento._

<!-- ex:
make setup   # instala deps, cria .env, sobe banco, migrate e seed
make dev     # inicia o servidor com reload
-->

## Convenções de Nomenclatura

_Preencha a tabela com as convenções adotadas no projeto._

| Elemento            | Convenção                             | Exemplo     |
| ------------------- | ------------------------------------- | ----------- |
| _Arquivos_          | _camelCase / kebab-case / snake_case_ | _preencher_ |
| _Interfaces/Types_  | _PascalCase_                          | _preencher_ |
| _Funções/variáveis_ | _camelCase / snake_case_              | _preencher_ |
| _PKs_               | _UUID / serial / cuid_                | _preencher_ |
| _Rotas HTTP_        | _kebab-case_                          | _preencher_ |

## Commits, Branches e PRs

Consulte [commit-rules.md](commit-rules.md) para regras de commit, branch, push e PR.

## Regras Globais

_Documente aqui as regras que valem para todo o código do projeto. As subseções abaixo são sugestões — adapte, adicione ou remova conforme o projeto._

### Auth e Autorização

_Descreva como rotas são protegidas e o que o middleware injeta no request._

<!-- ex: Toda rota protegida usa `preHandler: [app.authenticate]`. O middleware injeta `request.userId` e `request.userRole`. -->

### Banco de Dados

_Descreva o ORM/client utilizado e restrições de uso._

<!-- ex: Use Drizzle ORM — nunca SQL raw exceto via `db.execute(...)`. Operações são assíncronas (`await`). -->

### Tratamento de Erros

_Descreva as classes de erro e como elas chegam ao cliente._

<!-- ex: Lance classes de `src/lib/errors.ts` (`NotFoundError`, `ForbiddenError`). Nunca exponha erros internos ao cliente. -->

### Variáveis de Ambiente

_Indique como acessar variáveis de ambiente com segurança._

<!-- ex: Acesse sempre via `env` de `src/config/env.ts` — nunca `process.env` direto. -->

### Testes

_Descreva a cobertura mínima esperada._

<!-- ex: Toda feature com lógica de negócio (service) ou endpoint (routes) deve ter testes. -->

### Lint e Formatação

_Descreva as ferramentas e os comandos._

<!-- ex: ESLint (`npm run lint`) + TypeScript (`npm run typecheck`). -->

## Segurança

_Aponte para o arquivo ou descreva brevemente as preocupações de segurança do projeto._

<!-- ex: → ver [SECURITY.md](SECURITY.md) para detalhes de autenticação, rate limiting, CORS e validação de entrada. -->

## O que NÃO Fazer

_Liste os anti-padrões específicos deste projeto._

<!-- ex:
- **Não coloque lógica de negócio no routes.ts** — routes só faz HTTP e delega ao service
- **Não acesse o banco diretamente no routes.ts** — use sempre o service
- **Não use `console.log`** — use o logger do framework
- **Não acesse variáveis de ambiente direto** — use o módulo de config
-->