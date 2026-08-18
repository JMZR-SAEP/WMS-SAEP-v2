# Plano — Implementar o contrato de dismiss de flash messages em `_messages.html`

Issue: [#119](https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/119) — Etapa 2 (Feedback e estado)
do `docs/plans/audit-frontend-restante.md`.

## Escopo

### O que muda

1. **`apps/core/templates/core/partials/_messages.html`** — reescrito:
   - botão de fechar em todos os ramos, **fora** do nó que carrega o `role`;
   - auto-dismiss de 8s só em `success`/`info`, com pausa em `hover`/`focus-within`;
   - loop único sobre uma lista já ordenada, no lugar dos dois `{% for %}` sobre `messages`;
   - `debug` excluído explicitamente do ramo catch-all;
   - um mecanismo de espaçamento só (`space-y-2` no wrapper, sem `mb-2` nos filhos).
2. **`apps/core/templatetags/core_tags.py`** — nova tag/filtro que ordena e filtra as
   mensagens, seguindo o precedente de `classes_botao` (apresentação derivada em Python,
   template fino).
3. **`apps/core/static/core/js/mensagens.js`** (novo) — componente Alpine `mensagemFlash`,
   registrado em `alpine:init`, no mesmo padrão de `modal.js`, `autocomplete.js` e
   `item_form_row.js`.
4. **`apps/core/templates/base.html`** — inclui o novo `mensagens.js` na lista de scripts.
5. **`apps/accounts/templates/accounts/login.html`** — `_messages.html` passa para dentro
   do bloco centralizado.
6. **`apps/accounts/templates/accounts/login_bloqueado.html`** — passa a incluir `_messages.html`.
7. **`apps/core/tests/test_components.py`** — testes novos do contrato.
8. **`docs/plans/77-alert-component.md`** e **`.design/TASKS.md`** — correção das duas
   afirmações falsas sobre o estado do dismiss.
9. **`apps/core/static/core/css/app.css`** — recompilado (`make css-build`) se o markup
   novo introduzir utilitário Tailwind ainda não presente no bundle.

### O que NÃO muda

- `apps/core/templates/components/alert.html` — decisão do dono do produto (2026-08-18):
  `alert.html` e `_messages.html` seguem separados, sem `_feedback_box.html` compartilhado.
  A paridade entre os dois é a issue #124, bloqueada por esta.
- `docs/CONVENTIONS.md:174-181` — o doc está certo como intenção; o código é que deve.
- As asserções de contagem de `role` em `apps/requisicoes/tests/test_views.py:2713` —
  o markup novo tem que continuar verde **sem tocar no teste**.
- Views, services, policies, models. Esta issue é 100% camada de apresentação.
- O mapeamento exceção → nível de mensagem.

## Arquivos tocados

| Arquivo | Natureza |
|---|---|
| `apps/core/templates/core/partials/_messages.html` | reescrita |
| `apps/core/templatetags/core_tags.py` | símbolo novo (`mensagens_visiveis`) |
| `apps/core/static/core/js/mensagens.js` | arquivo novo |
| `apps/core/templates/base.html` | uma linha de `<script>` |
| `apps/accounts/templates/accounts/login.html` | mover um `{% include %}` |
| `apps/accounts/templates/accounts/login_bloqueado.html` | acrescentar `{% include %}` |
| `apps/core/tests/test_components.py` | testes novos |
| `docs/plans/77-alert-component.md` | correção de texto (linhas 70-73) |
| `.design/TASKS.md` | correção de estado (linha 23) |
| `apps/core/static/core/css/app.css` | artefato de build |

## Desenho

### Estrutura do item

O `role` sai do container e passa a envolver **só** o texto:

```html
<div class="flex items-start gap-2 …" x-data="mensagemFlash({ auto: true })" x-show="visivel">
  <svg aria-hidden="true" …></svg>
  <div role="status" class="min-w-0 flex-1">{{ message }}</div>
  <button type="button" aria-label="Fechar mensagem" @click="fechar()" class="… min-h-11 min-w-11">…</button>
</div>
```

Consequências:

- o leitor de tela anuncia o texto, não `"…, Fechar mensagem, botão"`;
- a contagem de `role="alert"` e `role="status"` continua 1 por mensagem — `test_views.py:2713`
  passa sem alteração;
- o ícone é `aria-hidden` e fica fora da live region, o que também é correto.

### Ordenação e filtragem — `mensagens_visiveis`

Hoje o template itera `messages` duas vezes. Funciona porque o `BaseStorage` do Django é
re-iterável depois do primeiro consumo, mas é dependência não declarada num detalhe de
framework — e é a causa do wrapper vazio (o segundo `<div class="space-y-2">` renderiza
mesmo sem nenhuma mensagem `success`/`info`).

A saída é materializar uma lista só, ordenada, em Python:

```python
@register.filter
def mensagens_visiveis(mensagens): ...
```

O nome cobre as duas responsabilidades — quais mensagens chegam ao usuário final e em
que ordem —, porque separar em dois filtros encadeados faria o template iterar o storage
duas vezes de novo, que é justamente o que se quer eliminar.

- descarta `debug` (nível de desenvolvimento; nunca foi para o usuário final, e hoje o
  catch-all da linha 30 o renderiza como info);
- ordena assertivas (`error`, `warning`) antes de polidas, com `sorted` estável, o que
  preserva a ordem relativa dentro de cada grupo — mesmo resultado visual de hoje;
- devolve uma `list`, então o template itera uma vez só e o `{% if %}` do wrapper passa a
  ser decidível.

Isso resolve três achados de higiene de uma vez (wrapper vazio, `debug`, re-iteração) em
vez de comentar dois deles.

### Auto-dismiss e WCAG 2.2.1 (Timing Adjustable)

A norma exige poder desligar, ajustar ou estender qualquer limite de tempo. A assimetria
adotada, registrada como comentário no template:

- **`success`/`info` somem em 8s** — a tela já reflete o resultado (a requisição saiu da
  fila, o estado mudou); a faixa é redundante e o conteúdo permanece disponível na tela;
- **`warning`/`error` nunca somem sozinhos** — a mensagem é a única fonte da informação
  (é o que `CONVENTIONS.md:178-179` já manda);
- **o timer pausa em `hover` e `focus-within`** e não recomeça do zero: retomar continua
  de onde parou, para que passar o mouse não vire uma forma de perder o resto do tempo.

O par pausa/retoma é o mecanismo de "estender" da 2.2.1; a exclusão de `warning`/`error`
é o "desligar" onde a perda seria real.

### Componente Alpine `mensagemFlash`

Arquivo novo `apps/core/static/core/js/mensagens.js`, registrado em `alpine:init`
(`window.Alpine.data('mensagemFlash', factory)`) como os outros três componentes do
projeto. Carregado em `base.html` **antes** de `alpine.min.js`, na mesma posição dos demais.

Estado: `visivel`, mais o handle do timer. API: `fechar()`, `pausar()`, `retomar()`.
Sem timer quando `auto` é falso — `warning`/`error` só ganham `fechar()`.

**Destino do foco após o dismiss.** Quem fecha pelo teclado está com o foco no próprio
botão que some. Sem tratamento, o foco cai no `<body>` e o usuário perde o lugar na tela —
o critério "dispensável só pelo teclado" só vale se depois de dispensar ainda dá pra
trabalhar. `fechar()` devolve o foco ao `<main id="conteudo" tabindex="-1">`
(`base_auth.html:171`), que é o mesmo alvo do skip link: recomeça a ordem de tabulação no
início do conteúdo, sem inventar um destino novo. Nas telas de auth, onde o `<main>` não
tem `tabindex`, o fallback é `document.body`, e o efeito prático é o mesmo porque o card
de login é o primeiro focável da página.

`x-show` com valor inicial `true` não pisca, então não há `x-cloak` a declarar.
Com JS desligado o botão não faz nada e a faixa continua legível: degradação aceitável
para chrome de confirmação, e nenhuma informação se perde.

### Ícone de fechar

SVG inline no próprio template, como os quatro ícones de nível que já vivem ali e como o
"X" do toggle de menu em `base_auth.html:52`. O catálogo de `{% icon %}`
(`ICONES_CATALOGO`) não tem `fechar` e criar uma entrada para um único uso interno de um
partial é superfície a mais sem consumidor.

### Posicionamento nas telas de auth

- `login.html`: o `{% include %}` sai da linha 7 e entra dentro do
  `<div class="flex min-h-screen items-center justify-center …">`, acima do `<section>` do
  card, num wrapper `w-full max-w-sm`. Hoje a mensagem `"Sessão encerrada."` fica acima de
  uma dobra de 100vh e no celular nunca é vista.
- `login_bloqueado.html`: mesmo tratamento, incluindo `_messages.html` no mesmo ponto.
  Hoje qualquer mensagem enfileirada antes do 429 do axes desaparece sem rastro.

## Estratégia de teste

Camada de componente (`apps/core/tests/test_components.py`), renderizando o template pelo
engine do Django com um `FallbackStorage` real — não varredura estática de HTML. A memória
`frontend/etapa2_feedback_backlog` registra que o parser estático devolve `[]` para estes
arquivos porque 100% do estado visual vive dentro de `{% if %}`, e que isso é "não medido",
não "limpo".

| Caso | Asserção |
|---|---|
| Botão presente nos 4 níveis | um `<button aria-label="Fechar mensagem">` por mensagem, para `error`, `warning`, `success` e `info` |
| Alvo de 44px | o botão carrega `min-h-11` e `min-w-11` |
| Botão fora da live region | o nó com `role` não contém o `<button>` — extraído por `apps/core/tests/marcacao.py`, não por regex de grafia |
| Contagem de role | `role="alert"` e `role="status"` uma vez por mensagem (espelha `test_views.py:2713`) |
| Auto-dismiss em success/info | o item traz o argumento de auto no `x-data` |
| Ausência de auto-dismiss | `warning` e `error` **não** trazem auto — asserção de ausência, que é o buraco que o guarda de 44px tinha |
| Pausa | `@mouseenter`/`@mouseleave` e `@focusin`/`@focusout` presentes no item com timer |
| Foco após dismiss | `fechar()` move o foco para `#conteudo` — coberto em teste de unidade do componente Alpine, com DOM mínimo |
| `debug` não renderiza | mensagem `debug` não aparece no HTML e não gera caixa |
| Wrapper vazio | sem mensagens polidas, não sobra `<div class="space-y-2">` vazio |
| Espaçamento único | `mb-2` não coexiste com `space-y-2` no arquivo |
| Ordem do DOM | assertivas antes de polidas |
| `login_bloqueado.html` inclui `_messages.html` | render da view/template contém a faixa quando há mensagem |

Testes de `mensagens_visiveis` em Python direto: descarta `debug`, ordena assertivas
primeiro, estabilidade dentro do grupo, entrada vazia.

Teclado: o botão é `<button type="button">` nativo, focável e acionável por `Enter`/`Espaço`
sem nenhum handler de teclado próprio — o critério "dispensável só pelo teclado" é
satisfeito pela escolha de elemento, e o teste que o protege é o de presença do `<button>`
(um `<div @click>` reprovaria).

Regressão a não quebrar: `apps/requisicoes/tests/test_views.py:2713` roda sem edição.

## Invariantes

Da `docs/design-acesso-rapido/matriz-invariantes.md` e do design system:

- **Piso de 44px em controle clicável** — o botão novo é o primeiro clicável do arquivo;
  nasce com `min-h-11 min-w-11`. O guarda existente (`test_components.py:434`) só detecta
  `min-h-9`/`min-h-10` e **não** veria a ausência — por isso a asserção positiva entra no
  teste novo desta issue (a correção do guarda em si é a issue #120).
- **Live region declarada uma vez por mensagem** — `role` implica `aria-live`; nenhum
  `aria-live` explícito é adicionado.
- **Tokens semânticos, sem paleta crua** — o markup reusa os tokens já presentes
  (`-subtle`, `-border`, `-text-emphasis`); nenhuma classe `slate-`/`amber-`/etc. nova.
- **Ordem do DOM: assertivo antes de polido** — preservada pela ordenação estável.
- **Componente global não conhece enum de domínio** — `mensagens_visiveis` opera sobre
  `level_tag` do Django, não sobre estado de requisição.
- **Regra sem mecanismo vira sugestão** (`docs/design-system.md`) — já falhou 3 vezes neste
  conjunto de arquivos. Esta issue fecha com teste, não só com correção.

## Riscos

| Risco | Mitigação |
|---|---|
| Mover o `role` quebra `test_views.py:2713` | a contagem continua 1 por mensagem; o teste roda sem edição e é critério de aceite |
| Utilitário Tailwind novo (`min-w-11`) ausente do `app.css` minificado | `make css-build` após a implementação; `app.css` é artefato versionado |
| `x-show` antes do init do Alpine | valor inicial `true` — o item já nasce visível; sem `x-cloak` a declarar |
| JS desligado | botão inerte, faixa legível; nenhuma informação perdida |
| Auto-dismiss engolir informação | restrito a `success`/`info`, onde a tela já reflete o resultado; pausa em hover/foco |
| `mensagens_visiveis` consumir o storage cedo demais | o filtro materializa uma lista uma vez; o consumo (`used = True`) já acontecia no primeiro `{% for %}` de hoje |
| Regressão de layout no login | a faixa entra no fluxo do card centralizado, em wrapper de mesma largura (`max-w-sm`) |

Sem risco de concorrência, de contrato OpenAPI, de mutação de estoque ou de máquina de
estados: nenhuma camada de domínio é tocada.

## Fora de escopo (issues vizinhas)

- Paridade `alert.html` × `_messages.html` — #124, bloqueada por esta.
- Correção do guarda de 44px que não vê ausência — #120.
- Política de falha de componente e guarda de cor crua — #122 (HITL).
