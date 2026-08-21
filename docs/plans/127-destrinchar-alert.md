# Plano — #127 Destrinchar `alert.html`: extrair o painel de decisão de workflow

Issue: https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/127
Origem: Etapa 2 (Feedback e estado) de `docs/plans/audit-frontend-restante.md`.
Comando recomendado pela issue: `/impeccable shape` sobre `alert.html` e
`_confirmacao_acao.html` — **já executado**, com as três decisões abertas
respondidas pelo dono do produto (registradas em "Decisões do shape" abaixo).
A execução usa `/impeccable distill` nos mesmos alvos, na fase de implementação,
antes de escrever markup.

## Estado real do repositório (a issue está desatualizada em três pontos)

A issue foi escrita em 2026-08-18. As issues #119–#126 fecharam desde então e o
plano parte do código vivo, não do texto da issue:

1. **`variant="primary"` não é mais contrato oculto.** O achado descreve
   `_confirmacao_acao.html` dependendo de `"primary"` cair no `{% else %}`. Hoje
   o partial passa `variant=variant_token`, e os cinco chamadores de
   `detalhe.html` passam `info`, `warning` ou `danger` — todos no catálogo.
   `apps/core/tests/test_components_alert.py:311`
   (`test_nenhum_chamador_de_alert_passa_variante_fora_das_quatro_conhecidas`)
   já vigia isso. O critério de aceite correspondente **já está satisfeito**; o
   plano só precisa não regredir.
2. **A falha silenciosa já morreu.** O achado descreve variante desconhecida
   caindo no azul de `info`. A #122 substituiu isso pela Decisão A-1 (falha
   alta): fundo `bg-danger` preenchido, linha "Aviso indisponível",
   `data-alert-variant` cru e `role="alert"` sem exceção. Esta issue **consome**
   essa decisão — e estende o mesmo fallback ao painel de decisão, que hoje não
   tem nenhum.
3. **A paridade e o ícone em `currentColor` já foram feitos.** A #124 alinhou o
   `layout="stack"` à faixa de flash e trocou a cor fixa do ícone por
   `currentColor` (o achado de contraste 2.07:1 do `warning` está fechado).
   `apps/core/tests/test_paridade_feedback.py` guarda os dois lados.

Consequência de escopo: dos onze achados listados na issue, três já estão
fechados. O trabalho real é a extração, a redução do contrato e a migração.

## Decisões do shape (2026-08-21) — não reabrir

| # | Pergunta | Decisão |
|---|---|---|
| S-1 | Onde mora o painel de decisão? | **Partial de domínio.** `_confirmacao_acao.html` renderiza a própria marcação. Nenhum componente global de painel; o `decision_panel.html` do "corte sugerido" da issue não nasce. |
| S-2 | Como o painel comunica o nível além da cor? | **Ícone por variante**, 16px, `currentColor`, mesmo desenho do `layout="stack"` do `alert.html`. |
| S-3 | O que fazer com `icone=False`? | **Remover o parâmetro.** O ícone passa a ser sempre emitido. |

Justificativa de S-1: o painel tem exatamente um consumidor
(`requisicoes/detalhe.html`, 3 cards + 2 banners). `detalhe_saida_excepcional.html`
resolve o mesmo problema com botão no cabeçalho, não com painel. O
`docs/design-system.md` é explícito contra generalizar para um consumidor só.

Contagem do índice: o §Índice de componentes conta os partials internos de
`components/` (`_modal_body.html` e `_modal_icon.html` estão lá). O
`_icone_nivel.html` de D-6 é um deles, então o índice vai de **21 para 22** —
por um glifo compartilhado, não por um painel generalizado. A frase de abertura
do §Índice ("21 componentes") precisa mudar junto, e é isso que o critério de
aceite da issue cobra.

## Escopo

### Unidade de contagem

Todo número de call site neste plano conta **includes de template**, nunca
arquivos nem grupos de migração. Um arquivo com três `{% include %}` conta três.
A issue fala em "7 call sites de domínio" sem definir a unidade; o levantamento
no código vivo, em includes, está no fim deste documento e é o número que vale.

### O que muda

| # | Mudança | Arquivo |
|---|---|---|
| D-1 | `layout="row"` sai do componente, junto com `action_template`, `heading_id` e `bg_class` | `apps/core/templates/components/alert.html` |
| D-2 | `icone` deixa de existir; o ícone é sempre emitido (mata `icone != False`) | `apps/core/templates/components/alert.html` |
| D-3 | `aria_live` deixa de existir; o `role` é o único botão de ARIA | `apps/core/templates/components/alert.html` |
| D-4 | Slot de hidratação: com `id`, o wrapper interno recebe `id="{{ id }}-conteudo"`, declarado no docstring | `apps/core/templates/components/alert.html` |
| D-5 | Docstring reescrito: contrato de uma frase + parâmetros sobreviventes | `apps/core/templates/components/alert.html` |
| D-6 | Glifo de nível extraído para partial único, em `currentColor` | novo `apps/core/templates/components/_icone_nivel.html` |
| D-7 | `classes_painel_decisao`: mapa variante→token do painel, num lugar só, com fallback A-1 | `apps/core/templatetags/core_tags.py` |
| D-8 | O partial passa a renderizar a própria superfície (card e banner), sem incluir `alert.html` | `apps/requisicoes/templates/requisicoes/partials/_confirmacao_acao.html` |
| D-9 | Nome acessível nos dois layouts: `role="group"` só é emitido com `aria-labelledby` | `_confirmacao_acao.html` |
| D-10 | Switch de variante sai dos corpos; descrição sobe de `text-xs` para `text-sm` | `_confirmacao_acao_corpo.html`, `_confirmacao_acao_banner_corpo.html` |
| D-11 | `desc_class` e `bg_class` deixam de existir na API do painel | `_confirmacao_acao.html` + **2** includes em `detalhe.html` (só os dois banners, linhas 300 e 327; os 3 cards nunca passaram nenhum dos dois) |
| D-12 | `icone=False` removido dos 3 chamadores restantes | `copiar_confirmacao.html`, `nova_saida_excepcional.html` (2 chamadas) |
| D-13 | `aria_live` removido dos 2 chamadores | `confirmar_importacao_scpi.html` |
| D-14 | O JS de duplicidade escreve no slot, não na raiz | `nova_saida_excepcional.html` |
| D-15 | Documentação: contagem de 21→22, linha do `alert.html` sem `row`, entrada do `_icone_nivel.html` e §Paridade sem o parágrafo do `layout="row"` | `docs/design-system.md` |
| D-16 | Vocabulário de sombra: 1dp deixa de citar "banner de alerta em layout `row`" | `DESIGN.md` |
| D-17 | Guardas novas e migração das existentes | 4 arquivos de teste (ver §Estratégia de testes) |

### O que NÃO muda

- **A cor do banner de estorno.** Continua `danger`. A contradição entre a Regra
  da Reversão Não é Erro e o uso de `danger` no estorno é a issue #128, e a
  própria memória do backlog manda resolver no doc antes de tocar código.
- **O gate de permissão.** `detalhe.html` continua decidindo o que renderizar
  por `pode_autorizar` / `pode_recusar` / `pode_retornar` / `pode_cancelar` /
  `pode_estornar`. O painel apresenta; o domínio decide. Nenhum `{% if %}` de
  permissão se move.
- **`_confirmacao_acao_banner_botao.html`.** Continua sendo o slot de ação;
  muda só o docstring, que hoje o descreve como `action_template` do
  `alert.html`.
- **`components/_modal_icon.html`.** É uma **quarta** cópia dos mesmos traçados
  de ícone, com chrome próprio (círculo de 40px, fundo `-muted`). Não é alvo
  desta issue — o corte da issue é `alert.html` + `_confirmacao_acao.html`.
  Registrado aqui para não se perder.
- **`_message_item.html`.** O mapa dele é de níveis do Django messages
  (`debug`/`info`/`success`/`warning`/`error`), vocabulário diferente do de
  variante visual, e a #124 já o amarrou por teste de paridade. Fica fora.
- **O `role` do `alert.html`.** Sobrevive, e é intencional:
  `preview_importacao_scpi.html:290` rebaixa um `warning` para `role="status"`
  de propósito, e a casca de duplicidade usa `role="none"`.
- **Etapa 6 do plano de auditoria.** A pergunta "quanto disso ainda precisa
  existir depois das etapas 1–5?" segue em issue própria.

## Por que dois mapas de cor não são duplicação

O critério de aceite diz "nenhum partial de domínio reimplementa o mapa
variante→token de cor". Depois da mudança:

- `alert.html` tem o mapa do **banner estático**: raio de campo (`rounded-lg`),
  sem sombra, texto em `-text-emphasis` (`-text` no âmbar, pela exceção da
  escala de sufixos fixada na #124).
- `classes_painel_decisao` tem o mapa do **painel de decisão**: raio de papel
  (`rounded-xl`), `shadow-sm`, texto em `-text-strong`.

São superfícies diferentes com valores diferentes — não são o mesmo mapa escrito
duas vezes. O que morre é a repetição real: os dois corpos de domínio que hoje
reescrevem o switch que o `alert.html` já tinha, para colorir `<h2>`/`<h3>`.
Cada mapa passa a existir exatamente uma vez, e o do painel fica testável
isoladamente — precedente direto de `classes_botao`, criada em `core_tags.py`
pelo mesmo motivo.

`classes_painel_decisao` mora em `apps/core/templatetags/core_tags.py`, não em
`requisicoes_tags.py`: a entrada é `info|warning|danger`, vocabulário de
design system, sem nenhum enum de domínio. É o espelho da regra "componente
global não conhece enum de domínio".

## Arquivos tocados

| Arquivo | Natureza |
|---|---|
| `apps/core/templates/components/alert.html` | reduzido (D-1…D-5) |
| `apps/core/templates/components/_icone_nivel.html` | **novo** (D-6) |
| `apps/core/templatetags/core_tags.py` | `classes_painel_decisao` (D-7) |
| `apps/requisicoes/templates/requisicoes/partials/_confirmacao_acao.html` | marcação própria (D-8, D-9, D-11) |
| `apps/requisicoes/templates/requisicoes/partials/_confirmacao_acao_corpo.html` | sem switch, `text-sm`, id do `<h3>` (D-10) |
| `apps/requisicoes/templates/requisicoes/partials/_confirmacao_acao_banner_corpo.html` | sem switch, `text-sm` (D-10) |
| `apps/requisicoes/templates/requisicoes/partials/_confirmacao_acao_banner_botao.html` | só docstring |
| `apps/requisicoes/templates/requisicoes/detalhe.html` | 2 dos 5 includes perdem `desc_class`/`bg_class` (D-11); os 5 são revalidados |
| `apps/requisicoes/templates/requisicoes/copiar_confirmacao.html` | perde `icone=False` (D-12) |
| `apps/estoque/templates/estoque/nova_saida_excepcional.html` | perde 2× `icone=False`; JS escreve no slot (D-12, D-14) |
| `apps/estoque/templates/estoque/confirmar_importacao_scpi.html` | perde 2× `aria_live` (D-13) |
| `apps/core/tests/test_components_alert.py` | remove casos de `row`/`icone`/`aria_live`; adiciona o contrato reduzido |
| `apps/core/tests/test_paridade_feedback.py` | migra `test_layout_row_mantem_raio_de_papel_e_a_razao_esta_no_arquivo` |
| `apps/core/tests/test_components.py` | guarda: nenhum chamador passa parâmetro morto |
| `apps/requisicoes/tests/test_partials.py` | testes do painel de decisão |
| `docs/design-system.md` | D-15 |
| `DESIGN.md` | D-16 |
| `apps/core/static/core/css/app.css` | só se `make css-build` produzir diff |

## Ordem de implementação (TDD, fatias verticais)

Cada fatia é RED → GREEN → REFACTOR e fecha num commit próprio. A ordem é
escolhida para que a suíte nunca fique vermelha por mais de uma fatia.

1. **F-1 — `classes_painel_decisao` + `_icone_nivel.html`.** Teste do mapa
   (3 variantes conhecidas + fallback A-1) e do glifo em `currentColor`. Nada
   consome ainda; `alert.html` passa a incluir o glifo.
2. **F-2 — painel de decisão renderiza sozinho.** `_confirmacao_acao.html` para
   de incluir `alert.html` nos dois layouts. Testes de nome acessível, ícone,
   `text-sm` e fallback.
3. **F-3 — migração dos 5 includes de `_confirmacao_acao.html`.** Dois deles
   (os banners) perdem `desc_class` e `bg_class`; os três cards já não passavam
   nenhum dos dois e só precisam ser revalidados. Teste por include (a
   `detalhe.html` já tem cobertura de view em `test_views.py` para renderizar
   cada estado).
4. **F-4 — redução do `alert.html`.** Remove `layout`, `action_template`,
   `heading_id`, `bg_class`, `icone`, `aria_live`; adiciona o slot
   `-conteudo`. Migra os 5 includes de `alert.html` que passam parâmetro morto
   (`copiar_confirmacao` ×1, `nova_saida_excepcional` ×2,
   `confirmar_importacao_scpi` ×2).
5. **F-5 — JS do slot.** `nova_saida_excepcional.html` escreve em
   `#aviso-duplicidade-conteudo`. Teste de marcação (o wrapper de flex
   sobrevive à hidratação porque não é mais o alvo).
6. **F-6 — guardas e documentação.** Guarda de parâmetro morto, `design-system.md`,
   `DESIGN.md`, migração do teste de paridade.

## Estratégia de testes

Cada linha abaixo é uma guarda; `docs/design-system.md` avisa que "regra sem
mecanismo vira sugestão", e este conjunto já perdeu essa aposta três vezes.

### Caminho feliz

- Os 3 cards (`info`, `warning`, `danger`) e os 2 banners (`danger`) de
  `detalhe.html` renderizam com título, descrição, ícone e botão.
- O ícone certo por variante, herdando `currentColor` — o mesmo teste que a
  #124 aplica ao `alert.html` e ao `_message_item.html`, estendido ao painel.
- Descrição em `text-sm` nos dois layouts (Regra dos 14px).
- `alert.html` reduzido segue emitindo `role="alert"` para `warning`/`danger` e
  `role="status"` para `info`/`success`.

### Contrato de acessibilidade

- Todo `role="group"` do painel tem `aria-labelledby` apontando para um heading
  presente no mesmo fragmento — nos **dois** layouts. Nenhum "grupo, grupo,
  grupo" na navegação estrutural.
- `test_messages_html_declara_live_region_uma_vez_por_mensagem`
  (`apps/requisicoes/tests/test_views.py:2713`) renderiza `_messages.html` e
  cobra `aria-live=` ausente, `role="alert"` == 1 e `role="status"` == 1. O
  painel de decisão não é live region e o `alert.html` não muda de `role`, mas
  a suíte inteira roda mesmo assim — a memória do backlog registra que esse
  teste é o canário de qualquer mudança na marcação de feedback.
- Combinação contraditória `role`/`aria-live` é impossível por construção:
  `aria_live` deixou de existir e o `role` carrega a assertividade.

#### Fronteira com o contrato de dismiss (fora deste escopo, e por quê)

O contrato de `docs/CONVENTIONS.md` §Níveis e ARIA — `success`/`info` em
`role="status"`, `warning`/`error` em `role="alert"`, **toda mensagem com
dispensa manual** — governa as *flash messages* do Django, renderizadas por
`core/partials/_messages.html` e `core/partials/_message_item.html`. Ele foi
implementado na #119 e é verificado lá; nenhum arquivo desse par é tocado por
esta issue.

`components/alert.html` e o painel de decisão estão **fora** desse contrato, e
isso é decisão registrada, não omissão: o docstring do `alert.html` já declara a
separação, e a #124 fixou que os dois seguem separados de propósito porque os
contratos ARIA são incompatíveis. Um banner de página não é dispensável — ele
descreve uma condição da tela, não um evento passado — e o painel de decisão
menos ainda, já que dispensá-lo esconderia a única forma de autorizar ou
recusar. A paridade que os dois **têm** é de superfície (raio, padding, degrau
de texto, ícone em `currentColor`), e é isso, e só isso, que
`apps/core/tests/test_paridade_feedback.py` cobra.

O que este plano preserva do lado do `alert.html`: `warning`/`danger` continuam
em `role="alert"` e `info`/`success` em `role="status"` (D-3 remove `aria_live`,
nunca o `role`). Nenhuma fatia adiciona, remove ou altera controle de dispensa.

### Erro de contrato (falha alta, Decisão A-1)

- Variante desconhecida no `alert.html`: fallback preservado, `role="alert"`
  sem exceção do parâmetro `role`, `data-alert-variant` cru e escapado.
- `variant_token` desconhecido no painel. **Hoje a superfície já grita**, e é
  preciso ser exato sobre por quê: `_confirmacao_acao.html:64,69` repassa
  `variant_token` como `variant` para o `alert.html`, então o ramo de variante
  desconhecida do componente já emite `bg-danger` preenchido, a linha "Aviso
  indisponível", `role="alert"` e `data-alert-variant`. O que **não** tem
  `{% else %}` hoje são os corpos de domínio: `_confirmacao_acao_corpo.html:9-10`
  e `_confirmacao_acao_banner_corpo.html:7` só cobrem `info`/`warning`/`danger`,
  e um token fora disso deixa `<h2>`/`<h3>` e a descrição **sem token de cor
  nenhum** — texto herdado sobre o fundo de grito.

  Depois da extração o painel deixa de herdar o fallback do `alert.html` e passa
  a ser dono dele. Os quatro sinais são requisito explícito, não emergentes, e
  cada um vira asserção: fundo `bg-danger` preenchido com borda
  `border-danger-hover`, linha "Aviso indisponível" antes do conteúdo,
  `role="alert"` sem exceção do `role` do chamador, e `data-alert-variant` com o
  valor cru escapado. `classes_painel_decisao` é quem os resolve, e o título e a
  descrição ganham o token de texto do grito — fechando o buraco que existe hoje.

### Guardas contra regressão

- Nenhum template passa `icone`, `aria_live`, `layout`, `action_template`,
  `heading_id` ou `bg_class` a `components/alert.html`. Varre `apps/**/*.html`
  e falha na **presença**, não na contagem — o erro que a #120 corrigiu no
  teste de piso de 44px foi exatamente esse.
- Nenhum partial de domínio escreve `text-{primary,warning,danger}-text-strong`
  numa cadeia de `{% if variant`. O mapa vive na tag.
- `test_layout_row_mantem_raio_de_papel_e_a_razao_esta_no_arquivo` migra de
  alvo: a razão do raio de papel passa a ser cobrada no painel de decisão, não
  no `alert.html` — que a partir daqui é campo, sem exceção interna.
- O JS de duplicidade escreve num id que existe no DOM renderizado.

### O que não dá para testar aqui

O contraste medido do ícone (`currentColor` sobre `-subtle`) foi verificado na
issue `#124` e está registrado na memória do backlog. Não remedir.

## Invariantes

Nenhum invariante de `docs/matriz-invariantes.md` é tocado: a mudança é de
apresentação, sem service, sem policy, sem model, sem migration. Os invariantes
que **governam** o trabalho são as regras nomeadas do design system:

| Regra | Como este plano a honra |
|---|---|
| Sinal Único | O painel deixa de comunicar nível só por cor: ganha ícone de variante. |
| Falha alta, nunca plausível (A-1) | Estendida ao painel, que hoje não tem fallback. |
| Token, nunca shade | Nenhuma cor crua entra; a tag emite utilities semânticas. |
| 14px | Descrição de decisão irreversível sobe de `text-xs` para `text-sm`. |
| Raio Crescente | Painel = papel (`rounded-xl`, `shadow-sm`); `alert.html` = campo (`rounded-lg`, sem sombra). A exceção interna do `alert.html` morre junto com o `row`. |
| Chrome Sem Parâmetro | `desc_class` — classe completa vinda da tela chamadora — deixa de existir. |
| Reversão Não é Erro | **Deliberadamente não aplicada aqui.** É a #128. |
| O domínio manda na interface | Os `{% if pode_* %}` de `detalhe.html` não se movem. |

## Riscos

| Risco | Mitigação |
|---|---|
| **Gate do `app.css`.** `app.css` é versionado e o `AGENTS.md` não menciona o passo. Classe Tailwind nova em template não compilada = estilo silenciosamente ausente. | Rodar `make css-build` antes do PR e conferir o diff. As classes previstas (`flex`, `gap-2`, `h-4`, `w-4`, `shrink-0`, `mt-0.5`, `text-sm`, `rounded-xl`, `shadow-sm`) já são usadas hoje, então a expectativa é diff vazio — mas a expectativa não substitui a execução. |
| **Regressão visual nos 5 painéis.** São a superfície onde o chefe de setor autoriza e recusa. | Migração numa fatia própria (F-3), com teste por call site; `detalhe.html` já tem cobertura de view por estado. |
| **Ícone novo em 3 telas** (D-12). Mudança visível que ninguém pediu explicitamente. | É a decisão S-3, tomada pelo dono do produto no shape. Registrar no corpo do PR. |
| **Contagem de live region.** `test_views.py:2713` quebra se a marcação de feedback mudar de forma. | O painel não é live region e o `alert.html` não muda de `role`. Rodar a suíte inteira, não só os testes de componente. |
| **Casca hidratada com ícone.** Com `icone` morto, a caixa de duplicidade passa a renderizar um ícone `danger` que antes não existia — dentro de um elemento `hidden` com `role="none"`. | Comportamento correto (a caixa aparece com ícone quando o JS a revela) e coberto por teste de marcação. |
| **Escopo escorregando para `_modal_icon.html` ou para a #128.** | Ambos listados em "O que NÃO muda". |

## Critérios de aceite × onde são fechados

| Critério da issue | Fatia |
|---|---|
| Shape feito e API registrada antes do código | §Decisões do shape, este documento |
| `alert.html` com contrato de uma frase | F-4 (D-5) |
| Nenhum call site depende de `{% else %}` não documentado | já satisfeito; guarda em F-6 |
| Nome acessível por painel, sem `role="group"` anônimo | F-2 (D-9) |
| Nenhum partial de domínio reimplementa o mapa de cor | F-1 + F-2 (D-7, D-10) |
| Painel comunica nível por mais do que cor | F-2 (D-6, S-2) |
| Descrição do painel em corpo de 14px | F-2 (D-10) |
| `desc_class` deixou de existir | F-3 (D-11) |
| `icone=False` resolvido na raiz | F-4 (D-2, S-3) |
| `role`/`aria-live` contraditórios impossíveis | F-4 (D-3) |
| Casca hidratada com slot de `id` declarado | F-4 + F-5 (D-4, D-14) |
| Call sites migrados (a issue diz "7"; em includes são **10**: 5 de `_confirmacao_acao.html` + 5 de `alert.html` com parâmetro morto) | F-3 + F-4 |
| Testes cobrindo API nova e cada include migrado | todas as fatias |
| `docs/design-system.md` §Índice atualizado | F-6 (D-15) |
| `pytest`, `ruff check`, `ruff format --check`, `mypy apps` verdes | antes do push |

Nota sobre a contagem de call sites: a issue fala em "7 call sites de domínio".
O levantamento no código vivo dá **12** includes de `components/alert.html` —
`login_bloqueado.html` (1), `copiar_confirmacao.html` (1), `rascunho_form.html`
(1), `_confirmacao_acao.html` (2), `preview_importacao_scpi.html` (3),
`confirmar_importacao_scpi.html` (2), `nova_saida_excepcional.html` (2) — mais
**5** includes de `_confirmacao_acao.html` em `detalhe.html`. Depois da
extração, `alert.html` fica com **10** chamadores, todos `stack`. Destes, 5
passam parâmetro morto e são migrados: `copiar_confirmacao.html` (1),
`nova_saida_excepcional.html` (2), `confirmar_importacao_scpi.html` (2).
