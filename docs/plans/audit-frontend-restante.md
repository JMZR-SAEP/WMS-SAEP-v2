# Plano de auditoria — front-end restante

Continuação da auditoria de UI conduzida via `/impeccable`. As 19 telas full-page já foram
auditadas (blocos 1–4 de requisições/auth + blocos A–D de estoque/notificações). Este plano cobre
o que sobrou: a camada de tokens, os 24 componentes compartilhados, os 25 partials de domínio e o
comportamento em JS.

## Por que a ordem importa

As telas foram auditadas de fora pra dentro. O restante vai de dentro pra fora: token → componente
→ partial → regressão. Auditar componente antes de token gera retrabalho, porque todo achado de cor,
espaçamento ou tipografia no componente é sintoma de decisão tomada em `input.css`.

Cada etapa é uma branch `fix/{desc}`, com code-review antes do merge, conforme `AGENTS.md`.

## Inventário da superfície restante

| Camada | Arquivos | Linhas aprox. |
|---|---|---|
| Tokens e base CSS | `apps/core/static/core/css/input.css` | 631 |
| Componentes compartilhados | `apps/core/templates/components/**` (24) | ~1.100 |
| Shell e navegação | `base.html`, `base_auth.html`, `_topbar_nav`, `_side_nav`, `_messages` | ~290 |
| Partials de requisições | `apps/requisicoes/templates/requisicoes/partials/**` (14) | — |
| Partials de estoque | `apps/estoque/templates/estoque/partials/**` (10) | — |
| Partials de accounts | `apps/accounts/templates/accounts/partials/**` (1) | — |
| Comportamento | `apps/core/static/core/js/*.js` (4) | 586 |

`app.css` é artefato de build (`npm run css:build`) — não auditar, não editar à mão.

---

## Etapa 0 — Tokens semânticos e base CSS

```bash
/impeccable audit apps/core/static/core/css/input.css docs/design-system.md
```

Fundação de tudo que vem depois. Foco:

- Escala semântica (`--color-primary-*`, `success`, `warning`, `danger`) — cobertura completa por
  família, sem buraco que force valor cru no componente
- Contraste de cada par texto/fundo em AA, incluindo os `-subtle` sobre branco
- Estados de foco: anel visível e consistente, não removido por reset
- Escala de espaçamento e tipografia — quantos degraus realmente em uso vs. definidos
- **Drift**: `docs/design-system.md` descreve o que `input.css` implementa? Divergência aqui é o
  achado de maior alcance do plano inteiro
- Piso de 44px em campo e escala de z-index (já fixados em `1539479`) continuam respeitados

## Etapa 1 — Primitivos de ação e entrada

```bash
/impeccable audit apps/core/templates/components/button.html apps/core/templates/components/form_field.html apps/core/templates/components/item_form_row.html apps/core/static/core/js/form-submit.js apps/core/static/core/js/item_form_row.js
```

- `button`: variantes vs. hierarquia real de uso; estado `loading`/`disabled`; alvo de toque; o
  botão destrutivo é distinguível sem depender de cor
- `form_field`: label sempre presente, `aria-describedby` para erro e ajuda, campo obrigatório
  sinalizado no label e não só por `required`
- `item_form_row` + JS: foco após inserir linha via HTMX, remover a última linha, índice do formset
- `form-submit.js`: duplo-submit bloqueado, estado visual durante envio

## Etapa 2 — Feedback e estado

```bash
/impeccable audit apps/core/templates/components/alert.html apps/core/templates/components/error_summary.html apps/core/templates/components/empty_state.html apps/core/templates/components/badge.html apps/core/templates/core/partials/_messages.html
```

- Os quatro níveis (`error`/`warning`/`success`/`info`) com ARIA role correto por nível
- `error_summary` ancorando no campo com foco programático
- `empty_state`: vazio-inicial vs. vazio-pós-filtro precisam de textos distintos
- `badge`: estado nunca comunicado só por cor; truncamento de rótulo longo
- `_messages`: região live, não empilhar indefinidamente, dispensável pelo teclado

## Etapa 3 — Overlay

```bash
/impeccable audit apps/core/templates/components/modal.html apps/core/templates/components/_modal_body.html apps/core/templates/components/_modal_icon.html apps/core/static/core/js/modal.js
```

- Trap de foco, retorno do foco ao gatilho no fechamento, `Esc`, clique no backdrop
- `aria-modal`, `aria-labelledby`, `inert` no fundo
- Scroll do body travado; modal alto em viewport curta
- Consistência com os 7 modais de domínio que consomem este componente

## Etapa 4 — Busca e filtro

```bash
/impeccable audit apps/core/templates/components/autocomplete.html apps/core/static/core/js/autocomplete.js apps/core/templates/components/filter_shell.html apps/core/templates/components/filter_busca.html apps/core/templates/components/filter_select.html apps/core/templates/components/filter_data.html apps/core/templates/components/filter_checkbox_group.html apps/core/templates/components/filter_acoes.html
```

- `autocomplete`: padrão combobox ARIA completo — setas, `Enter`, `Esc`, `aria-activedescendant`,
  anúncio de contagem de resultados; estados buscando / zero resultados / erro de rede
- Debounce e cancelamento de requisição em voo
- Família `filter_*`: rótulo em cada campo, filtros ativos visíveis, ação de limpar, comportamento
  em mobile (colapsar?), preservação de filtro na paginação

## Etapa 5 — Listagem

```bash
/impeccable audit apps/core/templates/components/table.html apps/core/templates/components/pagination.html apps/core/templates/components/page_header.html apps/core/templates/components/ordenacao_data.html apps/core/templates/components/icons/
```

- `table`: `scope` em cabeçalho, caption ou rótulo acessível, alinhamento numérico à direita,
  estratégia de overflow horizontal em mobile
- `pagination`: página atual anunciada, alvos de toque, contagem total
- `page_header`: hierarquia de título e ação primária, breadcrumb
- Ícones: `aria-hidden` quando decorativos, rótulo quando informativos

## Etapa 6 — Partials de requisições

```bash
/impeccable audit apps/requisicoes/templates/requisicoes/partials/
```

14 partials: 6 modais de ação, os 4 fragmentos de `_confirmacao_acao`, `_timeline`, `_estado_badge`,
os alerts de formset/inelegíveis/nota de cópia e o autocomplete de beneficiário.

Pergunta central: quanto disso ainda precisa existir depois das etapas 1–5? Os 6 modais devem ser
casca fina sobre `components/modal.html`; os alerts, sobre `components/alert.html`. Divergência aqui
é dívida, não customização.

## Etapa 7 — Partials de estoque e accounts

```bash
/impeccable audit apps/estoque/templates/estoque/partials/ apps/accounts/templates/accounts/partials/
```

11 partials: badges de tipo/estado, `_delta_movimentacao`, `_chip_so_saidas`, os 6 alerts de
importação SCPI, modal de estorno, autocomplete de material, alert de erro de login.

Mesma pergunta da etapa 6, mais: os 6 alerts de SCPI dizem coisas diferentes ou são o mesmo alert
com texto trocado?

## Etapa 8 — Passe de regressão

```bash
/impeccable audit
```

Sem alvo — varredura das 19 telas já auditadas, agora sobre a base refeita. Verifica:

- Nenhuma tela regrediu com a troca de token ou refatoração de componente
- Dark mode e mobile em todas as 19
- Consistência final entre as 4 listas de requisições e as 3 de estoque

---

## Resumo

| Etapa | Escopo | Alvos |
|---|---|---|
| 0 | Tokens e base CSS | 2 |
| 1 | Ação e entrada | 5 |
| 2 | Feedback e estado | 5 |
| 3 | Overlay | 4 |
| 4 | Busca e filtro | 8 |
| 5 | Listagem | 5 |
| 6 | Partials de requisições | 14 |
| 7 | Partials de estoque e accounts | 11 |
| 8 | Regressão das 19 telas | 19 |

Total: 9 etapas. A etapa 0 é bloqueante para todas as outras; 1–5 são independentes entre si e
podem trocar de ordem; 6 e 7 dependem de 1–5; 8 fecha.
