# commit-rules.md — GIT GUIDELINES

Regras de versionamento do projeto. Seguir este guia garante histórico limpo, PRs revisáveis e deploys previsíveis.

## Verificação de branch antes de implementar

Verifique a branch atual com `git branch --show-current`. Se estiver em `main`, `staging` ou `develop`, **não comece** — crie uma nova branch:

- Nova funcionalidade → `feat/<nome>`
- Correção de bug → `fix/<nome>`
- Tarefa técnica/infra → `chore/<nome>`
- Refactor → `refactor/<nome>`
- Documentação → `docs/<nome>`
- Correção urgente em produção → `hotfix/<nome>`

## Lint e Testes antes do Commit

> **⚠ Não commite sem rodar lint e testes.** Código quebrado polui o histórico e trava o CI.

<!-- ex: npm run lint && npm run typecheck && npm run test -->

## Quando fazer um Commit

Após concluir a implementação e rodar lint e testes, sugira commitar. Nunca execute sem autorização.

> **⚠ NUNCA execute `git commit` sem ser solicitado.**

## Quando fazer Push e PR

Após tudo concluído, pode sugerir o push. Nunca execute sem autorização explícita.

> **⚠ NUNCA execute `git push` nem abra PR sem ser solicitado e autorizado.**

## Commits — Conventional Commits

Padrão: `<tipo>(<escopo opcional>): <descrição curta>`

**Tipos:**

| Tipo       | Quando usar                                   |
| ---------- | --------------------------------------------- |
| `feat`     | nova funcionalidade visível ao usuário        |
| `fix`      | correção de bug                               |
| `refactor` | mudança de código sem alterar comportamento   |
| `chore`    | tarefas de manutenção (deps, config, scripts) |
| `docs`     | apenas documentação                           |
| `test`     | adição ou correção de testes                  |
| `perf`     | melhoria de performance                       |
| `ci`       | mudanças em pipelines de CI/CD                |

**Regras:**

- Inglês, imperativo, sem ponto final: `add`, `fix`, `remove` — não `added`, `fixes`
- Máximo 72 caracteres na primeira linha
- Escopo identifica o módulo: `feat(auth):`, `fix(users):` ou apenas `feat:`
- Breaking changes: `feat(api)!:` com detalhes no corpo do commit

**Exemplos:**

```
feat(auth): add JWT refresh token rotation
fix(users): prevent duplicate email on signup
refactor(feed): extract pagination logic to helper
chore: update drizzle-orm to v0.30
```

Breaking change com corpo:

```
feat(payments)!: replace Stripe with Adyen

BREAKING CHANGE: PaymentIntent shape changed — see migration guide
```

## Branches

Inspirado no Git Flow, com nomenclatura curta:

```
main        ← produção (sempre estável)
develop     ← integração das features
└── feat/<descricao>
└── fix/<descricao>
└── chore/<descricao>
└── refactor/<descricao>
└── docs/<descricao>
└── hotfix/<descricao>    ← urgente, direto de main
```

Nomenclatura: `kebab-case`, curta e descritiva — `feat/user-avatar`, `fix/signup-validation`.

**Ciclo:**

1. Crie a branch a partir de `develop` (ou `main` para hotfix)
2. Commits atômicos — um assunto por commit, sempre após lint e testes verdes
3. Abra PR para `develop` ao concluir

## Regras técnicas de Push

- **Nunca force-push em `main` ou `develop`**
- Force-push em branches pessoais é permitido após rebase — use `--force-with-lease`
- Prefira rebase a merge para manter histórico linear: `git rebase develop`
- Faça push só ao concluir — evita rebase em branch que já está na origin

## Pull Requests

_Preencha as regras específicas do projeto._

### Tamanho
_Defina o tamanho máximo esperado de um PR._
<!-- ex: Idealmente menos de 400 linhas. PRs maiores devem ser justificados. -->

### Revisão
_Defina quantos aprovadores são necessários._
<!-- ex: Mínimo 1 aprovação. PRs que afetam auth ou banco exigem 2. -->

### CI
_Liste os checks obrigatórios antes do merge._
<!-- ex: lint, typecheck e testes devem passar. -->

### Descrição
_Descreva o que deve constar na descrição de um PR._
<!-- ex: O que foi feito, por que, e como testar. Screenshots para mudanças visuais. -->

## O que NÃO Fazer

- **Não execute `git commit` ou `git push` sem autorização explícita** — nem mesmo em sessões onde já houve autorização anterior
- **Não commite diretamente em `main`, `staging` ou `develop`** — sempre via PR
- **Não misture assuntos no mesmo commit** — um commit, uma responsabilidade
- **Não use mensagens vagas** — `fix bug`, `update`, `WIP` não são aceitáveis
- **Não force-push em branches compartilhadas** — prefira `--force-with-lease` em branches pessoais