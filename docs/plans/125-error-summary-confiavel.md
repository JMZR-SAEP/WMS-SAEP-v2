# Plano — `error_summary` confiável, e adotado nas três telas de formset longo

Issue: [#125](https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/125) — Etapa 2 do
`docs/plans/audit-frontend-restante.md`. Desbloqueada: a
[#120](https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/120) fechou em 2026-08-19
(PR #11) e já entregou o piso de 44px e o raio das âncoras do mesmo arquivo.

Comando recomendado pela issue, executado na fase de implementação:

```bash
/impeccable harden apps/core/templates/components/error_summary.html apps/estoque/templates/estoque/nova_saida_excepcional.html apps/requisicoes/templates/requisicoes/rascunho_form.html apps/requisicoes/templates/requisicoes/atender_retirada.html
```

## Escopo

### O que muda

1. **Anel de foco visível no foco programático** — `error_summary.html` troca
   `focus-visible:` por `focus:` **no contêiner do sumário** (e só nele).
2. **Fallback sem Alpine** — o contêiner ganha `autofocus`, que é atributo global
   de HTML e funciona em elemento focável por `tabindex`. O `x-init="$el.focus()"`
   permanece como caminho HTMX (swap não reprocessa `autofocus`).
3. **Contagem por campo** — `coletar_erros` passa a emitir **um item por alvo**
   (campo), agregando as mensagens daquele campo numa string só. `erros|length`
   volta a ser "quantos lugares o usuário precisa visitar".
4. **Frase-líder parametrizável** — novo parâmetro `acao` (default `salvar`).
   `atender_retirada.html` passa `acao="registrar o atendimento"`.
5. **Cabeçalho no lugar de `<p>`** — o título do sumário vira `<h2>`, entrando no
   outline da página e na navegação por cabeçalhos.
6. **Adoção nas três telas de formset longo** —
   `nova_saida_excepcional.html` ganha o sumário; os dois alertas inline de
   `formset.non_form_errors` (em `nova_saida_excepcional.html` e em
   `rascunho_form.html`) saem, porque o sumário já os coleta.
7. **Documentação** — a regra "anel sempre `focus-visible`, nunca `focus`" de
   `docs/design-system.md` ganha a exceção já praticada: **alvo de foco
   programático não é controle**.

### O que NÃO muda

- As **âncoras** dos itens de erro continuam com `focus-visible:` — elas recebem
  foco por teclado, que é exatamente o caso que `:focus-visible` casa. Também não
  se toca no `block min-h-11 py-2.5 rounded-md` que a #120 fixou.
- O `role="alert"` + `tabindex="-1"` do contêiner: o padrão GOV.UK fica.
- A **borda** `border-danger-border-strong` das seções em erro fica. Ela é
  um marcador de localização, não repetição da mensagem — não é a duplicata que a
  issue pede para remover.
- O alerta de `erro_geral` no topo de `nova_saida_excepcional.html` fica: é erro
  de view (falha de serviço), não `non_form_errors` do formset.
- Nenhuma mudança de model, migration, service, policy ou selector. Zero schema.
- `empty_state.html`, `badge.html`, `alert.html` e `_messages.html` ficam fora —
  são as issues #126, #121, #127.

## Arquivos tocados

| Arquivo | Mudança |
|---|---|
| `apps/core/templates/components/error_summary.html` | `focus:` no contêiner, `autofocus`, `<h2>`, parâmetro `acao`, comentário de API atualizado |
| `apps/core/templatetags/core_tags.py` | `coletar_erros` agrega mensagens por alvo |
| `apps/estoque/templates/estoque/nova_saida_excepcional.html` | `{% coletar_erros %}` + include após o `csrf_token`; remove o alerta de `non_form_errors` |
| `apps/requisicoes/templates/requisicoes/rascunho_form.html` | remove o alerta de `non_form_errors` da seção Materiais |
| `apps/requisicoes/templates/requisicoes/atender_retirada.html` | passa `acao="registrar o atendimento"` |
| `apps/estoque/templates/estoque/partials/_alert_erros_formset.html` | removido (sem consumidor) |
| `apps/requisicoes/templates/requisicoes/partials/_alert_erros_formset.html` | removido (sem consumidor) |
| `apps/core/tests/test_components.py` | testes do componente + guard de duplicata nas três telas |
| `apps/core/tests/test_tokens_semanticos.py` | `focus:ring-danger-accent` entra em `UTILITIES_ESPERADAS` |
| `apps/requisicoes/tests/test_views.py` | agregação de `coletar_erros` (2 mensagens, ordem, `id` repetido) + POST inválido em `rascunho_form` e `atender_retirada` |
| `apps/estoque/tests/test_views.py` | POST inválido em `nova_saida_excepcional` |
| `apps/core/static/core/css/app.css` | regerado por `npm run css:build` (utility `focus:ring-danger-accent` é nova) |
| `docs/design-system.md` | exceção do anel de foco em alvo programático |

Nada em `apps/*/views.py`, `services.py`, `policies.py` ou `forms.py`.

## Decisões de desenho

### Por que `focus:` e não `focus-visible:` — e por que isso não afrouxa a regra

`docs/design-system.md` manda `focus-visible` em **todo controle**. O sumário não
é controle: é um alvo de foco programático, focado por `tabindex="-1"` depois de
um POST que o usuário disparou com o mouse ou com o dedo. Nesse caminho
`:focus-visible` não casa, e o usuário de teclado recebe o foco sem saber onde
ele foi parar. O precedente já existe e já está justificado no código:
a barra de estatísticas de
`apps/estoque/templates/estoque/preview_importacao_scpi.html` usa `focus:` pelo
mesmo motivo, e diz por quê no `{% comment %}` logo acima. O que falta é a regra do doc reconhecer a exceção — regra sem
exceção declarada vira regra que alguém "corrige" de volta.

### Por que `autofocus` como fallback, e não uma âncora no redirect

Um POST inválido **re-renderiza** o formulário; não há redirect e portanto não há
fragmento de URL para carregar `#sumario-erros`. O único mecanismo que leva o foco
ao sumário sem JavaScript é o atributo `autofocus`, que o HTML define como global
e aplicável a qualquer área focável — e `tabindex="-1"` torna a `<div>` focável.
Sem Alpine: HTML puro leva o foco. Com Alpine: o `x-init` refoca o mesmo elemento,
sem efeito visível. No swap HTMX o `autofocus` não é reprocessado, e é o `x-init`
que continua fazendo o trabalho — por isso os dois convivem em vez de um
substituir o outro.

### Por que agregar por campo em `coletar_erros`, e não contar diferente no template

Contar de um jeito e listar de outro deixaria "2 problemas" acima de 3 `<li>`. A
raiz é que hoje um campo com duas mensagens vira **duas âncoras para o mesmo
`#id`** — o usuário clica na segunda e a tela não se move. Agregar por alvo
conserta a lista e a contagem de uma vez.

Regras da agregação:

- chave é o `id` do campo; entradas **sem** `id` (`__all__`, `non_form_errors`)
  **não** são agrupadas — cada uma é um problema próprio, e agrupá-las por chave
  vazia juntaria erros de origens diferentes numa linha só;
- a ordem de primeira aparição é preservada;
- as mensagens do mesmo campo são unidas por `' '` — nenhuma mensagem é
  descartada. É a mesma regra da #121: fallback preserva o dado;
- `id` igual vindo de **fontes distintas** também colapsa, e isso é correto:
  duas fontes que produzem o mesmo `id_for_label` gerariam `id` repetido no DOM,
  violando a unicidade que o HTML espera e tornando a âncora ambígua — o
  navegador salta para o primeiro elemento com aquele `id`, então as duas âncoras
  levariam ao mesmo lugar de qualquer forma;
- quando as fontes colidem com **rótulos diferentes**, vence o **primeiro**, pela
  mesma razão que fixa a ordem: o item consolidado é o alvo que apareceu antes, e
  seu rótulo não pode mudar debaixo dele conforme fontes posteriores são lidas.
  Alternativas foram descartadas — concatenar rótulos produziria
  `"Quantidade / Qtd.: …"` para um único campo, e deixar o último vencer tornaria
  o texto dependente da ordem dos argumentos de `{% coletar_erros %}`, que é
  detalhe da tela. Regra escrita como asserção, não como acidente do `dict`.

**A mudança de contrato precisa ser dita com precisão**, porque só metade dele
fica igual:

| Aspecto do contrato | Antes | Depois |
|---|---|---|
| Chaves do item | `{'id', 'rotulo', 'mensagem'}` | iguais |
| Cardinalidade | uma entrada por **mensagem** | uma entrada por **alvo**; entradas sem `id` seguem uma por mensagem |
| Conteúdo de `mensagem` | uma mensagem | todas as mensagens daquele alvo, unidas por `' '` |
| Ordem | ordem de iteração do `form.errors` | ordem de **primeira aparição** do alvo |
| `rotulo` na colisão de `id` | não existia colisão: um item por mensagem | o **primeiro** rótulo vence |

`test_coletar_erros_achata_form_e_formset`
(`apps/requisicoes/tests/test_views.py`) afirma só forma e presença de `id`, então
sobrevive sem edição — mas isso é consequência, não licença: a mudança de
cardinalidade ganha testes próprios (ordem de primeira aparição, `id` repetido
entre fontes, mensagem agregada), e o docstring de `coletar_erros` passa a dizer
"um item por alvo" no lugar de "achata".

### Por que `acao` e não a frase inteira como parâmetro

A pluralização ("1 problema" / "N problemas") é do componente. Se a tela passar a
frase inteira, ela reescreve a pluralização — e uma delas vai errar. `acao`
parametriza só o verbo: `Não foi possível {{ acao }}: N problemas encontrados.`

### Por que o alerta inline de `non_form_errors` sai das duas telas

`coletar_erros` já lê `formset.non_form_errors()` no ramo
`hasattr(fonte, 'non_form_errors')`. Com o
sumário no topo, o alerta lá embaixo mostra **a mesma string** a várias roladas de
distância, sem marcador de que é a mesma. O usuário lê "3 problemas", corrige, e
reencontra um deles achando que é o quarto. Removidos os dois consumidores, os
partials `_alert_erros_formset.html` de `estoque` e de `requisicoes` ficam órfãos
e saem junto.

## Estratégia de testes

ADR-0010, em três camadas — e as três são obrigatórias, não alternativas:

1. **Unidade / renderização** — `render_to_string` no componente e chamada direta
   de `coletar_erros`.
2. **Contrato HTTP** — POST inválido em **cada uma das três telas**, via `client`,
   conferindo o HTML que a view devolve de verdade. É o que as *path
   instructions* do repo exigem para mudança de template, e é a única camada que
   prova que a view monta o contexto que o sumário precisa (`form`, `formset`,
   `cabecalho`). Guard de arquivo não vê isso.
3. **Guard de arquivo** — o que precisa continuar ausente (duplicata, include
   órfão), porque ausência não se prova renderizando.

| Caso | O que prova | Onde |
|---|---|---|
| Caminho feliz — anel de foco | contêiner do sumário tem `focus:ring-2`, e **nenhuma** classe `focus-visible:ring` | `apps/core/tests/test_components.py` |
| Âncora não regride | `<a>` do item **mantém** `focus-visible:ring-2` — o guard impede "consertar" o alvo errado | idem |
| Fallback sem JS | contêiner tem `autofocus` **e** `tabindex="-1"` | idem |
| Contagem por campo | campo com 2 mensagens → 1 item, 1 âncora, texto "1 problema encontrado" | idem |
| Nenhuma mensagem perdida | as 2 mensagens do campo aparecem no HTML final | idem |
| Erro não-de-campo não agrega | 2 `non_form_errors` → 2 itens | `apps/requisicoes/tests/test_views.py` |
| Ordem de primeira aparição | alvo que erra primeiro aparece primeiro, mesmo recebendo mensagem de fonte posterior | idem |
| `id` repetido entre fontes | duas fontes com o mesmo `id_for_label` → 1 item | idem |
| Rótulo na colisão | fontes com o mesmo `id` e rótulos diferentes → o item consolidado mantém o **primeiro** rótulo, e as duas mensagens | idem |
| Cabeçalho | o título é `<h2>`, não `<p>` | `apps/core/tests/test_components.py` |
| Nível de falha preservado | o sumário mantém `role="alert"` | idem |
| Sem qualquer auto-ocultação | o HTML renderizado não contém **nenhum** mecanismo capaz de esconder o sumário sozinho: nem `mensagemFlash`, nem `setTimeout`/`x-init` que chame `remove`/`hidden`/`display:none`, nem `x-show`/`x-if` sobre estado temporizado. Asserção sobre o conjunto de mecanismos, não sobre uma grafia — checar só `mensagemFlash` deixaria passar um timer escrito de outro jeito | idem |
| Sem dismiss manual | o sumário não renderiza `<button>` algum — fechar a caixa apagaria a única navegação até os campos inválidos | idem |
| Frase parametrizável | default diz "salvar"; `acao="registrar o atendimento"` aparece na frase | idem |
| Adoção nas três telas | as 3 telas contêm `{% coletar_erros %}` + `components/error_summary.html` | guard de arquivo, parametrizado |
| Sem duplicata | nenhuma das 3 telas cita `non_form_errors` fora do `{% if %}` de borda de seção | guard de arquivo |
| Partial órfão | `_alert_erros_formset.html` não existe **e** nenhum arquivo de `apps/` ainda o cita | guard de arquivo (as duas metades) |
| **POST inválido — `nova_saida_excepcional`** | resposta 200 traz o sumário, com `autofocus`, nomeando o campo em erro; e **não** traz o alerta de `non_form_errors` duas vezes | `apps/estoque/tests/test_views.py` |
| **POST inválido — `rascunho_form`** | idem, e a `non_form_errors` do formset aparece exatamente 1 vez no corpo | `apps/requisicoes/tests/test_views.py` |
| **POST inválido — `atender_retirada`** | idem, e a frase-líder diz "registrar o atendimento", não "salvar" | idem |
| Utility compilada | `focus:ring-danger-accent` presente no `app.css` | `apps/core/tests/test_tokens_semanticos.py` |
| `atender_retirada` na prática | POST inválido re-renderiza com o sumário e com a frase da tela | `apps/requisicoes/tests/test_views.py` |

O guard de duplicata é o que fecha a issue de verdade: `docs/design-system.md`
avisa que *"regra sem mecanismo vira sugestão"*, e este conjunto já perdeu essa
aposta três vezes.

### O que essas três camadas NÃO provam

Todas elas leem HTML. Nenhuma delas prova **comportamento de navegador**:
`document.activeElement` depois do POST, o `x-init` rodando depois de um swap
HTMX, ou o que um leitor de tela de fato fala. O repositório não tem infra de
teste de navegador (não há Playwright, Selenium nem Cypress em `package.json` ou
`pyproject.toml`), e montar uma é escopo muito maior que esta issue.

O que fica no lugar, explicitamente:

- **Validação em navegador, manual e registrada no PR.** Subir o servidor de
  desenvolvimento e submeter as três telas com dados inválidos, em três
  caminhos: Alpine carregado, Alpine bloqueado (para exercitar o `autofocus`
  sozinho) e swap HTMX.

  **Critério de aprovação, igual nos três**, porque "ler `document.activeElement`"
  não é critério — passaria com o foco em qualquer lugar:

  ```js
  document.activeElement?.id === 'sumario-erros'   // → true
  ```

  `sumario-erros` é o `id` default do contêiner; numa tela que passe `id=`
  próprio, o valor esperado é o que a tela passou. Os três resultados vão no
  corpo do PR, cada um dizendo caminho, tela e o booleano observado — não
  "validado". É o mesmo tipo de validação que
  `docs/plans/62-browser-validation-ia-doc.md` já usa neste repositório.
- **Fora de escopo, e dito como tal**: a matriz navegador × leitor de tela
  (NVDA/JAWS/VoiceOver). Exige AT real e uma pessoa ouvindo; nenhum agente
  fecha isso. Se a validação manual mostrar anúncio duplicado ou interrompido,
  isso vira issue própria da Etapa 2 em vez de ser resolvido às cegas aqui.

Onde o plano antes afirmava que os dois caminhos de anúncio são "mutuamente
exclusivos por construção", agora ele afirma menos: **é o que o mecanismo prevê,
e a validação em navegador é o que confirma.**

## Invariantes

- **Componente global não conhece domínio** (`docs/design-system.md`): `acao` é
  string de apresentação passada pela tela; o componente não deduz nada de enum.
- **Contagem de live regions em `_messages.html`**: `role="alert"` == 1 e
  `role="status"` == 1 (`apps/requisicoes/tests/test_views.py:2713`). O sumário
  adiciona um `role="alert"` **dentro do `<form>`**, não no partial de flash —
  a contagem daquele teste é sobre `_messages.html` e não é afetada. Verificar
  na execução, não no papel.
- **Piso de 44px** (#120): as âncoras seguem `block min-h-11 py-2.5`.
- **Escala de raio**: nada de `rounded` pelado
  (`test_nenhum_raio_fora_da_escala` já vigia os dois templates).
- **Sem cor crua**: `focus:ring-danger-accent` é token, não paleta.
- **Camadas (ADR-0004)**: `coletar_erros` continua apresentação pura — lê
  `form.errors`, não valida nada.

## Riscos

| Risco | Mitigação |
|---|---|
| `autofocus` numa `<div>` ser ignorado por algum navegador | O `x-init` continua lá; o `autofocus` é **rede**, não substituição. Teste garante a presença do atributo, não o comportamento do navegador |
| `autofocus` roubar o foco em tela que carrega sem erro | O sumário inteiro está dentro de `{% if erros %}` — sem erro, não existe elemento |
| `autofocus` + `role="alert"` no mesmo nó anunciarem duas vezes, ou o foco interromper o anúncio | Pelo mecanismo, os caminhos não se cruzam: `role="alert"` dispara com **mudança** (swap HTMX), e no POST full-page o conteúdo já está no DOM, então quem anuncia é o foco. Mas isso é previsão, não observação — a validação manual em navegador (seção acima) é o que confirma, e a matriz com leitor de tela real fica declarada fora de escopo |
| `focus:` ser revertido por quem lê a regra do design system e não a exceção | A exceção entra no doc **e** o teste trava as duas metades (contêiner `focus:`, âncora `focus-visible:`) |
| Agregação juntar erros de forms diferentes do formset | Ids de formset são únicos por form (`id_itens-0-quantidade`); só agrega quem tem `id` |
| `app.css` desatualizado no commit | `npm run css:build` (`make css-build`) antes de commitar; `test_css_build_gera_tokens_e_utilities_novas` cobre |
| Remover o alerta inline esconder erro numa tela não auditada | Os dois únicos consumidores são `nova_saida_excepcional.html` e `rascunho_form.html`, e **os includes saem antes dos arquivos** (passos 4-5). O guard tem duas metades: arquivo ausente **e** nenhuma referência residual em `apps/` — só a primeira deixaria passar um include sobrevivente, que viraria `TemplateDoesNotExist` em produção |
| Contagem por campo mudar número em teste existente | `test_coletar_erros_achata_form_e_formset` só afirma forma e presença de `id` — sobrevive; revalidar na execução |

Sem risco de concorrência, de mutação de estoque ou de máquina de estados: o
diff não sai da camada de apresentação.

## Registrado, não adotado

### Dismiss manual — não se adota. Ausência de auto-dismiss — já vale, e ganha teste

As duas metades da regra citada têm destinos opostos, e juntá-las num título só
era convite a implementar um timer. Separadas:

- **ausência de auto-dismiss**: vale aqui, e passa a ser verificada. O sumário
  nunca teve timer e não ganha nenhum;
- **botão de dismiss manual**: não se adota, pelo motivo abaixo.


`docs/CONVENTIONS.md` §Níveis e ARIA (linhas 172-181) fixa, para o nível `error`,
`role="alert"` + sem auto-dismiss, e fecha com *"Todas as mensagens têm botão de
dismiss manual."* Essa tabela vive dentro de `## Mensagens ao usuário` e governa
o contrato de **flash messages do Django** (`messages.error`,
`messages.warning`, …), renderizado por `core/partials/_messages.html` — o mesmo
contrato cujos 8s de auto-dismiss e cujo mapeamento `EstadoInvalido →
messages.warning` estão na mesma seção. O dismiss é a issue #119; a paridade
entre a faixa e o banner é a #124.

`error_summary.html` não é flash message: é componente de formulário, montado a
partir de `form.errors` no corpo do `<form>`, não da fila de `django.contrib.messages`.
A mesma distinção já foi registrada duas vezes neste repositório —
`docs/plans/122-politica-falha-componente-guard-cor-crua.md` (§"Conflito
registrado, não resolvido aqui") e
`docs/plans/123-copy-scpi-quem-decide.md` (§`role="alert"` no alerta de
divergência — recusado) — e o cabeçalho de `components/alert.html` a declara
literalmente.

Além de fora do contrato, **dismiss num sumário de erros seria dano**: os erros
continuam no formulário depois de fechar a caixa. O usuário perderia o único
dispositivo de navegação até os campos inválidos e ficaria com a tela
"aparentemente intacta" — exatamente a falha que o `{% comment %}` do topo do
componente diz existir para prevenir.

O que **é** adotado desta regra, e já estava no plano: o sumário é nível de
falha, mantém `role="alert"` e não some sozinho — não há timer nenhum no
componente, antes ou depois desta mudança. `danger-*` é o nome visual de `error`
no vocabulário de variante dos componentes, como
`docs/plans/122-politica-falha-componente-guard-cor-crua.md` já registrou.

## Ordem de execução

1. `coletar_erros` agrega por alvo + teste da agregação (RED → GREEN).
2. `error_summary.html`: `focus:`, `autofocus`, `<h2>`, `acao` — um ciclo por
   comportamento, com os guards de contêiner-vs-âncora.
3. `atender_retirada.html` passa `acao`.
4. `nova_saida_excepcional.html` adota o sumário e perde o alerta inline.
5. `rascunho_form.html` perde o alerta inline; os dois partials órfãos saem.
6. Guards de adoção, de não-duplicata e de referência residual ao partial.
7. Testes de contrato HTTP: POST inválido nas três telas.
8. `npm run css:build` + `focus:ring-danger-accent` em `UTILITIES_ESPERADAS`.
9. `docs/design-system.md`: exceção do anel em alvo de foco programático.
10. `ruff format .`, `ruff check .`, `mypy apps`, suíte completa.
11. Validação em navegador: `document.activeElement?.id === 'sumario-erros'`
    nos três caminhos (full-page com Alpine, full-page sem Alpine, swap HTMX),
    com os três booleanos colados no corpo do PR.

## Critérios de aceite (espelho da issue)

- [ ] Anel de foco aparece no foco programático após POST full-page
- [ ] Sumário funciona e leva o foco mesmo sem Alpine
- [ ] Contagem reflete campos a corrigir
- [ ] Frase-líder parametrizável, e `atender_retirada.html` usa frase coerente
- [ ] Título do sumário é cabeçalho
- [ ] `nova_saida_excepcional.html` inclui `{% coletar_erros %}` + sumário após o `csrf_token`
- [ ] Alerta genérico de `non_form_errors` removido de `nova_saida_excepcional.html`
- [ ] Alerta de `non_form_errors` removido de `rascunho_form.html`
- [ ] Nenhuma tela exibe o mesmo erro em dois lugares
- [ ] Testes: contagem por campo, presença nas três telas, ausência de duplicata
- [ ] Testes de contrato HTTP de POST inválido nas três telas
- [ ] Validação em navegador: `document.activeElement?.id === 'sumario-erros'` verdadeiro nos três caminhos (Alpine, sem Alpine, swap HTMX), com os três resultados no corpo do PR
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run mypy apps` verdes
