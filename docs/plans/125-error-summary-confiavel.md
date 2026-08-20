# Plano — `error_summary` confiável, e adotado nas três telas de formset longo

Issue: [#125](https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/125) — Etapa 2 do
`docs/plans/audit-frontend-restante.md`. Desbloqueada: a
[#120](https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/120) fechou em 2026-08-19
(PR #11) e já entregou o piso de 44px e o raio das âncoras do mesmo arquivo.

Comando recomendado pela issue, executado na fase de implementação:

```
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
  marcador de localização, não repetição da mensagem — não é a duplicata que a
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
| `apps/requisicoes/tests/test_views.py` | teste de `coletar_erros` ganha o caso de campo com 2 mensagens |
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
  descartada. É a mesma regra da #121: fallback preserva o dado.

O formato do item continua `{'id', 'rotulo', 'mensagem'}`, então o contrato com o
template não muda e o teste de forma existente
(`test_coletar_erros_achata_form_e_formset`, em
`apps/requisicoes/tests/test_views.py`) continua valendo.

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

ADR-0010. Tudo aqui é camada de template/templatetag: `render_to_string` para o
componente, leitura do arquivo para os guards de tela, `pytest.mark.django_db` só
onde a view for exercida.

| Caso | O que prova | Onde |
|---|---|---|
| Caminho feliz — anel de foco | contêiner do sumário tem `focus:ring-2`, e **nenhuma** classe `focus-visible:ring` | `apps/core/tests/test_components.py` |
| Âncora não regride | `<a>` do item **mantém** `focus-visible:ring-2` — o guard impede "consertar" o alvo errado | idem |
| Fallback sem JS | contêiner tem `autofocus` **e** `tabindex="-1"` | idem |
| Contagem por campo | campo com 2 mensagens → 1 item, 1 âncora, texto "1 problema encontrado" | idem |
| Nenhuma mensagem perdida | as 2 mensagens do campo aparecem no HTML final | idem |
| Erro não-de-campo não agrega | 2 `non_form_errors` → 2 itens | `apps/requisicoes/tests/test_views.py` |
| Cabeçalho | o título é `<h2>`, não `<p>` | `apps/core/tests/test_components.py` |
| Frase parametrizável | default diz "salvar"; `acao="registrar o atendimento"` aparece na frase | idem |
| Adoção nas três telas | as 3 telas contêm `{% coletar_erros %}` + `components/error_summary.html` | guard de arquivo, parametrizado |
| Sem duplicata | nenhuma das 3 telas cita `non_form_errors` fora do `{% if %}` de borda de seção | guard de arquivo |
| Partial órfão | `_alert_erros_formset.html` não existe mais em nenhum dos dois apps | guard de arquivo |
| Utility compilada | `focus:ring-danger-accent` presente no `app.css` | `apps/core/tests/test_tokens_semanticos.py` |
| `atender_retirada` na prática | POST inválido re-renderiza com o sumário e com a frase da tela | `apps/requisicoes/tests/test_views.py` |

O guard de duplicata é o que fecha a issue de verdade: `docs/design-system.md`
avisa que *"regra sem mecanismo vira sugestão"*, e este conjunto já perdeu essa
aposta três vezes.

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
| `autofocus` + `role="alert"` no mesmo nó anunciarem duas vezes | O `role="alert"` só dispara com **mudança** (swap HTMX); no POST full-page o conteúdo já está no DOM e quem anuncia é o foco. Os dois caminhos são mutuamente exclusivos por construção, não por sorte — é o mesmo fato que o `{% comment %}` do topo do arquivo já documenta |
| `focus:` ser revertido por quem lê a regra do design system e não a exceção | A exceção entra no doc **e** o teste trava as duas metades (contêiner `focus:`, âncora `focus-visible:`) |
| Agregação juntar erros de forms diferentes do formset | Ids de formset são únicos por form (`id_itens-0-quantidade`); só agrega quem tem `id` |
| `app.css` desatualizado no commit | `npm run css:build` (`make css-build`) antes de commitar; `test_css_build_gera_tokens_e_utilities_novas` cobre |
| Remover o alerta inline esconder erro numa tela não auditada | Só as duas telas com o sumário perdem o alerta; nenhuma outra tela usa `_alert_erros_formset.html` |
| Contagem por campo mudar número em teste existente | `test_coletar_erros_achata_form_e_formset` só afirma forma e presença de `id` — sobrevive; revalidar na execução |

Sem risco de concorrência, de mutação de estoque ou de máquina de estados: o
diff não sai da camada de apresentação.

## Ordem de execução

1. `coletar_erros` agrega por alvo + teste da agregação (RED → GREEN).
2. `error_summary.html`: `focus:`, `autofocus`, `<h2>`, `acao` — um ciclo por
   comportamento, com os guards de contêiner-vs-âncora.
3. `atender_retirada.html` passa `acao`.
4. `nova_saida_excepcional.html` adota o sumário e perde o alerta inline.
5. `rascunho_form.html` perde o alerta inline; os dois partials órfãos saem.
6. Guards de adoção e de não-duplicata nas três telas.
7. `npm run css:build` + `focus:ring-danger-accent` em `UTILITIES_ESPERADAS`.
8. `docs/design-system.md`: exceção do anel em alvo de foco programático.
9. `ruff format .`, `ruff check .`, `mypy apps`, suíte completa.

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
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run mypy apps` verdes
