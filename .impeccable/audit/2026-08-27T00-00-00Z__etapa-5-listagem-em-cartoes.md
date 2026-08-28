# Audit — Etapa 5: Listagem em cartões

**Alvos:** `components/table.html`, `components/pagination.html`, `components/page_header.html`,
`components/ordenacao_data.html`, `components/icons/` (4 partials — `_check.html` removido nesta
etapa, ver P3 abaixo — + 15 svg)
**Data:** 2026-08-27 · **Plano:** `docs/plans/audit-frontend-restante.md` § Etapa 5, Fase 1

Verificação: markup lido; 8 telas renderizadas via `django.test.Client` com usuário do
`seed_dev` e inspecionadas em navegador a 1280×900 e 375×812 (geometria, nomes acessíveis e
árvore de headings medidos por DOM, não por captura). Folha de contato dos 19 ícones renderizada
e conferida glifo a glifo.

O detector mecânico rodou **degradado** (`htmlparser2`, `css-select`, `css-tree`, `domutils`
ausentes) e devolveu `[]`. Isso é subcontagem, não aprovação — os achados abaixo vêm de leitura e
de medição no navegador.

## Audit Health Score

| # | Dimensão | Nota | Achado principal |
|---|---|---|---|
| 1 | Acessibilidade | 2 | Os dois controles de paginação anunciam "Paginação do histórico de requisições" em vez de "Anterior"/"Próxima" |
| 2 | Performance | 2 | 3 listagens sem paginação nem `LIMIT`; catálogo de materiais renderiza o SCPI inteiro (~1,2 KB e 14 nós de DOM por cartão) |
| 3 | Responsivo | 4 | Zero overflow horizontal em 375 e 1280; todo alvo de toque em 44px |
| 4 | Tematização | 3 | `font-mono` no histórico de importações é uma segunda família não declarada; resto usa token semântico |
| 5 | Integridade de implementação | 2 | Três latas de lixo no catálogo de ícones para três significados; `enviar.svg` com traço-fantasma; `spinner.svg` morto e divergente da cópia inline |
| **Total** | | **13/20** | **Aceitável — trabalho significativo pela frente** |

## Veredito de integridade de implementação

**Falha parcial.** O chrome de cartões em si é coerente e específico do produto: `card_abertura`
sem parâmetro, grade que responde de 375 a 1536, `<h2>` por cartão, `dl` explícito, badge de estado
nunca só por cor. A Regra do Cartão Único da #83 se sustenta na medição.

O que falha é a borda do sistema:

- **A regra vale para 7 das 9 listagens.** `lista_materiais.html` copia a string de grade do
  `#cards_abertura` e escreve o `<article>` literal; `notificacoes/lista.html` é `<ul>` com linhas
  divididas. São três chromes de listagem convivendo para o mesmo trabalho.
- **O catálogo de ícones não é fonte única.** 12 SVGs inline no shell e nos componentes ignoram
  `{% icon %}`; dois deles duplicam um path do catálogo — e o spinner inline **diverge** do
  `spinner.svg` (que tem zero consumidores).
- **O catálogo tem três latas de lixo** (`lixeira`, `remover`, `estornar`) para três operações de
  domínio diferentes, uma delas — estorno — que por princípio de auditabilidade não apaga nada.

## Sumário executivo

- Score: **13/20** (Aceitável)
- 13 achados: **3 P1**, **6 P2**, **4 P3** (a paginação das três listagens é P1 pelo custo em
  produção, com rota de correção via `/impeccable optimize` — daí a marca P1→P2 no placar)
- Críticos:
  1. Nome acessível errado nos dois controles de paginação, em 5 telas (P1)
  2. Foco perdido a cada troca de ordenação (P1)
  3. Catálogo de materiais, saídas excepcionais e histórico de importações sem paginação (P1→P2)
  4. Três latas de lixo e um `enviar.svg` malformado no catálogo (P2)

## Achados por severidade

### [P1] Paginação: os dois botões herdam o `aria-label` do `<nav>`

- **Local:** `apps/core/templates/components/pagination.html:48,52,58,62` (raiz);
  5 chamadores: `historico_requisicoes.html:141`, `historico_movimentacoes.html:118`,
  `lista_minhas.html:68`, `fila_autorizacao.html:50`, `fila_atendimento.html:59`
- **Categoria:** Acessibilidade
- **Impacto:** `{% include %}` sem `only` deixa `aria_label` do contexto do include cair dentro de
  `button.html`, que renderiza `{% if aria_label %}aria-label="..."{% endif %}`. Medido no
  navegador: os dois controles anunciam `Paginação do histórico de requisições`. Quem usa leitor de
  tela ouve o mesmo nome duas vezes e não tem como saber qual avança e qual volta — o texto visível
  "Anterior"/"Próxima" é sobrescrito pelo `aria-label`.
- **WCAG:** 2.4.4 Link Purpose (A) e 4.1.2 Name, Role, Value (A)
- **Correção:** passar `aria_label=None` (ou usar `{% include ... only %}` com repasse explícito)
  nos quatro includes de `button.html` dentro de `pagination.html`. `TestPaginationHref`
  (`test_components.py:1246`) nunca passa `aria_label` no contexto, então o bug é invisível para
  ela: adicionar o parâmetro ao `_render` e travar o nome acessível de cada controle.
- **Comando:** `/impeccable harden`

### [P1] Ordenação: foco cai no `<body>` a cada troca

- **Local:** `apps/core/templates/components/ordenacao_data.html:43,45`
- **Categoria:** Acessibilidade
- **Impacto:** o controle vive **dentro** do próprio `hx-target` (`#resultados-…`) e não tem `id`.
  O htmx 2.0.10 restaura foco após swap procurando o mesmo `id` no DOM novo; sem `id`, o elemento
  focado é destruído e o foco volta para `<body>`. Quem ordena pelo teclado é jogado para o topo do
  documento e precisa tabular a tela inteira de volta. Confirmado no navegador
  (`sortHasId: false`, `sortInsideTarget: true`).
- **WCAG:** 2.4.3 Focus Order (A)
- **Correção:** dar um `id` estável ao controle (ex. `id="ordenacao-{{ target_id }}"`) — o htmx
  restaura o foco sozinho a partir daí. A live region `role="status"` também só anuncia a
  contagem; anunciar a nova ordem junto fecha o laço.
- **Comando:** `/impeccable harden`

### [P1] Três listagens sem paginação, com selector sem limite

- **Local:** `estoque/lista_materiais.html` (`selectors.listar_materiais_com_saldo`),
  `estoque/lista_saidas_excepcionais.html` (`listar_saidas_excepcionais`),
  `estoque/historico_importacoes_scpi.html` (`listar_historico_importacoes_scpi`)
- **Categoria:** Performance
- **Impacto:** as três renderizam o queryset inteiro. Medido: **1,2 KB de HTML e 14 nós de DOM por
  cartão**. O catálogo de materiais é populado pela importação SCPI, ou seja, cresce com o arquivo
  do sistema legado: 2.000 materiais viram ~2,4 MB de HTML e ~28.000 nós numa resposta só — numa
  tela que o almoxarifado abre **do celular, em pé no galpão**. `components/pagination.html` já
  existe e já preserva querystring; as três telas simplesmente não o chamam.
  `historico_importacoes_scpi.html:12` ainda conta com `{{ importacoes|length }}`, que materializa
  o queryset inteiro só para exibir o número.
- **Correção:** `listagem.paginar(...)` na view + `{% include 'components/pagination.html' %}` nas
  três telas, como já fazem as outras seis. No catálogo, `filter_busca` no lugar do `<form>`
  artesanal fecha a mesma lacuna do lado do filtro.
- **Comando:** `/impeccable optimize`

### [P2] Catálogo de ícones: três latas de lixo para três significados

- **Local:** `components/icons/lixeira.svg`, `remover.svg`, `estornar.svg`
- **Categoria:** Integridade de implementação
- **Impacto:** conferido na folha de contato: os três desenham a mesma lata de lixo com tampa,
  variando só o detalhe interno. Servem a "cancelar requisição" (`detalhe.html:215`), "remover
  linha de item" e "estornar requisição" (`detalhe.html:330`). O glifo diz *apagar* nos três casos.
  No estorno isso contradiz o Princípio 2 do produto — auditabilidade acima de conveniência: o
  estorno preserva número público, timeline e movimentação; nada é apagado. O ícone ensina o
  contrário do domínio.
- **Correção:** manter a lata só onde algo some de fato (`remover` de linha); dar ao estorno um
  glifo de reversão (a família do `devolver.svg` já existe) e ao cancelamento um glifo próprio.
- **Comando:** `/impeccable clarify`

### [P2] `enviar.svg` renderiza com traço-fantasma e corpo assimétrico

- **Local:** `components/icons/enviar.svg`
- **Categoria:** Integridade de implementação
- **Impacto:** ampliado a 110px, o path emite um traço fino solto no canto superior esquerdo, fora
  do corpo do avião, e o corpo é assimétrico em relação ao eixo horizontal (o `paper-airplane` de
  origem é simétrico). O segmento final `…l1.21-4.35a1.5 1.5 0 0 1 .3-1.4z` não fecha a silhueta.
  O ícone está em duas CTAs primárias: "Enviar para autorização" (`rascunho_form.html:315`,
  `detalhe.html:226`).
- **Correção:** revendorizar o glifo a partir da fonte, num viewBox 20 coerente com o resto.
- **Comando:** `/impeccable polish`

### [P2] `spinner.svg` é código morto e diverge da cópia inline em uso

- **Local:** `components/icons/spinner.svg` (0 consumidores) vs
  `components/autocomplete.html:137`
- **Categoria:** Integridade de implementação
- **Impacto:** o catálogo traz o arco de 1/4 padrão (`M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z`);
  o autocomplete inlina uma fatia de pizza (`M4 12a8 8 0 018-8v8z`). Dois spinners diferentes para
  o mesmo estado, e o que está no catálogo — o correto — nunca é usado. `autocomplete.html:132`
  também inlina, byte a byte, o path de `confirmar.svg`. O `{% icon %}` valida nome contra
  `ICONES_CATALOGO` e barra traversal, mas nada impede o bypass por SVG inline: são 12 no shell e
  nos componentes.
- **Correção:** trocar as duas cópias do `autocomplete.html` por `{% icon %}` e apagar a divergência.
  Um guard em `test_components.py` no formato do `test_todo_icon_template_de_button_honra_a_classe`
  (nenhum `<svg>` inline com `<path>` que já exista no catálogo) impede a reincidência.
- **Comando:** `/impeccable extract`

### [P2] `lista_materiais.html` duplica o chrome em vez de reusá-lo

- **Local:** `estoque/lista_materiais.html:37,39-42,77`
- **Categoria:** Integridade de implementação
- **Impacto:** a grade `grid items-start gap-3 sm:grid-cols-2 2xl:grid-cols-3` é copiada do
  `#cards_abertura` — o container não tem nada de condicional, só o `<article>` tem. Uma mudança de
  breakpoint no chrome não chega aqui. A linha 77 ainda carrega um comentário órfão
  (`{# Desktop: tabela de dados. <tr> literal … #}`) descrevendo uma tabela que a #83 removeu —
  documentação que contradiz o código. E o `aria-label="Material com divergência crítica"` no
  `<article>` (linha 41) substitui o nome acessível do cartão: o leitor de tela anuncia o rótulo
  genérico no lugar do código do material, que é a identidade do registro. O badge "Divergente" ao
  lado já comunica o estado.
- **Correção:** usar `#cards_abertura` no container; manter o `<article>` literal (o estilo
  condicional justifica) mas remover o `aria-label`; apagar o comentário órfão.
- **Comando:** `/impeccable distill`

### [P2] O `<h2>` do cartão não identifica o cartão

- **Local:** `historico_requisicoes.html:96`, `lista_minhas.html:34`,
  `historico_movimentacoes.html:90`
- **Categoria:** Acessibilidade
- **Impacto:** medido na árvore de headings: o histórico entrega três `H2:Rascunho` idênticos na
  mesma página; o ledger entrega `H2:MAT-002 — Caneta esferográfica` repetido a cada
  movimentação do mesmo material. Navegar por heading — que é como se varre uma lista com leitor de
  tela — devolve uma lista de rótulos indistinguíveis. No ledger o diferenciador real (tipo, data,
  delta) está fora do heading. O `aria_label` do botão já desambigua a *ação*
  ("Ver detalhes do rascunho criado em …"); o título do cartão não.
- **Correção:** compor o heading com o discriminador que a tela já tem em mãos — data no rascunho,
  tipo+data no ledger — resolvido na tela chamadora, sem parametrizar o chrome (guardrail da #83).
- **Comando:** `/impeccable clarify`

### [P2] O rótulo do controle de ordenação descreve o estado, não a ação

- **Local:** `components/ordenacao_data.html:43,45`
- **Categoria:** Acessibilidade / clareza
- **Impacto:** com `ordem='desc'` o botão diz "Mais recentes primeiro ↓" e o `aria-label` diz
  "atualmente decrescente" — mas o `href` é `?ordem=asc`. Rótulo e destino discordam: quem lê "Mais
  recentes primeiro" e quer isso clica e recebe o inverso. É um botão de estado disfarçado de botão
  de ação, sem `aria-pressed` nem `aria-sort` que resolvessem a ambiguidade (o `<th aria-sort>` que
  fazia esse papel saiu com a tabela).
- **Correção:** ou o rótulo passa a nomear a ação ("Ordenar por mais antigas ↑"), ou o controle vira
  um par de opções com estado (`aria-pressed`). A primeira é a menor mudança e resolve.
- **Comando:** `/impeccable clarify`

### [P3] `_check.html` no estado vazio das saídas excepcionais

- **Local:** `components/icons/_check.html` usado em `lista_saidas_excepcionais.html:62,64`
- **Categoria:** Clareza
- **Impacto:** o partial desenha uma **caixa marcada** — "feito", "aprovado". Ele ilustra
  "Nenhuma saída excepcional registrada", ou seja, o oposto: nada foi feito ainda. O `_prancheta` e
  o `_caixa_entrada` usados nos outros estados vazios acertam o registro.
- **Correção:** trocar por `_prancheta` (registro em branco) ou `_caixa_entrada`.
- **Comando:** `/impeccable clarify`

### [P3] Duas convenções de dimensionamento e dois viewBox no catálogo

- **Local:** `components/icons/*.svg`
- **Categoria:** Integridade de implementação
- **Impacto:** 13 SVGs dimensionam por `class`, `devolver.svg` aceita os dois, `voltar.svg` só por
  `size` (e ignora `class` em silêncio). `devolver` e `voltar` usam viewBox 24 contra 20 dos demais,
  o que os deixa opticamente mais leves na mesma caixa — visível na folha de contato. O caso pior
  (`icon_template` recebendo um SVG que só dimensiona por `size`, gerando `width=""`) **já está
  travado** por `test_todo_icon_template_de_button_honra_a_classe`, cujo docstring, porém, fala em
  "10 dos 11 `.svg`" quando hoje são 15.
- **Correção:** `class="{{ class }}"` em todos, viewBox 20 uniforme, e atualizar o docstring do guard.
- **Comando:** `/impeccable polish`

### [P3] `confirmar.svg` e `confirmar_check.svg` são o mesmo glifo

- **Local:** `components/icons/confirmar.svg`, `confirmar_check.svg`
- **Categoria:** Integridade de implementação
- **Impacto:** conferido lado a lado a 110px: o mesmo check, variando só a espessura do traço. Um
  serve "Registrar saída excepcional", o outro "Confirmar importação" — duas confirmações que não
  precisam de dois desenhos. Nome também não distingue nada (`confirmar_check` é redundante).
- **Correção:** manter um; o outro sai do `ICONES_CATALOGO` junto com o arquivo.
- **Comando:** `/impeccable distill`

### [P3] Deriva tipográfica no histórico de importações e no `page_header`

- **Local:** `historico_importacoes_scpi.html:27,48`; `components/page_header.html:20-23`
- **Categoria:** Tematização
- **Impacto:** o `<h2>` do cartão é `font-mono text-xs` — 12px é o tamanho de *rótulo estrutural*,
  não o de título de cartão (os outros seis usam `text-sm font-semibold`), e `font-mono` introduz
  uma segunda família de fonte que o DESIGN.md não declara ("uma família só"). Separadamente, o
  docstring do `page_header` diz que `class` é "obrigatório na prática", mas
  `notificacoes/lista.html:8` legitimamente não passa (o wrapper flex já dá o respiro) — a regra
  documentada não é a regra real.
- **Correção:** alinhar o título do cartão de importação ao resto (`text-sm font-semibold`,
  mono só no hash); corrigir o docstring do `page_header` para "margem quando a tela não a
  fornece por layout".
- **Comando:** `/impeccable typeset`

## Padrões e problemas sistêmicos

1. **`{% include %}` sem `only` vaza contexto.** A paginação é o caso que dói (P1), mas a causa é
   estrutural: qualquer componente que receba um parâmetro homônimo de um parâmetro de
   `button.html` produz o mesmo silêncio. Vale um guard genérico, não cinco correções pontuais.
2. **O catálogo de ícones não tem exclusividade.** `{% icon %}` valida nome e barra traversal, mas
   12 SVGs inline passam ao largo dele — e onde a cópia inline diverge do catálogo (spinner), é a
   divergente que está em produção.
3. **A Regra do Cartão Único vale para 7 de 9 listagens.** As duas exceções não estão declaradas em
   lugar nenhum: uma copia o chrome, a outra usa `<ul>`. Ou viram exceção documentada, ou voltam
   para o chrome.
4. **O comentário sobrevive ao código que descrevia.** `lista_materiais.html:77` e o docstring do
   guard de ícones descrevem um mundo com tabela e com 11 SVGs. Comentário denso é o padrão da casa
   e funciona — mas envelhece.

## O que está funcionando

- **A medição da #83 se confirma.** Zero overflow horizontal em 375 e em 1280; grade de 1 → 2
  colunas; cartão de 327px no celular. A tabela teria estourado nas duas larguras.
- **Alvos de toque impecáveis.** Todo controle das telas medidas em 44px, incluindo os de
  paginação no mobile. Os únicos elementos abaixo disso são os `<input type=checkbox>` de 20px,
  que são o padrão documentado (label de 44px em volta).
- **Hierarquia de heading correta** em todas as telas de cartão: um `H1` da tela, `H2` por cartão,
  sem salto de nível.
- **A preservação de querystring da paginação está certa e travada.** `querystring_sem_page` +
  `page` no fim batem com a ordem canônica da #152, e `TestPaginationHref` cobre as três armadilhas
  de template que já quebraram isso antes (`add` numérico, escape duplo do `&`, separador do
  `yesno`).
- **`page_header.html` faz exatamente uma coisa** e a documentação explica *por que* o `<h1>` não
  mora na topbar — a decisão de arquitetura está no lugar onde alguém a procuraria.
- **Contagem total presente e sem duplicação:** `ordenacao_data` só mostra o número quando
  `pagination` não vai mostrá-lo.

## Nota sobre o plano

A Fase 1 da Etapa 5 pedia conferência em **dark mode**. O projeto não tem dark mode: zero
`prefers-color-scheme`, zero `dark:` no `app.css` compilado, e o DESIGN.md compromete-se com um
único mundo claro ("papel frio sobre papel branco"). Não era regressão — era premissa do plano que
não batia com o sistema incumbente, e auditar a ausência mediria o plano, não o produto.

**Resolvido:** o item saiu das Etapas 5 e 8 de `docs/plans/audit-frontend-restante.md`, com a
justificativa registrada nas notas do inventário para ninguém reintroduzi-lo. Adotar dark mode
continua possível, mas como decisão de produto — ADR e revisão da escala de tokens inteira —, não
como item de checklist de auditoria.

O que existia de real e adjacente foi corrigido nesta etapa: `base.html` não declarava
`color-scheme: light`, então o widget nativo do `<input type="date">` dos filtros herdava o tema
escuro do SO numa página que só existe em claro.

## Ações recomendadas, em ordem

1. **[P1] `/impeccable harden`** — nome acessível da paginação (5 telas) e `id` do controle de
   ordenação para o htmx restaurar o foco.
2. **[P1] `/impeccable optimize`** — paginar catálogo de materiais, saídas excepcionais e histórico
   de importações; matar o `|length` que materializa o queryset.
3. **[P2] `/impeccable clarify`** — glifo do estorno, `_check` do estado vazio, rótulo da ordenação
   e discriminador no `<h2>` do cartão.
4. **[P2] `/impeccable extract`** — trazer os SVGs inline do `autocomplete.html` para `{% icon %}` e
   guardar o catálogo contra bypass.
5. **[P2] `/impeccable distill`** — `lista_materiais` reusando `#cards_abertura`, comentário órfão
   fora, um check só no catálogo.
6. **[P3] `/impeccable typeset`** — título do cartão de importação e docstring do `page_header`.
7. **[P3] `/impeccable polish`** — revendorizar `enviar.svg`, uniformizar viewBox e convenção de
   dimensionamento.
