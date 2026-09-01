# Plano de auditoria — front-end restante

Continuação da auditoria de UI conduzida via `/impeccable`. As 19 telas full-page já foram
auditadas (blocos 1–4 de requisições/auth + blocos A–D de estoque/notificações). Este plano cobre
o que sobrou: a camada de tokens, os componentes compartilhados, os partials de domínio e o
comportamento em JS.

> **Estado deste plano (revisado em 2026-08-31).**
>
> - **Etapas 0–5 concluídas.** Não mexer — ver "Etapas concluídas" abaixo. A Etapa 5 (listagem em
>   cartões) fechou com audit + correções + critique; o reteste da tabela no catálogo está em
>   `DESIGN.md`.
> - **Etapa 7 concluída** (2026-08-31): audit + 6 PRs de correção + critique. Pontuação heurística
>   23/40; o P0 e os P1 que sobraram viraram as issues #161–#164. Ver "Etapa 7" abaixo.
> - **Etapa 8 concluída** (2026-09-01): audit sem alvo + correções + critique sem alvo. Pontuação
>   heurística **21/40** — a baseline do produto que não existia. Ver "Etapa 8" abaixo.
> - **Etapa 6 pendente.** Tem duas fases: `/impeccable audit` (defeito técnico — a11y, responsivo,
>   performance) seguida de `/impeccable critique` (revisão de UX com pontuação heurística sobre o
>   resultado do audit). A critique fecha a etapa e alimenta o backlog de `polish` se restar P0/P1.
> - Contexto da revisão: `components/table.html` virou chrome de cartões (#83 — não há mais tabela),
>   entraram `filter_chips.html` e `filter_presets_periodo.html` (#152–#154), `field_error.html` e
>   `_icone_nivel.html` saíram de markup duplicado (#127).

## Por que a ordem importa

As telas foram auditadas de fora pra dentro. O restante vai de dentro pra fora: token → componente
→ partial → regressão. Auditar componente antes de token gera retrabalho, porque todo achado de cor,
espaçamento ou tipografia no componente é sintoma de decisão tomada em `input.css`.

Cada etapa é uma branch `fix/{desc}`, com code-review antes do merge, conforme `AGENTS.md`.

Da Etapa 5 em diante, a sequência dentro da etapa é fixa: **audit → aplicar correções → critique**.
O audit é técnico e gera achados objetivos; a critique roda sobre o resultado já corrigido e dá a
leitura de UX (pontuação, P0/P1). Rodar critique antes de fechar o audit mede uma superfície que vai
mudar.

## Inventário da superfície restante

| Camada | Arquivos | Linhas aprox. |
|---|---|---|
| Tokens e base CSS | `apps/core/static/core/css/input.css` | 810 |
| Componentes compartilhados | `apps/core/templates/components/*.html` (25) + `components/icons/` (3 partials + 15 svg) | — |
| Shell e navegação | `base.html`, `base_auth.html`, `core/_topbar_nav.html`, `core/partials/_side_nav.html`, `core/partials/_messages.html`, `core/partials/_message_item.html` | — |
| Partials de requisições | `apps/requisicoes/templates/requisicoes/partials/**` (13) | — |
| Partials de estoque | `apps/estoque/templates/estoque/partials/**` (10, eram 11) | — |
| Comportamento | `apps/core/static/core/js/*.js` (7) | 1720 |

Notas:

- `app.css` é artefato de build (`make css-build`) — não auditar, não editar à mão.
- `accounts` não tem mais partials: `login.html` e `login_bloqueado.html` são telas full-page e já
  passaram pelo bloco de auth; o erro de login é inline em `login.html`.
- O shell foi reescrito em torno da API de slots do topbar (`.design/topbar/DESIGN_BRIEF.md`):
  `topbar_menu`, `topbar_leading`, `topbar_actions`, `topbar_overflow`, `topbar_domain`.
- **Dark mode está fora do escopo desta auditoria** e saiu das etapas 5 e 8. Não existe no
  produto: zero `prefers-color-scheme` e zero `dark:` no `app.css` compilado, e o `DESIGN.md`
  compromete-se com um mundo claro só ("papel frio sobre papel branco"). Auditar a ausência
  mediria uma premissa do plano, não uma regressão. Adotar dark mode é decisão de produto, com
  ADR e uma revisão inteira da escala de tokens — não item de checklist de auditoria. O que
  existe de real e adjacente já foi resolvido na Etapa 5: `base.html` declara
  `color-scheme: light`, senão o widget nativo do `<input type="date">` dos filtros herdava o
  tema escuro do SO numa página que só existe em claro.

---

## Etapas concluídas (0–5) — não mexer

| Etapa | Escopo | Alvos |
|---|---|---|
| 0 | Tokens semânticos e base CSS | `input.css`, `docs/design-system.md` |
| 1 | Primitivos de ação e entrada | `button`, `form_field`, `item_form_row`, `form-submit.js`, `item_form_row.js`, `acao-bloqueada.js` |
| 2 | Feedback e estado | `alert`, `error_summary`, `field_error`, `empty_state`, `badge`, `_icone_nivel`, `_messages`, `_message_item`, `mensagens.js` |
| 3 | Overlay | `modal`, `_modal_body`, `_modal_icon`, `modal.js` |
| 4 | Busca e filtro | família `autocomplete` + `filter_*` (inclui `filter_chips`, `filter_presets_periodo`) |
| 5 | Listagem em cartões | `table.html` (chrome de cartões), `pagination`, `page_header`, `ordenacao_data`, `icons/` (`_check` removido), `cartao-alvo.js` (novo); reteste da tabela no catálogo em `DESIGN.md` |

Achados dessas etapas viraram issues próprias (#127, #147, #149, #151, #152–#154). Regressão sobre
elas é responsabilidade da Etapa 8.

---

## Etapa 5 — Listagem em cartões (concluída)

Entregue: audit + correções + critique. Achados de UX que sobraram foram para o backlog de
`polish`; o reteste da Regra do Cartão Único no catálogo de materiais está registrado em `DESIGN.md`.
As duas fases abaixo ficam como registro do que foi rodado.

### Fase 1 — audit

```text
/impeccable audit apps/core/templates/components/table.html apps/core/templates/components/pagination.html apps/core/templates/components/page_header.html apps/core/templates/components/ordenacao_data.html apps/core/templates/components/icons/
```

`table.html` **não renderiza mais tabela** — é chrome de cartões via `partialdef` nativo do Django 6
(`cards_abertura`, `card_abertura`), decisão medida da issue #83: com a side nav e o respiro do
`<main>`, a tabela só caberia a partir de ~1370px de viewport. Foco:

- `card_abertura`: `<article>` com hierarquia de heading correta (`<h2>` do título do item), `dl`
  explícito para os campos, badge de estado nunca só por cor
- `cards_abertura`: grid responsivo (1 col mobile → `sm:2` → `2xl:3`) — conferir em viewport curto e
  largo
- Guardrail da #83: os fragmentos não recebem parâmetro que descreva conteúdo de célula. Se a
  auditoria concluir que precisam, isso é um achado — registrar a decisão antes de parametrizar
- `pagination`: página atual anunciada, alvos de toque, contagem total, preservação de querystring
- `page_header`: hierarquia de título e ação primária; interação com o slot `topbar_leading` quando
  a tela sobrescreve a brand
- `ordenacao_data`: controle de ordenação — estado atual anunciado, reversão
- `icons/`: 3 partials (`_caixa_entrada`, `_funil`, `_prancheta`) + 15 svg —
  `aria-hidden` quando decorativos, rótulo quando informativos; conferir se partial e svg do mesmo
  glifo divergem

### Fase 2 — critique

```text
/impeccable critique apps/core/templates/components/table.html apps/core/templates/components/pagination.html apps/core/templates/components/page_header.html apps/core/templates/components/ordenacao_data.html
```

Sobre o cartão já corrigido. Leitura de UX, não de conformidade:

- O cartão carrega mais campos que a tabela carregava — a densidade ficou legível ou virou parede
  de `dl`? Hierarquia entre título, estado e ação primária dentro do cartão
- Escaneabilidade da lista: dá pra achar um item específico correndo o olho, ou todo cartão parece
  igual? Papel do badge de estado nessa varredura
- `page_header` + ação primária + ordenação competindo por atenção no topo da lista
- Pontuação heurística + P0/P1 para o backlog de `polish`

## Etapa 6 — Partials de requisições

### Fase 1 — audit

```text
/impeccable audit apps/requisicoes/templates/requisicoes/partials/
```

13 partials: 5 modais de ação (`_modal_form_cancelar`, `_recusar`, `_retornar`, `_devolucao`,
`_estorno`), `_modal_corpo_atender_retirada`, `_confirmacao_acao` + `_painel_decisao`, `_timeline`,
`_estado_badge`, os alerts `_alert_itens_inelegiveis_corpo` e `_alert_nota_copia_corpo`, e
`_autocomplete_item_beneficiario`.

- `_confirmacao_acao` é só composição (painel de decisão + modal no mesmo `x-data="modalController"`);
  a superfície visível vive em `_painel_decisao.html` — auditar o painel, não a composição
- Pergunta central: quanto disso ainda precisa existir depois das etapas 1–5? Os modais devem ser
  casca fina sobre `components/modal.html`; os alerts, sobre `components/alert.html`. Divergência
  aqui é dívida, não customização

### Fase 2 — critique

```text
/impeccable critique apps/requisicoes/templates/requisicoes/partials/_painel_decisao.html apps/requisicoes/templates/requisicoes/partials/_timeline.html apps/requisicoes/templates/requisicoes/partials/_modal_corpo_atender_retirada.html
```

Sobre os fluxos de decisão da requisição:

- `_painel_decisao`: o par painel + modal comunica o peso da ação (autorizar vs. recusar vs.
  estornar)? Ação destrutiva parece destrutiva antes do clique?
- `_timeline`: a ordem dos eventos e o estado atual são lidos num relance? Ruído vs. sinal
- `_modal_corpo_atender_retirada`: carga cognitiva do passo de conferência
- Pontuação heurística + P0/P1

## Etapa 7 — Partials de estoque (concluída em 2026-08-31)

Entregue: audit + 6 PRs de correção + critique. Pontuação heurística **23/40**; snapshot em
`.impeccable/critique/2026-08-31T16-24-38Z__templates-estoque-partials-delta-movimentacao-html.md`.

### Respostas às perguntas que a etapa fazia

**Os 5 alerts do SCPI dizem coisas diferentes ou são o mesmo alert com texto trocado?**
Três distintos, dois redundantes. `_alert_erro_arquivo_corpo` e `_alert_erro_confirmacao_corpo`
tinham marcação idêntica e divergiam só no título e no nome da variável; viraram
`_alert_erro_scpi_corpo.html`, parametrizado por `titulo`/`detalhe`. Os outros três
(`_divergencias`, `_novos_materiais`, `_sucesso`) têm copy própria com teste. **11 partials → 10.**

**`_chip_so_saidas` deixou referência pendurada?**
Não em código — `components/filter_chips.html` cobre o caso, e não sobrou include, view ou JS
apontando para ele. Sobrava resíduo de nomenclatura em seis nomes de teste e dois comentários,
limpo no PR #52.

**O operador entende o que vai mudar no estoque antes de confirmar?**
Parcialmente. A ordem de informação do modal (identidade → o que muda → o que **não** muda →
irreversibilidade) é a melhor peça do fluxo. O que falha é o peso: `Materiais novos a criar`
(cria saldo), `Divergências a registrar` (registra alerta) e `Linhas lidas do arquivo` (não faz
nada) saem na mesma tipografia. Issue #164.

**O sinal e a magnitude do delta são lidos sem contar dígito?**
Não. O valor tem o mesmo tamanho, família e cor do texto vizinho; o negativo usa hífen ASCII contra
um `+` de largura plena; e `tabular-nums` é inerte porque o número fica inline depois de um rótulo
de largura variável. Issue #163.

**Os alerts como conjunto formam progressão?**
Não — e a progressão está invertida. Os dois do preview saem idênticos em geometria e sem
linha-líder; os dois do desfecho têm linha-líder. Ou seja, os que aparecem quando ainda há decisão
a tomar são os mais planos. Issue #164.

### O que a Fase 1 corrigiu

O achado que governou a etapa: `apps/core/quantidades.py` existe para matar o bug do `1,000` que em
pt-BR se lê *mil*, e **nenhum ponto de estoque tinha adotado a política**. O preview mostrava
`WMS 50,000` ao lado de `SCPI 42` na tela cuja função inteira é comparar os dois.

| PR | Escopo | Severidade |
|---|---|---|
| #50 | Política de precisão por unidade em 4 pontos de render | P0 |
| #51 | Rótulo do form de estorno volta para `.rotulo-campo` | P1 |
| #52 | Renomeia testes do chip de filtro extinto | P3 |
| #53 | Cada saldo do autocomplete leva o próprio rótulo | P1 |
| #54 | Consolida os alerts de erro + conserta o de sucesso | P1/P2 |
| #55 | Legibilidade do preview SCPI (7 achados) | P1/P2/P3 |

Efeito colateral que vale registro: a lista `divida_etapa_7` de
`test_nenhum_rotulo_de_campo_escrito_a_mao` nomeava esta etapa como dona e mandava sumir quando ela
fechasse. **Fechou** — o guarda vale para `apps/` inteiro agora, sem escotilha.

### P0/P1 que sobraram

Viraram issue própria em vez de entrar em `/impeccable polish`, porque o escopo passa de
front-end:

- **#161** (P0) — persistir as divergências e entregá-las ao chefe de almoxarifado. O fluxo termina
  sem produzir a lista de CADPROs que ele veio buscar.
- **#162** (P1) — recorte e âncora no preview: sem filtro nem paginação, 300 linhas dão ~61 telas; e
  a barra de ação é `fixed sm:static`, ou seja, o desktop é a única cena sem barra.
- **#163** (P1) — desenhar `_delta_movimentacao`. O átomo do north star nunca foi desenhado.
- **#164** (P2) — copy: hierarquia da recapitulação, legenda que promete uma cor que nenhum cartão
  veste, e a progressão invertida dos alerts.

### Nota de método

A critique rodou em dois sub-agentes isolados (revisão de design / detector + navegador). O
detector devolveu `[]` nos seis arquivos — um canário sintético confirmou que ele dispara, mas a
engine estática não resolve utility do Tailwind para cor, então **toda medição de contraste veio do
navegador**. Vale para as próximas etapas: em template Django + Tailwind, o `[]` do detector não é
evidência de ausência.

## Etapa 8 — Passe de regressão (concluída em 2026-09-01)

Entregue: audit sem alvo + 3 commits de correção + critique sem alvo. Pontuação heurística
**21/40**; snapshot em `.impeccable/critique/2026-09-01T16-35-35Z__apps.md`.

Método: 20 telas full-page (o plano dizia 19; o inventário de `templates/` fora de `partials/` dá
20 — `copiar_confirmacao.html` não tinha entrado na conta), medidas no navegador a 1366×1000 e
375×812, sob 4 papéis reais, com dataset cobrindo os 8 estados de requisição, 16 materiais, 3
saídas excepcionais e 1 importação SCPI com divergência. A critique rodou em dois sub-agentes
isolados (revisão de design / detector + navegador).

### Respostas às perguntas que a etapa fazia

**Alguma tela regrediu com troca de token ou refatoração de componente?**
Não por refatoração. Os P0 são de outra natureza: a política de precisão de quantidade da Etapa 7
**não alcançou as telas que a #161 criou depois**. `_cartoes_divergencias_scpi.html` imprimia os dois
saldos crus, e com `LANGUAGE_CODE=pt-br` o `DecimalField(decimal_places=3)` saía `820,000` — que em
pt-BR se lê *oitocentos e vinte mil* —, com o delta ao lado, no mesmo cartão, já obedecendo à
política.

**Mobile nas 19?**
Zero rolagem horizontal em 39 das 40 combinações medidas (a exceção: `/requisicoes/7/atender/` a
375px ficou inalcançável depois que a requisição saiu do estado atendível). Três defeitos reais, os
três de quebra de identidade: o número público partido em duas linhas quando o badge é longo, o
`Origem: SXP-2026-000003` partido no meio, e o `<dl>` em `grid-cols-2` fixo dando ~145px por célula.

**As 7 listagens contam a mesma história?**
Não, e a divisão era o inverso da necessidade: as duas telas com recorte completo (`historico`,
`movimentacoes`) têm cartões **inertes**, e as cinco onde se age sobre um registro não tinham como
achar um registro. As duas telas de **decisão** do fluxo eram as que menos informavam — "Minhas
requisições" não dizia nada do conteúdo e a fila de autorização dizia só "Itens: N", o mesmo defeito
que a fila de atendimento já tinha corrigido. Convergido na grafia da fila de atendimento (nome do
material + "e mais N"). O que sobra é a paridade de filtro/ordenação/contagem, que segue em 2 de 7.

**O detector serve?**
Não nesta superfície, e agora está quantificado. Seis canários sintéticos isolaram duas cegueiras
independentes: ele não resolve utility do Tailwind (dispara com `style=` inline, não dispara com
`text-slate-300`) e as regras estruturais só rodam em documento completo. **82 dos 83 templates são
fragmentos e 55 dos 83 usam utility de cor.** A nota de método da Etapa 7 vale como regra: em
template Django + Tailwind, `[]` não é evidência de ausência.

### O que a Fase 1 corrigiu

O achado que governou a etapa: **contraste é do par, não do token**. O piso do cinza de metadado do
`DESIGN.md` tinha sido medido só contra branco (4,76:1); sobre `bg-subtle` dá 4,35:1 e sobre
`primary-subtle` 4,38:1 — reprova. E `danger-accent` reprova nas quatro superfícies (3,48 a 3,81),
sendo a cor do asterisco de campo obrigatório, único indicador visual de obrigatoriedade do produto.

| Commit | Escopo | Severidade |
|---|---|---|
| `abbd109` | Precisão de quantidade no cartão de divergência; gate do "Nova importação"; CTA de saída excepcional; rótulo `" divergências"`; 13 ocorrências de contraste; 3 defeitos de mobile; convergência das 7 listagens; ordenação e carimbo de inativo no catálogo; páginas 403/404/500 | P0/P1/P2 |
| `6a79977` | Guardas das páginas de erro e da lista de notificações | — |
| `586f8cd` | O par `text-tertiary` sobre `primary-subtle` e a afordância do link de notificação | P1 |

Duas regras nomeadas novas no `DESIGN.md` (**A Regra do Cinza Medido**, com a tabela das quatro
superfícies, e **A Regra da Identidade Que Não Quebra**) e guarda de pares de cor em
`test_tokens_semanticos.py`, com o limite registrado: o guarda vê par no mesmo elemento, e o caso de
`atender_retirada.html` — fundo no pai, cor no filho — só apareceu no navegador. Fechar isso é
trabalho da lane Navegador (ADR-0019).

### P0/P1 que sobraram

- **P0** — o saldo é invisível nos dois pontos em que decide (o autocomplete apaga o saldo ao
  selecionar o material; a tela de decisão do chefe não exibe saldo nenhum), e a mensagem de erro
  descarta os dois números que tem em mãos. O chefe fica só com `Recusar`.
- **P1** — paridade de interação das listagens: filtro, ordenação e contagem seguem em 2 de 7, e as
  duas telas que os têm são as de cartão inerte.
- **P1** — a cerimônia da ação segue o template, não a consequência: saída excepcional grava no
  saldo físico sem confirmação, `Estornar` tem duas apresentações opostas, e devolução e estorno são
  dois painéis teal adjacentes de geometria quase idêntica.
- **P1** — retirante, quantidade devolvida e justificativa por item são exigidos, gravados em
  `TimelineRequisicao.metadata` e nunca exibidos; "entregue líquida" só existe atrás de
  `pode_devolver`.
- **P2** — `/notificacoes/` é a única listagem fora do sistema de cartões, com a afordância
  invertida (o link parece metadado, o descarte parece o link).
- **P2** — custo assumido desta etapa: o `flex-wrap` que consertou o número partido fez o carimbo de
  estado ocupar a linha 1 em uns cartões e a linha 3 em outros.

### Nota de método

A maior oportunidade é única e resolve várias linhas da tabela heurística de uma vez: **promover a
quantidade a componente**. O modal de retirada já provou a forma certa — número com peso, unidade
colada, referência abaixo em menor. Um `quantidade.html` usado nas sete telas conserta de uma vez o
alinhamento do catálogo, a unidade órfã do detalhe, o número nu do atendimento e o separador
decimal, porque passaria a existir um ponto só para consertar.

---

## Resumo

| Etapa | Escopo | Alvos | Fases |
|---|---|---|---|
| 0–5 | Tokens, ação, feedback, overlay, busca/filtro, listagem em cartões | — | **concluídas** |
| 6 | Partials de requisições | 13 | audit + critique |
| 7 | Partials de estoque | 11 → 10 | **concluída** (23/40) |
| 8 | Regressão das 19 telas | 20 | **concluída** (21/40) |

Etapas 0–5, 7 e 8 concluídas e congeladas. Na Etapa 6 a ordem interna é fixa (audit → correções →
critique). P0/P1 que sobrarem das critiques alimentam `/impeccable polish` ou viram issue própria
quando o escopo passa de front-end (foi o caso da #161).

As etapas 7 e 8 rodaram antes da 6 — as três só dependiam de 1–5, não uma da outra. A Etapa 8 fechou
com a 6 ainda pendente por decisão: ela mede as telas full-page, e a 6 mede os partials de
requisições, que são outra superfície. Rodar a 6 depois não invalida a baseline de 21/40, mas os
achados dela entram no mesmo backlog.
