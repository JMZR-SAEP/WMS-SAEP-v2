# Plano de auditoria — front-end restante

Continuação da auditoria de UI conduzida via `/impeccable`. As telas full-page já haviam sido
auditadas (blocos 1–4 de requisições/auth + blocos A–D de estoque/notificações). Este plano cobriu
o que sobrou: a camada de tokens, os componentes compartilhados, os partials de domínio e o
comportamento em JS.

Nota de contagem: este plano falava em "19 telas full-page" desde o começo. A Etapa 8 recontou o
inventário de `templates/` fora de `partials/` e achou **20** — `copiar_confirmacao.html` não
tinha entrado na conta original. As 20 foram varridas.

> **PLANO CONCLUÍDO (2026-09-01).** As nove etapas fecharam. Nada aqui é trabalho pendente — o
> documento vira registro do que foi medido, decidido e corrigido. O que sobrou está em "Depois do
> plano", no fim.
>
> | Etapa | Fechou em | Audit | Critique |
> |---|---|---|---|
> | 0–5 | até 2026-08-27 | — | — |
> | 6 — partials de requisições | 2026-08-28 (PR #47) | 15/20 | 25/40 |
> | 7 — partials de estoque | 2026-08-31 | — | 23/40 |
> | 8 — regressão das telas | 2026-09-01 | — | **21/40** (baseline do produto) |
>
> - **Etapas 0–5.** Não mexer — ver "Etapas concluídas" abaixo. A Etapa 5 (listagem em cartões)
>   fechou com audit + correções + critique; o reteste da tabela no catálogo está em `DESIGN.md`.
> - **Etapa 6** (2026-08-28): audit + correções + critique num PR só. 0 P0, 4 P1 e 2 P2, todos
>   corrigidos na própria branch.
> - **Etapa 7** (2026-08-31): audit + 6 PRs de correção + critique. O P0 e os P1 que sobraram
>   viraram as issues #161–#164 — **as quatro fechadas**.
> - **Etapa 8** (2026-09-01): audit sem alvo + correções + critique sem alvo + backlog da critique
>   executado. É a baseline heurística do produto inteiro, que não existia. O P0, os três P1 e os
>   dois P2 dela foram fechados na sequência, em oito commits.
> - **As issues do plano fecharam.** O que sobrou virou backlog novo — #165 a #173, listadas em
>   "Depois do plano".
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

## Etapa 6 — Partials de requisições (concluída em 2026-08-28)

Entregue no PR #47 (`fix/etapa-6-partials-requisicoes`), nas duas fases que o plano fixa. Audit
**15/20**; critique **25/40** com 0 P0, 4 P1 e 2 P2 — todos os P1 e P2 corrigidos na própria branch.

### Resposta à pergunta que a etapa fazia

**Quanto disso ainda precisa existir depois das etapas 1–5?**
Duas respostas opostas no mesmo diretório. **Passou:** os dois alerts de corpo são `body_template`
puro dentro de `components/alert.html`; `_estado_badge` é o modelo do contrato de partial de
domínio; `_confirmacao_acao` + `_painel_decisao` são casca fina de verdade. **Falhou:** os 5 modais
de ação não usavam `.rotulo-campo`, `components/form_field.html` nem o marcador de obrigatório
canônico — quatro traziam `text-sm font-medium text-text-primary` e o de devolução
`text-xs font-semibold uppercase`, com a régua até o campo em `mt-3` num e `mt-1` noutro. Duas
tipografias de rótulo e três réguas nos modais da mesma tela, que é exatamente a doença que
`.rotulo-campo` foi criada para curar.

### O que a Fase 1 corrigiu

Além do contrato de campo dos cinco modais:

- `_modal_form_estorno` era o único que não marcava o campo inválido no 422 — o erro existia para o
  leitor de tela e não para o olho;
- `render_modal_erro` não conhecia `corpo_com_campo_focavel` nem `loading_label`, então todo
  re-render com erro ganhava uma parada de tabulação a mais e perdia o rótulo de progresso;
- painéis de decisão não preenchiam a linha da grade (medido a 202px de coluna: wrappers 214/214/214,
  painéis 194/214/194);
- o trilho da timeline estava a 17px do centro dos marcadores (84px contra 101px, medido no
  navegador);
- a caixa EST-07 era um alerta desenhado à mão, com os tokens de `warning` mas sem o glifo de nível
  — severidade só por cor, em 12px.

`test_nenhum_rotulo_de_campo_escrito_a_mao` deixava os cinco passarem porque exigia
`text-xs`/`font-medium`/`uppercase` **juntas**; o critério passou a ser "a label declara tipografia
própria".

### O que a Fase 2 corrigiu

- **Borda de contorno reprovava na WCAG 1.4.11.** Medido sobre branco: `danger-outline` 1,92:1,
  `warning-outline` 1,45:1, `return-outline` 1,26:1, contra os 4,77:1 do `secondary`. Quatro dos
  cinco gatilhos de workflow do detalhe usavam as variantes reprovadas — as ações destrutivas eram
  os controles menos visíveis da página. `warning-outline` ficou como exceção documentada: a família
  âmbar não tem nenhum token de borda que passe (amber-500 dá 2,15:1). A exceção vive em
  `docs/design-system.md`, §Exceções abertas ao piso de contraste, com a medição e o critério de
  encerramento — este plano registra que ela foi aberta, o contrato registra que ela segue aberta.
- **O estorno usava o vocabulário de perigo**, com a contradição escrita no próprio
  `_modal_icon.html`. Migrado para `return` nas quatro superfícies.
- **O recap da retirada omitia o que faz uma entrega estar errada:** linhas parciais, justificativa
  obrigatória e retirante.
- **A grade de decisão afirmava equivalência** entre autorizar, retornar e recusar — três cartões a
  383×154px, três botões a 349×44px, lavagens `info` e `danger` a 1,00:1 e o mesmo glifo circular.
- **O alerta EST-07 diagnosticava e abandonava** (zero links no feed). Ganhou rota para a saída
  excepcional, condicionada a `pode_consultar_saidas_excepcionais`.

### Pendências que a etapa deixou — as duas fechadas

- A lista nomeada de quatro rótulos de `estoque/` dentro do guarda, com instrução de sumir quando a
  Etapa 7 fechasse: **fechou**, e o guarda vale para `apps/` inteiro.
- `corpo_com_campo_focavel` faltando no equivalente de `apps/estoque/views.py`: **corrigido**
  (`views.py:534`).

### Nota de método

A Etapa 6 foi a primeira a registrar por experimento que o `[]` do detector é não-evidência: um
controle com os mesmos três defeitos dá 3 achados em estilo inline e `[]` em classes Tailwind. A
Etapa 7 repetiu o achado e a Etapa 8 o quantificou — 82 de 83 templates são fragmentos, 55 de 83
usam utility de cor.

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

### P0/P1/P2 que sobraram — as quatro issues fechadas

Viraram issue própria em vez de entrar em `/impeccable polish`, porque o escopo passava de
front-end. Todas fechadas até 2026-09-01:

- **#161** (P0) — persistir as divergências e entregá-las ao chefe de almoxarifado. O fluxo termina
  sem produzir a lista de CADPROs que ele veio buscar.
- **#162** (P1) — recorte e âncora no preview: sem filtro nem paginação, 300 linhas dão ~61 telas; e
  a barra de ação é `fixed sm:static`, ou seja, o desktop é a única cena sem barra.
- **#163** (P1) — desenhar `_delta_movimentacao`. O átomo do north star nunca foi desenhado.
- **#164** (P2) — copy: hierarquia da recapitulação, legenda que promete uma cor que nenhum cartão
  veste, e a progressão invertida dos alerts.

A #164 merece nota: a Etapa 8 remediu a legenda do preview e o desencontro **ainda estava lá** — os
swatches em `bg-warning-muted`/`bg-primary-muted` (shade 100, rgb(254,243,198) e rgb(219,234,254))
contra cartões em `-subtle` (shade 50, rgb(255,251,235) e rgb(239,246,255)). O que a #164 fechou foi
a hierarquia da recapitulação; o degrau da legenda sobreviveu à issue que o nomeava e virou a
**#167**, que carrega esse escopo restante. É o tipo de achado que só uma segunda medição pega.

### Nota de método

A critique rodou em dois sub-agentes isolados (revisão de design / detector + navegador). O
detector devolveu `[]` nos seis arquivos — um canário sintético confirmou que ele dispara, mas a
engine estática não resolve utility do Tailwind para cor, então **toda medição de contraste veio do
navegador**. Vale para as próximas etapas: em template Django + Tailwind, o `[]` do detector não é
evidência de ausência.

## Etapa 8 — Passe de regressão (concluída em 2026-09-01)

Entregue: audit sem alvo + 3 commits de correção + critique sem alvo + 8 commits fechando o backlog
que ela produziu. Pontuação heurística **21/40**, medida ANTES desses oito commits; snapshot em
`.impeccable/critique/2026-09-01T16-35-35Z__apps.md`.

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

**Mobile nas 20?**
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

### O backlog da critique, executado

O P0, os três P1 e os dois P2 foram fechados na mesma etapa, em oito commits.

| Commit | Escopo | Severidade |
|---|---|---|
| `f040ece` | `components/quantidade.html` + `formatar` em notação pt-BR + entregue líquida fora de `pode_devolver` | P1 |
| `df909e0` | Saldo visível nos dois pontos de decisão, erro com os dois números, item marcado, `retornar` liberado ao chefe | **P0** |
| `a8c21dc` | Contagem nas quatro listagens nuas; ledger e catálogo deixam de terminar em beco | P1 |
| `e8df9bd` | Modal na saída excepcional, `MOTIVO` sem default real, retirante e devolução lidos na timeline | P1 |
| `020e675` | Notificações viram cartões com o desfecho no título; `return-strong` separa estorno de devolução | P1/P2 |
| `3ce426c` | Carimbo de estado com posição fixa até `xl` | P2 |
| `6a8719d` | Uma gramática de busca, e busca nas três listagens de trabalho | P1 |
| `83344ca` | Estáticos com hash no nome no piloto | P2 |

**A maior oportunidade era única e foi a primeira.** A quantidade é o dado que este produto existe
para controlar e recebia tratamento tipográfico em **um** lugar — o modal de retirada. Promovê-la a
componente consertou de uma vez o alinhamento do catálogo (os três valores começavam em x=330, x=361
e x=360 no mesmo cartão; agora terminam todos em x=582), a unidade órfã do detalhe, o número nu do
atendimento e o separador decimal — porque passou a existir um ponto só para consertar.

**Duas decisões de rumo que os testes existentes forçaram**, e as duas estavam certas: as filas têm
ordem de domínio (FIFO por `atualizado_em`) e não podiam ganhar inversão de ordem, só contagem; e o
marcador de alvo de cartão só vale dentro do chrome de `#card_abertura`, o que tirou o catálogo da
lista de cartões clicáveis e lhe deu um link explícito com piso de 44px.

**Uma mudança fora do front-end**, declarada: `pode_retornar_para_rascunho` passou a incluir o chefe
do setor do beneficiário. A condição é a mesma de autorizar e recusar, então não abre alcance novo —
quem já podia encerrar a requisição passa a poder devolvê-la. `docs/matriz-permissoes.md` e a TR-006
de `docs/estado-transicoes-requisicao.md` foram atualizadas.

### Nota de método

A critique cobrou o preço de uma correção da própria Fase 1: o `flex-wrap` que consertou o número
público partido a 375px fez o carimbo de estado ocupar a linha 1 em uns cartões e a linha 3 em
outros. Vale registrar como padrão de trabalho — correção de defeito medido pode comprar outro
defeito medido, e a fase seguinte é onde isso aparece. A emenda está em `DESIGN.md`, com o
deslocamento do carimbo medido em cinco viewports.

---

## Resumo

| Etapa | Escopo | Alvos | Fases |
|---|---|---|---|
| 0–5 | Tokens, ação, feedback, overlay, busca/filtro, listagem em cartões | — | **concluídas** |
| 6 | Partials de requisições | 13 | **concluída** (15/20 · 25/40) |
| 7 | Partials de estoque | 11 → 10 | **concluída** (23/40) |
| 8 | Regressão das telas | 20 | **concluída** (21/40) |

As nove etapas estão concluídas e congeladas. A ordem real de execução foi 6 → 7 → 8, na sequência
que o plano previa: as três só dependiam de 1–5, e a 8 fechou por último porque é a de regressão.
P0/P1 que sobravam das critiques viraram issue própria quando o escopo passava de front-end — foi o
caso da #161 —, e todas as issues abertas por este plano estão fechadas.

---

## Depois do plano

O que **não** entrou, com o motivo. Nada aqui bloqueia o piloto; é o que uma próxima rodada pegaria.
Tudo abaixo está no rastreador — o documento registra a decisão, a issue carrega o trabalho.

| Issue | Item | Triagem |
|---|---|---|
| #165 | Remedir a baseline heurística | `ready-for-agent` |
| #166 | Varredura de contraste na lane Navegador | `ready-for-agent` |
| #167 | Legenda do preview SCPI um degrau acima dos cartões | `ready-for-agent` |
| #168 | Mover `input.css` para fora da árvore de estáticos | `ready-for-agent` |
| #169 | 257 KB em toda tela | `needs-triage` |
| #170 | `Recusar` e `Cancelar` são duas operações? | `needs-triage` |
| #171 | Preview SCPI com arquivo real | `needs-triage` |
| #172 | Silhueta própria para o glifo `danger` | `needs-triage` |
| #173 | Achados menores da critique da Etapa 8 | `needs-triage` |

Dark mode **não** virou issue: a decisão de mantê-lo fora está registrada no inventário desta
auditoria, com o motivo, e abrir issue para ela seria reabrir uma decisão já tomada. Adotá-lo pede
ADR, não ticket.

### Medição

- **Rerodar `/impeccable critique` sem alvo.** A baseline de 21/40 foi medida ANTES dos oito commits
  do backlog da Etapa 8. Seis das dez heurísticas foram atacadas depois dela (2, 4, 5, 6, 7, 9), e a
  nota atual é desconhecida. Sem essa segunda medição não há tendência, só um ponto.
- **Varredura de contraste na lane Navegador (ADR-0019).** O guarda de pares de cor de
  `test_tokens_semanticos.py` vê par no mesmo elemento; o caso de fundo no pai e cor no filho —
  o de `atender_retirada.html` — só apareceu medindo no navegador. É o único achado desta auditoria
  cuja recorrência nada impede.

### Dívida declarada

- **`input.css` dentro da árvore de estáticos.** Ele é fonte do Tailwind, não asset servido, e
  obrigou `apps/core/staticfiles.py` a existir para o `collectstatic` do piloto não morrer no
  `@import "tailwindcss"`. Movê-lo para fora é a correção certa e mexe em Makefile, teste de tokens
  e documentação do design system.
- **Peso da página.** 11 arquivos e ~257 KB decodificados em toda tela, incluindo `modal.js` (32 KB)
  e `autocomplete.js` (17 KB) no `/login/`, que tem dois campos e um botão. Sem code splitting nem
  carregamento condicional. Aceitável em rede interna; medido e registrado.

### Decisões de produto que a auditoria levantou e não podia tomar

- **Dark mode** segue fora de escopo (ver a nota do inventário). Adotá-lo é ADR e revisão inteira da
  escala de tokens.
- **`Recusar` e `Cancelar` são duas operações ou uma com dois donos?** Ambas encerram a requisição
  sem baixa de estoque, e a tela do chefe mostra as duas em painéis vermelhos quase idênticos.
- **Preview do SCPI a 300 linhas.** A #162 fechou o recorte; o comportamento com um arquivo real do
  SCPI nunca foi medido com dado real.
- **Glifo próprio para `danger`.** `informacao.svg` e `alerta.svg` continuam quase iguais em 16px
  dessaturados. Acrescentar um glifo é decisão de vocabulário visual.
