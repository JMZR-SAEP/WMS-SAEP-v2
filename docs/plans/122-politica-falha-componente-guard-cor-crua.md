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
3. **`apps/requisicoes/templates/requisicoes/partials/_estado_badge.html`**
   deixa de mapear estado desconhecido para `variant="slate"`. Repassa o estado
   cru como `variant`, deixando o fallback do `badge.html` fazer o trabalho que
   ele já sabe fazer.
4. **`apps/core/tests/test_tokens_semanticos.py`** passa a enxergar as famílias
   que hoje ficam fora do regex, varre todos os templates do repositório em vez
   de só `components/` + `_messages.html`, e materializa a exceção declarada do
   design system numa allowlist por `(arquivo, família)` com justificativa
   escrita. A Decisão B fica registrada no próprio arquivo de teste. A docstring
   do módulo, que hoje descreve o alvo como
   "cor de paleta crua (blue/red/amber/green/teal)... dentro de
   `apps/core/templates/components/`", é reescrita junto — senão o arquivo passa
   a mentir sobre o próprio guard no primeiro parágrafo.
5. **Testes novos** cobrindo o comportamento de fallback escolhido nos três
   arquivos de template.

### O que NÃO muda

- **A lista de variantes de nenhum componente.** `badge.html` continua com 13
  variantes conhecidas + fallback; `alert.html` continua com `info`, `success`,
  `warning`, `danger`.
- **O visual de qualquer variante conhecida.** Nenhuma classe muda em nenhum
  ramo reconhecido, nem no `badge.html`, nem no `alert.html`, nem no
  `_estado_badge.html`.
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
| `apps/core/tests/test_tokens_semanticos.py` | Regex, escopo de varredura, allowlist, registro da Decisão B |
| `apps/core/tests/test_components_alert.py` | Testes do grito de `alert.html` |
| `apps/requisicoes/tests/test_partials.py` (novo) | Teste do estado não mapeado chegando ao fallback |

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
- **ARIA:** no `layout="stack"`, variante desconhecida recebe `role="alert"`
  (junto de `warning` e `danger`); `info` e `success` seguem com `role="status"`.
  No `layout="row"` **não** nasce `role` automático — esse layout é painel de
  decisão persistente, e transformá-lo em live region por causa de um erro de
  variante criaria um anúncio a cada render. O grito ali é visual + atributo de
  depuração.

Um ponto exige decisão explícita: no `layout="row"`, `bg_class` sobrescreve o
fundo derivado da variante. Com variante desconhecida, **o grito vence o
`bg_class`**. `bg_class` é escotilha de ajuste fino de opacidade para uma
variante válida; deixá-lo silenciar o fallback recriaria, dentro do próprio
componente global, o mesmo bug que o `_estado_badge.html` tem hoje.

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
3. **Exceção invisível.** A allowlist é um `dict` de
   `caminho relativo -> frozenset de famílias`, com a justificativa de cada
   entrada escrita em comentário logo acima — o mesmo formato da exceção de
   prosa inline do piso de 44px em `test_components.py`. Duas entradas:
   `badge.html` com `{orange, indigo, violet, yellow}` e `modal.html` com
   `{slate}`.

A allowlist é **exata nos dois sentidos**, como o
`test_badge_nao_tem_cor_crua_fora_das_quatro_variantes_de_catalogo` já faz para
o badge: família nova no arquivo isento quebra o teste, e família que sumiu do
arquivo também quebra — exceção que sobrevive ao seu motivo é como a regra vira
sugestão de novo.

O `test_components_badge.py` já tem um guard equivalente restrito ao
`badge.html`. Ele **fica**: é o teste de unidade do componente e falha com
mensagem local. O de `test_tokens_semanticos.py` é o guard de repositório e
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
| Variante desconhecida recebe `role="alert"` no `stack` | Postura ARIA da falha |
| Ausência de `variant` continua `info`/`role="status"` | A normalização não engoliu o default |
| `variant=""` explícito continua `info` | Idem, pelo caminho da string vazia |
| Cada uma das quatro variantes conhecidas mantém classes e `role` de hoje | Nenhuma regressão visual |
| `role` explícito continua sobrescrevendo, inclusive com variante desconhecida | Contrato do parâmetro preservado |
| `layout="row"` com variante desconhecida grita e **não** cria `role` automático | Painel de decisão não vira live region |
| `layout="row"` com `bg_class` + variante desconhecida: o grito vence | A escotilha não silencia o fallback |

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

### Guard de cor crua

| Caso | O que prova |
|---|---|
| Varredura real de `apps/**/*.html` fica limpa | O estado atual respeita a regra |
| `badge.html` bate exatamente com as quatro famílias da allowlist | Exceção verificada, não declarada |
| `modal.html` bate exatamente com `{slate}` | Idem para a segunda exceção |
| Fixture sintética com `bg-violet-100` fora da allowlist é reprovada | O guard morde |
| Fixture sintética com família nova **dentro** do `badge.html` é reprovada | Variante de catálogo nova sem entrar na allowlist quebra |
| Família da allowlist que sumiu do arquivo é reprovada | Exceção não sobrevive ao motivo |

As três últimas exercitam o mecanismo por entrada sintética passada à função de
checagem — nunca por sujeira real deixada num template de verdade.

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
| Tornar `alert.html` mais barulhento pode mudar telas em produção | O grito só dispara para variante **fora** das quatro conhecidas. Varredura dos chamadores de `alert.html` faz parte do primeiro ciclo: qualquer chamador com typo de variante vira correção, não exceção |

## Fora de escopo — achados vizinhos que esta issue não fecha

Três partials de domínio têm o mesmo `{% else %}` silencioso que o
`_estado_badge.html` tem hoje:

- `apps/estoque/templates/estoque/partials/_badge_tipo_movimentacao.html:22` → `slate`
- `apps/estoque/templates/estoque/partials/_estado_saida_badge.html:8-9` → `teal`
- `apps/estoque/templates/estoque/historico_importacoes_scpi.html:36` → `slate`

Eles **não** entram aqui: a Decisão A-1, como está escrita na issue, nomeia
`alert.html` e `_estado_badge.html:25` como o conteúdo da opção, e os critérios
de aceite falam em "os três arquivos". Ficam registrados aqui para virar issue
própria — a política agora existe no `docs/design-system.md`, então a migração
deles passa a ter uma regra para citar.
