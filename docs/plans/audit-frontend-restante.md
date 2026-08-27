# Plano de auditoria — front-end restante

Continuação da auditoria de UI conduzida via `/impeccable`. As 19 telas full-page já foram
auditadas (blocos 1–4 de requisições/auth + blocos A–D de estoque/notificações). Este plano cobre
o que sobrou: a camada de tokens, os componentes compartilhados, os partials de domínio e o
comportamento em JS.

> **Estado deste plano (revisado em 2026-08-27).**
>
> - **Etapas 0–4 concluídas.** Não mexer — ver "Etapas concluídas" abaixo.
> - **Etapas 5–8 pendentes.** Cada uma tem agora duas fases: `/impeccable audit` (defeito técnico —
>   a11y, responsivo, performance) seguida de `/impeccable critique` (revisão de UX com pontuação
>   heurística sobre o resultado do audit). A critique fecha a etapa e alimenta o backlog de
>   `polish` se restar P0/P1.
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
| Componentes compartilhados | `apps/core/templates/components/*.html` (25) + `components/icons/` (4 partials + 15 svg) | — |
| Shell e navegação | `base.html`, `base_auth.html`, `core/_topbar_nav.html`, `core/partials/_side_nav.html`, `core/partials/_messages.html`, `core/partials/_message_item.html` | — |
| Partials de requisições | `apps/requisicoes/templates/requisicoes/partials/**` (13) | — |
| Partials de estoque | `apps/estoque/templates/estoque/partials/**` (11) | — |
| Comportamento | `apps/core/static/core/js/*.js` (6) | 1648 |

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

## Etapas concluídas (0–4) — não mexer

| Etapa | Escopo | Alvos |
|---|---|---|
| 0 | Tokens semânticos e base CSS | `input.css`, `docs/design-system.md` |
| 1 | Primitivos de ação e entrada | `button`, `form_field`, `item_form_row`, `form-submit.js`, `item_form_row.js`, `acao-bloqueada.js` |
| 2 | Feedback e estado | `alert`, `error_summary`, `field_error`, `empty_state`, `badge`, `_icone_nivel`, `_messages`, `_message_item`, `mensagens.js` |
| 3 | Overlay | `modal`, `_modal_body`, `_modal_icon`, `modal.js` |
| 4 | Busca e filtro | família `autocomplete` + `filter_*` (inclui `filter_chips`, `filter_presets_periodo`) |

Achados dessas etapas viraram issues próprias (#127, #147, #149, #151, #152–#154). Regressão sobre
elas é responsabilidade da Etapa 8.

---

## Etapa 5 — Listagem em cartões

### Fase 1 — audit

```bash
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
- `icons/`: 4 partials (`_caixa_entrada`, `_check`, `_funil`, `_prancheta`) + 15 svg —
  `aria-hidden` quando decorativos, rótulo quando informativos; conferir se partial e svg do mesmo
  glifo divergem

### Fase 2 — critique

```bash
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

```bash
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

```bash
/impeccable critique apps/requisicoes/templates/requisicoes/partials/_painel_decisao.html apps/requisicoes/templates/requisicoes/partials/_timeline.html apps/requisicoes/templates/requisicoes/partials/_modal_corpo_atender_retirada.html
```

Sobre os fluxos de decisão da requisição:

- `_painel_decisao`: o par painel + modal comunica o peso da ação (autorizar vs. recusar vs.
  estornar)? Ação destrutiva parece destrutiva antes do clique?
- `_timeline`: a ordem dos eventos e o estado atual são lidos num relance? Ruído vs. sinal
- `_modal_corpo_atender_retirada`: carga cognitiva do passo de conferência
- Pontuação heurística + P0/P1

## Etapa 7 — Partials de estoque

### Fase 1 — audit

```bash
/impeccable audit apps/estoque/templates/estoque/partials/
```

11 partials: `_badge_tipo_movimentacao`, `_estado_saida_badge`, `_delta_movimentacao`, os 5 alerts
de importação SCPI (`_alert_divergencias_corpo`, `_erro_arquivo_corpo`, `_erro_confirmacao_corpo`,
`_novos_materiais_corpo`, `_sucesso_importacao_corpo`), `_modal_corpo_confirmar_importacao`,
`_modal_form_estorno_saida`, `_autocomplete_item_material`.

Mesma pergunta da etapa 6, mais: os 5 alerts de SCPI dizem coisas diferentes ou são o mesmo alert
com texto trocado? (`_chip_so_saidas` foi absorvido pelo `filter_chips` genérico — conferir que não
sobrou referência.)

### Fase 2 — critique

```bash
/impeccable critique apps/estoque/templates/estoque/partials/_modal_corpo_confirmar_importacao.html apps/estoque/templates/estoque/partials/_alert_divergencias_corpo.html apps/estoque/templates/estoque/partials/_delta_movimentacao.html
```

Sobre o fluxo de importação SCPI, que é onde o operador toma decisão de verdade:

- Confirmação de importação: o operador entende o que vai mudar no estoque antes de confirmar?
  Divergências e novos materiais apresentados de forma acionável, não como despejo de dados
- `_delta_movimentacao`: o sinal de entrada/saída e a magnitude são lidos sem contar dígito
- Os 5 alerts como conjunto: progressão clara (sucesso → atenção → erro) ou cinco caixas parecidas?
- Pontuação heurística + P0/P1

## Etapa 8 — Passe de regressão

### Fase 1 — audit

```bash
/impeccable audit
```

Sem alvo — varredura das 19 telas já auditadas, agora sobre a base refeita. Verifica:

- Nenhuma tela regrediu com a troca de token ou refatoração de componente
- Mobile em todas as 19
- Consistência final entre as 4 listas de requisições e as 3 de estoque, agora todas em cartões

### Fase 2 — critique

```bash
/impeccable critique
```

Sem alvo — leitura de UX do produto inteiro depois de tudo refeito. É a baseline heurística que não
existe (`critique.latest` nulo). Verifica:

- As 4 listas de requisições e as 3 de estoque contam a mesma história de interação
- Fluxo completo de ponta a ponta (criar requisição → autorizar → atender) sem degrau de carga
  cognitiva entre telas
- Pontuação final do produto + P0/P1 que sobrarem viram entrada de `/impeccable polish`

---

## Resumo

| Etapa | Escopo | Alvos | Fases |
|---|---|---|---|
| 0–4 | Tokens, ação, feedback, overlay, busca/filtro | — | **concluídas** |
| 5 | Listagem em cartões | 5 | audit + critique |
| 6 | Partials de requisições | 13 | audit + critique |
| 7 | Partials de estoque | 11 | audit + critique |
| 8 | Regressão das 19 telas | 19 | audit + critique |

Etapas 0–4 concluídas e congeladas. Nas etapas 5–8 a ordem interna é fixa (audit → correções →
critique); 5 é independente, 6 e 7 dependem das correções de 1–5 já mergeadas, 8 fecha. P0/P1 que
sobrarem das critiques alimentam `/impeccable polish`.
