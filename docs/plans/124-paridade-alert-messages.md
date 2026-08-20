# Plano — Issue #124: paridade documentada e verificada entre `alert.html` e `_messages.html`

Os dois arquivos renderizam os mesmos quatro níveis de severidade e não
compartilham nada. A decisão do dono do produto (2026-08-18) é **manter os dois
separados** — os contratos ARIA são incompatíveis: um é banner estático de
página/formulário, o outro é fila de flash messages com dismiss, timer
assimétrico e ordenação por assertividade. Essa decisão está certa e não é
reaberta aqui.

O que ela não autoriza é o drift. "Bem documentado" era a condição da separação
e ainda não existe, e quatro dimensões já divergiram.

## Estado medido hoje (não é o que a issue descreve)

A issue #124 foi escrita antes da #119. A #119 extraiu a marcação da faixa para
`core/partials/_message_item.html`; `_messages.html` hoje só resolve a variante
e passa as classes por parâmetro. Então:

- as classes de raio/padding citadas como `_messages.html:11` vivem agora em
  `_message_item.html:23`;
- o token de texto por nível vive em `_messages.html:37-43`, no parâmetro `caixa`;
- os ícones da faixa já usam `currentColor` (`_message_item.html:25`) — o lado
  que precisa mudar é só o `alert.html`.

Drift real, conferido nos arquivos vivos:

| Dimensão | `alert.html` stack (`:74`, `:77`) | faixa de flash (`_message_item.html:23`, `_messages.html:37-43`) |
|---|---|---|
| Raio | `rounded-lg` (0.5rem, campo) | `rounded-md` (0.375rem, **controle**) |
| Padding | `px-4 py-3` | `px-3 py-2` |
| Texto `warning` | `text-warning-text` (amber-800) | `text-warning-text-strong` (amber-900) |
| Texto `success`/`danger`/`info` | `-emphasis` (800) | `-emphasis` (800) — já iguais |
| Fundo e borda | `-subtle` / `-border` | `-subtle` / `-border` — já iguais |
| Cor do ícone | token fixo da variante (`text-warning`, …) | `currentColor` |
| `role` | warning/danger `alert`, success/info `status` | warning/error `alert`, success/info `status` — já iguais |

Os dois tokens de texto passam AA sobre `warning-subtle` (6.88:1 e 8.77:1), então
a divergência de texto é de consistência, não de contraste. O ícone não: amber-500
sobre amber-50 dá **2.07:1** e falha WCAG 1.4.11 (3:1 para componente não-textual).
O ícone é o único sinal não-cromático de nível num fundo com L≈98% — quem não
distingue matiz não tem outra pista.

## Escopo

### O que muda

1. **`components/alert.html`** — os ícones do `layout="stack"` deixam de receber
   classe de cor e passam a herdar o token de texto da caixa via `currentColor`.
   Os cinco ramos condicionais de cor de ícone somem. O `{% comment %}` de
   cabeçalho ganha a justificativa do raio `stack` × `row`.
2. **`core/partials/_message_item.html`** — a caixa adota o vocabulário de
   superfície do `alert.html` stack: `rounded-lg` e `px-4 py-3`.
3. **`core/partials/_messages.html`** — `warning` passa de
   `text-warning-text-strong` para `text-warning-text`, alinhando os quatro
   níveis no mesmo degrau (800).
4. **`docs/design-system.md`** — seção nova de paridade: tabela dos 4 níveis × 7
   propriedades, razão da separação e o que **não** é compartilhado de propósito.
5. **`apps/core/tests/test_paridade_feedback.py`** (novo) — o mecanismo: lê a
   tabela do design system e verifica cada célula contra o HTML renderizado dos
   dois caminhos.
6. **`apps/core/static/core/css/app.css`** — rebuild, porque as classes de ícone
   removidas deixam de ser geradas e `rounded-lg`/`px-4 py-3` passam a existir no
   caminho da faixa.

### O que NÃO muda

- A separação dos dois arquivos. Nenhum `_feedback_box.html` compartilhado.
- O contrato de dismiss da #119: botão, `auto: true/false` por nível, pausa em
  hover/foco, botão fora do nó que carrega o `role`, âncora de foco.
- A ordenação por assertividade (`mensagens_visiveis`) e o descarte de `debug`.
- `role`, `aria-live`, `body_template`, `action_template`, `bg_class`, `id`,
  `class` e o ramo de fallback de variante desconhecida do `alert.html`.
- `layout="row"` do `alert.html`, incluindo seu `rounded-xl` — ver D-3.
- Qualquer service, selector, policy, model, form, view ou migration. Esta issue
  não toca camada de domínio.
- Os ícones de `_message_item.html`, que já estão certos.

## Decisões

### D-1 — A faixa adota a superfície do banner, não o contrário

`rounded-md` é 0.375rem, o **raio de controle** da escala de
`docs/design-system.md` (§Espaçamento e forma: controle 0.375 / campo 0.5 /
papel 0.75 / modal 1rem). Uma flash message não é um controle: não é acionável,
não recebe foco como unidade, não tem estado pressionado. Ela é uma superfície
que carrega texto — mesma camada do banner de formulário. Logo `rounded-lg`, e
`px-4 py-3` junto, porque padding menor num raio maior desequilibra a caixa.

O sentido do alinhamento é o do banner porque o `alert.html` é o componente
global indexado em `docs/design-system.md`; a faixa é um partial de domínio de
`core/`. Quem define vocabulário de superfície é o componente.

### D-2 — Token de texto: `warning` cai para o degrau 800

`_messages.html` usa `-emphasis` (800) em success, error e info, e
`text-warning-text-strong` (amber-900) só em warning. A escala de âmbar não tem
`-emphasis`: seus degraus são `text-subtle` (700), `text` (800), `text-strong`
(900). Ou seja, o equivalente de `-emphasis` em âmbar é `text-warning-text`, que
é exatamente o que o `alert.html` já usa. Alinhar põe os quatro níveis no mesmo
degrau em vez de deixar um deles um passo acima sem motivo.

Efeito colateral verificado: `text-warning-text-strong` continua tendo
consumidor (`core_tags.py:162` e `badge.html`), então segue compilado e a
asserção de `UTILITIES_ESPERADAS` em `test_tokens_semanticos.py:158` não quebra.

### D-3 — `stack` × `row` é resolvido como justificado, não como igualado

`layout="row"` usa `rounded-xl` (0.75rem, papel) e o `stack` usa `rounded-lg`
(0.5rem, campo). Não é drift: o `row` tem `shadow-sm` e `p-4 sm:p-6`, e o
design system diz "sombra: `shadow-sm` só em papel". Uma superfície com sombra e
padding de seção é papel e leva raio de papel; um banner sem sombra, embutido no
fluxo do formulário, é campo. A divergência fica, com a razão escrita no
`{% comment %}` do arquivo — que é onde a próxima pessoa vai procurar.

### D-4 — A tabela do design system é a fonte, e o teste a lê

O critério de aceite pede um teste que falhe "quando os dois templates divergem
em qualquer célula da tabela". Literal: o teste **parseia** a tabela de paridade
de `docs/design-system.md` e confere cada célula contra o HTML renderizado dos
dois caminhos. Assim a tabela não pode virar ficção — mentir nela quebra o teste
tanto quanto mentir no template.

O parser falha alto se a tabela não for encontrada, tiver número de colunas
diferente do esperado ou não cobrir os quatro níveis. Tabela sumida tem que
quebrar o teste, não fazê-lo passar vacuamente — é o mesmo buraco de
`test_nenhum_controle_abaixo_do_piso_de_44px`, corrigido na #120.

### D-5 — `danger` e `error` são o mesmo nível com dois nomes

`alert.html` chama a variante de `danger` (análogo a `button.html`);
`_messages.html` recebe `error` do Django. A tabela usa uma coluna de nível
canônico e declara os dois nomes, e o teste faz o de-para. Renomear qualquer um
dos dois está fora do escopo.

## Arquivos tocados

| Arquivo | Mudança |
|---|---|
| `apps/core/templates/components/alert.html` | ícone `currentColor`, 5 ramos de cor removidos, comentário do raio |
| `apps/core/templates/core/partials/_message_item.html` | `rounded-lg px-4 py-3` |
| `apps/core/templates/core/partials/_messages.html` | `text-warning-text` no nível `warning` |
| `docs/design-system.md` | seção "Paridade entre banner e faixa de flash" |
| `apps/core/tests/test_paridade_feedback.py` | **novo** — teste dirigido pela tabela |
| `apps/core/static/core/css/app.css` | rebuild via `make css-build` |

Nenhum teste existente assere cor crua de ícone (`text-warning`, `text-success`,
`text-danger`, `text-primary` não aparecem em nenhum `.py` de `apps/`), então
`test_components_alert.py` não precisa de ajuste — só ganha, no arquivo novo, o
guarda da ausência.

## Estratégia de testes

Arquivo novo `apps/core/tests/test_paridade_feedback.py`, sem DB, renderizando
pelo engine do Django (`render_to_string`) — não por parser de HTML estático,
porque 100% do estado visual dos dois arquivos vive dentro de `{% if %}`.

Helpers já existentes: `apps/core/tests/marcacao.py` (`elementos`, `atributo`,
`classes`). A faixa é renderizada como em `TestMessagesDismiss._render`
(`RequestFactory` + `FallbackStorage`); o banner como em
`test_components_alert.py._render`.

| Caso | O que verifica |
|---|---|
| Paridade célula a célula (parametrizado por nível × propriedade) | raio, padding, fundo, borda e token de texto iguais nos dois caminhos e iguais ao que a tabela declara |
| Nenhum dos dois usa raio de controle | `rounded-md` ausente na caixa do banner e na da faixa |
| Ícone do banner herda `currentColor` | o `<svg>` do stack não tem classe `text-*` de cor |
| Ícone da faixa continua sem classe de cor | o lado que já estava certo não regride |
| `role` por nível | warning/danger→`alert`, success/info→`status`, nos dois caminhos |
| Tabela do design system existe e é bem formada | 4 níveis × 7 propriedades; parser falha alto se a seção sumir |
| Razão da separação está escrita | a seção nomeia os contratos ARIA incompatíveis e o que não é compartilhado |
| `layout="row"` não é arrastado para a paridade | `rounded-xl` do `row` continua, e a razão está no `{% comment %}` |

**Medição do contraste do ícone.** O critério de aceite pede o número, não a
inferência. O repositório não tem ferramenta de contraste, e escrever uma
conversão OKLCH→sRGB dentro da suíte seria carregar matemática de cor num
projeto que não a usa em mais nenhum lugar. Então a divisão é: o **mecanismo
durável** é o teste estrutural (o `<svg>` do stack não pode ter classe de cor —
se alguém recolar uma, quebra), e o **número** vem de uma medição pontual sobre
o `app.css` compilado, com o par por variante e o antes/depois, registrada no
corpo do PR. O script fica no scratchpad; não entra no repositório, porque
ferramenta sem segundo uso vira manutenção órfã.

**Ordem TDD (RED antes de qualquer correção):** o arquivo de teste é escrito e
rodado contra o estado atual **antes** de tocar template, e precisa falhar nas
células de raio, padding, texto de `warning` e cor de ícone. Isso é critério de
aceite explícito da issue, não zelo — a evidência do RED entra no corpo do PR.

Regressões que não podem quebrar:

- `apps/requisicoes/tests/test_views.py:2713` — conta `role="alert"` == 1 e
  `role="status"` == 1 em `_messages.html`.
- `apps/core/tests/test_components.py::TestMessagesDismiss` — contrato da #119.
- `apps/core/tests/test_tokens_semanticos.py` — allowlist de cor crua (nenhuma
  cor crua é introduzida) e `UTILITIES_ESPERADAS` (nenhuma utility esperada
  perde seu último consumidor).

## Invariantes

- **Regra do Raio Crescente** (`docs/design-system.md`, §Espaçamento e forma):
  controle 0.375 / campo 0.5 / papel 0.75 / modal 1rem. É a regra que a issue
  está fazendo valer.
- **WCAG 1.4.11** (3:1 para componente gráfico não-textual): o ícone do banner
  passa a herdar o token de texto da própria caixa. Os quatro pares
  texto/fundo já passam AA (≥ 4.5:1) — é o que a auditoria mediu —, então o
  ícone sai de 2.07:1 no `warning` para o mesmo valor do texto (6.88:1).
- **Contrato de níveis e ARIA** (`docs/CONVENTIONS.md`, §Níveis e ARIA):
  error/warning assertivos, success/info polidos. Preservado nos dois caminhos.
- **Live region não é o mecanismo depois de POST full-page** (checklist de
  acessibilidade do design system): esta issue não introduz `aria-live` novo.
- **Token, nunca shade**: nenhuma cor crua entra; o guard de
  `test_tokens_semanticos.py` continua exato.
- **Regra sem mecanismo vira sugestão** (`docs/design-system.md`): por isso a
  entrega fecha com teste dirigido pela própria tabela, não com seção de doc.

## Riscos

| Risco | Mitigação |
|---|---|
| Parser de markdown frágil quebra por formatação | O parser exige cabeçalho e contagem de colunas e falha alto; a tabela vive num só lugar e o teste roda em todo commit |
| Rebuild do CSS esquecido — classe nova em template sem utility no `app.css` | `make css-build` é passo obrigatório antes do commit; `test_tokens_semanticos.py` roda o build e confere as utilities |
| Utility perde o último consumidor e some do `app.css` | Conferido: `text-warning-text-strong` segue em `core_tags.py:162` e `badge.html`; os `text-warning`/`text-success`/`text-danger`/`text-primary` removidos não estão em `UTILITIES_ESPERADAS` |
| Padding maior na faixa muda o layout de telas que a empilham | `space-y-2` do wrapper não muda; a faixa cresce ~8px em altura, dentro do fluxo normal |
| Conflito com a #127, que vai destrinchar o `alert.html` | Esta issue não muda a API do componente nem move responsabilidade — só remove ramos condicionais, o que reduz o trabalho da #127 |
| A #124 mexer no mesmo arquivo da #119 | A #119 está fechada (PR #9 merged); não há trabalho em paralelo |

## Fluxo de trabalho

A issue recomenda um comando, e ele entra no passe de implementação — depois do
RED do teste de paridade e antes do commit final:

```
/impeccable polish apps/core/templates/components/alert.html apps/core/templates/core/partials/_messages.html docs/design-system.md
```

`polish` é o passe de qualidade final: consistência entre superfícies que
deveriam falar a mesma língua. Aqui ele carrega as três metades juntas —
alinhar os valores divergentes, escrever a seção de paridade e manter o teste
que a torna verdadeira. `_message_item.html` entra no alvo junto com
`_messages.html`, porque foi para lá que a #119 moveu a marcação.

Verificação final, conforme `AGENTS.md`:

```
uv run ruff format --check .
uv run ruff check .
uv run mypy apps
uv run pytest -q -ra --tb=short --strict-markers --disable-warnings -n logical
```
