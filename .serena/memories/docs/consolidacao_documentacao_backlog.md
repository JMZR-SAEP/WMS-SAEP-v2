# Consolidação da documentação — backlog acionável

Contexto para atacar os achados da auditoria de documentação em PRs posteriores, em
conversas novas. Auditoria feita em **2026-08-19**, somente leitura, sobre
`main` em `2740bc8`.

## De onde isso vem

Relatório completo foi gravado **só no scratchpad da sessão** (efêmero, já perdido).
**Esta memória é a única fonte sobrevivente** — ela é autossuficiente de propósito.
Cada achado abaixo traz a evidência que o sustenta; não precisa remedir.

Método usado: inventário de 170 arquivos de doc/config, `git log --name-only` por
arquivo, leitura integral dos documentos-núcleo, cruzamento contra `apps/`, `config/`,
`.github/workflows/ci.yml`, `pyproject.toml` e as 127 issues/PRs de
`JMZR-SAEP/WMS-SAEP-v2` (#1 a #128).

## Premissa que estava errada — não repetir o erro

**`.serena/memories/` NÃO entra em contexto automaticamente.** Na ativação do projeto
o Serena devolve só a *lista de nomes*; conteúdo só vem por `read_memory` explícito.

Contexto realmente automático, medido: `CLAUDE.md` 10 B + `AGENTS.md` 6.574 B +
`MEMORY.md` do Claude 1.508 B + descrições de 4 skills/2 agents 1.453 B + lista de
nomes ~200 B ≈ **9,7 KB ≈ 2.400 tokens/sessão**.

Consequência: **não há economia de tokens relevante a fazer.** Quem propuser
"enxugar a doc para economizar contexto" está resolvendo o problema errado. O ganho
desta consolidação é **reduzir erro**, não custo. Único alvo com efeito real por
sessão é `AGENTS.md` (68% do total) — e ele já está enxuto.

---

## Bloco A — correções pontuais, risco quase nulo, nenhuma quebra de referência

Cada linha é fato verificado. Podem ir em um PR só (`docs/corrige-achados-auditoria`).

| # | Alvo | O que está errado | Evidência |
|---|---|---|---|
| A1 | `AGENTS.md` §comandos · `.claude/skills/gates/SKILL.md` · `docs/ci-pipeline.md:194-202` | falta `make css-build` — **maior custo operacional do repo** | `ci.yml:64-82` tem job que roda `make css-build` e falha se `apps/core/static/core/css/app.css` (56.694 B, versionado) divergir. O skill fala em "os **cinco** gates"; o CI tem **6 jobs**. Agente edita template → `/gates` verde → PR quebra |
| A2 | `README.md:122` · `Makefile:97` | ambos dizem que `make clean` limpa "sem afetar o banco" | `Makefile:97` é `clean: resetpostgres`; `resetpostgres` (`:112-117`) roda `DROP SCHEMA IF EXISTS public CASCADE` |
| A3 | `docs/adr/0012:3-5` | Status ainda `Proposto` | CI em produção há meses, badge em `README.md:1`, `docs/ci-pipeline.md` é manual operacional, e o job `css-build` nem existe na ADR |
| A4 | `docs/ci-pipeline.md:24, 121, 135, 137, 194-202` | `:24` manda `uv run pytest` sem flags (contradiz `ci.yml:149` e a própria `:7`); `:137` manda `@pytest.mark.flaky(reruns=2)` — `pytest-rerunfailures` não está em `pyproject.toml:14-21` e o CI usa `--strict-markers`, então **seguir a instrução quebra a suíte**; "floppy" em vez de "flaky" 3× (`:121, :135, :137`); `:194-202` lista 5 checks, CI tem 6 | leitura direta |
| A5 | `README.md:153` | diz `notificacoes` "em construção — aguarda #45" | app completo: models, views, urls (3 rotas), services, selectors, policies, `context_processors.py`, admin e **6 módulos de teste**. Issue #45 fechada |
| A6 | `.env.example:9` · `README.md:66-67` | `CORS_ALLOWED_ORIGINS` documentado | busca em `config/` e `apps/`: **zero ocorrências**. `django-cors-headers` não é dependência. Resíduo da era DRF/SPA que o projeto rejeitou |
| A7 | `docs/design-system.md:248` + §Formulário | diz "21 componentes" | existem **22** `.html` em `apps/core/templates/components/` (26 com `icons/`). Falta `field_error.html` no índice — componente real, com `{% comment %}` de 14 linhas, teste próprio (`apps/core/tests/test_components_field_error.py`) e 4 consumidores. `docs/plans/audit-frontend-restante.md:21` dá um terceiro número: 24 |
| A8 | `DESIGN.md:222` vs `:243` | `:222` lista "estorno" entre usos legítimos de `danger`; `:243` diz "Nenhum evento legítimo do domínio recebe a cor da recusa" | contradição interna no mesmo arquivo. **É a issue #128, aberta — HITL, não resolver sozinho.** Ver `mem:frontend/etapa2_feedback_backlog` |
| A9 | `docs/processos-almoxarifado.md:109` | "O sistema deve permitir estorno parcial de requisições" | assinatura real: `estornar_requisicao(*, ator_id: int, requisicao_id: int, justificativa: str)` em `apps/requisicoes/services/ciclo_vida.py:652-657` — sem quantidade; reverte a entregue líquida inteira |
| A10 | `docs/matriz-permissoes.md:12` | cita `permission_classes` (DRF) | projeto declara não ter API REST (`README.md:10`, `PRODUCT.md:48`) |
| A11 | `AGENTS.md:3` | `@/Users/jmzr/.codex/RTK.md` — caminho absoluto de máquina específica em arquivo versionado | quebra em qualquer outro clone |

---

## Bloco B — reescritas, risco médio

### B1 — Reescrever `docs/CONVENTIONS.md` (a ação de maior impacto)

**É o nó de maior grau do repositório: 48 referências de entrada e 5 automações
apontam para ele.** E é o documento mais atrasado do núcleo: **2 commits, o último em
2026-05-21**.

O que está errado, medido:

1. **Assinatura de policy revogada.** `:60` diz `pode_*(ator, obj) -> bool`. Código real:
   `pode_*(papel: PapelEfetivo, recurso)` — ver `apps/requisicoes/policies.py:159` e `:312`.
   A virada foi a issue #52 (fechada, `docs/plans/52-flip-contrato-policies.md`,
   2026-07-01), registrada como **emenda dentro de ADR-0011**; `CONVENTIONS.md` nunca
   foi atualizado.
2. **Cinco módulos obrigatórios ausentes.** Busca literal no arquivo devolve "não" para:
   `PapelEfetivo`, `traduz_erro_dominio`, `paginar_com_filtros`, `composites`,
   `acoes_disponiveis`, `Operacao`. Todos existem: `apps/accounts/papeis.py`,
   `apps/core/presentation.py`, `apps/core/listagem.py`,
   `apps/requisicoes/services/composites.py`, `apps/requisicoes/selectors.py`.
3. **Reimplementa código já extraído.** `:160-166` mostra `htmx_redirect` testando
   `request.headers.get("HX-Request") == "true"`. O real (`apps/core/http.py:23`) usa
   `request.htmx` e documenta por que não delega a `HttpResponseClientRedirect`
   (aquele responde 200, quebraria o contrato 204 do PRG).
4. **Layout de app incompleto** (`:12-23`): omite `types.py`, `context_processors.py`,
   `templatetags/`, que existem.
5. **Falta a tabela exceção→HTTP**, que hoje só existe em
   `.claude/skills/contrato-camadas/SKILL.md`: `PermissaoNegada` 403, `DadosInvalidos`
   422, `EstadoInvalido` 409, `ConflitoDominio` 409.

Fonte para a reescrita: `.claude/skills/contrato-camadas/SKILL.md` está **correto e
atual** — mas ele próprio declara "não é fonte de verdade". Hoje o resumo sabe mais que
a fonte que ele diz obedecer. Inverter isso é o objetivo do B1.

Fazer em PR próprio, rodando o agente `revisor-camadas` contra o resultado.

### B2 — ADR-0019 consolidando as emendas de 2026-06-26

**Nenhum dos 18 ADRs está marcado como *superseded*** — a palavra não aparece em
nenhum arquivo. ADR-0004 e ADR-0011 foram **emendados no lugar**, com trechos do corpo
marcados `> **Substituído pela Emenda 2026-06-26.**` (ADR-0011:110 e :146).

Isso preserva o registro, mas deixa o corpo com regra revogada — e **já custou duas
automações para compensar**:

- `.claude/skills/contrato-camadas/SKILL.md:22-25`: "⚠️ ADR-0004 e ADR-0011 têm emendas
  … Ler só o começo do ADR entrega regra revogada."
- `.claude/agents/revisor-camadas.md:31`: "Quando a emenda de um ADR contradiz o corpo
  original, a emenda vence."

Os 3 pontos mais revogados: policies recebem `PapelEfetivo` e não `User`;
`transitions.py` é keyed por `Operacao` e não por estado de origem; a view não abre
`transaction.atomic` — isso é service composto.

**Restrição inviolável: ADR aceita não se reescreve nem se apaga.** O remédio é ADR
nova superseding, com o registro antigo preservado. Depois disso o aviso do skill pode
ser simplificado.

### B3 — Corrigir `.design/INFORMATION_ARCHITECTURE.md`

Navegação está **exata**: a tabela de 3 seções / 11 itens (`:57-72`) bate item a item
com `NAVEGACAO` em `apps/core/templatetags/core_tags.py:351-442`. Não mexer nisso.

Rotas divergem:

| Linha | Diz | Real |
|---|---|---|
| `:19-21` | `editar/`, `atender/`, `devolucao/` "[fora de escopo atual]" | as três implementadas |
| `:160`, `:187` | `/requisicoes/nova/` e `atender/` "[escopo futuro]" | implementadas |
| `:257` | `/requisicoes/<id>/devolucao/` | real: `<pk>/devolver/<item_pk>/` (por item) |
| `:276` | `reverse('requisicoes:atender', …)` | nome real: `registrar_atendimento` → esse `reverse` levanta `NoReverseMatch` |
| `:47` | "`LOGIN_REDIRECT_URL = '/'` em `settings.py`" | está em `config/settings/base.py:109`; não existe `settings.py` |
| Site Map | — | omite `copiar/`, `estornar/`, `recusar/`, `autorizar/`, `cancelar/`, `separar-retirada/`, `enviar/`, `retornar-rascunho/`, `materiais/busca/`, `beneficiarios/busca/`, todo `/notificacoes/` e 8 das 10 rotas de `/estoque/` |

Importa porque `.claude/skills/nova-slice/SKILL.md` exige ler este arquivo na Fase 0.

### B4 — Criar `docs/processos-importacao-scpi.md`

O contrato do arquivo SCPI **só existe em código**: `CADPRO;DENOMINACAO;QUAN3`, alias
`DISC1` para nome e `QT` para quantidade, quantidade em `000.000.000`, tolerância a BOM
e a linhas quebradas. Fonte: `apps/estoque/selectors.py:89-155` + ~30 testes em
`apps/estoque/tests/`. `CONTEXT.md` só diz que `CADPRO` ↔ `Material.codigo`.

Grave porque é a **única integração com sistema externo**, e `PRODUCT.md:30` declara
que a coexistência com o SCPI é **indefinida**, não fase de migração.

### B5 — `docs/agents/` em PT-BR, e corrigir a instrução errada

Os 3 arquivos (`domain.md`, `issue-tracker.md`, `triage-labels.md`) estão
**inteiramente em inglês**, dentro do glob `docs/**/*.md` que `.coderabbit.yaml:195-196`
declara PT-BR obrigatório. Escaparam por serem de 2026-05-20, anteriores à config.
1 commit cada, nunca tocados.

Além do idioma:

- `issue-tracker.md:14` diz "Infer the repo from `git remote -v`" — **instrução errada**.
  Issues vivem no `origin` (`JMZR-SAEP`), PRs e CodeRabbit no fork `joaozuneda6`. Ver
  `mem:project_overview` para a topologia.
- Falta documentar que **`gh issue create --label` falha em silêncio** aqui: a conta
  ativa `joaozuneda6` abre issue em `JMZR-SAEP` mas não rotula
  (`AddLabelsToLabelable`). Rotular num segundo passe com
  `GH_TOKEN=$(gh auth token --user joaorighetto)` na própria invocação, sem trocar a
  conta ativa. Hoje isso só vive em `mem:frontend/etapa2_feedback_backlog`.
- `triage-labels.md` é **tabela identidade** — as duas colunas têm os mesmos valores —
  e termina com a instrução de template "Edit the right-hand column to match whatever
  vocabulary you actually use". Zero informação.
- `domain.md` é genérico de template ("if it exists", "proceed silently") e cita
  `/grill-with-docs`.

Se fundir os três, **`AGENTS.md` cita os 3 caminhos literais** — atualizar no mesmo commit.

---

## Bloco C — arquivamento (desordem, não custo)

> Numeração sem C7 e C11 de propósito: C7 (`.impeccable/`) virou não-decidido nº 1,
> e C11 (caminho absoluto do RTK em `AGENTS.md:3`) virou A11. Os identificadores
> foram preservados para casar com quem já citou o achado.

**Arquivar é `git mv` para `docs/arquivo/`, nunca `rm`.** A rastreabilidade
issue→plano→PR é o que torna o histórico auditável, e `PRODUCT.md:82` eleva
auditabilidade a princípio de produto.

| # | Ação | Cuidado |
|---|---|---|
| C1 | `docs/plans/` → `docs/arquivo/plans/`, **exceto** `audit-frontend-restante.md` (vivo: 4 refs., citado pelos planos #119/#120/#121 e por `mem:frontend/etapa2_feedback_backlog`) | `docs/plans/77-alert-component.md` é citado **de dentro de um template**: `apps/core/templates/components/alert.html`. Quebra código, não doc |
| C2 | `docs/superpowers/plans\|specs` → `docs/arquivo/superpowers/` | 2 arquivos de 2026-07-02 contra 93 em `docs/plans/`; descrevem `requisicoes:historico`, implementado; scaffolding em inglês ("REQUIRED SUB-SKILL"). Convenção descontinuada |
| C3 | `.design/TASKS.md`, `TASKS_REMEDIATION.md`, `movimentacoes-estoque/TASKS.md`, `audit-uiux-2026-07/` → `.design/arquivo/` | **`AGENTS.md` manda ler `.design/TASKS.md`** (contexto automático); `.claude/skills/nova-slice/SKILL.md` também; `mem:task_completion` idem. Editar os três no mesmo commit |
| C4 | Antes de C3: resolver os 2 conflitos de `.design/TASKS.md` com o design system | ver "conflitos `.design/` ×" abaixo |
| C5 | `docs/code-review-guidelines.md`: extrair §"Anti-padrões de review" (`:195-204`) e §"Checklist final" (`:208-215`) para `docs/CONVENTIONS.md` ou `.coderabbit.yaml`; **apagar o resto** | **0 referências de entrada em todo o repo.** 1 commit, 2026-05-21. ~20 de 217 linhas são originais; o resto duplica `CONVENTIONS.md` + `.coderabbit.yaml`. Já tem texto obsoleto: `:128` diz "movimentação e reserva, **quando implementadas**" — implementadas por ADR-0015 desde 2026-06-12 |
| C6 | `docs/processos-almoxarifado.md`: apagar §1.3 (`:31-75`, duplica `estado-transicoes-requisicao.md` §3 com menos informação), desduplicar §1.4 (`:64-69` repete literalmente `:91-96` **dentro do mesmo arquivo**), manter §1.1/§1.2 | 3 refs. de entrada — preservar o caminho |
| C8 | Cabeçalho "snapshot de handoff, não especificação viva" nos 6 `DESIGN_BRIEF.md` | nada hoje diz isso, por isso os `TASKS.md` são lidos como pendência real |
| C9 | `docs/matriz-invariantes.md`: coluna "Ref." usa `Crit. N.N` / `Modelo N.N` **34 vezes**; essa notação aparece em **um único arquivo do repo — ele mesmo**. Documento-fonte não existe aqui | ou recuperar a fonte, ou reescrever a coluna |
| C10 | `docs/matriz-permissoes.md`: marcar as 6 linhas da §4 que são backlog, não regra viva — `:46` (Gerenciar papéis), `:89` (Consultar divergências críticas), `:93`, `:94` (relatórios), `:95` (Exportar CSV), `:96` (Painel Gestão) | busca por `relatorio\|exportar_csv\|painel_gestao\|divergencias_criticas\|gerir_papeis` em `apps/`: **zero acertos**. Marcar cala 6 falsos positivos permanentes do agente `auditor-permissoes` |
| C12 | `mem:project_overview`: diz que `/requisicoes/` é rota canônica — **não é**, não há `path('')` em `apps/requisicoes/urls.py`. Lista de rotas também omite `historico`, `copiar`, `estornar`, `devolver`, `beneficiarios/busca` | — |
| C13 | `mem:frontend/etapa2_feedback_backlog` cita `.impeccable/critique/2026-08-18T11-33-52Z__apps-core-templates-components-feedback-e-estado.md` — **arquivo não existe no repo** | referência pendurada |

---

## Mapa de referências fixas — consultar antes de mover qualquer coisa

Skills, agentes e hooks apontam para caminhos literais. Levantado por varredura de
`.claude/**`:

| Artefato | Aponta para |
|---|---|
| `.claude/agents/auditor-permissoes.md` | `docs/matriz-permissoes.md`, `docs/matriz-invariantes.md`, `docs/adr/0011-*` |
| `.claude/agents/revisor-camadas.md` | `docs/CONVENTIONS.md`, `docs/adr/0004-*`, `docs/adr/0011-*` |
| `.claude/skills/contrato-camadas/SKILL.md` | `docs/CONVENTIONS.md`, `docs/adr/0004-*`, `0010-*`, `0011-*`, `docs/matriz-permissoes.md`, `docs/matriz-invariantes.md` |
| `.claude/skills/nova-slice/SKILL.md` | `.design/INFORMATION_ARCHITECTURE.md`, `.design/<area>/DESIGN_BRIEF.md`, `.design/TASKS.md`, `docs/CONVENTIONS.md`, `docs/design-system.md`, `docs/matriz-permissoes.md`, `docs/matriz-invariantes.md` |
| `.claude/skills/gates/SKILL.md`, `reset-schema/SKILL.md` | `AGENTS.md` |
| `.claude/hooks/bloqueia_migrations.py` | `AGENTS.md` |
| `.claude/settings.local.json` | `docs/design-system.md` |
| `AGENTS.md` | `docs/agents/{domain,issue-tracker,triage-labels}.md`, `docs/CONVENTIONS.md`, `docs/design-system.md`, `.design/*`, ADR-0004/0008/0009/0010/0011 |
| `apps/core/templates/components/alert.html` | `docs/plans/77-alert-component.md` |

Contagem de referências de entrada (maior primeiro): `matriz-invariantes.md` 53,
`CONVENTIONS.md` 48, `design-system.md` 44, `AGENTS.md` 22, `matriz-permissoes.md` 22,
`CONTEXT.md` 19, `estado-transicoes-requisicao.md` 19. **`code-review-guidelines.md` 0.**

---

## Conflitos `.design/` × fonte superior — `.design/` perde

Por `AGENTS.md`, `.design/` não sobrepõe ADR, `docs/design-system.md`,
`docs/CONVENTIONS.md`, domínio, testes ou código vivo.

1. `.design/TASKS.md:69` — "Sem botões disabled por regra de negócio — apenas o
   permitido aparece". `docs/design-system.md:154-159` e `DESIGN.md:323, 364` mandam o
   oposto: **ação de workflow bloqueada fica visível e desabilitada, com o motivo em
   texto** amarrado por `aria-describedby`, usando `aria-disabled` e não `disabled`
   nativo. O design system vence.
2. `.design/TASKS.md:95` — pede "`<table>` semântico com `thead`+`th scope`".
   `DESIGN.md:278` ("A Regra do Cartão Único") e `:378` ("Don't reintroduzir `<table>`
   em listagem") proíbem. O design system vence.

`.design/TASKS.md` também tem 3 itens marcados como abertos que já existem:
`button.html` (`:17`), `form_field.html` (`:19`), `status_badge.html` (`:21` — foi
renomeado para `badge.html`). E `:9` diz "Última sincronização: 2026-06-23" com último
commit em 2026-08-18.

---

## Lacunas — o que não existe em lugar nenhum

| Falta | Destino proposto |
|---|---|
| Contrato do arquivo SCPI | `docs/processos-importacao-scpi.md` (B4) |
| `css-build` como gate | `AGENTS.md` + skill `gates` (A1) |
| Onboarding: por onde começar a ler entre 18 ADRs, 10 docs, 6 briefs e 93 planos | `docs/agents/domain.md` reescrito, ou seção no `README.md` |
| Estratégia de deploy do piloto — **onde** sobe, como, quem opera, rollback | ADR nova ou `docs/deploy-piloto.md`. Existe `config/settings/piloto.py`, `README.md:72-98`, `.env.example` e `docs/checklist-go-live.md`, mas nenhum ADR do piloto |
| Tabela exceção→HTTP status | `docs/CONVENTIONS.md` (B1) |
| Onde vive a aprovação do gate do CodeRabbit (issue comment do walkthrough, não `/pulls/N/reviews`) | `AGENTS.md` ou o que sobrar de `code-review-guidelines.md` |

Já têm respaldo versionado, **não** precisam de doc nova: contrato de mensagens ao
usuário (`CONVENTIONS.md:153-224`), estratégia de seed (ADR-0009 + `:89-123`),
estratégia de testes (ADR-0010 + `:125-151`).

---

## Não-decididos — bloqueiam, precisam do dono do produto

1. **`.impeccable/design.json` (36 KB) e `.impeccable/critique/` (21 KB): regenerar,
   arquivar ou apagar?** Não se sabe se `/impeccable` **lê** `design.json` como entrada
   ou só o escreve. Fato: `generatedAt` 2026-08-12, `narrative.overview` é cópia
   literal do de `DESIGN.md`, e ele ainda lista **"A Regra da Dupla Renderização"** —
   revogada por `DESIGN.md:278-282` ("A Regra do Cartão Único"), que documenta a
   medição que a derrubou. Suas classes `.ds-btn-*`/`.ds-badge-*` têm **zero
   ocorrências** em `apps/**`.
2. **`DESIGN.md` e `PRODUCT.md` ficam na raiz?** Ambos carregam schema de ferramenta
   (`<!-- impeccable:product-schema 1 -->`; frontmatter com 66 tokens OKLCH). **Não
   fundir em prosa.** Mover para `docs/` reduz ruído da raiz, mas não se sabe se o
   Impeccable procura por caminho fixo. Premissa assumida: ficam onde estão.
3. **B2 (ADR-0019) vale o custo?** Alternativa: manter emendas in loco + o aviso no
   skill. Funciona hoje — mas funciona porque uma automação compensa a forma do
   documento.
4. **`docs/agents/` vira 1 arquivo PT-BR ou 3 seções em `AGENTS.md`?** A segunda opção
   acrescenta ~40 linhas ao contexto automático — **não recomendada**.
5. **Matriz de permissões vira duas (vigente × planejada) ou ganha coluna de status?**
   Coluna de status (C10) é mais barata e preferida.
6. **`docs/plans/audit-design-system.md` e `audit-frontend-restante.md` são auditorias,
   não planos de issue.** Criar `docs/auditorias/` ou deixá-los em `docs/plans/` quando
   o resto for arquivado?
7. **A8 / issue #128** — a contradição `danger`/estorno é HITL declarada.

---

## Fatos medidos que não precisam ser remedidos

- **`docs/plans/`: 93 arquivos, 89 com prefixo numérico, todos mapeando issue ou PR
  fechada. Zero abertas.** Cruzado com as 127 issues/PRs de `JMZR-SAEP/WMS-SAEP-v2`.
  **Ressalva:** 11 arquivos usam prefixo de 1 dígito (`5-`, `6-`×2, `7-`×3, `8-`×3,
  `9-`×2) e a numeração **colide com a do tracker atual** —
  `docs/plans/6-historico-movimentacoes-estoque.md:1` diz "Issue #6", mas a #6 de
  `JMZR-SAEP` é "Minhas requisições e detalhe com timeline". `gh5-modal-universal.md:3`
  aponta para `jmarcoszuneda/WMS-SAEP-v2#5` — um **terceiro** nome de repositório.
  Qualquer automação que cruze prefixo × issue vai errar nesses 11.
- **Checklists mortos:** `.design/TASKS_REMEDIATION.md` 41 abertos / 0 feitos, parado
  desde 2026-05-27. `.design/movimentacoes-estoque/TASKS.md` 19 abertos / 0 feitos,
  mas a tela está em produção (`estoque:historico_movimentacoes`) e o selector
  `movimentacoes_visiveis_para` — a task 1 — é citado como fronteira viva em
  `matriz-permissoes.md:106`. `docs/checklist-go-live.md` **não tem checkbox nenhum** —
  é runbook, está saudável, não mexer.
- **`.design/telas-operacionais/TASKS.md` não existe.** O arquivo real é
  `.design/movimentacoes-estoque/TASKS.md`.
- **ADR-0013 × 0015 × 0017 não se contradizem — se sucedem.** 0013:46 ("baixa direta de
  `saldo_fisico`") é anterior ao ledger; 0015 retrofita os services; 0017:68 declara
  explicitamente sua relação com 0015. A composição está registrada em
  `CONTEXT.md:209-213`. **Único achado: falta em ADR-0013 uma nota prospectiva para
  ADR-0015.** Não há supersessão a declarar entre as três.
- **ADR-0014 tem 0 citações** em todo o repo. Baixa tração também: 0006 (2), 0007 (3),
  0013 (4), 0001 (5), 0012 (5). Alta: 0011 (59), 0010 (57), 0005 (30), 0004 (28),
  0015 (23).
- **Dois formatos de cabeçalho de ADR coexistem.** 0008/0013/0016 usam
  `**Status**: / **Data**: / **Decisores**:`; os outros 15 usam `## Status` sem data.
  ADR-0008 escreve `Accepted` em inglês.
- **`docs/matriz-invariantes.md`: 58 códigos declarados, 19 citados literalmente em
  `apps/`** (`EST-02, EST-06, EST-07, EST-11, LED-01, LED-02, NOT-01, REQ-04, REQ-08,
  REQ-09, SAE-01, SAE-04, SAE-09, TR-015B, USR-01, USR-04, USR-05, USR-06, USR-07`).
  Isso mede **citação, não cumprimento** — não concluir que os outros 39 estão
  violados.
- **Código: 27 funções `pode_*`** (requisicoes 16, estoque 9, notificacoes 1,
  accounts 1) contra ~55 linhas de ação na §4 da matriz. Único sem par `exigir_pode_*`:
  `pode_ser_beneficiario` — pode ser predicado interno deliberado.
- **`CONTEXT.md` tem cabeçalhos em inglês** (`## Language` `:7`, `## Relationships`
  `:168`, `## Example dialogue` `:223`, `## Flagged ambiguities` `:234`) — resíduo do
  template do `/grill-with-docs`. Fora de `docs/**`, o CodeRabbit não pega.
- **`Makefile:136` declara `test` em `.PHONY` mas não existe alvo `test:`.** E
  `.coderabbit.yaml:242` manda revisar "`make test` deve refletir gates reais" —
  instrução sobre alvo inexistente.
- **A divisão `DESIGN.md` ↔ `docs/design-system.md` é deliberada e declarada**
  (`design-system.md:16-18`): linguagem visual lá, regra operacional aqui. ~40 linhas
  se sobrepõem (z-index, 4 degraus, 44px, Token-nunca-Shade, Reversão-não-é-Erro, nota
  sobre `--color-info*`). **Aceitável — não "consolidar".**
- **Documentos saudáveis, não mexer além das correções pontuais:**
  `docs/estado-transicoes-requisicao.md` (8 estados e 10 operações batendo com
  `EstadoRequisicao` e `TRANSICOES`), `docs/design-system.md` (19 commits, 8 regras
  invioláveis com teste nomeado), `docs/checklist-go-live.md`, os 4 skills e os 2
  agents de `.claude/`.

---

## Armadilhas

- **Esta memória nasce untracked.** `.serena/memories/` é versionado, mas arquivo novo
  não sobrevive a troca de branch nem a limpeza da working tree. **Commitar junto com o
  trabalho da branch em que foi criada.** Já aconteceu antes — ver
  `mem:frontend/etapa2_feedback_backlog`.
- **Nunca `rm` em plano, brief ou ADR.** Arquivar por `git mv`.
- **Nenhum PR deste backlog deve tocar `.design/` e `docs/` na mesma mudança** sem
  atualizar `AGENTS.md` no mesmo commit quando um caminho citado por ele se mover.
- **CodeRabbit rejeita `docs/**/*.md` em inglês** (`.coderabbit.yaml:3, 195-196`), e o
  template do `/ship-issue` gera cabeçalhos em inglês — traduzir antes de abrir PR.
- **Nunca usar pipe, redirecionamento, `grep`/`head`/`tail` ou truncamento** de saída
  (`AGENTS.md`). Em falha, ler o `[full output: ...]` do RTK Tee System.

## O que não foi verificado

- Se os 39 códigos de invariante não citados estão implementados (exigiria ler ~2.000
  testes).
- Se as regras dos briefs de `.design/` (layout, copy, responsividade por tela) foram
  implementadas — templates não foram abertos tela a tela.
- SLA do pipeline (`ci-pipeline.md:246-256`) — CI não foi executado.
- **Se há regra viva que só existe em walkthrough do CodeRabbit** — os PRs do fork
  `joaozuneda6` não foram consultados. A memória persistente do Claude
  (`~/.claude/projects/-Users-jmzr-Dev-WMS-SAEP-v2/memory/project_coderabbit_gate_walkthrough.md`,
  fora do repo — não é memória Serena) sugere que sim.
