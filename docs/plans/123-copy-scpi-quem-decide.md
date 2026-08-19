# Plano — Issue #123: copy da importação SCPI nomeia quem decide sobre a divergência

O `PRODUCT.md` declara que a divergência entre WMS e SCPI é **estado normal e
esperado**, não erro, e que o ajuste é "manual posterior no SCPI". A decisão do
dono do produto (2026-08-18) fechou a lacuna que faltava: **quem decide é o
chefe de almoxarifado**. Nada disso chega ao usuário hoje — o alerta informa só
o efeito técnico ("saldo do WMS não será alterado") e cala sobre dono e próxima
ação.

O token não muda: `warning` continua correto, porque o `DESIGN.md` define âmbar
como *"a decisão está com alguém"* e agora esse alguém tem nome. O que muda é a
copy, mais dois defeitos adjacentes nas mesmas linhas.

## Escopo

### O que muda

1. **Copy de `_alert_divergencias_corpo.html`** — nomeia a divergência como
   sendo entre o saldo do WMS e a quantidade informada no arquivo do SCPI,
   afirma que é estado esperado da coexistência (não falha da importação),
   mantém a garantia de que o saldo do WMS não muda, e diz a próxima ação com
   dono: o chefe de almoxarifado confere e ajusta no SCPI.
2. **Copy de `_alert_novos_materiais_corpo.html`** — passa a dizer o que o
   material novo herda do SCPI e o que fica pendente de conferência humana.
3. **Corpo em 14px** — os dois corpos trocam `text-xs` (12px) por `text-sm`.
4. **Os três `aria_live` inertes saem** e são substituídos por mecanismos que de
   fato anunciam depois de um POST full-page.
5. **A decisão vira documentação** em `docs/processos-almoxarifado.md` e a
   armadilha da live region inerte entra no checklist de
   `docs/design-system.md`.

### O que NÃO muda

- `variant="warning"` no include de `_alert_divergencias_corpo.html` em
  `preview_importacao_scpi.html`.
- `role="status"` explícito desse mesmo include, nem o comentário que o
  justifica.
- `variant="info"` do alerta de materiais novos.
- A barra de estatísticas, a legenda, os cartões de linha, o delta por linha e o
  modal de confirmação — exceto pelo atributo de foco descrito abaixo.
- Qualquer service, selector, policy, model ou migration. Esta issue não toca
  camada de domínio.
- `alert.html`. O componente global não ganha parâmetro novo; a issue #127
  ainda vai destrinchá-lo e ampliar sua superfície aqui seria trabalhar contra
  ela.

## Decisões

### D-1 — Copy de divergências

Direção (texto final ajustado ao glossário do `CONTEXT.md`, que define
"Divergência SCPI" como a diferença entre a quantidade do arquivo SCPI e o saldo
do WMS para o mesmo `CADPRO`):

> **N** divergências entre o saldo do WMS e a quantidade informada no arquivo do
> SCPI. Divergência é estado esperado da coexistência entre os dois sistemas, não
> falha da importação — o saldo do WMS não será alterado. Cabe ao chefe de
> almoxarifado conferir cada divergência e ajustar no SCPI.

Três coisas que quem lê passa a entender sem perguntar a ninguém: que aquilo é
esperado, que nada foi corrompido, e o que precisa acontecer a seguir. Nenhum
termo de implementação — `saldo_fisico`, `CADPRO`, "alerta registrado" saem;
"saldo do WMS", "SCPI", "divergência" e "chefe de almoxarifado" são todos do
glossário.

### D-2 — Copy de materiais novos

A issue pede para revisar "no mesmo passe" se este alerta também deve dizer quem
confere. **Sim, deve** — e o motivo é verificável em
`confirmar_importacao_scpi` (`apps/estoque/services.py:713`): o material novo
nasce com `nome` vindo da denominação do SCPI e com
`unidade=UnidadeMedida.UNIDADE` fixa, porque o CSV do SCPI não informa unidade. Ou seja, existe conferência humana pendente de fato,
não uma suposição de processo.

Direção:

> **N** materiais novos serão criados com a denominação e o saldo inicial do
> SCPI. A unidade entra como "unidade" porque o SCPI não a informa — cabe ao
> chefe de almoxarifado conferir no catálogo depois da importação.

Esta é a única extrapolação de julgamento do plano: a decisão do dono do produto
nomeou o chefe de almoxarifado para a divergência, e este plano estende o mesmo
dono para a conferência do catálogo, por ser a mesma pessoa que responde pelo
almoxarifado. Se a revisão discordar, a segunda frase sai e o alerta volta a ser
puramente informativo — a mudança de `text-xs` para `text-sm` e a remoção do
`aria_live` seguem válidas de qualquer forma.

### D-3 — `text-xs` → `text-sm`

`DESIGN.md:266` (Regra dos 14px) reserva 12px a rótulo estrutural em caixa alta.
Os dois corpos carregam o número que sustenta a decisão do chefe de almoxarifado,
renderizado hoje no tamanho de metadado. Passam a `text-sm`.

### D-4 — Os `aria_live` inertes

Live region só dispara com **mudança**; conteúdo já presente no carregamento não
é anunciado — é o que `components/error_summary.html:10-11` já documenta. As
três passagens de `aria_live` para `alert.html` (`preview_importacao_scpi.html`
linhas 93, 266 e 270 **antes** desta mudança; os números da tabela abaixo também
são os de hoje e mudam com o diff) não anunciam nada hoje. Saem todas, e cada ramo ganha o
mecanismo que funciona depois de um POST full-page:

| Ramo | Hoje | Depois |
|---|---|---|
| Erro de arquivo (`:93`) | `aria_live="assertive"` inerte; o input de retry já tem `autofocus` e `aria-invalid` | O alerta ganha `id="erro-arquivo-alerta"` e o input de retry ganha `aria-describedby="erro-arquivo-alerta"`. O foco automático passa a anunciar rótulo + inválido + o texto do erro. É o padrão que o próprio checklist de `docs/design-system.md` cobra: "campo com erro usa `aria-invalid` + `aria-describedby`" |
| Alerta de materiais novos (`:266`) | `aria_live="polite"` inerte | Sem `aria_live`. O `role="status"` automático da variante `info` permanece |
| Alerta de divergências (`:270`) | `aria_live="polite"` inerte | Sem `aria_live`. `role="status"` explícito permanece, com o comentário |
| Barra de resumo (`:131-136`) | `role="status"` + `aria-live="polite"`, sem foco | Ganha `tabindex="-1"` e `x-init="$el.focus()"`: vira o alvo de foco programático no retorno do upload, que é o mecanismo que de fato anuncia após um POST. É o padrão GOV.UK já usado em `error_summary.html` |
| Bloco de CTA que embrulha os dois alertas | sem `id` | Ganha `id="alertas-importacao"`, e o botão "Confirmar importação" ganha `aria_describedby="alertas-importacao"` |

**Por que a barra de resumo não basta sozinha.** Ela anuncia contagens — "3
divergências" — e não a responsabilidade nem a próxima ação, que é justamente o
que esta issue existe para dizer. E os dois alertas não estão na ordem de
tabulação: quem navega por teclado vai da barra de resumo direto ao botão
"Confirmar importação" sem nunca passar por eles. Por isso o bloco de CTA que já
embrulha os dois alertas ganha `id="alertas-importacao"` e o botão de confirmar
os referencia por `aria_describedby` — parâmetro que `button.html` já expõe, sem
mudança no componente. Focar o botão passa a anunciar quem decide e o que fazer
a seguir, no exato momento em que a decisão de gravar é tomada.

O `id` fica no **wrapper**, não em cada alerta, porque o wrapper existe sempre e
os alertas são condicionais (`novos > 0`, `divergencias > 0`). Sem divergência
nem material novo o wrapper renderiza vazio e o `aria-describedby` simplesmente
não anuncia nada — em vez de apontar para um `id` inexistente.

O anel de foco da barra de resumo usa `focus:`, **não** `focus-visible:` —
`focus-visible` não casa em foco programático que não veio do teclado, armadilha
já registrada no audit da Etapa 2.

O `role="status"` e o `aria-live="polite"` próprios da barra de resumo ficam como
estão: não são passados a `alert.html`, não estão nos critérios de aceite da
issue, e `role="status"` continua sendo a semântica correta para um resumo. O que
muda ali é só ganhar foco.

### D-5 — Onde a decisão fica registrada

Dois lugares, cada um com o pedaço que lhe cabe:

- **`docs/processos-almoxarifado.md`** — nova seção `1.5 Importação SCPI e
  divergência`, com a regra de domínio: importação nunca sobrescreve saldo, a
  divergência é estado esperado da coexistência, e a decisão de ajuste é do chefe
  de almoxarifado, executada no SCPI. É a substância da decisão e ela é de
  domínio, não de design.
- **`docs/design-system.md`** — uma linha no checklist de acessibilidade: live
  region não anuncia conteúdo presente no carregamento; depois de um POST
  full-page o mecanismo é foco programático. A armadilha já custou tempo três
  vezes neste conjunto de arquivos.

## Arquivos tocados

| Arquivo | Mudança |
|---|---|
| `apps/estoque/templates/estoque/partials/_alert_divergencias_corpo.html` | Copy nova (D-1); `text-xs` → `text-sm` |
| `apps/estoque/templates/estoque/partials/_alert_novos_materiais_corpo.html` | Copy nova (D-2); `text-xs` → `text-sm` |
| `apps/estoque/templates/estoque/preview_importacao_scpi.html` | Remove os 3 `aria_live`; `id` no alerta de erro; `aria-describedby` no input de retry; `tabindex="-1"` + `x-init` + anel `focus:` na barra de resumo; `id="alertas-importacao"` no bloco de CTA e `aria_describedby` no botão de confirmar |
| `apps/estoque/tests/test_partials.py` | Testes de copy e de tamanho de corpo dos dois partials, sem DB |
| `apps/estoque/tests/test_views.py` | Atualiza `test_post_csv_com_novos_e_divergencias_usa_components_alert_com_aria`; novos testes de foco programático e de `aria-describedby` |
| `docs/processos-almoxarifado.md` | Seção 1.5 |
| `docs/design-system.md` | Uma linha no checklist de acessibilidade |

## Estratégia de testes

Cada critério de aceite fecha com um teste, porque *regra sem mecanismo vira
sugestão* — e neste conjunto de arquivos isso já aconteceu três vezes.

### Em `apps/estoque/tests/test_partials.py` (sem DB, `render_to_string`)

| Teste | O que trava |
|---|---|
| `test_alerta_de_divergencia_nomeia_o_chefe_de_almoxarifado` | A copy nomeia o dono da decisão |
| `test_alerta_de_divergencia_diz_a_proxima_acao_no_scpi` | A copy diz conferir e ajustar no SCPI |
| `test_alerta_de_divergencia_afirma_que_o_saldo_do_wms_nao_muda` | A garantia que já existia não se perde na reescrita |
| `test_alerta_de_divergencia_enquadra_divergencia_como_esperada` | A copy não deixa a divergência parecer erro do sistema |
| `test_corpos_de_alerta_do_preview_usam_corpo_de_14px` | Parametrizado nos dois partials: `text-sm` presente, `text-xs` ausente |
| `test_alerta_de_materiais_novos_diz_quem_confere_o_catalogo` | D-2 |
| `test_corpos_de_alerta_flexionam_singular_e_plural` | A reescrita preserva o `pluralize` de hoje nos dois corpos (regressão do `test_post_csv_com_dois_novos_flexiona_plural_corretamente`, agora no nível do partial) |

### Em `apps/estoque/tests/test_views.py`

| Teste | O que trava |
|---|---|
| `test_alerta_de_divergencia_mantem_variante_warning_e_role_status` | O token e o `role` que a issue manda **não** mudar. Sem este teste nada impede uma passagem futura de "corrigir" o âmbar |
| `test_preview_nao_declara_live_region_inerte` (renomeia o teste `..._usa_components_alert_com_aria`) | `aria-live` aparece exatamente uma vez na resposta — só a barra de resumo. Antes eram 3 |
| `test_resumo_do_preview_recebe_foco_no_retorno_do_upload` | `tabindex="-1"` + `x-init="$el.focus()"` na barra de resumo |
| `test_erro_de_arquivo_amarra_a_mensagem_ao_campo_de_retry` | `id` no alerta e `aria-describedby` correspondente no input; `aria-live="assertive"` ausente |
| `test_botao_de_confirmar_e_descrito_pelos_alertas_da_importacao` | `id="alertas-importacao"` no wrapper e `aria-describedby="alertas-importacao"` no botão de confirmar — trava o caminho pelo qual quem usa teclado ouve quem decide antes de gravar |

O teste existente `test_post_csv_com_dois_novos_flexiona_plural_corretamente`
depende da string `'serão criados'`, que a copy de D-2 preserva — sem alteração
necessária. `test_modal_de_confirmacao_recapitula_os_numeros_a_gravar` depende de
`'Nenhum saldo do WMS é sobrescrito'`, que vive no
`_modal_corpo_confirmar_importacao.html` e não é tocado.

### Verificação de suíte

Validação a executar **depois** da implementação — nada aqui é resultado já
obtido:

```
uv run pytest -q -ra --tb=short --strict-markers --disable-warnings -n logical
uv run ruff check .
uv run ruff format --check .
uv run mypy apps
```

Baseline observada na branch `main`, antes desta branch e antes de qualquer
alteração: **1842 passed**. O critério é a suíte terminar verde com contagem
igual ou maior que essa.

## Invariantes

| Invariante | Situação |
|---|---|
| **LED-01** (`docs/matriz-invariantes.md`) — o bootstrap do SCPI fica fora do ledger nesta fase | Inalterado. Esta issue não toca service nem saldo |
| **EST-07** — divergência crítica é estado de domínio válido, não erro | Reforçado: a copy passa a dizer isso ao usuário em vez de deixá-lo deduzir de um âmbar mudo |
| `CONTEXT.md` — "Divergência SCPI gera alerta; nunca altera `saldo_fisico`" | Preservado e agora explícito na tela |
| `PRODUCT.md` — importação SCPI nunca sobrescreve saldo; divergência é estado normal | Preservado; a copy passa a carregá-lo |
| Regra dos 14px (`DESIGN.md:266`) | De violada para respeitada nos dois corpos |
| Piso de 44px | Não se aplica: nenhum controle acionável novo. A barra de resumo recebe `tabindex="-1"`, que a torna alvo de foco programático, **não** um controle na ordem de tabulação |

## Divergências com a revisão do plano

Duas sugestões da revisão automatizada foram verificadas contra o código e a
documentação vivos e **não** foram adotadas. Ficam registradas aqui para que a
decisão não precise ser refeita.

### `role="alert"` no alerta de divergência — recusado

A sugestão cita `docs/CONVENTIONS.md` §Níveis e ARIA, onde `warning` → `alert`.
Essa tabela vive dentro de `## Mensagens ao usuário` e governa o contrato de
**flash messages** do Django — os mesmos níveis que trazem auto-dismiss de 8s,
botão de dismiss e o mapeamento `EstadoInvalido → messages.warning`. Ela é
renderizada por `core/partials/_messages.html`.

O próprio cabeçalho de `components/alert.html` diz isso literalmente: *"Fora do
contrato de dismiss de `docs/CONVENTIONS.md` (§Níveis e ARIA) — essa regra
governa o contrato de flash messages Django, renderizado por
`core/partials/_messages.html`, que não usa este componente."*

Somam-se duas razões independentes:

- O `role="status"` explícito é **critério de aceite da issue #123**, com a
  justificativa registrada: divergência no preview pede leitura, não interrupção
  assertiva. Rebaixar isso aqui reabriria uma decisão do dono do produto.
- O override foi introduzido deliberadamente pela issue #95
  (`docs/plans/95-migrar-banners-alert.md`), justamente para não regredir a
  assertividade do anúncio na migração para `alert.html`.

### Restringir "nunca sobrescreve saldo" ao preview — recusado

A sugestão pede que a garantia valha só no preview. Ela vale também na
confirmação: `confirmar_importacao_scpi` só escreve `SaldoEstoque` para linhas
com `status == 'novo'`; nenhuma linha divergente tem saldo tocado. O `PRODUCT.md`
afirma a regra sem recorte — *"a importação SCPI nunca sobrescreve saldo"* — e o
`CONTEXT.md` repete: *"Divergência SCPI gera alerta; nunca altera
`saldo_fisico`"*. Estreitar a frase para o preview enfraqueceria uma garantia
verdadeira e mais forte, e é exatamente a garantia que acalma quem lê o alerta.

A primeira metade da mesma sugestão **foi** adotada: a copy passa a dizer
"quantidade informada no arquivo do SCPI" em vez de "saldo do SCPI", preservando
o WMS como fonte única do saldo.

## Riscos

1. **Alerta mais longo empurra o CTA.** A copy cresce de uma linha para três
   nos dois alertas, e eles ficam logo acima do botão de confirmar. Abaixo de
   `sm` o botão já vive numa barra fixa no rodapé, então o CTA não sai da tela;
   acima de `sm` o deslocamento é de poucas dezenas de px. Aceito: o alerta só
   aparece quando a contagem é maior que zero, e é exatamente nesse caso que o
   texto precisa ser lido antes do botão.
2. **Foco programático rouba a posição de rolagem.** Ao voltar do upload, o foco
   vai para a barra de resumo, no topo do resultado — que é onde o usuário quer
   estar. O risco real seria o inverso: focar algo no meio da lista. Não é o
   caso.
3. **`x-init` depende do Alpine.** Se o Alpine falhar em carregar, o foco não
   acontece e a tela degrada para o comportamento de hoje — sem anúncio, mas sem
   quebra. Mesmo perfil de risco de `error_summary.html`, que já usa a mesma
   técnica em produção.
4. **D-2 é julgamento, não decisão registrada.** Marcado explicitamente acima
   para que a revisão possa recusá-lo sem derrubar o resto do trabalho.
5. **Sem risco de concorrência, contrato de API ou mutação de estoque.** O
   escopo é template, teste e documentação.
