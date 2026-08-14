# Design System — WMS-SAEP

Design system pragmático em Django templates + Tailwind CSS v4 + HTMX + Alpine.js.
Cobre tokens visuais, componentes globais e padrões de interação operacional.

Não é SPA, não é biblioteca JS pesada, não é identidade de marca. É ferramenta de
trabalho.

**Este documento é regra e índice, nunca cópia de API.** A documentação de cada
componente vive no bloco `{% comment %}` do próprio arquivo, que é onde ela não
apodrece — ali estão parâmetros, obrigatoriedade, contrato ARIA e o motivo de
cada decisão. Uma versão anterior deste arquivo mantinha um "inventário" paralelo
que descrevia quatro componentes inexistentes e uma API que `button.html` não
tinha há meses. O índice abaixo aponta; não repete.

A linguagem visual — a POV, o vocabulário de cor, a escala de elevação, as regras
nomeadas em prosa — vive em `DESIGN.md`. Aqui ficam as regras operacionais e o
mapa do catálogo.

## Princípios

- **Pragmático**: decidir com base em necessidade real, não antecipar
- **Operacional**: o usuário entende rápido o que pode fazer, em que estado está, onde há erro
- **Neutro**: sistema administrativo interno — visual profissional e acessível
- **Simples**: componentes com responsabilidade clara, sem excesso de parâmetros
- **Progressivo**: HTMX/Alpine para interação incremental; sem estado de domínio no JavaScript

## Regras invioláveis

Sete regras. Cada uma tem o mecanismo que a verifica, porque **regra sem
mecanismo vira sugestão** — foi assim que o piso de 44px e o raio de campo
saíram do ar em silêncio, sem quebrar teste nenhum.

| Regra | O que diz | O que verifica |
|---|---|---|
| **Token, nunca shade** | Template usa a utility semântica (`bg-primary`, `text-danger-text`), nunca a cor crua da paleta (`bg-blue-600`) nem a custom property no HTML. É o que torna um rebrand uma troca de valor em `input.css`. Exceção viva: as variantes de catálogo de `badge.html` e o backdrop de `modal.html`, ambas declaradas. | revisão |
| **Piso de 44px** | Todo controle acionável tem `min-h-11` — botão, campo, select, e a *label* que embrulha radio/checkbox. A mesma tela é operada com o dedo, em pé no galpão, e com teclado no escritório. | `test_nenhum_controle_abaixo_do_piso_de_44px` |
| **Campo tem uma definição só** | Campo de texto, número, busca, select e textarea usam `class="campo"` (definida em `input.css`). Não se escreve a string de campo à mão, nem em template nem em `forms.py`. | `test_nenhum_template_escreve_campo_na_mao` |
| **Botão tem uma definição só** | Toda ação passa por `components/button.html`. Se uma variante não existe, ela nasce no componente — não numa tela. | revisão |
| **Raio crescente** | Controle 0.375rem → campo 0.5rem → papel 0.75rem → modal 1rem → pill. Um raio intermediário inventado quebra a leitura de hierarquia por geometria. | revisão |
| **Quatro degraus de elevação** | 0dp repouso, 1dp papel, 8dp menu, 24dp modal, mais o 4dp exclusivo da barra de aplicação. Nenhuma sombra nova para componente novo. | revisão |
| **Reversão não é erro** | Devolução e reversão usam teal (`return`), jamais vermelho. Vermelho é negação, falha ou divergência; devolver material é o processo funcionando. | revisão |

As demais regras nomeadas — Sinal Único, Cartão Único, Chrome Sem Parâmetro,
Caixa Alta Estrutural, 14px, Empilhamento Fechado — estão em `DESIGN.md` com a
prosa e a medição que as originaram.

## Tokens

Os tokens vivem em `@theme` de `apps/core/static/core/css/input.css`. As
famílias e o significado de cada shade estão em `DESIGN.md` §Colors; aqui fica só
o que é operacional.

### Escala de sufixos

| Sufixo | Shade | Uso |
|---|---|---|
| `-subtle` | 50 | fundo de alerta, item de navegação ativo |
| `-muted` | 100 | fundo de badge |
| `-muted-strong` | 200 | fundo de badge "forte" |
| `-border` | 200 | borda de alerta, ring de badge |
| `-border-strong` | 300 | ring de badge forte, borda de botão outline |
| `-text-subtle` | 700 | aviso inline menos enfático (só `warning`) |
| `-text` | 700 | texto colorido de corpo |
| `-text-emphasis` | 800 | texto de banner de alerta |
| `-text-strong` | 900 | texto de badge e de caixa de erro |
| `-accent` | 500 | foco de botão destrutivo, asterisco de obrigatório (só `danger`) |
| `-border-input` | 400 | borda de campo inválido (só `danger`) |
| `-hover` / `-active` | 700 / 800 | pressão em botão (`primary` e `danger`) |

### As três bordas

Distinção de contraste medido, não de gosto:

- `border` (slate-200) e `border-strong` (slate-300) são **estruturais** — borda
  de papel, divisor, contorno tracejado de estado vazio. Separam superfícies que
  já se distinguem por tom.
- `border-control` (slate-500) **identifica um controle** — campo, select, botão
  secundário, upload. Ali a linha é a única pista de que há um controle, e a
  WCAG 1.4.11 pede 3:1.

Medido contra branco: slate-300 dá 1.48:1, slate-400 dá 2.63:1, slate-500 dá
4.77:1. Só o último passa em todas as superfícies do sistema.

### Tailwind v4 só compila o que é usado

`@theme` declara o token, mas a custom property e a utility só entram no
`app.css` quando algum template referencia a classe. É JIT real, não um dump.
Consequência prática: usar `bg-info-subtle` num template novo funciona
normalmente após `npm run css:build`; só não espere a classe já existir no
`app.css` sem ter sido consumida antes.

A família `--color-info*` (slate) está declarada e não é consumida por nenhum
template — a variante `info` de `alert.html` e o nível padrão de `_messages.html`
renderizam **azul** via `primary-*`, por decisão. Use `info-*` só quando precisar
de um aviso realmente neutro.

### Tipografia

Fonte do sistema, sem CDN: `ui-sans-serif, system-ui, sans-serif`.

| Papel | Tamanho | Peso | Onde |
|---|---|---|---|
| Display | 1.875rem | 600 | título de tela em desktop, um por página |
| Headline | 1.5rem | 600 | título de tela em mobile |
| Title | 1rem → 1.125rem em `sm` | 500 | título e marca na barra de aplicação |
| Body | **0.875rem** | 400 | o tamanho dominante do sistema |
| Label | 0.75rem | 600 | rótulo de campo, cabeçalho de seção, badge (sem caixa alta) |

O corpo é 0.875rem e não 1rem — decisão de densidade operacional (Regra dos 14px,
`DESIGN.md`). Se um texto precisa de mais presença, mude o peso ou o tom, não o
tamanho.

Controles (botão, item de menu, ação da barra, skip link) usam peso **500**.

### Espaçamento e forma

```
container:  80rem (--width-content); card de login 24rem (--width-card-sm)
padding:    p-4 em cartão de listagem, p-6 em seção maior
gap:        gap-2 entre controles irmãos, gap-3/gap-4 em grade
rounded:    controle 0.375 / campo 0.5 / papel 0.75 / modal 1rem / pill
sombra:     shadow-sm só em papel; campo e botão não têm sombra
```

### Empilhamento (z-index)

Escala fechada, para que uma superfície nova não precise adivinhar um valor:

| Camada | z-index | Onde |
|---|---|---|
| Conteúdo da página | auto | padrão |
| Barra de ação fixa no rodapé | `z-10` | ações sticky de formulário no mobile |
| Popover ancorado | `z-20` | dropdown do `autocomplete.html` |
| Barra de aplicação / overlay de navegação | `z-30` | `.app-bar`, scrim do menu |
| Drawer de navegação | `z-40` | `.app-bar__menu-wrap` |
| Skip link | `z-50` | primeiro foco tabulável |
| Modal | top layer | `<dialog>` nativo, fora da escala |

A regra que importa: **a barra de ação fixa fica abaixo do popover**. Quando ela
subiu para `z-30` e empatou com a barra de aplicação, o dropdown de material
passou a ser pintado por baixo dela no celular, e a opção ativa do combobox
ficava encoberta (WCAG 2.4.11).

## Estados de UI

### Desabilitado (ação bloqueada por permissão ou estado)

`button.html` já entrega: `disabled:opacity-60 disabled:cursor-not-allowed`,
preservando a variante — o botão continua reconhecível como a ação que é.

- Ação de **workflow** bloqueada: visível + `disabled` + motivo em texto,
  amarrado por `aria_describedby` ao parágrafo que explica.
- Ação **administrativa** irrelevante: fora da marcação.

```django
{% if pode_autorizar %}
  {% include "components/button.html" with label="Autorizar" variant="primary" %}
{% else %}
  {% include "components/button.html" with label="Autorizar" variant="primary" disabled=True aria_describedby="motivo-bloqueio" %}
  <p id="motivo-bloqueio" class="text-sm text-text-tertiary">
    Disponível apenas para o chefe do setor do beneficiário.
  </p>
{% endif %}
```

### Carregando

`button.html` cobre os dois caminhos:

- **Submit de formulário**: `loading_label="Registrando…"` — `form-submit.js`
  troca o texto e bloqueia o duplo envio.
- **Estado Alpine**: `x_disabled`, `x_aria_busy`, `spinner_show` e `label_bind`.

O spinner usa `motion-reduce:animate-none`.

### Readonly (campo preenchido, não editável)

`bg-bg-subtle`, borda neutra, cursor padrão. Nunca `disabled`, que impediria o
envio, e nunca `aria-disabled`, porque o campo não está semanticamente
desabilitado.

### Foco

Anel de foco em **todo** controle, sempre `focus-visible` e nunca `focus`:

```
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focus focus-visible:ring-offset-1
```

`.campo` já traz o seu. Em ação destrutiva o anel é `danger-accent`. Remover
`outline` só é aceitável porque o anel o substitui.

### Erro em campo

Vem sempre do Form, nunca hardcoded no componente. `form_field.html` costura
`aria-invalid` + `aria-describedby`, e `.campo[aria-invalid="true"]` pinta a
borda em `danger-border-input`. Formulário longo ganha também
`error_summary.html` no topo.

## Onde uma coisa mora

```
É estilo de campo?            -> .campo, em input.css
É uma ação clicável?          -> components/button.html (variante nova nasce lá)
Precisa de estado de domínio  -> partial de domínio em apps/<app>/templates/<app>/partials/
  (status="autorizada")?
Serve a 2+ telas, sem domínio -> componente global em apps/core/templates/components/
Usado 1 vez, fluxo instável   -> inline na tela, até estabilizar
```

### Componente global

Vive em `apps/core/templates/components/`. Conhece variantes visuais, estados e
ARIA. **Não** conhece semântica de domínio: recebe `variant` e `label` já
resolvidos.

### Partial de domínio

Vive em `apps/<app>/templates/<app>/partials/`. Conhece enums e regras do app, e
usa os componentes globais por dentro. É quem mapeia `EstadoRequisicao → variant`.

### Inline

Permitido para bloco usado uma vez, fluxo instável ou markup muito acoplada à
tela. Extrair quando for reutilizado 2+ vezes, quando o padrão visual estabilizar
ou quando uma mudança central precisar se refletir em vários lugares.

Estrutura **flat** em `components/`. Hierarquia só se passar de 30–40
componentes ou surgir uma família grande.

## Índice de componentes

21 componentes. A API de cada um está no `{% comment %}` do próprio arquivo —
esta tabela diz o que existe e para quê, não como se chama cada parâmetro.

### Ação e navegação

| Componente | Para quê |
|---|---|
| `button.html` | Toda ação do sistema. 9 variantes, `<a>` ou `<button>`, passthrough HTMX/Alpine/modal |
| `pagination.html` | Paginação server-side, preservando filtros ativos |
| `ordenacao_data.html` | Inverte a ordem por data/hora de uma listagem paginada |
| `page_header.html` | `<h1>` de tela principal, dentro do `<main>` |

### Formulário

| Componente | Para quê |
|---|---|
| `form_field.html` | Campo com label vinculada, ajuda, erro e fiação ARIA completa |
| `error_summary.html` | Sumário de erros no topo do formulário (padrão GOV.UK, foco no mount) |
| `item_form_row.html` | Linha de formset de item, compartilhada entre requisição e saída excepcional |
| `autocomplete.html` | Combobox ARIA de busca de material |

### Filtro

Família `filter_*`, montada por composição explícita na tela chamadora.

| Componente | Para quê |
|---|---|
| `filter_shell.html` | Moldura: disclosure no mobile, `<form>` HTMX, grade de campos (`partialdef`) |
| `filter_busca.html` | Campo de busca textual |
| `filter_select.html` | Select com opção "Todos…" |
| `filter_data.html` | Campo de data único — chamar duas vezes para um par De/Até |
| `filter_checkbox_group.html` | Grupo multi-seleção em `fieldset`/`legend` |
| `filter_acoes.html` | "Aplicar filtros" + "Limpar filtros" condicional, com reemite OOB |

### Superfície e feedback

| Componente | Para quê |
|---|---|
| `table.html` | Chrome de listagem em cartões (`partialdef`). Não há renderização em tabela |
| `modal.html` | `<dialog>` nativo com foco preso — componente-assinatura |
| `_modal_body.html` | Corpo compartilhado do modal (header, erro, corpo, rodapé) |
| `_modal_icon.html` | Ícone semântico do header de modal |
| `alert.html` | Banner de aviso estático, layout `stack` ou `row` |
| `badge.html` | Pill de estado. 13 variantes visuais, zero conhecimento de domínio |
| `empty_state.html` | Estado vazio com causa distinguida e CTA opcional |

Fora de `components/`: `core/partials/_messages.html` (flash messages do Django) e
`core/partials/_side_nav.html` (navegação lateral em `lg:`).

## Contrato de componente novo

```
[ ] Bloco {% comment %} de cabeçalho: parâmetros, obrigatoriedade, contrato
    ARIA e o motivo das decisões não óbvias
[ ] Só tokens semânticos — zero classe de paleta crua
[ ] Raio conforme a camada (controle / campo / papel / modal)
[ ] Elevação em um dos quatro degraus
[ ] Piso de 44px em qualquer coisa acionável
[ ] focus-visible:ring-2 com offset
[ ] Zero semântica de domínio — variante e label chegam resolvidos
[ ] Uma linha no índice acima
```

Se o componente precisa de um parâmetro que descreve **conteúdo** e não
estrutura, a abstração está errada. Parar e registrar, não generalizar.

## Checklist de revisão — acessibilidade

```
[ ] Contraste de texto ≥ 4.5:1; borda que identifica controle ≥ 3:1
[ ] Todo controle interativo tem focus-visible
[ ] Botão em carregamento usa aria-busy
[ ] Campo com erro usa aria-invalid + aria-describedby
[ ] Readonly e disabled visualmente distintos
[ ] Modal e dropdown operáveis por teclado (Tab, Escape, Enter/Espaço)
[ ] Ação bloqueada tem motivo textual amarrado por aria-describedby
[ ] Atualização HTMX crítica tem aria-live ou feedback visível
[ ] Ícone tem alternativa textual (aria-label, ou contexto que já o nomeia)
[ ] Badge de dado estático NÃO usa role="status" — 20 linhas virariam 20 live regions
```

## Exemplos de uso

Botão com HTMX:

```django
{% include "components/button.html" with label="Ver detalhes" variant="secondary" href=url_detalhe aria_label="Ver detalhes da requisição REQ-2026-001" %}
```

Campo de formulário:

```django
{% include "components/form_field.html" with field=form.observacao_geral %}
```

Campo fora de um Form Django (raro — prefira o Form):

```django
<input type="search" name="busca" class="campo" aria-label="Buscar material">
```

Badge de estado, via partial de domínio:

```django
{# em requisicoes/partials/_estado_badge.html #}
{% if requisicao.estado == "rascunho" %}
  {% include "components/badge.html" with variant="slate" label="Rascunho" prefixo_sr="Estado: " %}
{% elif requisicao.estado == "autorizada" %}
  {% include "components/badge.html" with variant="blue" label="Autorizada" prefixo_sr="Estado: " %}
{% endif %}
```

Listagem em cartões, com o fragmento de resultado pronto para swap HTMX:

```django
{% partialdef resultados %}
{% if lista %}
  {% include "components/table.html#cards_abertura" %}
    {% for item in lista %}
      {% include "components/table.html#card_abertura" %}
        <div class="flex items-start justify-between gap-3">
          <h2 class="break-words text-sm font-semibold text-text-primary">{{ item.titulo }}</h2>
          <span class="shrink-0">{% include "components/badge.html" with variant="blue" label="Autorizada" %}</span>
        </div>
      </article>
    {% endfor %}
  </div>
{% else %}
  {% include "components/empty_state.html" with titulo="Nada por aqui" %}
{% endif %}
{% endpartialdef %}
{% partial resultados %}
```

O fragmento é sempre **GET-only**. Transição de estado de domínio continua
retornando `204` com `HX-Redirect` (`docs/CONVENTIONS.md`); este fragmento nunca
é alvo delas.

Confirmação de ação irreversível:

```django
<div x-data="modalController({ id: 'confirmar-estorno' })">
  {% include "components/button.html" with variant="danger-outline" label="Estornar" data_modal_trigger="confirmar-estorno" %}
  {% include "components/modal.html" with id="confirmar-estorno" titulo="Estornar requisição?" descricao="Esta operação é irreversível." action_url=url_estornar confirm_label="Confirmar estorno" confirm_variant="danger" icon_variant="danger" form_body_template="requisicoes/partials/_modal_form_estorno.html" %}
</div>
```

## Armadilhas do template Django

Duas que já custaram bug em produção de tela:

- **`{# … #}` não atravessa linha.** O lexer só casa comentário numa linha só;
  um `{#` multi-linha não vira comentário, e as tags de dentro são executadas.
  Para comentário de várias linhas use `{% comment %}`. Travado por
  `test_nenhum_template_usa_comentario_de_linha_em_varias_linhas`.
- **`{% with %}` fecha no mesmo bloco.** Não dá para abrir um `{% with %}` num
  ramo de `{% if %}` e usá-lo fora. Quando precisar de um valor condicional,
  resolva com filtro (`yesno`, `firstof`, `default`) antes do `with`.

## Quando aparecer identidade corporativa da SAEP

Se a SAEP trouxer guideline oficial (logo, cores, tipografia):

1. Atualizar os tokens em `input.css` e o frontmatter de `DESIGN.md`
2. Não alterar templates individuais
3. Rodar `npm run css:build`

Isso é possível porque componentes usam `variant="primary"` e `class="campo"`,
não `bg-blue-600` nem a string de campo copiada.

## Futuro — dark mode

Adiado; o sistema começa em light mode. Se virar requisito, os tokens `--color-*`
já são o ponto único de troca: basta redefini-los sob
`@media (prefers-color-scheme: dark)` e `:root[data-theme="dark"]`. Nenhum
componente precisa ser reescrito.
