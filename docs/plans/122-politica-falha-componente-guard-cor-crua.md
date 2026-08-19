# Plano de implementação — #122

**Issue:** [#122 — Definir a política de falha de componente e fechar o guard de cor crua](https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/122)

**Tipo:** HITL — a issue abre com duas decisões de política. Ambas foram tomadas
pelo dono do produto antes de qualquer linha de código:

- **Decisão A = A-1** — falha alta em todo lugar. `alert.html` passa a gritar como
  o `badge.html` já grita, e `_estado_badge.html:25` para de anular o fallback
  vermelho do componente global.
- **Decisão B = B-1** — o regex do guard cobre as famílias de paleta crua, e
  `badge.html` entra numa allowlist explícita que nomeia as quatro variantes de
  catálogo permitidas. Vazamento em qualquer outro arquivo quebra o teste.

## Escopo

### O que muda

1. **`docs/design-system.md`** ganha a Decisão A como regra inviolável nomeada,
   com o mecanismo que a verifica na coluna de sempre. A tabela hoje diz "Sete
   regras" — passa a oito.
2. **`apps/core/templates/components/alert.html`** deixa de mandar variante
   desconhecida para o azul de info. O `{% else %}` passa a ser o ramo do grito.
3. **Os quatro partials de domínio que anulam o fallback** deixam de mapear
   valor desconhecido para uma variante plausível. Cada um repassa o valor cru
   como `variant`, deixando o fallback do `badge.html` fazer o trabalho que ele
   já sabe fazer:
   `requisicoes/partials/_estado_badge.html` (`slate`),
   `estoque/partials/_badge_tipo_movimentacao.html` (`slate`),
   `estoque/partials/_estado_saida_badge.html` (`teal`) e
   `estoque/historico_importacoes_scpi.html` (`slate`).
   Os três de estoque entraram no escopo por decisão do dono do produto depois
   da primeira rodada de revisão: "em todo lugar" da Decisão A-1 é para valer.
4. **`apps/core/tests/test_tokens_semanticos.py`** passa a enxergar as famílias
   que hoje ficam fora do regex, varre todos os templates do repositório em vez
   de só `components/` + `_messages.html`, e materializa a exceção declarada do
   design system numa allowlist por `(arquivo, família)` com justificativa
   escrita. A Decisão B fica registrada no próprio arquivo de teste. A docstring
   do módulo, que hoje descreve o alvo como
   "cor de paleta crua (blue/red/amber/green/teal)... dentro de
   `apps/core/templates/components/`", é reescrita junto — senão o arquivo passa
   a mentir sobre o próprio guard no primeiro parágrafo.
5. **Testes novos** cobrindo o comportamento de fallback escolhido. Os "três
   arquivos" do critério de aceite são `badge.html`, `alert.html` e
   `_estado_badge.html`. O `badge.html` **já** grita e **já** é testado — a
   issue #121 entregou o fallback que preserva dado, e
   `test_components_badge.py` cobre o sinal visível, o `label` em `sr-only`, o
   `data-badge-variant` e o token no lugar de `text-white`. Aqui ele entra como
   regressão: nada muda no arquivo, e os testes existentes passam a valer como
   o terceiro pé da mesma política, agora nomeada no `docs/design-system.md`.
   Os testes novos são de `alert.html` e `_estado_badge.html`, os dois arquivos
   que hoje contradizem essa política.
6. **A cadeia `_confirmacao_acao.*`** troca o token de cor `primary` por `info`,
   porque hoje ela depende **de propósito** do `{% else %}` do `alert.html` para
   traduzir vocabulário de botão em vocabulário de alerta — e é justamente esse
   `{% else %}` que a Decisão A-1 tira de circulação. Nenhuma classe muda.

### O que NÃO muda

- **A lista de variantes de nenhum componente.** `badge.html` continua com 13
  variantes conhecidas + fallback; `alert.html` continua com `info`, `success`,
  `warning`, `danger`.
- **O visual de qualquer valor que existe hoje.** Nenhuma classe muda em nenhum
  ramo reconhecido — nem nos componentes globais, nem nos quatro partials de
  domínio. Os três enums de estoque e o `EstadoRequisicao` continuam pintados
  exatamente como estão, incluindo o `teal` de `estornada`, que ganha ramo
  próprio justamente para não mudar.
- **As quatro variantes de catálogo do `badge.html`** (`orange`, `indigo`,
  `violet`, `yellow`) continuam de pé, com cor crua. Elas são a exceção
  declarada no `docs/design-system.md`; o problema desta issue nunca foi a
  existência delas, e sim o guard não enxergá-las.
- **O backdrop `bg-slate-900/50` do `modal.html`**, a segunda exceção declarada
  na mesma linha do design system. Ele entra na allowlist junto — hoje escapa
  do guard só porque a varredura não olha para `slate` e porque o `modal.html`
  nunca foi comparado contra a família certa.
- **O contrato de dismiss, o `_messages.html` e a paridade `alert` × `messages`.**
  São as issues #119 e #124.
- **`role`/`aria-live` de qualquer variante conhecida.** O `role` explícito
  passado pelo chamador continua tendo precedência sobre o default da variante.

## Arquivos tocados

| Arquivo | Natureza da mudança |
|---|---|
| `docs/design-system.md` | Regra inviolável nova + contagem "Sete" → "Oito" |
| `apps/core/templates/components/alert.html` | `{% else %}` vira ramo do grito; `info` ganha ramo explícito |
| `apps/requisicoes/templates/requisicoes/partials/_estado_badge.html` | `{% else %}` repassa o estado cru como `variant` |
| `apps/estoque/templates/estoque/partials/_badge_tipo_movimentacao.html` | Idem; `aria_label` sai do ramo do grito e vira `prefixo_sr` |
| `apps/estoque/templates/estoque/partials/_estado_saida_badge.html` | Ramo explícito para `estornada` **antes** de o `{% else %}` gritar; mesma troca de `aria_label` |
| `apps/estoque/templates/estoque/historico_importacoes_scpi.html` | `{% else %}` repassa `imp.status` cru como `variant` |
| `apps/requisicoes/templates/requisicoes/partials/_confirmacao_acao.html` | `variant_token` "primary" → "info": alinhar ao vocabulário do `alert.html` (ver abaixo) |
| `apps/requisicoes/templates/requisicoes/partials/_confirmacao_acao_corpo.html` | Mesma troca nas duas condicionais de cor |
| `apps/requisicoes/templates/requisicoes/partials/_confirmacao_acao_banner_corpo.html` | Mesma troca na condicional de cor |
| `apps/requisicoes/templates/requisicoes/detalhe.html` | Único chamador que passa `variant_token="primary"` (linha 260) |
| `apps/core/tests/test_tokens_semanticos.py` | Regex, escopo de varredura, allowlist, registro da Decisão B |
| `apps/core/tests/test_components_badge.py` | Guard local apertado para classe+contagem, no mesmo rigor do guard de repositório |
| `apps/core/tests/test_components_alert.py` | Testes do grito de `alert.html` |
| `apps/requisicoes/tests/test_partials.py` (novo) | Teste do estado não mapeado chegando ao fallback |
| `apps/estoque/tests/test_partials.py` (novo) | Mesmos testes para os três partials de estoque |

## Desenho da implementação

### `alert.html` — o `{% else %}` deixa de ser o info

O componente tem hoje cinco cadeias condicionais sobre `variant` (fundo e borda
do `layout="row"`; classe do `layout="stack"`; cor do ícone; `path` do ícone) e
uma sobre o `role`. Em todas, `info` é o `{% else %}` — que é exatamente o que
faz variante desconhecida se disfarçar de informação legítima.

A correção não pode ser só "trocar o `{% else %}`": `variant` é **opcional com
default `info`**, então uma chamada sem `variant` chega ao template com string
vazia e cairia no grito. A normalização acontece uma vez, no topo, embrulhando
o corpo inteiro:

```django
{% with variant=variant|default:'info' %}
```

O filtro `default` dispara em valor falsy — ausente, `None` ou `''` —, que é
precisamente o conjunto "o chamador não escolheu variante". Isso depende de
`string_if_invalid` continuar sendo `''`: com um placeholder truthy, o Django
devolve o placeholder e **não aplica os filtros**, e a normalização morreria em
silêncio. Verificado — `config/settings/base.py` não sobrescreve a opção, e o
projeto já depende desse mesmo comportamento em `core_tags.py:26`. Depois disso cada
cadeia ganha um ramo `{% elif variant == 'info' %}` explícito e o `{% else %}`
fica livre para gritar, com termo único por ramo, sem condição composta
repetida cinco vezes.

O grito espelha o do `badge.html` e não descarta dado:

- **Cor:** `danger` preenchido (`bg-danger` + `text-text-on-primary` +
  `border-danger-hover`), não o `-subtle` de nenhuma variante legítima. Fundo
  cheio é o que distingue "não sei o que isto é" de "isto é um erro conhecido",
  do mesmo jeito que no badge.
- **Sinal visível:** uma linha `Aviso indisponível` antes do conteúdo. O
  `message`/`body_template` continua renderizado logo abaixo — o grito não come
  a mensagem, exatamente como o fallback do badge preserva o `label`.
- **Depuração:** `data-alert-variant="{{ variant }}"` na raiz, gêmeo do
  `data-badge-variant`.
- **ARIA:** variante desconhecida recebe `role="alert"` **nos dois layouts**, e
  esse `role` **não** é sobrescrevível pelo parâmetro `role`. Ver a seção
  seguinte para o porquê.

#### O nível semântico da falha, e o que ele obriga

`docs/CONVENTIONS.md` (§Níveis e ARIA) fixa `error` = "ação falhou" →
`role="alert"`, sem auto-dismiss. Variante que o componente não reconhece é
falha, então o fallback herda esse nível — e `danger` é apenas o **nome visual**
de `error` no vocabulário de variante dos componentes, exatamente como o
cabeçalho do `alert.html:2-5` já registra ("`danger` é o nome de variante aqui,
análogo a `button.html`"). O plano passa a dizer isso por extenso em vez de
deixar implícito.

Três consequências, todas ajustadas em relação à primeira versão deste plano:

1. **`role="alert"` nos dois layouts.** A versão anterior isentava o
   `layout="row"` com o argumento de que um painel de decisão persistente não
   deve virar live region. O argumento não se sustenta contra a Decisão A-1:
   `role="alert"` só é anunciado quando o nó **entra** ou **muda** no DOM, e
   conteúdo já presente no carregamento da página não dispara anúncio nenhum —
   é o mesmo fato que o `error_summary.html:10-11` documenta. O custo real do
   `role` no `row` é zero em render full-page, e o benefício é a falha não ter
   um layout onde ela é muda.
2. **O grito vence o `role` explícito.** No ramo do fallback, o parâmetro `role`
   é ignorado. Nas quatro variantes conhecidas ele continua tendo precedência —
   contrato preservado. Deixar o `role` do chamador rebaixar uma falha a `group`
   ou `note` seria o mesmo bug que o `_estado_badge.html` tem hoje, só que dentro
   do componente global.
3. **O grito vence o `bg_class`.** No `layout="row"`, `bg_class` sobrescreve o
   fundo derivado da variante. Com variante desconhecida, o grito vence.
   `bg_class` é escotilha de ajuste fino de opacidade para uma variante válida.

**Conflito registrado, não resolvido aqui:** a mesma seção do
`docs/CONVENTIONS.md` também exige botão de dismiss manual e proíbe auto-dismiss.
Isso **não** se aplica a este componente: a tabela §Níveis e ARIA governa o
contrato de *flash messages* do Django (`messages.error`/`messages.warning`),
renderizado por `core/partials/_messages.html`, e o cabeçalho do
`alert.html:7-9` já declara o componente fora desse contrato. Dismiss é a issue
#119 (`_messages.html`) e a paridade entre os dois é a #124. Nada de dismiss
entra aqui.

### O chamador que a Decisão A-1 quebra: `variant_token="primary"`

Varredura de todos os `{% include "components/alert.html" %}` do repositório:
10 chamadas com `variant="danger"`, 4 com `"warning"`, 1 com `"success"`, 1 com
`"info"` — e uma rota indireta, `_confirmacao_acao.html`, que repassa o
parâmetro `variant_token`. O cabeçalho desse partial (linhas 13-15) documenta
literalmente que `"primary"` **cai no ramo `{% else %}` do `alert.html`
(mesmas classes de "info")**. Hoje é verdade; com A-1, esse cartão vira um
grito vermelho.

O chamador real é um só: `detalhe.html:260`, o cartão "Autorização integral".

A correção é de vocabulário, não de exceção. `primary` é o nome de variante do
`button.html`; o vocabulário do `alert.html` é `info`. Depender do `{% else %}`
para traduzir um vocabulário no outro é exatamente o acidente que a Decisão A-1
elimina. Então `variant_token` passa a aceitar `info | warning | danger`, o
`detalhe.html:260` passa `variant_token="info"`, e as três condicionais de cor
dos dois partials de corpo trocam `variant_token == 'primary'` por
`variant_token == 'info'`. **Nenhuma classe muda**: a variante `info` do
`alert.html` já é desenhada com os tokens `primary-*`, e é por isso que
`text-primary-text-strong` continua sendo a cor do título nos três pontos.

Um teste fecha a rota: nenhum chamador de `alert.html` no repositório pode
passar variante fora das quatro conhecidas. Sem ele, o próximo `variant_token`
inventado só apareceria como grito vermelho numa tela de produção.

### Os três partials de estoque — mesma correção, mesmo motivo

Decisão do dono do produto, tomada depois da primeira rodada de revisão deste
plano: a Decisão A-1 diz "em todo lugar", então **em todo lugar** inclui os três
pontos de estoque que hoje mapeiam desconhecido para uma cor plausível. Deixá-los
de fora criaria uma regra inviolável nova no `docs/design-system.md` com três
violações vivas no dia em que ela nasce.

| Arquivo | Enum | Ramos explícitos hoje | `{% else %}` hoje | Alcançável hoje? |
|---|---|---|---|---|
| `_badge_tipo_movimentacao.html:21-22` | `TipoMovimentacaoEstoque` (7 valores) | 7 | `slate` | Não |
| `_estado_saida_badge.html:8-9` | `EstadoSaidaExcepcional` (2 valores) | 1 (`registrada`) | `teal` | **Sim** — é por onde passa `estornada` |
| `historico_importacoes_scpi.html:31-37` | `StatusImportacaoSCPI` (2 valores) | 2 | `slate` | Não |

Dois deles já cobrem o enum inteiro: o `{% else %}` é ramo morto que existe só
para o valor futuro, e é exatamente aí que ele está armado para mentir. O
terceiro é diferente e mais grave: o `_estado_saida_badge.html` usa o `{% else %}`
como **ramo de verdade** — `estornada` chega ali. Então esse arquivo ganha um
ramo `{% elif estado == 'estornada' %}` explícito com o `teal` de hoje, e só
depois o `{% else %}` fica livre para gritar. Sem esse passo, a correção pintaria
de vermelho todo estorno de saída excepcional em produção.

Nos três, o `{% else %}` passa a repassar o valor cru como `variant`, como no
`_estado_badge.html`. **Nenhuma cor muda em nenhum valor existente dos três
enums.**

#### O `aria_label` que tornaria o grito mudo

`_badge_tipo_movimentacao.html` e `_estado_saida_badge.html` passam
`aria_label="Estado: "|add:label` (e `"Tipo de movimentação: "|add:rotulo`), e o
fallback do `badge.html` propaga `aria_label` literalmente — comportamento
testado em `test_fallback_preserva_role_e_aria_label`.

Consequência se nada mais mudasse: um badge visivelmente escrito "Indisponível"
carregando `aria-label="Estado: Estornada"`. O nome acessível substitui o
conteúdo, então quem usa leitor de tela ouviria o rótulo normal e **nunca**
saberia que o componente falhou. Falha alta para quem enxerga, falha silenciosa
para quem não enxerga — que é A-1 pela metade, e pior: discriminatória.

Correção: no ramo do grito desses dois partials, **não** passar `aria_label`;
passar `prefixo_sr` no lugar. O `badge.html` então compõe o nome acessível do
jeito que o cabeçalho dele já promete — `sr-only` do prefixo + "Indisponível"
visível + `sr-only` do rótulo real entre parênteses — e o leitor de tela ouve
"Estado: Indisponível (Estornada)". Os ramos conhecidos seguem com o
`aria_label` de hoje, intocados.

O `role="status"` que esses dois partials passam **fica como está**, inclusive no
ramo do grito. Ele contraria a orientação do cabeçalho do `badge.html` sobre
badge de dado estático, mas isso é anterior a esta issue e mexer nele aqui seria
trocar um achado por outro sem decisão que o cubra.

### `_estado_badge.html` — parar de anular o fallback

```django
{% else %}
  {% include "components/badge.html" with variant=estado label=label prefixo_sr="Estado: " %}
{% endif %}
```

O partial repassa o estado cru como `variant`. Como nenhum valor de
`EstadoRequisicao` fora dos oito mapeados existe no componente global, o
`badge.html` cai no próprio fallback e rende "Estado: Indisponível (rótulo
real)" com `data-badge-variant="<estado>"`. O `label` continua indo junto —
o fallback do badge o preserva em `sr-only`, então nada de dado se perde.

Os oito estados de `EstadoRequisicao` estão todos mapeados hoje, então este
ramo é inalcançável em produção **agora**. Esse é o ponto: ele existe para o
nono estado, e hoje ele está armado para mentir.

### O guard de cor crua

Três buracos, três correções:

1. **Regex cego.** `(?:blue|red|amber|green|teal)` deixa de fora exatamente as
   famílias presentes no repositório. Passa a cobrir a paleta padrão do
   Tailwind por extenso. Cobrir só as nove famílias em uso hoje deixaria um
   `bg-lime-100` colado amanhã passar batido — e o critério de aceite pede que
   variante de catálogo **nova** quebre o teste, o que só vale se o regex não
   depender de a família já existir no repositório.
2. **Escopo curto.** A varredura olha `components/*.html` + `_messages.html`.
   O critério de aceite fala em "qualquer outro template", então o alvo passa a
   ser `apps/**/*.html`. Varredura de confirmação já feita: no repositório
   inteiro existem 13 ocorrências de paleta crua — as 12 do `badge.html` e o
   `backdrop:bg-slate-900/50` do `modal.html`. Nenhum outro template tem cor
   crua hoje, então a expansão não vem acompanhada de correção nenhuma.
3. **Exceção invisível — e frouxa demais se for por família.** Uma allowlist
   `caminho -> famílias permitidas` não fecha o buraco: ela liberaria qualquer
   `slate-*` no `modal.html`, quando a exceção declarada é só o backdrop
   `bg-slate-900/50`; e uma variante de catálogo nova no `badge.html` que
   reaproveitasse `orange` passaria em silêncio, que é exatamente o caso que o
   critério de aceite manda quebrar.

   A allowlist é, então, por **classe exata com contagem**:
   `caminho relativo -> {classe crua: nº de ocorrências}`. Cada entrada leva a
   justificativa escrita em comentário logo acima, no mesmo formato da exceção
   de prosa inline do piso de 44px em `test_components.py`. Duas entradas:

   - `components/badge.html` — 12 classes, as quatro variantes de catálogo
     nomeadas uma a uma (`bg-orange-100`/`text-orange-900`/`ring-orange-200` e
     os trios equivalentes de `indigo`, `violet` e `yellow`), uma ocorrência
     cada.
   - `components/modal.html` — `bg-slate-900`, uma ocorrência: o backdrop.

A comparação é de **igualdade entre os dois dicionários**, não de continência:

| Mudança | Resultado |
|---|---|
| `bg-violet-100` colado em qualquer outro template | Quebra — arquivo não isento |
| `bg-lime-100` colado no `badge.html` | Quebra — classe fora da allowlist |
| Variante de catálogo nova no `badge.html` reusando `bg-orange-100` | Quebra — a contagem de `bg-orange-100` sobe de 1 para 2 |
| Variante nova com shade novo da mesma família (`bg-orange-50`) | Quebra — classe fora da allowlist |
| `bg-slate-800` no `modal.html` | Quebra — só `bg-slate-900` é isento |
| Uma das 12 classes some do `badge.html` | Quebra — exceção que sobrevive ao motivo é como a regra vira sugestão de novo |

A contagem é o que impede o caso mais fácil de deixar passar: reaproveitar uma
classe já isenta em um ramo novo não introduz classe nova nenhuma, e uma
allowlist de conjunto não teria como notar.

O `test_components_badge.py` já tem um guard restrito ao `badge.html`
(`test_badge_nao_tem_cor_crua_fora_das_quatro_variantes_de_catalogo`), por
**família** e por conjunto. Ele **fica** e é **apertado junto**, para não haver
dois guards com rigores diferentes sobre o mesmo arquivo: passa a comparar as
mesmas 12 classes com contagem. É o teste de unidade do componente e falha com
mensagem local; o de `test_tokens_semanticos.py` é o guard de repositório e
responde a outra pergunta ("alguém colou cor crua em algum lugar?"). A
duplicação é de asserção, não de mecanismo.

## Estratégia de testes

Cada comportamento abaixo vira um ciclo RED → GREEN.

### `alert.html`

| Caso | O que prova |
|---|---|
| Variante desconhecida no `stack` renderiza `bg-danger` + `text-text-on-primary` | O grito existe e é preenchido, não `-subtle` |
| Variante desconhecida emite o sinal visível `Aviso indisponível` | Falha visível, não só semântica |
| Variante desconhecida **preserva** `message` no HTML | Gritar não é descartar dado |
| Variante desconhecida preserva `body_template` | Mesmo contrato para o corpo rico |
| Variante desconhecida emite `data-alert-variant` com o valor cru | Depuração |
| Variante desconhecida recebe `role="alert"` no `stack` | Nível semântico `error` da falha |
| Variante desconhecida recebe `role="alert"` no `row` | A falha não tem layout onde é muda |
| Variante desconhecida **ignora** `role` explícito, nos dois layouts | O chamador não rebaixa uma falha a `group`/`note` |
| `role` explícito continua vencendo nas quatro variantes conhecidas | Contrato do parâmetro preservado onde ele vale |
| Ausência de `variant` continua `info`/`role="status"` | A normalização não engoliu o default |
| `variant=""` explícito continua `info` | Idem, pelo caminho da string vazia |
| Cada uma das quatro variantes conhecidas mantém classes e `role` de hoje | Nenhuma regressão visual |
| `layout="row"` com variante conhecida continua **sem** `role` automático | O `row` só ganha `role` na falha |
| `layout="row"` com `bg_class` + variante desconhecida: o grito vence | A escotilha não silencia o fallback |
| `layout="row"` com `bg_class` + variante conhecida: `bg_class` vence | A escotilha continua existindo |
| Nenhum chamador de `alert.html` no repositório passa variante fora das quatro | O grito não nasce disparando em tela de produção |

### `_estado_badge.html`

| Caso | O que prova |
|---|---|
| Estado inexistente renderiza `Indisponível` visível | O partial parou de anular o fallback |
| Estado inexistente emite `data-badge-variant` com o estado cru | O valor não some |
| O rótulo real continua no HTML (em `sr-only`) | Nada de dado descartado |
| Os oito estados canônicos mantêm a variante de hoje | Nenhuma regressão de listagem |

O teste usa um dublê leve com `.estado` e `.get_estado_display` em vez de tocar
o banco: o partial só lê esses dois atributos, e `EstadoRequisicao` não aceita
um nono valor para ser gravado de verdade.

### Os três partials de estoque

O mesmo quarteto de casos vale para cada um, com o dublê leve equivalente
(`.tipo`/`rotulo`, `.estado`/`.get_estado_display`, `.status`/`.get_status_display`):

| Caso | O que prova |
|---|---|
| Valor inexistente renderiza `Indisponível` visível | O partial parou de anular o fallback |
| Valor inexistente emite `data-badge-variant` com o valor cru | O valor não some |
| O rótulo real continua no HTML (em `sr-only`) | Nada de dado descartado |
| Todos os valores canônicos de cada enum mantêm a variante de hoje | Nenhuma regressão de listagem |

Mais três casos que só existem por causa do escopo ampliado:

| Caso | O que prova |
|---|---|
| `estornada` em `_estado_saida_badge.html` continua `teal` | O ramo explícito novo cobriu o que o `{% else %}` cobria — sem ele, todo estorno viraria vermelho |
| No grito, `_badge_tipo_movimentacao.html` e `_estado_saida_badge.html` **não** emitem `aria-label` | O nome acessível não substitui o sinal de falha |
| No grito, o nome acessível resultante contém `Indisponível` **e** o rótulo real | A falha chega igual a quem usa leitor de tela |

O penúltimo é o que impede A-1 de valer só para quem enxerga.

### Guard de cor crua

| Caso | O que prova |
|---|---|
| Varredura real de `apps/**/*.html` fica limpa | O estado atual respeita a regra |
| `badge.html` bate exatamente com as 12 classes da allowlist, uma ocorrência cada | Exceção verificada, não só declarada |
| `modal.html` bate exatamente com `bg-slate-900`, uma ocorrência | Idem para a segunda exceção |
| Entrada sintética com `bg-violet-100` num arquivo não isento é reprovada | O guard morde |
| Entrada sintética com `bg-lime-100` **dentro** do `badge.html` é reprovada | Variante de catálogo nova, família nova |
| Entrada sintética com `bg-orange-100` duas vezes no `badge.html` é reprovada | Variante nova **reusando** classe isenta |
| Entrada sintética com `bg-orange-50` no `badge.html` é reprovada | Shade novo de família isenta |
| Entrada sintética com `bg-slate-800` no `modal.html` é reprovada | A isenção é da classe, não da família |
| Entrada sintética a que falta uma das 12 classes do `badge.html` é reprovada | Exceção não sobrevive ao motivo |

Tudo abaixo da terceira linha exercita o mecanismo por entrada sintética passada
à função de checagem — nunca por sujeira real deixada num template de verdade,
que é o jeito de o próprio teste virar o vazamento que ele deveria pegar.

## Invariantes preservadas

- **Componente global não conhece enum de domínio.** O `_estado_badge.html`
  continua sendo quem traduz estado → variante; o `badge.html` continua sem
  saber o que é uma requisição. Repassar o estado cru como `variant` não ensina
  domínio ao componente: para ele é só uma string que não casa com nenhum ramo.
- **Badge de dado estático não é live region.** Nada nesta mudança adiciona
  `role="status"`/`alert` ao `badge.html` — `test_estado_badge_nao_e_live_region`
  (`apps/requisicoes/tests/test_views.py:3842`) continua valendo.
- **`_messages.html` mantém `role="alert"` == 1 e `role="status"` == 1**
  (`apps/requisicoes/tests/test_views.py:2713`). Nenhum arquivo dessa cadeia é
  tocado.
- **Zero mudança de camada.** Só template, doc e teste. Nenhum service, policy,
  selector, model ou migration.

## Riscos

| Risco | Mitigação |
|---|---|
| `{% with variant=variant\|default:'info' %}` embrulhando o corpo inteiro muda o escopo de todas as variáveis do template | O `with` só rebinda `variant`; todo o resto do contexto segue herdado. Coberto pelos testes de regressão das quatro variantes conhecidas e pelos testes de `body_template`, `class`, `id` e `aria_live` que já existem |
| Expandir a varredura para `apps/**/*.html` derruba a suíte por template não auditado | Varredura de confirmação já rodada: só `badge.html` e `modal.html` têm cor crua no repositório inteiro. A expansão nasce verde |
| Regex mais largo passa a casar utility semântica com dígito (ex. `bg-primary-500`) | O projeto não tem token semântico com sufixo numérico, e o regex ancora na lista fechada de famílias do Tailwind, não em `[a-z]+`. O teste de varredura real na base atual é a prova |
| `bg-danger` / `border-danger-hover` podem não estar compilados no `app.css` | O Tailwind v4 compila por scan de conteúdo; escrever a classe no template é o que a gera. `test_css_build_gera_tokens_e_utilities_novas` recebe as duas na lista de utilities esperadas |
| `_estado_saida_badge.html` usa o `{% else %}` como ramo real (`estornada` passa por ele) — trocá-lo por grito pintaria todo estorno de vermelho | O ramo explícito `{% elif estado == 'estornada' %}` com o `teal` de hoje entra **antes**, e um teste dedicado cobra o `teal` desse estado. É o único dos quatro partials onde o `{% else %}` não é ramo morto |
| O grito no estoque pode ficar mudo para leitor de tela, porque os dois partials passam `aria_label` e o fallback do `badge.html` o propaga literalmente | No ramo do grito, `aria_label` sai e `prefixo_sr` entra; teste cobra a ausência de `aria-label` e a presença de `Indisponível` + rótulo real no nome acessível |
| Tornar `alert.html` mais barulhento pode mudar telas em produção | O grito só dispara para variante **fora** das quatro conhecidas. Varredura dos chamadores já feita: um único ponto dependia do `{% else %}` (`variant_token="primary"`), e ele vira correção de vocabulário, não exceção. Um teste passa a cobrar isso de todo chamador futuro |

## Fora de escopo

Nada de dismiss, paridade `alert` × `_messages`, destrinchamento do `alert.html`
ou a contradição do estorno no `DESIGN.md`. São as issues #119, #124, #127 e
#128.
