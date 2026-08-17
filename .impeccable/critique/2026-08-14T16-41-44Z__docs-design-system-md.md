---
target: design system (input.css + docs/design-system.md)
total_score: 26
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 4
timestamp: 2026-08-14T16-41-44Z
slug: docs-design-system-md
---
## Nota de saúde de design

| # | Heurística | Nota | Achado-chave |
|---|---|---|---|
| 1 | Visibilidade do status | 3 | `hx-indicator` aparece **1 vez** no repositório inteiro; filtrar e ordenar disparam HTMX sem sinal nenhum |
| 2 | Correspondência com o mundo real | 4 | Vocabulário travado na IA ("nunca pedido", "nunca pendente"); `cancelamento` ≠ `descarte` com copy distinta; "Divergência (SCPI ≠ WMS)" tratada como estado, não erro |
| 3 | Controle e liberdade | 3 | Escape em modal e menu, back-arrow contextual, `?next=`; falta caminho de "enviar para autorização" a partir do modo editar |
| 4 | Consistência e padrões | 2 | **Quatro** implementações divergentes de botão primário e **quatro** de campo, incluindo `focus-visible:ring-text-disabled` que existe em 1 lugar no mundo |
| 5 | Prevenção de erro | 2 | Importação SCPI grava sem modal de confirmação — única escrita irreversível sem porta |
| 6 | Reconhecimento vs. memória | 3 | Fila de autorização mostra *quantos* itens, não *quais*; o chefe decide sem ver o que autoriza |
| 7 | Flexibilidade e eficiência | 1 | Zero atalhos, zero ação em lote, zero filtro salvo. Um único `keydown` no repositório, e é fechar o menu |
| 8 | Estético e minimalista | 3 | Restrição real e disciplinada; quebra na tela de preview SCPI e na grade de decisão de 3 cartões de peso idêntico |
| 9 | Recuperação de erro | 3 | `error_summary.html` é padrão GOV.UK legítimo; mas o textarea do estorno é hand-rolled sem `aria-invalid` |
| 10 | Ajuda e documentação | 2 | `docs/design-system.md` está factualmente errado nos pontos em que alguém confiaria nele |
| **Total** | | **26/40** | **Aceitável — melhorias significativas necessárias** |

## Veredito de especificidade

**Parcialmente ancorado. As regras são deste produto; a superfície não é.**

O que nenhum outro produto poderia copiar sem quebrar: a Regra da Reversão Não é Erro (teal para devolução, porque devolver material é o processo funcionando); o piso de 44px derivado da cena e não da checklist; a barra de ação fixa em `z-10` **abaixo** do popover, escala invertida em relação ao instinto porque no celular o dropdown do autocomplete ficava coberto; e `atender_retirada.html` inteiro, com ações fixas no rodapé porque a separação acontece em pé com o material nas mãos. Isso é design de produto: o layout mudou por causa de onde o corpo do usuário está.

O que é intercambiável: quase tudo o que se vê. Blue-600 sobre slate-50, cartões `rounded-xl border shadow-sm`, badges pill, sidebar de 240px, top bar MD2. Troque as strings PT-BR por inglês e é qualquer admin Tailwind de 2024.

**O achado mais incômodo:** a north star do DESIGN.md — "O Livro-Razão", *"linhas, colunas, carimbos de estado e uma trilha que ninguém apaga"* — **não sobreviveu à morte da tabela**. Colunas e linhas de pauta eram a encarnação literal da metáfora. Sem elas restou uma grade de cartões que não é livro-razão nem outra coisa; só o badge ainda funciona como carimbo. O documento mais autoral do repositório está descrevendo uma versão morta do sistema, o que é pior que ser genérico.

## Varredura determinística

**O detector mecânico não achou nada em markup.** `detect.mjs` sobre os 4 apps: `[]`, exit 0. Sanidade verificada com um HTML sintético que disparou corretamente — o silêncio é real.

Os 17 achados vieram só do CSS compilado, e se resolvem em uma origem única:

- **10× `design-system-color` + 2× `ai-color-palette`** — todos rastreiam para `badge.html:39,43,45,47`, as 4 variantes de catálogo em paleta crua (`orange`/`indigo`/`violet`/`yellow`). O rótulo "on heading" do detector é impreciso: são `<span>` de badge.
- **4× `design-system-font-size`** — dois fatos, contados duas vezes (fonte + minificado): `.app-bar__title` em `1rem` e `.app-bar__menu-heading` em `0.6875rem`, ambos fora da rampa do DESIGN.md.
- **1 falso positivo confirmado:** `gray-on-color` "text-slate-400 on bg-blue-600". Nenhuma das duas classes existe em template algum — o Tailwind v4 varre o repositório inteiro e emitiu utilities citadas em `.md` de documentação e em `test_views.py`. A regra pareou dois seletores que coexistem no bundle sem nunca coocorrerem num elemento.

**Medição de paleta crua:** 13 ocorrências em 2 arquivos de 79. `badge.html` (12) e `modal.html` (1, o backdrop). Os outros 77 templates são 100% token semântico. É disciplina rara.

**Browser (desktop 1280 + mobile 375, autenticado):** zero erro de JS, zero 404 de aplicação, `lang="pt-br"`, exatamente 1 `<h1>` por tela, zero `img` sem `alt`, zero `label` sem `for`, zero input ou botão sem nome acessível, e `scrollWidth == clientWidth == 375` nas quatro telas — **nenhum overflow horizontal**.

**`app.css` está sincronizado.** `npm run css:build` produziu zero bytes de diferença.

## Impressão geral

Este é um sistema construído por alguém que pensa. A ARIA é raciocinada e não copiada — `badge.html` **recusa** `role="status"` explicando que 20 linhas virariam 20 live regions; `rascunho_form.html` mantém a live region presente e vazia porque `display:none` a tira da árvore. Decisões que a maioria dos sistemas erra em silêncio.

E ao mesmo tempo o sistema não consegue concordar consigo mesmo sobre o que é um botão.

A maior oportunidade não é estética: é que **as regras boas deste sistema não têm mecanismo que as sustente.** A Regra do Token pegou (13 ocorrências cruas em 79 arquivos) porque a utility semântica é o caminho mais curto. A Regra do Raio Crescente, o piso de 44px e a promessa de 3:1 na borda não pegaram, porque escrever a classe errada custa igual. A diferença entre as duas situações é ergonomia, não disciplina.

## O que está funcionando

**1. A cena física governa estrutura, não só copy.** A barra fixa no rodapé de `atender_retirada.html` existe porque numa requisição de 15 itens o confirmar ficava depois de toda a lista, e o almoxarife está de pé. O `z-10` (e não `z-30`) veio de um bug real no celular.

**2. Estados vazios que distinguem causa.** "Nenhum resultado para este filtro / Ajuste ou limpe os filtros" ≠ "Ainda não há movimentações visíveis para o seu papel". Só o caso com próxima ação legítima recebe CTA. A borda tracejada é a única textura de contorno do sistema — assinatura visual real.

**3. Contraste de texto irrepreensível.** 17 pares texto/fundo medidos nos componentes, **nenhum abaixo de 4.5:1**. O pior é 6.69:1 (`danger-text` sobre `danger-muted`), o melhor 16.83:1. Ninguém raspou o mínimo.

## Problemas prioritários

### [P1] A promessa de 3:1 na borda é falsa por medição

**O que é.** O DESIGN.md declara que `border-strong` (slate-300) é *"reservada a borda de campo e de botão secundário, que precisam de 3:1"*. Medido: **`border-strong` sobre `surface` branco dá 1.48:1**. Sobre `bg-page`, 1.42:1. E os 15 pares de borda do sistema estão **todos** abaixo de 3:1 — o melhor é `primary-border`/`bg-page` a 1.90:1, o pior `success-border`/`success-muted` a 1.18:1.

**Por que importa.** A borda de um campo de texto é o que identifica o elemento como campo. WCAG 1.4.11 exige 3:1 para informação visual necessária a identificar componentes de interface. Num galpão com luz de teto e tela suja, um input delimitado a 1.48:1 desaparece. Pior que a falha: o sistema **acredita** que passa, e escreveu isso no documento — então ninguém vai medir de novo.

Atenuante honesto: em `badge.html` e `alert.html` a borda não é o único portador de informação (há texto e fundo), então lá é aceitável. O problema é onde a borda é a única pista: campo, botão secundário, cartão.

**Correção.** Introduzir `--color-border-control: var(--color-slate-400)` (~2.6:1) ou `slate-500` (3.8:1) para campo e botão secundário, mantendo `border-strong` como divisor decorativo. Depois corrigir a frase no DESIGN.md e no `design-system.md` — a afirmação de 3:1 não pode continuar escrita sem ser verdade.

**Comando:** `/impeccable harden`

---

### [P1] Existem quatro definições de botão e quatro de campo

**O que é.** `button.html` é canônico e é incluído por 20 templates. Mas reimplementam botão à mão: `_modal_body.html:47,57,65` (três botões, `font-semibold`, `shadow-sm`, `ring-offset-2`, e um `focus-visible:ring-text-disabled` que **existe em exatamente 1 lugar no repositório inteiro**), `filter_acoes.html:29`, `pagination.html:23,39`, `ordenacao_data.html:19`, `confirmar_importacao_scpi.html:14,33`, `lista_materiais.html:29`.

A prova mais nítida está em `lista_materiais.html:16-32`: um `{% include button.html %}` primário e um `<a>` hand-rolled secundário **lado a lado no mesmo `<form>`**, com raio, sombra e peso diferentes.

Para campo, a string `border-border-strong px-3 py-2` aparece 19 vezes em 7 arquivos, com o raio oscilando entre `rounded-lg` (forms.py, autocomplete) e `rounded-md` (os três `filter_*`, `_modal_form_estorno_saida`) — violando a Regra do Raio Crescente do próprio DESIGN.md.

**Por que importa.** Para o operador: "Aplicar filtros" e "Salvar rascunho" são objetos visualmente distintos fazendo a mesma classe de coisa. Para quem constrói: o rebrand prometido no `design-system.md` ("não alterar templates individuais") é falso — são 19 lugares.

**Correção.** (a) Migrar os oito botões hand-rolled para `button.html`; todos cabem nas variantes existentes. Onde não couberem (o `font-semibold` do confirmar de modal), **decidir de vez o peso do botão primário** — hoje `button.html` não declara peso nenhum, então renderiza em 400 enquanto os hand-rolled renderizam em 600. (b) Criar `@layer components { .campo { … } }` em `input.css` com a string canônica e trocar as 19 ocorrências; os widgets de `forms.py` passam a declarar `'class': 'campo'`, tirando apresentação do Python.

**Comando:** `/impeccable distill`

---

### [P1] `docs/design-system.md` ensina errado com autoridade

**O que é.** Verificado independentemente pelas duas avaliações. A doc descreve `card.html`, `form_errors.html`, `table_empty.html` e `dropdown.html` — **nenhum dos quatro existe**. O exemplo de `card.html` usa `{% block %}` dentro de `{% include %}` com `{% endinclude %}`, sintaxe que o Django não tem: quem copiar recebe `TemplateSyntaxError`. Diz "modal.html (adiar até uso real)" — o modal existe e é o componente-assinatura. Documenta `page_header.html` com `subtitle`/`actions`/`breadcrumb`; o arquivo aceita `titulo` e `class`. Diz `body: text-base` quando a Regra dos 14px fixa `0.875rem`. Diz `container: max-w-5xl` quando o real é 80rem. Diz que desabilitado é `bg-slate-200 text-slate-500` quando `button.html` usa `disabled:opacity-60`. E a seção de foco prescreve `ring-blue-500` — **cor crua de paleta, contradizendo a Regra do Token que a mesma doc estabelece 240 linhas antes**.

**Por que importa.** É falha de prevenção de erro aplicada ao segundo público. Quem construir a próxima tela seguindo a doc inclui componente inexistente, escreve `text-base`, usa `ring-blue-500` — e é reprovado no review por violar a regra que a doc lhe ensinou.

**Correção.** Cortar a seção "Inventário inicial" inteira. Ela é um plano de 2025, não um catálogo. Substituir por um índice de uma linha por componente, apontando para o arquivo — os blocos `{% comment %}` dos 22 componentes já são documentação melhor que a doc central. Corrigir tipografia, container, disabled e foco. E reconciliar `INFORMATION_ARCHITECTURE.md:87`, que afirma "Não há sidebar" (há, desde `base_auth.html:144`) e fixa "máximo 4 links por papel" quando a seção Almoxarifado tem 6.

**Comando:** `/impeccable document`

---

### [P1] A importação SCPI grava sem confirmação

**O que é.** Em `preview_importacao_scpi.html:271-281`, "Confirmar importação" é um submit direto — sem modal, sem recapitulação do que será gravado. (Precisão: o botão **usa** `button.html` e tem `data-prevent-double-submit` + `loading_label`; o que falta é a porta de confirmação, não o componente.) Ao lado, `:183` (`onchange="this.form.submit()"`) e o handler de drop descartam a pré-visualização atual sem perguntar. E o CTA fica **depois de todos os cartões de linha** — um CSV do SCPI com 800 materiais renderiza 800 `<article>`, sem paginação, entre a pessoa e o botão.

**Por que importa.** É a única escrita irreversível sem porta, num sistema que provou saber fazê-la: `atender_retirada.html` diz, antes de confirmar, *"baixa estoque das quantidades entregues e libera as reservas não entregues. Não pode ser desfeita."* O PRODUCT.md declara que este fluxo exige "confirmação explícita antes de gravar" e descreve estes usuários como *"gente que confia mais no papel do que no software"*. É exatamente a tela que não lhes dá um segundo de pausa.

**Correção.** (a) `data_modal_trigger` + `modal.html` com recapitulação gerada: "Serão criados N materiais novos e registradas M divergências. Nenhum saldo do WMS será sobrescrito." (b) Fixar a barra de CTA no rodapé em `z-10`, mesmo padrão de `atender_retirada.html`. (c) Ordenar o preview por divergências e novos primeiro — a pessoa está ali para ver o delta, não as linhas "OK". (d) Confirmar antes de substituir arquivo já pré-visualizado.

**Comando:** `/impeccable harden`

---

### [P2] Filtrar, ordenar e paginar a mesma lista usam três modelos de interação

**O que é.** Em `historico_requisicoes.html`: filtrar é swap HTMX, ordenar é swap HTMX, **paginar é navegação completa** — `pagination.html:23,39` são `<a href="?page=N">` puros. E nenhum dos três tem `hx-indicator`; a diretiva aparece **uma vez** em todo o repositório.

**Por que importa.** O usuário aprende que a lista se atualiza sozinha ao filtrar, clica em "Próxima", e a página inteira pisca com o foco voltando ao topo. Sem indicador, no 3G do galpão, filtrar parece um botão quebrado — e a pessoa clica de novo.

**Correção.** Dar a `pagination.html` os mesmos `hx-get`/`hx-target`/`hx-push-url` que `ordenacao_data.html` já tem, recebendo `target_id`. Adicionar um `hx-indicator` compartilhado numa barra fina sob o cabeçalho da lista — presente no DOM em opacidade 0, sem spinner central.

**Comando:** `/impeccable animate`

---

### [P2] Cinco controles abaixo do piso de 44px, concentrados no fluxo do almoxarife

**O que é.** Cruzando a varredura estática com a medição no browser a 375px, sobram cinco violações reais: `historico_importacoes_scpi.html:17` em `min-h-9` (36px); `confirmar_importacao_scpi.html:14,33` em `min-h-10` (40px); `lista_materiais.html:18,29` (busca e "Limpar") sem piso, ~38px; e os inputs de arquivo de `preview_importacao_scpi.html:67,108`. O brand `<a>` da app-bar mede 28px, mas é link para a home com destino redundante — P3.

`min-h-9` e `min-h-10` não são omissões. São alguém escolhendo conscientemente um número menor, o que significa que a regra não foi lida.

**Correção.** `min-h-11` nos cinco; adotar `filter_busca.html` em `lista_materiais.html` no lugar do formulário hand-rolled, o que resolve piso e raio de uma vez; e um teste de template que barre `min-h-9`/`min-h-10` em elemento clicável — a regra precisa de mecanismo, não de mais uma linha de doc.

**Comando:** `/impeccable adapt`

---

**Correção de rota:** as duas medições apontaram radios de 20px em `rascunho_form.html:113` e checkboxes de 20px em `filter_checkbox_group.html:19` como violações. **São falsos positivos** — verifiquei: ambos vivem dentro de `<label class="flex min-h-11 items-center">` com `for` correto, então o alvo clicável é a label de 44px, exatamente como o `design-system.md` prescreve. A medição de browser pegou o `<input>`, não o alvo real. Nada a corrigir ali.

## Red flags por persona

**Alex — chefe de setor limpando a fila de segunda-feira**
- `fila_autorizacao.html` não tem seleção múltipla nem ação em lote. 12 requisições = 12 ciclos fila → detalhe → modal → confirmar → voltar, com quatro carregamentos por requisição.
- `filter_busca.html:19` é um `type="search"` sem `hx-trigger="keyup changed delay:300ms"`, e nenhum `<select>` submete ao mudar. Todo filtro exige clique em "Aplicar".
- Na grade de decisão de `detalhe.html:257`, Autorizar, Retornar e Recusar são três cartões idênticos em estrutura e peso. Alex clica no errado uma vez e nunca mais confia na grade.

**Sam — leitor de tela e teclado**
- `_side_nav.html:18` é o único controle do sistema sem `focus-visible:ring` declarado. Sobrevive pelo outline nativo, mas fora da gramática de foco de todo o resto.
- `_modal_body.html:50` usa `focus-visible:ring-text-disabled` (slate-400) no cancelar — mais claro que o `border-focus` de todo o resto, e sobre `bg-surface` branco isso raspa o mínimo para indicador não-textual.
- `_modal_form_estorno_saida.html:11-18` é um textarea hand-rolled sem `aria-invalid`, sem `aria-describedby`, sem id de erro. É **a ação mais destrutiva do sistema com a pior fiação de erro** — em oposição a `form_field.html`, que faz tudo certo.
- Contrapeso justo: a árvore de acessibilidade renderizada é limpa — skip-link, landmarks marcados, combobox com listbox e status para o autocomplete, todo campo rotulado, um `<h1>` por tela.

**Vânia — auxiliar de almoxarifado, em pé no galpão** *(derivada do PRODUCT.md)*
- `atender_retirada.html` não oferece "entregar tudo o que foi autorizado". No caso mais comum — separação completa — Vânia digita 15 números que já estão na tela ao lado, um por um, em pé. Cada um é uma chance de errar o dígito, e cada erro é uma baixa errada num ledger append-only.
- O campo "Entregue" não vem pré-preenchido com o autorizado (`forms.py:264-285`, sem `initial`). O default correto seria o autorizado, com a alteração sendo o ato deliberado — que é justamente o caso que já exige justificativa.
- `preview_importacao_scpi.html` mistura linhas "OK" com divergências na ordem do arquivo. A tela que existe para evidenciar delta faz Vânia caçar 12 divergências entre 800 linhas iguais.
- `confirmar_importacao_scpi.html`, na tela de sucesso, oferece **um único botão: "Nova importação"**. Nada de "ver o que foi gravado", nada de "voltar ao catálogo". Vânia, que confia no papel, termina o ritual sem nada para conferir.

## Observações menores

- **Scaffolding morto da era da tabela.** `preview_importacao_scpi.html:208` tem `{# ── Desktop: tabela ── #}` seguido de nada; `lista_materiais.html:81` comenta `<tr>` e `<th>` inexistentes; `input.css:589` define `.scroll-shadow-x` "para tabelas com overflow-x" num sistema sem tabela.
- **Comentário mentiroso em `input.css:181`:** "Filosofia: surface dark (slate-900) com onSurface slate-50". A `.app-bar` usa `var(--color-primary)`, azul. Quem for mexer procura um slate-900 que não existe.
- **`preview_importacao_scpi.html:211` usa `space-y-3` em coluna única**, ignorando `table.html#cards_abertura`. É a única listagem em cartão que não segue a Regra do Cartão Único.
- **Duas encarnações da mesma navegação, dois vocabulários de seleção.** Sidebar ativa: `bg-bg-subtle`, ícone permanece `text-text-disabled`. Drawer ativo: fundo azul, texto azul, **ícone azul**. Mesma fonte de dados, dois estados ativos.
- **`badge.html:49`** — o fallback de variante desconhecida é o único badge com fundo saturado e texto branco, o que o faz parecer um estado de domínio legítimo e alarmante em vez de um bug de template.
- **`empty_state.html`** é chamado com ícone nas filas e sem ícone em `lista_materiais` e `historico_movimentacoes`. Estado vazio com e sem ilustração no mesmo produto.
- **`filter_select.html:27`** compara `selecionado == opcao.pk` — string de querystring contra int de PK. **Não verifiquei a view**; se a coerção não acontecer lá, o `selected` nunca aplica e o filtro de setor perde o valor ao repintar. Vale um teste.

## Perguntas a considerar

1. **A metáfora do livro-razão morreu com a tabela. Vocês vão enterrá-la ou reencarná-la?** Se o cartão é a renderização única, o que no cartão é "linha de pauta", "coluna" e "carimbo"? Hoje só o badge sobreviveu. Um DESIGN.md que descreve linhas e colunas num sistema sem nenhuma das duas é uma north star apontando para trás.

2. **Por que a fila mostra a *quantidade* de itens em vez dos itens?** O chefe está numa fila de decisão. Se três a cinco materiais coubessem no cartão, uma fração das autorizações seria decidida sem abrir o detalhe — e a fila deixaria de ser um índice para virar a tela de trabalho.

3. **O que aconteceria se "Entregue" já viesse preenchido com o autorizado?** O caso comum vira zero digitação; o excepcional vira alteração deliberada, que já é exatamente onde a justificativa é exigida.

4. **Se cor comunica só estado, o que comunica hierarquia de ação?** Na grade de decisão, Autorizar, Retornar e Recusar são igualmente grandes e coloridos. A cor está dizendo "estado", como manda a Regra do Sinal Único — mas então nada está dizendo "este é o caminho normal".

5. **Quantas pessoas vão escrever tela nova neste sistema?** Se for uma ou duas, `docs/design-system.md` está errado à toa e a correção mais barata é deletá-lo em favor dos comentários dos componentes, que são melhores. Se for mais, ele é o maior passivo do projeto — porque hoje ensina errado com autoridade.
