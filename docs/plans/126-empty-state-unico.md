# Plano — #126 `empty_state`: uma implementação só, anúncio no swap HTMX e copy uniforme

Issue: https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/126
Origem: Etapa 2 (Feedback e estado) de `docs/plans/audit-frontend-restante.md`.
Comando recomendado pela issue: `/impeccable onboard` sobre `empty_state.html`,
`preview_importacao_scpi.html` e `lista_materiais.html` — usado na fase de
implementação, antes de escrever markup.

## Estado real do repositório (difere da issue em dois pontos)

A issue foi escrita em 2026-08-18. Duas coisas mudaram desde então e o plano
parte do código vivo, não do texto da issue:

1. **`historico_requisicoes.html` já tem a live region de contagem.** Hoje o
   arquivo tem `<p id="resumo-historico-requisicoes" class="sr-only"
   role="status">` **fora** do wrapper de resultados, alimentado por
   `hx-swap-oob="innerHTML:"` no ramo `is_htmx`. O wrapper `#resultados-...`
   **não** é live region. Esse é o padrão-alvo desta issue; ele não precisa ser
   inventado, precisa ser **replicado**.
2. **`historico_movimentacoes.html` ainda está no padrão antigo.** O wrapper
   `#resultados-movimentacoes` carrega `aria-live="polite" aria-atomic="true"`
   — exatamente a marcação que o critério de aceite "a lista de resultados
   **não** virou live region" recusa. É o alvo real do item de anúncio HTMX
   desta issue.

Consequência de escopo: o item "anúncio no swap HTMX" vira **paridade** —
levar movimentações ao padrão que requisições já usa.

## Escopo

### O que muda

| # | Mudança | Arquivo |
|---|---|---|
| D-1 | Clone à mão do estado vazio passa a usar o componente | `apps/estoque/templates/estoque/preview_importacao_scpi.html` |
| D-2 | `nivel_titulo` parametriza o nível do cabeçalho (default 2, documentado) | `apps/core/templates/components/empty_state.html` |
| D-3 | Descrição ganha limite de medida (65–75ch) | `apps/core/templates/components/empty_state.html` |
| D-4 | Movimentações troca o wrapper-live-region pela live region de contagem | `apps/estoque/templates/estoque/historico_movimentacoes.html` |
| D-5 | Ícone de "nenhum resultado para este filtro" passa a comunicar filtro | novo `apps/core/templates/components/icons/_funil.html` + 2 chamadores |
| D-6 | Ícone do vazio-inicial das duas listagens filtradas deixa de ser seta de recarregar | `historico_requisicoes.html`, `historico_movimentacoes.html` |
| D-7 | Copy uniforme nos 11 chamadores (título sem ponto, ícone e descrição sempre presentes) | `lista_materiais.html` (2 chamadas) |
| D-8 | Guarda: nenhum template replica a marcação do estado vazio à mão | `apps/core/tests/test_components.py` |
| D-9 | Guarda: todo chamador do componente segue o padrão de copy | `apps/core/tests/test_components.py` |

Documentação: `docs/design-system.md` ganha o `nivel_titulo` no inventário do
componente e o padrão "live region de contagem fora da lista" como a forma
canônica de anunciar swap HTMX de listagem.

CSS: `max-w-prose` **não** está compilado em `apps/core/static/core/css/app.css`
hoje. D-3 exige `make css-build` antes do PR — o `app.css` é versionado.

### O que NÃO muda

- **`text-text-disabled` fora do clone.** As 5 outras ocorrências
  (`notificacoes/lista.html:40`, `_autocomplete_item_beneficiario.html:7`,
  `_autocomplete_item_material.html:10`, `preview_importacao_scpi.html:160` e
  `:247`) são Etapa 7/8, como a própria issue delimita.
- **O `text-text-disabled` do ícone do `empty_state.html`.** É `aria-hidden`,
  decorativo puro, e a 1.4.11 isenta grafismo decorativo. O critério de aceite
  fala de **texto**; o ícone não é texto. Mexer nele mudaria o peso visual dos
  11 chamadores sem que nada peça.
- **`_check.html` como ícone de `lista_saidas_excepcionais.html`.** O ícone é
  discutível, mas não é o ícone que a issue nomeia. Fora de escopo.
- **`lista_materiais.html` não vira HTMX.** A busca dele é form GET com recarga
  de página inteira; live region não é o mecanismo depois de navegação full-page
  (checklist do `docs/design-system.md`). O anúncio dele já é o `<h1>` da página
  recarregada.
- **A prosa de apoio das telas** (`max-w-3xl` dos parágrafos abaixo do
  `page_header`). D-3 é sobre a descrição **do componente**.
- **`preview_importacao_scpi.html:18`** — o dropzone é `border-2 border-dashed
  border-border`, marcação e propósito diferentes do estado vazio. A guarda D-8
  casa a assinatura exata (`border-dashed border-border-strong`), não "qualquer
  tracejado".
- Nenhum service, selector, policy, model, form, migration ou regra de domínio.

## Arquivos tocados

**Templates**

- `apps/core/templates/components/empty_state.html` — `nivel_titulo`, medida da
  descrição, docstring.
- `apps/core/templates/components/icons/_funil.html` — **novo**.
- `apps/core/templates/components/icons/_seta_circular.html` — **removido**:
  após D-5 e D-6 fica sem nenhum chamador (hoje tem exatamente 4, todos nas duas
  listagens filtradas).
- `apps/estoque/templates/estoque/preview_importacao_scpi.html` — D-1.
- `apps/estoque/templates/estoque/historico_movimentacoes.html` — D-4, D-5, D-6.
- `apps/requisicoes/templates/requisicoes/historico_requisicoes.html` — D-5, D-6.
- `apps/estoque/templates/estoque/lista_materiais.html` — D-7.

**Testes**

- `apps/core/tests/test_components.py` — D-2, D-3, D-8, D-9 (+ casos sintéticos
  que provam que as guardas detectam).
- `apps/estoque/tests/test_views.py` — reescreve
  `test_aria_live_polite_no_conteiner_de_resultados` (2089); atualiza
  `test_nenhum_material_cadastrado_exibe_empty_state_dashed` (1573, hoje casa a
  string com ponto final); cobre o componente no preview SCPI.
- `apps/requisicoes/tests/test_views.py` — ícone de filtro no vazio contextual.

**Docs e build**

- `docs/design-system.md` — `nivel_titulo` no inventário, padrão da live region de
  contagem, e o exemplo de uso da linha 514 alinhado à guarda D-9
- `apps/core/static/core/css/app.css` (gerado por `make css-build`)

## Decisões

### D-1 — o clone do preview SCPI vira include

Hoje (`preview_importacao_scpi.html:271-275`):

```django
<div class="rounded-xl border border-dashed border-border-strong bg-surface px-6 py-12 text-center">
  <p class="text-sm text-text-tertiary">O arquivo não contém linhas de dados após o cabeçalho.</p>
  <p class="mt-1 text-xs text-text-disabled">Verifique se o arquivo possui registros abaixo do cabeçalho.</p>
</div>
```

Vira include do componente, com `titulo` sem ponto final e `descricao`
carregando a próxima ação. `text-text-disabled` (2.63:1) desaparece por
construção: a descrição do componente é `text-text-tertiary`.

O ícone é `_prancheta.html` — documento/registro, que é do que o preview fala.
Não nasce ícone novo para um caso só.

**Nível do cabeçalho: fica no default (2).** O outline do preview foi conferido:
o único `<h2>` do arquivo (`:42`, "Carregar arquivo CSV do SCPI") vive no ramo de
upload do mesmo `{% if %}`, e os dois ramos nunca renderizam juntos. No ramo de
preview o `<h1>` do `page_header` é o único cabeçalho acima — os cartões de linha
abrem com `<code>`, não com heading. Um `<h2>` aqui é exatamente o degrau certo.

Esta conferência é o motivo de D-2 existir: hoje o acoplamento é real e não está
escrito em lugar nenhum, então cada novo chamador precisa refazê-la de cabeça.

### D-2 — `nivel_titulo`, default 2

```django
{% with nivel=nivel_titulo|default:2 %}
  <h{{ nivel }} class="...">{{ titulo }}</h{{ nivel }}>
{% endwith %}
```

O `{% with %}` não é enfeite: repetir `nivel_titulo|default:2` na abertura e no
fechamento cria duas fontes para o mesmo número, e um `<h3>…</h2>` não quebra
render nenhum — quebra o outline em silêncio.

O docstring também deixa de chamar `icone` de "opcional": com a guarda D-9, ele é
opcional para o componente e **obrigatório para chamador de tela**. Um parâmetro
descrito como opcional enquanto um teste o exige é armadilha para o próximo.

Default 2 preserva o comportamento dos 11 chamadores atuais — nenhum precisa ser
tocado por causa desta decisão. O docstring passa a declarar o default e o
porquê (as listagens usam `<h2>` nos títulos de cartão; o estado vazio ocupa o
mesmo degrau).

Sem validação de faixa em template: o componente não é superfície de entrada de
usuário e a guarda D-9 vê os chamadores. Uma validação silenciosa aqui só criaria
um segundo lugar onde a regra mora.

### D-3 — medida da descrição

`max-w-prose mx-auto` na descrição (`max-w-prose` = 65ch em Tailwind, o piso da
faixa 65–75ch de `DESIGN.md:259`). `mx-auto` porque a caixa é `text-center`: sem
ele, a coluna estreita encostaria à esquerda dentro de um bloco centralizado.

O título fica sem limite: é frase curta por contrato de copy (D-7), e limitar um
`<h2>` de uma linha só produziria quebra sem motivo.

**`max-w-prose` = 65ch é premissa a confirmar, não fato.** A escala do Tailwind é
conferida via Context7 (`/tailwindlabs/tailwindcss.com`) na implementação; se v4
mudou o valor, o plano cai para `max-w-[70ch]` arbitrado, que fica no meio da
faixa de `DESIGN.md:259`.

**Guarda do CSS compilado.** Um teste que lê o HTML renderizado vê a classe e
passa verde mesmo com `app.css` desatualizado — a classe seria inerte em
produção. Por isso D-3 fecha com uma asserção sobre
`apps/core/static/core/css/app.css`. É a mesma doutrina de "regra sem mecanismo
vira sugestão", aplicada ao passo de build que o `AGENTS.md` não menciona.

Procurar a string `max-w-prose` no bundle **não** é asserção suficiente: o nome
da classe aparece num seletor sem provar que ele declara a largura certa, e
`max-w-[70ch]` (a saída de fallback) nem sequer contém essa string. A guarda
localiza o seletor da classe efetivamente usada pelo componente e lê a
declaração `max-width` dele, exigindo unidade `ch` e valor dentro de 65–75 —
o intervalo de `DESIGN.md:259`, não um número mágico. Assim a guarda vale para
`max-w-prose` (65ch) e para `max-w-[70ch]` sem ser reescrita, e falha de verdade
quando o build não rodou.

### D-4 — live region de contagem em movimentações

Espelha requisições, linha a linha:

1. `#resultados-movimentacoes` **perde** `aria-live="polite"` e
   `aria-atomic="true"`.
2. Nasce `<p id="resumo-movimentacoes" class="sr-only" role="status"></p>`
   **fora** do wrapper, vazio no carregamento inicial (nada mudou ainda).
3. No ramo `is_htmx`, um `<span hx-swap-oob="innerHTML:#resumo-movimentacoes">`
   com a contagem.

**As três frases, literais.** "Plural por `pluralize`" não é especificação — em
PT-BR o filtro precisa dos dois sufixos escritos à mão, e requisições já paga
esse preço (`pluralize:"ão,ões"` mais `pluralize:"a,as"`, dois filtros na mesma
frase por causa da concordância do particípio). Movimentações é palavra
feminina regular, então basta um sufixo por palavra flexionada:

| Contagem | Texto anunciado |
|---|---|
| 0 | `Nenhuma movimentação encontrada.` |
| 1 | `1 movimentação encontrada.` |
| 2+ | `N movimentações encontradas.` |

`n` é **`page_obj.paginator.count`** — o total do recorte filtrado, não
`page_obj.object_list|length`. A listagem é paginada: anunciar o tamanho da
página diria "25 movimentações encontradas" para um filtro que casou 300, que é
pior que não anunciar. É a mesma fonte que requisições já usa.

Marcação: `{{ n }} movimenta{{ n|pluralize:"ção,ções" }} encontrada{{ n|pluralize }}.`
no ramo não-zero — com o ponto final, como as três frases da tabela. O sufixo padrão (`s`) serve para "encontrada"; "movimentação"
precisa do par explícito porque a flexão troca a sílaba tônica, não só acrescenta
letra. Os três casos viram três testes — 0, 1 e 2 —, não um só. Um teste que só
exercita o zero deixa "1 movimentações" passar em produção.

O `hx-swap-oob` dispara em **todo** `is_htmx`, não só no submit do filtro:
paginação e troca de ordenação também passam por ali e também vão anunciar a
contagem. É o comportamento que requisições já tem hoje, e é o desejado — as três
ações mudam o recorte visível sem navegar.

Por que trocar e não somar: as duas coisas juntas fazem o leitor de tela reler as
25 linhas **e** a contagem. O comentário já escrito em `historico_requisicoes.html`
explica a escolha e passa a valer para as duas telas.

Isso contradiz `docs/plans/8-responsivo-acessibilidade-ia.md:74` ("já presente,
não tocar"). Planos antigos são registro histórico, não contrato vivo; o critério
de aceite desta issue é explícito no sentido oposto e o `AGENTS.md` manda confiar
primeiro no código/documentação vivos. O plano antigo não é editado.

### D-5 e D-6 — os quatro `_seta_circular`

| Chamador | Hoje | Passa a ser | Por quê |
|---|---|---|---|
| `historico_requisicoes.html` filtro | `_seta_circular` | `_funil` | O estado é "seu recorte não achou nada", não "recarregue" |
| `historico_movimentacoes.html` filtro | `_seta_circular` | `_funil` | idem |
| `historico_requisicoes.html` inicial | `_seta_circular` | `_caixa_entrada` | Vazio-inicial é caixa vazia; já é o ícone das duas filas vazias |
| `historico_movimentacoes.html` inicial | `_seta_circular` | `_caixa_entrada` | idem |

`_funil.html` segue a forma dos irmãos: um `<path>` só, sem `<svg>`, sem
`fill`/`class` próprios — a cor e o tamanho vêm do componente.

Com os 4 migrados, `_seta_circular.html` fica órfão e é apagado no mesmo commit.
Esse commit tem pré-requisito de procedimento, não só de código: **confirmar a
branch atual** (`git branch --show-current` → `feat/126-empty-state-unico`) antes
de qualquer `git commit`, como manda o `AGENTS.md`, e só então rodar a suíte
completa. Apagar um partial direto na `main` é o tipo de erro que a suíte verde
não pega.
A varredura foi feita com `rg` no repositório inteiro, não só em `apps/`, em
chamada direta e sem pipe, redirecionamento ou truncamento (`AGENTS.md`): fora
dos 4 `{% include %}`, as únicas menções vivem em planos antigos
(`71-empty-state-component.md`, `81-icon-system.md`, `audit-design-system.md`),
que são registro histórico e não são editados.
Ícone sem chamador é convite a voltar a usar o ícone errado.

### D-7 — copy uniforme

O padrão majoritário (9 dos 11 chamadores) já é: **título sem ponto final,
descrição frase completa com ponto, ícone sempre presente**. As duas exceções
estão em `lista_materiais.html`:

| Linha | Hoje | Passa a ser |
|---|---|---|
| 84 | `titulo='Nenhum material cadastrado no estoque.'`, sem ícone, sem descrição | título sem ponto + `icone` + `descricao` com a próxima ação |
| 81 | `titulo=titulo_busca`, sem ícone, sem descrição | ganha `icone` + `descricao` (o CTA sozinho não diz o que aconteceu) |

Ícone das duas: `_caixa_entrada` no catálogo vazio, `_funil` na busca sem
resultado — mesma semântica das listagens filtradas.

### D-8 — guarda contra clone

Varre `apps/**/*.html` procurando a assinatura do estado vazio fora de
`components/empty_state.html`. Segue a anatomia já usada por
`test_nenhum_controle_abaixo_do_piso_de_44px`: varredura real **mais** uma classe
de casos sintéticos que prova que a varredura detecta.

**A busca é por conjunto de tokens, não por substring.** Procurar a sequência
literal `border-dashed border-border-strong` é guarda contornável por
formatação: trocar a ordem das classes, quebrar a linha entre elas ou intercalar
uma terceira classe já escapa — e nenhuma dessas três coisas muda um pixel do
render. A guarda usa os helpers de `apps/core/tests/marcacao.py` (`elementos`,
`classes`), que já normalizam atributo em conjunto de tokens, e casa quando
`{'border-dashed', 'border-border-strong'}` é subconjunto das classes do
elemento — em qualquer ordem, com qualquer quebra de linha.

Casos sintéticos: marcação clonada casa; **clone com as classes reordenadas
casa**; **clone com quebra de linha no meio do atributo casa**; o dropzone
(`border-2 border-dashed border-border`, sem `-strong`) não casa; marcação dentro
de `{% comment %}` não casa.

### D-9 — guarda de copy

Varre os `{% include %}` de `components/empty_state.html` em `apps/**/*.html`,
**parseia os argumentos** do include em pares `chave=valor` (mesma forma do
`pares()` de `marcacao.py`) e exige de cada chamada:

- `icone` presente **e com valor não vazio** — `icone=''` e `icone=""` são
  reprovados junto com a ausência. Chave presente não é contrato cumprido.
- `descricao` presente e com valor não vazio, pelo mesmo motivo.
- `titulo` sem ponto final.

**Título dinâmico não é ponto cego.** `titulo=titulo_busca` (`lista_materiais.html`)
não pode ser lido no template, mas a variável é montada duas linhas acima, num
`{% with %}` do mesmo arquivo. A guarda resolve `{% with nome=... %}` no escopo
do próprio arquivo antes de desistir: só cai para "não verificável" quando o
valor vem de contexto de view, e nesse caso registra o ponto de chamada numa
lista nomeada em vez de silenciosamente pular. Uma isenção que ninguém consegue
contar vira rota de fuga.

Casos sintéticos: falta de ícone reprova; `icone=''` reprova; falta de descrição
reprova; `descricao=""` reprova; título literal com ponto reprova; título vindo
de `{% with %}` com ponto **reprova**; título vindo de variável de view entra na
lista de não-verificáveis e não some.

**O conflito com o contrato do componente, resolvido explicitamente.** Hoje o
docstring do `empty_state.html` chama `icone` e `descricao` de opcionais, e os
dois são renderizados dentro de `{% if %}`. D-9 exige os dois de todo chamador.
As duas coisas parecem se contradizer; a resolução é que elas vivem em níveis
diferentes, e o plano nomeia isso em vez de deixar o leitor deduzir:

- **No componente, seguem opcionais — e o `{% if %}` fica.** Django não tem
  parâmetro obrigatório em `{% include %}`: omitir `descricao` não levanta erro,
  renderiza vazio. Um componente que assume presença produziria `<p>` órfão em
  vez de falhar. Além disso os testes de componente renderizam o mínimo de
  propósito (`render_to_string` com só `titulo`), para provar que o ramo
  condicional existe.
- **No chamador de tela, são obrigatórios — e a guarda é o único lugar onde essa
  obrigatoriedade pode morar.** Não existindo mecanismo de template, o mecanismo
  é o teste. Por isso D-9 varre `apps/**/*.html` (telas) e **não** alcança
  `render_to_string` de teste nem exemplo de documentação.

O docstring passa a dizer exatamente isso, com as duas metades: "opcional para o
componente, obrigatório para chamador de tela (guardado por
`test_todo_chamador_do_estado_vazio_segue_a_copy`)". Descrever como "opcional" e
puni-lo num teste é a armadilha que esta issue veio fechar, não abrir.

Piso de varredura (`assert quantidade >= 11`) pelo mesmo motivo do guarda de
44px: um guarda que não enxerga nada passa verde.

**O exemplo de `docs/design-system.md:514` vira mentira com esta guarda.** Ele
mostra `{% include "components/empty_state.html" with titulo="Nada por aqui" %}`
— sem ícone, sem descrição, e com um título que a guarda recusaria num template.
O exemplo é atualizado no mesmo commit. A guarda varre só `apps/**/*.html`, então
o doc não a quebraria; quebraria quem copiasse o doc.

## Estratégia de testes

Camada de componente (`apps/core/tests/test_components.py`, `render_to_string`,
sem DB) para o contrato do componente; camada de view para o que só existe
renderizado por uma tela real.

| Teste | O que trava |
|---|---|
| `test_titulo_usa_h2_por_padrao` | Default de `nivel_titulo`; hoje é implícito |
| `test_nivel_titulo_parametriza_a_tag_de_abertura_e_de_fechamento` | `nivel_titulo=3` → `<h3>…</h3>`; um fechamento errado quebraria o outline em silêncio |
| `test_descricao_respeita_a_medida_de_prosa` | `max-w-prose` na descrição |
| `test_descricao_centralizada_nao_encosta_na_esquerda` | `mx-auto` junto do `max-w-prose` |
| `test_medida_de_prosa_esta_compilada_no_app_css` | O passo de build: o seletor da classe existe em `app.css` **e** declara `max-width` em `ch` dentro de 65–75 |
| `test_nenhum_template_replica_a_marcacao_do_estado_vazio` | D-8, varredura real |
| `TestMecanismoDaGuardaDeClone` (sintéticos) | A guarda D-8 detecta clone, ignora dropzone e ignora `{% comment %}` |
| `test_todo_chamador_do_estado_vazio_segue_a_copy` | D-9, varredura real + piso de 11 |
| `TestMecanismoDaGuardaDeCopy` (sintéticos) | A guarda D-9 detecta falta de ícone, falta de descrição e título com ponto |
| `test_preview_sem_linhas_usa_o_componente_de_estado_vazio` (estoque) | D-1: componente presente, `text-text-disabled` ausente na caixa |
| `test_resultados_de_movimentacoes_nao_e_live_region` (estoque, reescreve o 2089) | Wrapper sem `aria-live`/`aria-atomic` |
| `test_movimentacoes_anuncia_contagem_em_swap_htmx` (estoque) | `#resumo-movimentacoes` existe vazio no GET full-page e chega preenchido no `hx-swap-oob` |
| `test_regiao_de_resumo_e_live_region_de_verdade` (estoque) | `role="status"` e `sr-only` no elemento, no GET **e** na resposta HTMX — um `<p>` sem `role` troca de texto sem anunciar nada e passaria em todos os testes de mensagem |
| `test_filtro_sem_resultado_anuncia_zero_movimentacoes` (estoque) | O caso da issue: filtro que zera a lista **anuncia** |
| `test_anuncio_no_singular_com_uma_movimentacao` (estoque) | "1 movimentação encontrada" — o caso que um teste só de zero deixa passar |
| `test_anuncio_no_plural_com_duas_movimentacoes` (estoque) | "2 movimentações encontradas": os dois `pluralize` flexionando juntos |

Os três testes de mensagem casam a frase **exata e inteira**, ponto final
incluído, e não só a contagem: `'2 movimentações encontradas.'`. Substring de
número passaria por cima de qualquer erro de concordância — que é justamente o
que se está travando.
| `test_nenhum_material_cadastrado_exibe_empty_state_dashed` (estoque, atualizado) | Título sem ponto + ícone + descrição |
| `test_vazio_contextual_usa_icone_de_filtro` (requisições) | D-5 nas duas telas filtradas |

**Caminho de permissão negada / violação de domínio / erro de contrato:** N/A —
nenhuma view, service ou policy muda. Os testes de permissão existentes das duas
listagens (`test_*_sem_permissao_*`) continuam cobrindo o acesso sem alteração e
devem seguir verdes.

## Invariantes

- **Regra sem mecanismo vira sugestão** (`docs/design-system.md`): D-1, D-5, D-6
  e D-7 são correções pontuais; D-8 e D-9 são o mecanismo que impede a
  reincidência. Nenhuma correção desta issue entra sem guarda.
- **Live region NÃO é o mecanismo depois de POST full-page** (checklist de
  acessibilidade): por isso `lista_materiais.html` e o preview SCPI não ganham
  live region nenhuma. O preview já resolveu o anúncio dele com foco programático
  na barra de resumo (#123).
- **`aria-live` só onde há mudança sem navegação**: sobra exatamente uma live
  region por listagem filtrada, e ela carrega contagem, não conteúdo.
- **Token, nunca shade**: nenhuma cor crua entra; o guarda de
  `test_tokens_semanticos.py` continua exato.
- **Contrato do componente é de dois níveis, e ambos ficam escritos**: opcional
  para o componente (Django não impõe parâmetro em `{% include %}`), obrigatório
  para chamador de tela (a guarda D-9 é o mecanismo). Nenhum dos dois lados é
  deixado implícito.
- **Componente global não conhece enum de domínio**: `titulo`, `descricao`,
  `icone` e `nivel_titulo` chegam resolvidos pelo chamador. `nivel_titulo` é
  número, não regra de tela.
- **`preview_importacao_scpi.html`**: `test_preview_nao_declara_live_region_inerte`
  exige `aria-live=` exatamente 1 vez na resposta. D-1 não adiciona nenhum.
- **Contagem de `role="alert"`/`role="status"` de `_messages.html`**
  (`apps/requisicoes/tests/test_views.py:2713`) não é afetada: as live regions
  desta issue vivem nos templates de listagem, não no partial de flash.

## Riscos

| Risco | Mitigação |
|---|---|
| `max-w-prose` não está compilado no `app.css` versionado | `make css-build` obrigatório antes do PR; sem isso a classe é inerte em produção e o teste de componente (que lê o HTML, não o CSS) passaria verde por cima |
| Tirar `aria-live` do wrapper de movimentações **reduz** acessibilidade se o oob falhar | O teste do swap HTMX cobre os dois lados: região presente no GET e preenchida na resposta HTMX, inclusive no zero |
| `<h{{ nivel_titulo }}>` com valor inesperado gera tag inválida | Só chamadores internos passam o parâmetro; a guarda D-9 pode ser estendida se algum dia um valor vier de contexto de domínio |
| Apagar `_seta_circular.html` quebra um chamador não visto | `rg _seta_circular` no repositório inteiro já confirmou exatamente 4 chamadores, todos migrados nesta issue; a suíte roda antes do commit que apaga, e a branch é confirmada antes dele |
| Reescrever `test_aria_live_polite_no_conteiner_de_resultados` parece "afrouxar" um teste | O teste novo é mais estrito, não menos: exige ausência no wrapper **e** presença da região de contagem **e** o anúncio no zero |
| Anúncio dizer o tamanho da página em vez do total do filtro | `n` é `page_obj.paginator.count`, declarado em D-4 e travado pelo teste que casa a frase inteira com a contagem esperada |
| Concorrência, contrato OpenAPI, mutação de estoque, máquina de estados | N/A — nenhuma linha de Python de domínio é tocada |
