# Auditoria do design system — `input.css` + `docs/design-system.md`

Data: 2026-08-14. Escopo: tokens (`apps/core/static/core/css/input.css`),
documentação (`docs/design-system.md`), catálogo de componentes
(`apps/core/templates/components/`), estilo de campo em `apps/*/forms.py`.

Auditoria técnica — não corrige, documenta. Toda evidência foi verificada no
código e no `app.css` compilado.

## Nota de saúde

| # | Dimensão | Nota | Achado principal |
|---|---|---|---|
| 1 | Acessibilidade | 3/4 | Controles secundários com `border-border` (slate-200, ~1,5:1) contrariam a própria regra do sistema de usar `border-strong` para garantir 3:1 |
| 2 | Performance | 4/4 | Server-rendered, sem webfont, CSS minificado de 54 KB, animação só em `transform`/`opacity` |
| 3 | Tokenização | 3/4 | 6 tokens mortos; `--width-content` declarado mas ignorado pelos templates; `duration-150` cru em 11 lugares |
| 4 | Responsividade | 3/4 | 7 larguras máximas diferentes num sistema que documenta "container único de 80rem" |
| 5 | Integridade de implementação | 2/4 | Duplicação estrutural em 5 frentes; inventário do `design-system.md` descreve uma API que não existe mais |
| **Total** | | **15/20** | **Bom — atacar as dimensões fracas** |

## Veredito de integridade

**Passa.** O sistema é coerente e específico do produto. A disciplina de token é
excepcional: numa varredura de 79 templates, cor crua de paleta aparece em
**exatamente dois lugares** — as 4 variantes de catálogo de `badge.html`
(`orange`/`indigo`/`violet`/`yellow`) e o `bg-slate-900/50` do backdrop de
`modal.html`, ambos já declarados como exceção consciente no DESIGN.md.
Comentário de cabeçalho em componente explica *por que*, não *o que* — padrão
raro e que deve ser preservado.

A perda de nota vem de **duplicação estrutural**, não de drift visual: o mesmo
padrão está implementado 2 a 17 vezes em lugares que podem divergir sem que nada
quebre. Já divergiram.

## Achados por severidade

### P1 — Corrigir antes da próxima tela

#### [P1] Campo de filtro usa raio de controle e sombra de papel

**Local:** `components/filter_busca.html`, `filter_select.html`, `filter_data.html`
**Categoria:** Tokenização / Integridade

Os três campos usam `rounded-md shadow-sm`. O restante do sistema — 17
declarações de widget em `apps/*/forms.py` e o `design-system.md` §"Altura de
controle" — usa `rounded-lg` sem sombra.

Isso viola duas regras nomeadas do DESIGN.md de uma vez: **A Regra do Raio
Crescente** (campo = 0.5rem, controle = 0.375rem) e **A Regra dos Quatro
Degraus** (1dp é papel/card, não campo). O efeito prático: na barra de filtros o
campo lê como botão, e a hierarquia por geometria — que é a forma de o sistema
comunicar "isto é papel, isto é campo, isto é controle" — deixa de valer
exatamente na tela mais densa do produto.

**Correção:** trocar por `rounded-lg` e remover `shadow-sm` nos três. Depois
extrair a string única (ver P1 abaixo).

**Comando sugerido:** `/impeccable polish`

---

#### [P1] Estilo de campo é uma string Python replicada 17 vezes

**Local:** `apps/accounts/forms.py` (2), `apps/estoque/forms.py` (4),
`apps/requisicoes/forms.py` (11)
**Categoria:** Integridade / Manutenção

```
'w-full min-h-11 rounded-lg border border-border-strong px-3 py-2 text-sm
 focus:border-border-focus focus:ring-2 focus:ring-border-focus focus:outline-none'
```

Essa string é a definição real do componente "campo" do sistema — e ela vive
copiada em `forms.py`, fora de `components/`, fora de `input.css` e fora do
alcance de qualquer revisão de design. Já divergiu: `requisicoes/forms.py:20` e
`:250` estão sem `min-h-11`, ou seja, dois campos abaixo do piso de 44px que o
`design-system.md` fixa como obrigatório.

Também é o único lugar do sistema que usa `focus:` em vez de
`focus-visible:` — 23 ocorrências contra 41. Consequência: campo mostra o anel
ao ser clicado com o mouse, botão não. A mesma tela responde de dois jeitos ao
mesmo gesto.

**Correção:** uma constante única (ex.
`apps/core/forms/widgets.py::CLASSE_CAMPO`) importada por todos os formulários,
ou uma classe de componente em `@layer components` do `input.css`
(`.campo`), consumida por `attrs={'class': 'campo'}`. A segunda opção tira a
apresentação do Python de vez e é a que combina com `.skip-link`/`.app-bar`,
que já moram lá. Padronizar em `focus-visible:` na mesma passada.

**Comando sugerido:** `/impeccable harden`

---

#### [P1] `_messages.html` é uma segunda implementação de `alert.html`

**Local:** `core/partials/_messages.html` vs `components/alert.html`
**Categoria:** Integridade

As mesmas quatro variantes semânticas (info/success/warning/danger), com os
mesmos tokens de fundo e borda, mantidas em dois arquivos. Já divergiram em três
pontos:

| | `alert.html` | `_messages.html` |
|---|---|---|
| raio | `rounded-lg` | `rounded-md` |
| respiro | `px-4 py-3` | `px-3 py-2` |
| texto de warning | `text-warning-text` (amber-800) | `text-warning-text-strong` (amber-900) |

Os `<path>` de SVG também estão duplicados, com desenhos ligeiramente
diferentes para o mesmo ícone (compare o triângulo de warning nos dois
arquivos). O comentário de `alert.html` já registra que `_messages.html` "não
usa este componente" — o que documenta a duplicação em vez de resolvê-la.

**Correção:** `_messages.html` passa a mapear `message.level_tag` → `variant` e
delegar a `alert.html`, preservando a ordenação DOM (assertivos primeiro) e a
decisão de não declarar `aria-live` no wrapper. É exatamente o contrato de
"partial de domínio usa componente global" que o `design-system.md` §Granularidade
já prescreve.

**Comando sugerido:** `/impeccable distill`

---

#### [P1] Inventário do `design-system.md` documenta uma API que não existe

**Local:** `docs/design-system.md` §"Inventário inicial" (linhas 459–599)
**Categoria:** Documentação

O inventário é a primeira coisa que alguém lê para usar o sistema, e está
descrevendo outro sistema. Divergências verificadas:

- **`button.html`** — documenta `variant` como `primary, secondary, danger, ghost, link`;
  o componente tem 8, incluindo `danger-outline`, `warning-outline` e
  `return-outline`. Documenta `size=sm|md|lg`; só existem `sm` e `md`.
  Documenta os parâmetros `loading`, `loading_label`, `icon`, `icon_position` —
  nenhum existe. Os reais são `icon_template`, `icon_class`, `loading_label`
  (semântica diferente da documentada: é o valor lido por `form-submit.js`),
  `x_disabled`, `x_aria_busy`, `label_bind`, `spinner_show`, `data_modal_trigger`,
  `full_width_mobile`, `label_mobile`, `name`, `value`, `href`.
- **`card.html`** — documentado com slots `header`/`body`/`footer`. **O arquivo
  não existe.** O exemplo de uso (§"Card com ações") usa `{% block %}` dentro de
  `{% include %}` e `{% endinclude %}`, que não são sintaxe válida do Django.
  Quem copiar esse trecho recebe `TemplateSyntaxError`.
- **`form_field.html`** — documenta 2 parâmetros; o componente tem 8.
- **`modal.html`** — documentado como "adiar até uso real". Existe, está em uso,
  e tem contrato próprio com `modalController` e `_modal_body.html`.
- **`table.html`** — a listagem de estrutura (linhas 432–447) inclui
  `table_empty.html`, `dropdown.html`, `form_errors.html`. Nenhum existe. Os
  nomes reais são `empty_state.html` e `error_summary.html`.

**Não documentados** (13 de 22 componentes): a família `filter_*` inteira (6),
`autocomplete.html`, `item_form_row.html`, `error_summary.html`,
`ordenacao_data.html`, `pagination.html`, `_modal_body.html`, `_modal_icon.html`.

Cada um desses tem um comentário `{% comment %}` de cabeçalho excelente — a
documentação real do sistema já está nos arquivos. O `design-system.md` está
competindo com ela e perdendo.

**Correção:** ver §"Escalabilidade" abaixo — o inventário vira índice, não cópia.

**Comando sugerido:** `/impeccable document`

---

### P2 — Corrigir na próxima passada

#### [P2] `badge.html`: 13 ramos com a mesma string de classe

**Local:** `components/badge.html:22–50`
**Categoria:** Integridade / Manutenção

Cada variante repete literalmente:

```
inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset
```

...mais o bloco `{% if role %}...{% if aria_label %}...{% if prefixo_sr %}`,
idêntico nas 13. São ~110 caracteres de estrutura × 13 e três condicionais ARIA
× 13. Mudar o respiro do badge hoje é uma edição em 13 lugares, e o ramo
`{% else %}` de fallback tem estrutura ARIA diferente dos outros 13 (não
propaga `role`, `aria_label` nem `prefixo_sr`).

Além disso, 4 das 13 (`orange`, `indigo`, `violet`, `yellow`) usam paleta crua e
não têm par `-strong`, enquanto `blue`/`amber`/`red` têm. A grade de variantes é
irregular sem regra que explique a irregularidade.

**Correção:** um `{% with %}` no topo resolvendo `classes_variante` por
variante e um único `<span>` no corpo. Alternativa mais limpa: um filtro
`classes_badge` em `core_tags.py` com um dicionário
`{'blue': 'bg-primary-muted text-primary-text-strong ring-primary-border', ...}`
— a estrutura fica em um lugar, o mapa de variante em outro, e adicionar
variante vira uma linha de dicionário. Promover as 4 variantes de catálogo a
tokens (`--color-catalogo-1..4`) na mesma passada elimina a única exceção viva
da Regra do Token.

**Comando sugerido:** `/impeccable distill`

---

#### [P2] `button.html`: string de variante duplicada entre `<a>` e `<button>`

**Local:** `components/button.html:57` e `:73`
**Categoria:** Integridade / Manutenção

~1.100 caracteres de cadeia `{% if variant == ... %}` copiados verbatim nos dois
ramos. Já há uma diferença entre eles (o ramo `<button>` acrescenta
`cursor-pointer disabled:cursor-not-allowed disabled:opacity-60`), o que torna a
duplicação difícil de auditar a olho: é preciso comparar duas linhas de mil
caracteres para saber se divergiram por engano ou de propósito.

**Correção:** `{% with classes_variante=... %}` calculado uma vez antes do
`{% if href %}`, ou o mesmo filtro de `core_tags` proposto para o badge.

**Comando sugerido:** `/impeccable distill`

---

#### [P2] Botões escritos à mão em 3 componentes, com estilo divergente

**Local:** `components/filter_acoes.html`, `pagination.html`, `ordenacao_data.html`
**Categoria:** Integridade / Acessibilidade

`button.html` é incluído por 20 templates, mas três componentes do próprio core
escrevem o botão na mão — com estilo que não bate:

| | `button.html` | `filter_acoes.html` | `pagination.html` |
|---|---|---|---|
| respiro | `px-3 py-2` | `px-4 py-2` | `px-3 py-2` |
| peso | (nenhum → 400) | `font-semibold` / `font-medium` | `font-medium` |
| sombra | — | `shadow-sm` | — |
| offset do anel | `ring-offset-1` | `ring-offset-2` | `ring-offset-1` |
| borda do secundário | `border-border-strong` | `border-border` | `border-border` |

A última linha é a que importa para acessibilidade: `border-border` é slate-200,
~1,5:1 sobre `bg-surface`. O DESIGN.md declara que `border-strong` (slate-300) é
"reservada a borda de campo e de botão secundário, que precisam de 3:1"
(WCAG 1.4.11). Os dois botões secundários mais usados do sistema — "Limpar
filtros" e "Anterior/Próxima" — não seguem isso.

Também vale notar: `button.html` não declara peso de fonte nenhum, então o botão
primário do sistema renderiza em 400 enquanto o "Aplicar filtros" renderiza em
600. Um dos dois está errado; o DESIGN.md não decide.

**Correção:** decidir o peso do botão no DESIGN.md (600 é o esperado para um
controle), aplicar em `button.html`, e migrar os três componentes para
`{% include "components/button.html" %}`. `pagination.html` precisa de uma
variante ou de um estado desabilitado em `<a>`/`<span>` — hoje ele resolve isso
com um `<span aria-disabled="true">` que não é focável.

**Comando sugerido:** `/impeccable harden`

---

#### [P2] `--width-content` é declarado mas nunca chega às páginas

**Local:** `input.css:105` vs `base_auth.html:171` e 5 telas de `estoque/`
**Categoria:** Tokenização / Responsividade

`--width-content: 80rem` existe e é consumido só por `.app-bar__inner`. As
páginas usam `max-w-screen-xl`, que no Tailwind v4 compila para
`max-width: var(--breakpoint-xl)` — verificado no `app.css`. São dois caminhos
independentes para o mesmo 80rem: mexer no token de layout desalinha a barra de
aplicação do conteúdo que ela cobre, silenciosamente.

`max-w-screen-*` também é utility depreciada no v4 e sai numa versão futura.

Agravante: o DESIGN.md declara "container único de 80rem", mas as telas usam
**sete** larguras diferentes — `max-w-screen-xl` (6 telas), `max-w-3xl` (8),
`max-w-2xl` (4), `max-w-5xl`, `max-w-xl`, `max-w-md`, `max-w-sm`. Algumas são
legítimas (formulário estreito, card de login), mas não há regra escrita
dizendo qual tela recebe qual — então a próxima tela escolhe por imitação.

**Correção:** `@theme { --container-content: 80rem; --container-form: 48rem; }`
gerando `max-w-content` / `max-w-form`, e uma regra nomeada no DESIGN.md ligando
tipo de tela → largura (listagem = content, formulário = form, autenticação =
card-sm). Trocar `max-w-screen-xl` por `max-w-content` nas 6 telas.

**Comando sugerido:** `/impeccable layout`

---

#### [P2] Seção "Estados de UI" do `design-system.md` contradiz a Regra do Token

**Local:** `docs/design-system.md:198–303`
**Categoria:** Documentação

A seção inteira é escrita em paleta crua — `bg-slate-200 text-slate-500`,
`focus-visible:ring-blue-500`, `bg-blue-600 hover:bg-blue-700`,
`text-amber-800 on bg-amber-50` — no mesmo documento que, 140 linhas acima,
proíbe paleta crua em template. Quem ler de cima para baixo recebe a regra e
depois oito exemplos que a quebram.

Pior: o estado desabilitado documentado (`bg-slate-200 text-slate-500`) **não é
o que o sistema faz**. `button.html` usa `disabled:opacity-60
disabled:cursor-not-allowed`, preservando a variante — comportamento que o
DESIGN.md descreve corretamente e o `design-system.md` descreve errado.

**Correção:** reescrever a seção em tokens (`bg-bg-subtle text-text-disabled`,
`focus-visible:ring-border-focus`) e alinhar o estado desabilitado ao
componente real.

**Comando sugerido:** `/impeccable document`

---

#### [P2] Duas convenções de ícone convivendo

**Local:** `components/icons/` — 4 arquivos `_*.html`, 11 arquivos `.svg`
**Categoria:** Integridade

`_check.html`/`_prancheta.html`/`_caixa_entrada.html`/`_seta_circular.html` são
partials contendo só o `<path>`, incluídos via `{% include icone %}` (contrato de
`empty_state.html`). Os 11 `.svg` são arquivos completos, consumidos pela tag
`{% icon "nome" %}`. Duas mecânicas para uma coisa só, e o chamador precisa saber
qual ícone mora em qual convenção.

Somando: 33 `<path>` inline aparecem em 13 templates fora do catálogo, incluindo
os 8 de `alert.html` + `_messages.html`.

**Correção:** convergir para `{% icon %}` e o formato `.svg`. `empty_state.html`
passa a receber `icone="nome"` em vez de caminho de partial.

**Comando sugerido:** `/impeccable distill`

---

### P3 — Polir se sobrar tempo

#### [P3] Seis tokens declarados que nunca compilam

**Local:** `input.css:61–66, 78`
**Categoria:** Tokenização

Verificado no `app.css`: `--color-info-subtle`, `--color-info-muted`,
`--color-info-border`, `--color-info-text` e `--color-surface-raised` não
aparecem no CSS compilado — nenhum template os consome.

Para a família `info-*` o `design-system.md` já explica o porquê em dois
parágrafos, e a explicação é correta. Mas dois parágrafos de nota de rodapé para
justificar um token morto é caro: quem lê precisa processar a exceção antes de
entender a regra. **Sugestão:** manter os tokens (custam zero em runtime) e
comprimir a explicação a uma linha — a explicação longa já vive no DESIGN.md.

`--color-surface-raised` é caso diferente: tem o **mesmo valor** de
`--color-surface` e não é citado em documento nenhum. É um token que promete uma
distinção que o sistema não tem. Remover.

**Comando sugerido:** `/impeccable distill`

---

#### [P3] `duration-150` cru em 11 lugares; `--ease-out`/`--ease-in` duplicam o Tailwind

**Local:** `base_auth.html`, 3 telas de `estoque/`; `input.css:96–102`
**Categoria:** Tokenização

`--duration-fast: 150ms` existe e é usado em 11 pontos do CSS de componente — e
os templates escrevem `duration-150` mesmo assim, 11 vezes. Trocar a duração
padrão do sistema hoje atinge metade dos lugares.

`--duration-instant` (50ms) não é usado em lugar nenhum.

`--ease-out: cubic-bezier(0, 0, 0.2, 1)` e `--ease-in: cubic-bezier(0.4, 0, 1, 1)`
são **exatamente** os defaults do Tailwind v4 para as mesmas utilities.
Redeclará-los não muda nada e sugere ao leitor que houve uma escolha.
`--ease-default` é o valor do `--ease-in-out` do Tailwind sob outro nome — esse
sim vale manter, porque o nome carrega a decisão ("a curva padrão do sistema").

**Correção:** `duration-150` → `duration-fast` nos 4 templates; remover
`--duration-instant`, `--ease-out`, `--ease-in`.

**Comando sugerido:** `/impeccable optimize`

---

#### [P3] Dois passos de tipografia fora da rampa

**Local:** `input.css:298` (`.app-bar__title`, 1rem), `:472`
(`.app-bar__menu-heading`, 0.6875rem) — confirmado pelo detector mecânico
**Categoria:** Documentação

O DESIGN.md define Title como 1.125rem; o CSS usa 1rem abaixo de 40rem e
1.125rem acima. É uma decisão MD2 legítima, só não documentada. E 0.6875rem
(11px) para o cabeçalho de seção do menu não existe na rampa de jeito nenhum.

**Correção:** documentar o passo mobile do Title no DESIGN.md, e ou subir o
cabeçalho de menu para 0.75rem (Label) ou registrar 0.6875rem como passo
`overline` da rampa.

**Comando sugerido:** `/impeccable typeset`

---

#### [P3] Classe de rótulo repetida em 6 lugares, com peso divergente do DESIGN.md

**Local:** `form_field.html`, `filter_select.html`, `filter_busca.html`,
`filter_data.html`, `filter_checkbox_group.html`
**Categoria:** Integridade

`block text-xs font-medium uppercase tracking-wide text-text-tertiary` aparece
literalmente em 5 componentes (66 ocorrências da assinatura em toda a base).
O DESIGN.md define Label como **600** (semibold); a implementação usa
`font-medium` (500), e `tracking-wide` (0.025em) bate com o token.

**Correção:** classe `.rotulo-campo` em `@layer components`, com o peso decidido
de um lado só.

**Comando sugerido:** `/impeccable typeset`

## Padrões sistêmicos

**1. O sistema tem dois catálogos de componente, e o de `components/` é o
melhor.** Os comentários `{% comment %}` de cabeçalho são documentação de
primeira: registram parâmetros, contrato ARIA, guardrails e — crucialmente — o
*motivo* de cada decisão (veja `error_summary.html`, `page_header.html`,
`table.html`). O `design-system.md` §Inventário tenta ser um segundo catálogo,
duplicando o que já está no arquivo, e é o que apodreceu. Regra a adotar: **o
componente é a fonte de verdade da sua própria API; o documento é índice e
regra transversal, nunca cópia.**

**2. Duplicação estrutural é o débito dominante, não drift visual.** Cinco
frentes — badge (13×), button (2×), alert vs messages (2×), campo em forms.py
(17×), rótulo (5×) — todas com o mesmo formato: a estrutura de um componente
copiada em vez de resolvida. Todas já divergiram em pelo menos um ponto. Nenhuma
delas quebra um teste quando diverge.

**3. Regra escrita sem mecanismo que a sustente vira sugestão.** A Regra do
Token pegou (2 exceções em 79 templates) porque a utility semântica é o caminho
mais curto. A Regra do Raio Crescente, o piso de 44px e a borda 3:1 não pegaram
nos filtros e na paginação, porque escrever a classe errada é igualmente fácil.
O que falta é um teste — um `test_design_system.py` que varra os templates
procurando `rounded-md` em campo, `focus:ring` fora de `focus-visible`, e
`border-border` em controle, custa pouco e trava as três de uma vez.

## O que está funcionando

- **Disciplina de token quase total.** 2 exceções em 79 templates, ambas
  declaradas e justificadas. Raro em qualquer base.
- **Acessibilidade por padrão, não por auditoria.** Skip link, `error_summary`
  no padrão GOV.UK com foco no mount, `renderizar_campo_com_aria` costurando
  `aria-describedby`, piso de 44px em campo *e* botão, e a decisão explícita de
  **não** usar `role="status"` em badge de listagem para não criar 20 live
  regions. Esse último detalhe é conhecimento de especialista.
- **Escala de empilhamento fechada e justificada por bug real.** A tabela de
  z-index e o parágrafo que explica por que a barra de ação fica abaixo do
  popover valem mais que qualquer convenção genérica.
- **Decisões com medição anexada.** A Regra do Cartão Único não é gosto: os
  números (734px disponíveis, 808–1081px necessários) estão no arquivo. É o
  padrão a replicar em toda decisão futura.
- **Rejeição explícita do `DataTable` config-driven.** O guardrail "se o chrome
  precisar de parâmetro que descreve conteúdo de célula, a abstração está
  errada" é a coisa mais valiosa do documento para escalabilidade.

## Escalabilidade — estrutura proposta

O sistema tem 22 componentes; o `design-system.md` diz que hierarquia só se
justifica acima de 30–40. Correto, e a estrutura flat deve continuar. O que
precisa de estrutura é o **documento**, não a pasta.

Reorganização sugerida do `docs/design-system.md`:

1. **Princípios** — mantém.
2. **Tokens** — mantém, mas a tabela de sufixos vira a referência única e a
   lista de "tokens novos adicionados em #86" some (histórico é do git).
3. **Regras invioláveis** — promover para o topo, com nome: Regra do Token,
   Regra do Raio Crescente, Regra dos Quatro Degraus, Piso de 44px, Regra da
   Reversão. Cada uma em duas linhas, cada uma com o teste que a verifica.
4. **Como escolher onde uma coisa mora** — a seção §Granularidade já é boa;
   ganha uma árvore de decisão de 5 linhas no topo.
5. **Índice de componentes** — tabela de uma linha por componente: nome, para
   que serve, onde está documentado (= o próprio arquivo). Sem cópia de
   parâmetro. Gerável por script a partir dos `{% comment %}`.
6. **Checklist de revisão** — mantém, é útil.

Remover: §Inventário inicial (linhas 459–599) inteiro, absorvido pelo índice.
Reescrever: §Estados de UI, em tokens.

**Contrato para componente novo** (o que hoje não existe e é o que trava
crescimento consistente):

```
[ ] Comentário de cabeçalho: parâmetros, obrigatoriedade, contrato ARIA, motivo
[ ] Só tokens semânticos — zero classe de paleta crua
[ ] Raio conforme a camada (controle 0.375 / campo 0.5 / papel 0.75 / modal 1rem)
[ ] Elevação em um dos quatro degraus (0/1/8/24dp)
[ ] Piso de 44px em qualquer coisa acionável
[ ] focus-visible:ring-2 com offset
[ ] Zero semântica de domínio — variante e label chegam resolvidos
[ ] Uma linha no índice do design-system.md
```

## Ações recomendadas, em ordem

1. **[P1] `/impeccable polish`** — raio e sombra dos três `filter_*`; alinhar ao
   `rounded-lg` do resto do sistema.
2. **[P1] `/impeccable harden`** — extrair a classe de campo de `forms.py` para
   uma fonte única, padronizar `focus-visible:`, e migrar `filter_acoes` /
   `pagination` / `ordenacao_data` para `button.html` (resolve o contraste 3:1
   dos secundários no caminho).
3. **[P1] `/impeccable distill`** — colapsar os 13 ramos de `badge.html` e a
   string duplicada de `button.html`; fazer `_messages.html` delegar a
   `alert.html`; unificar as duas convenções de ícone.
4. **[P1] `/impeccable document`** — remover o §Inventário, reescrever
   §Estados de UI em tokens, criar o índice de componentes e o contrato de
   componente novo.
5. **[P2] `/impeccable layout`** — tokenizar as larguras de container e escrever
   a regra de tela → largura.
6. **[P3] `/impeccable typeset`** — `.rotulo-campo` única, decidir peso do
   rótulo e do botão, documentar os dois passos de rampa do topbar.
7. **[P3] `/impeccable optimize`** — `duration-150` → `duration-fast`; remover
   tokens mortos.
8. **`/impeccable polish`** — passada final.
