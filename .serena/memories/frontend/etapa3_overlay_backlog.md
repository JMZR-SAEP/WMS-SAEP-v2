# Etapa 3 do audit de front-end — overlay (modal)

Contexto base para trabalhar as issues #129–#138 em conversas novas. Auditoria feita em
2026-08-23 com `/impeccable audit` + `/impeccable critique` (dual-agent, A e B isolados).
Nenhum código foi alterado — a etapa produziu só achados e issues.

## De onde isso vem

- Plano mestre: `docs/plans/audit-frontend-restante.md`. A Etapa 3 cobre os quatro arquivos abaixo.
- Snapshot do critique:
  `.impeccable/critique/2026-08-23T13-18-48Z__apps-core-templates-components-modal-html.md`
  (Design Health Score **21/40**; Audit Health Score **14/20**).
- A Etapa 0 (tokens/`input.css`) continua **não feita**, e a Etapa 2 (feedback e estado) está em
  andamento — ver `mem:frontend/etapa2_feedback_backlog`, que compartilha vocabulário e guardas
  com esta.

Arquivos auditados:

- `apps/core/templates/components/modal.html`
- `apps/core/templates/components/_modal_body.html`
- `apps/core/templates/components/_modal_icon.html`
- `apps/core/static/core/js/modal.js`

Os 8 consumidores reais, que é por onde o componente foi julgado (o componente sozinho engana):

| Modal | Onde | Corpo |
|---|---|---|
| `confirmar-cancelar`, `confirmar-enviar` | `requisicoes/detalhe.html:216,227` | `_modal_form_cancelar.html` / nenhum |
| `confirmar-separar` | `requisicoes/detalhe.html:321` | nenhum |
| `item.modal_devolver_id` | `requisicoes/detalhe.html:176` | `_modal_form_devolucao.html` |
| `confirmar-autorizar`, `confirmar-retornar`, `confirmar-recusar`, `estornar-modal` | via `requisicoes/partials/_confirmacao_acao.html` | vários |
| `confirmar-atender-retirada` | `requisicoes/atender_retirada.html:235` | nenhum — modo `submit_form_id` |
| `estornar-saida` | `estoque/detalhe_saida_excepcional.html:177` | `_modal_form_estorno_saida.html` |
| `confirmar-importacao-scpi` | `estoque/preview_importacao_scpi.html:313` | `_modal_corpo_confirmar_importacao.html` |

## As 10 issues (JMZR-SAEP/WMS-SAEP-v2), todas com `needs-triage`

| # | Escopo | Tipo | Blocked by | Comando |
|---|---|---|---|---|
| 129 | ADR: entra camada de teste de comportamento em navegador? | **HITL** | — | — |
| 130 | Contrato HTTP de toda `action_url` de modal (204+`HX-Redirect` ou 422+fragment) | AFK | — | `/impeccable harden` |
| 131 | Nome acessível do `<dialog>` — id `-titulo` duplicado com o painel — **FEITA** | AFK | — | `/impeccable harden` |
| 132 | Foco inicial vai para a ação menos destrutiva | AFK | 129 | `/impeccable harden` |
| 133 | Não fecha com requisição em voo; `htmx:responseError` visível | AFK | 129, 130 | `/impeccable harden` |
| 134 | Trava de scroll de fundo, `overscroll-contain`, `abrir_ao_carregar` server-side | AFK | 129 | `/impeccable harden` |
| 135 | Fonte única da copy de cada modal (template × 422) | AFK | 130 | `/impeccable clarify` |
| 136 | Vocabulário de severidade do ícone: obrigatório, falha alta, glifo correto, teal | **HITL** | 131 | `/impeccable polish` |
| 137 | Polimento: rodapé (feedback de submit, safe-area) e corpo (rolagem por teclado) | AFK | 129, 130, 131 | `/impeccable polish` |
| 138 | O modal nomeia o registro que está confirmando | **HITL** | 135, 136 | `/impeccable clarify` |

Ordem sugerida: **130 primeiro** — é o único P0 que não depende de decisão, é a correção de maior
impacto (duas ações irreversíveis do chefe de almoxarifado), e destrava 133/135/137. **131** em
paralelo, é barata e destrava 136/137. **129 é a decisão que destrava toda a família de JS**
(132/133/134) — sem ela, nenhum defeito de runtime tem como ser travado por teste. 136 e 138 não
devem ter código escrito antes das decisões que as bloqueiam.

## Decisões pendentes do dono do produto

Três issues estão marcadas HITL porque têm pergunta aberta, não porque são difíceis:

1. **#129** — entra camada de navegador no CI (ADR-0012)? Com que ferramenta? A ADR-0010 termina em
   Views e não tem camada de JS. Se a resposta for *não*, o ADR precisa dizer como os defeitos de
   runtime passam a ser prevenidos, e 132/133/134 seguem com o instrumento alternativo nomeado.
2. **#136** — qual glifo substitui a lixeira em `danger`? `icon_variant` vira obrigatório, e qual
   variante cada um dos 8 consumidores recebe? Entra variante `return` (teal) no ícone e teal
   preenchido em `button.html`?
3. **#138** — forma da identidade no modal: linha fixa sob o título, slot `resumo_template`,
   número público no `confirm_label`, ou combinação? O slot é obrigatório para ação que escreve
   movimentação? O `backdrop-blur-sm` fica?

## Fatos medidos que não precisam ser remedidos

**`x-trap` é código morto inteiro** em `modal.html:60,85`. `x-trap.inert.noscroll="$refs.dialog.open"`
não é reativo: `$refs` é `mergeProxies` (não `reactive()`) e `.open` é propriedade IDL nativa de
`HTMLDialogElement`. O `effect` do plugin roda uma vez no init com `open === false`, cai no
`S !== D` sendo `false !== false`, e nunca mais roda. Medido lado a lado na página real
(Alpine 3.15.12 + `alpine-focus.min.js` reais):

```
x-trap.inert.noscroll="$refs.dialog.open"  dialog.open=true -> documentElement.style.overflow ""
x-trap.inert.noscroll="menuOpen"           menuOpen=true    -> documentElement.style.overflow "hidden"
```

O segundo é `base_auth.html:63`, que funciona. Testado também no caminho `abrirAoCarregar`: morto
igual. **Contenção de foco NÃO é afetada** — `showModal()` já põe o diálogo no top layer e torna o
resto inerte (medido: `.focus()` fora do dialog não move o foco). O que se perde é só o `.noscroll`.

**`?? console.error` dispara sempre.** `_modal_body.html:76` gera
`getElementById(...)?.requestSubmit() ?? console.error(...)`. `requestSubmit()` devolve `undefined`,
e `undefined ?? X` avalia `X`. Medido no navegador com form existente:
`{"submitDisparado": true, "chamadasApos_formExistente": ["... nao encontrado"]}`.

**Contraste dos ícones do `_modal_icon.html` passa com folga** (oklch→sRGB, calculado):
`danger-text/danger-muted` (#c10007/#ffe2e2) **5.27:1**; `warning-text/warning-muted`
(#973c00/#fef3c6) **6.36:1**; `primary-text/primary-muted` (#1447e6/#dbeafe) **5.60:1**. Passam até
no piso de texto normal, e os `<span>` são `aria-hidden` (decorativos, isentos até dos 3:1).

**Alvos de toque do rodapé passam.** `min-h-11` vem de `_FORMA_BOTAO` em `core_tags.py:130`, e
`_TAMANHOS_BOTAO` é `px-3 py-2` nos dois tamanhos — nenhum toca altura. Única fuga teórica é
`confirm_variant="link"`, que cairia em `_FORMA_LINK`; nenhum dos 15 call sites usa.

**Tokens crus:** só `bg-slate-900/50` no backdrop, que é exceção allowlistada com contagem em
`test_tokens_semanticos.py:120` (`{'bg-slate-900': 1}`, comparação por igualdade de dicionário,
normalizada por `_classe_sem_opacidade`). `_modal_body.html` e `_modal_icon.html` estão limpos.

## Três hipóteses que foram REFUTADAS — não gastar tempo com elas de novo

1. **`htmx:afterSwap` não dispararia no alvo certo.** Falso. `swapOuterHTML` remove o target antigo
   de `settleInfo.elts` e empurra os elementos novos **antes** do `triggerEvent`, então
   `event.target` é o `[data-modal-body]` novo e `matches('[data-modal-body]')` dá `true`. Medido:
   o foco parou no `[aria-invalid="true"]`. `modal.js:52-56` funciona.
2. **Contraste dos ícones** — ver acima, passa.
3. **Alvos de toque abaixo de 44px no rodapé** — ver acima, passa.

Também: o htmx que **executa** é `apps/core/static/core/vendor/htmx.min.js` **2.0.10**
(`base.html:15`), não o 2.0.7 do `django_htmx` no `.venv`. Ler o do `.venv` para entender mecânica
é ok; afirmar comportamento a partir dele, não.

## Guardas existentes e seus buracos

- **`apps/core/tests/test_modal.py` são 5 testes** e cobrem só o contrato XOR de
  `validar_contrato_modal` (`core_tags.py:263`) e a presença da string `hx-sync="this:drop"`.
- **Não existe suíte de JS.** `package.json` tem `playwright` em `devDependencies`, zero specs,
  zero `playwright.config`, zero `e2e/`. Os scripts são só `css:build` e `css:dev`. Foi por isso que
  o `x-trap` morto e o `?? console.error` sobreviveram — nenhum dos dois aparece no HTML renderizado.
- Sem teste para: `x-trap`, a expressão gerada do `submit_form_id`, `_modal_icon.html` (nenhuma das
  3 variantes nem o fallback), o rodapé (que os dois botões saem de `button.html`), `acao_erro`,
  `hidden_inputs`, `aria-describedby` condicional.
- O que existe nos outros apps é asserção de **string** do lado servidor:
  `requisicoes/tests/test_views.py` (`data-modal-body`, `data-modal-erro`, `role="dialog"`,
  `data-modal-trigger`, e em 2263-2266 fatia o `<dialog>` para garantir ausência de `hx-post` no
  modo `submit_form_id`); `test_painel_decisao.py:101-103,313-314,339-355`;
  `estoque/tests/test_views.py:652-666,1038-1060`; `core/tests/test_components.py:1922-1934`
  (guard de superfície única de erro — `_modal_body.html` tem que usar `{% erros_do_formulario %}`).
- **O painel já cedeu o sufixo `-titulo` ao modal (#131, feita).** O card usa
  `{{ modal_id }}-painel-titulo`, e a reserva está no `{% comment %}` do painel e em
  `docs/design-system.md`. As guardas são `test_painel_decisao.py`
  (`test_o_card_nao_toma_o_sufixo_titulo_do_modal`) e, em `requisicoes/tests/test_views.py`,
  `test_detalhe_com_painel_de_decisao_nao_repete_nenhum_id` +
  `test_dialog_e_nomeado_pelo_titulo_do_proprio_modal`, que leem o HTML por `HTMLParser`
  (`_ids_do_documento`, `_dialogos`). Ainda não cobertas: as telas de modal de `estoque`, que
  compartilham o mesmo contrato de id de `components/modal.html`.

## Armadilhas técnicas

- **`detect.mjs` do Impeccable devolveu `[]` para estes 4 arquivos, e isso NÃO é "limpo".** Vale a
  mesma ressalva de `mem:frontend/etapa2_feedback_backlog`, mais uma específica: as classes do
  rodapé saem de `classes_botao` (Python) e os ícones de `{% icon %}` — nada disso é texto nos
  templates, logo nada disso entra no scan.
- **O critique exige dois subagentes isolados (A e B).** Rodar inline é run degradado e obriga
  banner `⚠️ DEGRADED`. O `context.mjs` emite `SUBAGENT_AUTHORIZATION`, que é a autorização para
  spawnar mesmo em harness que gateia subagente.
- **Browser: as telas de modal estão atrás de login.** Um agente que não digita senha não chega
  nelas. O caminho que funcionou foi injetar DOM instrumentado em `http://localhost:8000/login/`,
  onde as bibliotecas reais (Alpine, htmx, `alpine-focus`, `modal.js`) já estão carregadas pelo
  `base.html`. Harness em `file://` **não** executa script na pane — descartar.
- **`gh issue create --label` falha em silêncio neste repo**, e `gh issue edit --add-label` devolve
  `GraphQL: joaozuneda6 does not have the correct permissions to execute AddLabelsToLabelable`.
  Preferir `GH_TOKEN=$(gh auth token --user joaorighetto)` na própria invocação, sem trocar a conta
  ativa (trocar funciona, mas deixa a autoria da issue como `joaozuneda6` enquanto todas as
  existentes são de `joaorighetto`). As #129–138 nasceram com essa divergência de autoria.
- **Esta memória nasce untracked.** `.serena/memories/` é versionado, mas arquivo novo não sobrevive
  a troca de branch. Commitar junto com o trabalho da branch em que foi criada — a etapa 2 já perdeu
  a dela uma vez.

## Contradições e dívidas que a etapa expôs

- **`docs/design-system.md` afirma que o modal tem "foco preso (`x-trap.inert.noscroll`)"** — a parte
  de foco é verdadeira por acidente (`showModal()`), a de scroll é falsa. Corrigir na #134.
- **A lixeira contradiz a invariante central.** `_modal_icon.html:9` usa `{% icon "lixeira" %}` para
  `danger`, variante de recusar/cancelar/estornar. `CONTEXT.md` descreve **uma** operação que remove
  sem rastro: o **descarte** de rascunho sem número público. Cancelamento preserva o número, estorno
  grava movimentação reversora, a trilha é append-only.
- **A Regra da Reversão Não é Erro morre na porta do modal.** "Registrar devolução" tem trigger
  `return-outline` (teal) e abre modal sem ícone com `confirm_variant="primary"` (azul). Falta
  variante `return` no ícone e teal preenchido em `button.html`. Mesma família da issue #128 da
  etapa 2 — coordenar.
- **`abrir_ao_carregar` está documentado como server-side e é 100% Alpine.** `modal.html:13` mente;
  o template nunca emite `open` no `<dialog>`.
- **`_render_modal_erro` (`requisicoes/views.py:222`) tem `icon_variant: str = 'danger'` como
  default de assinatura** — reclassificaria como perigo qualquer modal `info` que passasse por ali.

## Achados desta auditoria que pertencem às Etapas 6/7, não à 3

Decidido em 2026-08-23 — **não antecipar**, porque a Etapa 6 pergunta primeiro se esses partials
ainda precisam existir:

- Três tipografias de label diferentes nos 5 `form_body_template`, nenhum usando
  `components/form_field.html`.
- `id="justificativa"` sem namespace em `estoque/partials/_modal_form_estorno_saida.html` — o único
  campo de modal do sistema sem prefixo.
- `requisicoes/partials/_modal_form_estorno.html` sem `aria-describedby` para `{{ id }}-erro` e sem
  `aria-invalid` no re-render (comparar com `_modal_form_recusar.html`, que faz certo).
- O `aria-describedby="alertas-importacao"` do SCPI preso no botão trigger, fora do diálogo.

## Fora de escopo por baixo impacto (P3 registrados e não issue-ados)

Sem afordância de fechar no header do modal; sem animação de saída (entrada tem 180ms
`cubic-bezier(0.16, 1, 0.3, 1)`); `<h2>` fixo no corpo, não parametrizável.

## O que estava certo e não deve ser "melhorado"

- **`cancel_label` default "Voltar"**, não "Cancelar" — "cancelar" é verbo de domínio aqui, e
  `_modal_form_cancelar.html` ensina a palavra inline. Nasceu do glossário.
- **Fonte única de corpo** entre render inicial e fragment 422: `_modal_body_fragment.html` é um
  wrapper de 7 linhas sobre `components/_modal_body.html`.
- **`hx-sync="this:drop"`** e o raciocínio de por que `form-submit.js` não bastava (ordem de
  listener: HTMX escuta no próprio `<form>`, o `preventDefault` de `document` chega tarde) — está
  documentado no template e tem teste.
- **`validar_contrato_modal`** falha no render, não em produção.
- **`focar=False` na caixa de erro do modal** — `modal.js` é o dono do foco ali, e dois donos brigam.
- **A animação inteira dentro de `prefers-reduced-motion: no-preference`** (`input.css:762`), em vez
  de matar com `0.01ms`.
