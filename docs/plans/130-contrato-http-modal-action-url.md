# Plano — fix(modal): contrato HTTP de toda `action_url` (Issue #130)

## Escopo

**O que muda**

1. Nasce `apps/core/modal.py::render_modal_erro` — a resposta 422 com o fragment do corpo do
   modal, hoje privada de `apps/requisicoes/views.py`, vira infraestrutura compartilhada entre
   apps.
2. `estornar_saida_excepcional_view` (`apps/estoque/views.py`) passa a responder
   204 + `HX-Redirect` no sucesso e 422 + fragment no erro de domínio quando `request.htmx`.
3. `confirmar_importacao_scpi_view` (`apps/requisicoes/views.py`) passa a responder
   204 + `HX-Redirect` no sucesso e 422 + fragment nos três ramos de erro quando `request.htmx`.
4. `registrar_devolucao_view` e `estornar_requisicao_view` param de usar
   `form.errors.as_text()`; o erro de formulário vai para o caminho 422 do modal com o texto
   vindo do próprio Form.
5. Nasce a guarda do contrato: uma varredura estática que enumera toda `action_url` de modal nos
   templates e um registro central de rotas, mais os testes HTTP por rota nos apps donos.

**O que NÃO muda**

- `components/modal.html`, `components/_modal_body.html`, `components/_modal_icon.html`,
  `core/static/core/js/modal.js` — a issue é de contrato de resposta, não do componente.
- Services, policies, selectors, models, migrations, formulários.
- Vocabulário de ícone do modal (issue #136), nome acessível do `<dialog>` (#131), foco inicial
  (#132) e trava de scroll (#134) — famílias vizinhas da mesma etapa, fora daqui.
- Os partials de corpo de form dos 5 modais (tipografia de label, `id` sem namespace em
  `_modal_form_estorno_saida.html`) — decidido em 2026-08-23 que pertencem às Etapas 6/7.
- O comportamento de qualquer rota que já cumpre o contrato: autorizar, retornar, recusar,
  cancelar, enviar, separar.

## Critérios de aceite (da issue)

| # | Critério | Como fica satisfeito |
|---|---|---|
| 1 | `estornar_saida_excepcional_view`: `htmx_redirect` no sucesso, 422 no erro de domínio | Passo 3 |
| 2 | `confirmar_importacao_scpi_view`: `htmx_redirect` no sucesso, 422 nos três ramos de erro | Passo 4 |
| 3 | Fallbacks sem HTMX continuam funcionando | Ramo `if request.htmx:` em cada uma; o `else` é o código de hoje |
| 4 | `registrar_devolucao_view` e `estornar_requisicao_view` sem `form.errors.as_text()` | Passo 5 |
| 5 | Teste de contrato que enumera toda `action_url` e verifica 204+`HX-Redirect` ou 422+fragment | Passos 6 e 7 |
| 6 | O teste falha se um modal novo apontar para uma view fora do contrato | Passo 6 (registro fechado) + passo 7 (`pytest.fail` sem cenário) |

A varredura enumera **nomes de rota**, não URLs concretas: `requisicoes:cancelar` aparece em dois
pontos de `detalhe.html` com o mesmo `{% url %}` e `pk` diferente por requisição. O nome é a
unidade que identifica a view responsável pela resposta — que é o que o contrato governa. A URL
concreta reaparece no passo 7, onde cada cenário faz o `reverse()` com o objeto que criou.

## Arquivos tocados

| Arquivo | Mudança |
|---|---|
| `apps/core/modal.py` | **novo** — `render_modal_erro` (fragment 422) |
| `apps/core/tests/contrato_modal.py` | **novo** — varredura de `action_url` + registro de rotas + asserção compartilhada |
| `apps/core/tests/test_contrato_modal.py` | **novo** — guarda estática (sem DB) |
| `apps/requisicoes/views.py` | `_render_modal_erro` delega ao core; SCPI, devolução e estorno passam a 422/204 |
| `apps/estoque/views.py` | `estornar_saida_excepcional_view` passa a 422/204 |
| `apps/estoque/templates/estoque/partials/_modal_form_estorno_saida.html` | preserva a justificativa digitada no re-render |
| `apps/requisicoes/templates/requisicoes/partials/_modal_body_fragment.html` | **removido** — indireção sem consumidor após o passo 2 |
| `apps/requisicoes/tests/test_contrato_modal_http.py` | **novo** — contrato HTTP das 9 rotas de `requisicoes:` |
| `apps/estoque/tests/test_contrato_modal_http.py` | **novo** — contrato HTTP de `estoque:estornar_saida_excepcional` |
| `docs/plans/130-contrato-http-modal-action-url.md` | este arquivo |

## O mapa medido: as 10 rotas que são `action_url` hoje

Toda `action_url` do sistema nasce de um `{% url %}` na linha imediatamente acima do
`{% include %}` — nenhuma é literal, nenhuma vem do contexto da view. É isso que torna a
varredura estática possível.

| Rota | Template | Estado hoje |
|---|---|---|
| `requisicoes:registrar_devolucao` | `requisicoes/detalhe.html:175` | ⚠️ `as_text()` no form inválido |
| `requisicoes:cancelar` | `detalhe.html:215` e `:299` | ✅ 204/422 |
| `requisicoes:enviar_rascunho` | `detalhe.html:226` | ✅ 204 |
| `requisicoes:separar_retirada` | `detalhe.html:320` | ✅ 204 |
| `requisicoes:estornar` | `detalhe.html:326` (via `_confirmacao_acao.html`) | ⚠️ `as_text()` no form inválido |
| `requisicoes:autorizar` | `detalhe.html:260` (via `_confirmacao_acao.html`) | ✅ 204 |
| `requisicoes:retornar_rascunho` | `detalhe.html:265` (via `_confirmacao_acao.html`) | ✅ 204 |
| `requisicoes:recusar` | `detalhe.html:270` (via `_confirmacao_acao.html`) | ✅ 204/422 — é o padrão de referência |
| `requisicoes:confirmar_importacao_scpi` | `estoque/preview_importacao_scpi.html:312` | ❌ página inteira / 302 |
| `estoque:estornar_saida_excepcional` | `estoque/detalhe_saida_excepcional.html:176` | ❌ 302 nos dois caminhos |

`requisicoes/atender_retirada.html:235` usa `submit_form_id`, não `action_url`: fica fora do
contrato por construção — o `<dialog>` não emite `hx-post` nenhum nesse modo, e
`validar_contrato_modal` (`core_tags.py:263`) garante que os dois nunca coexistem.

## Implementação

### Passo 1 — `apps/core/modal.py`

```python
def render_modal_erro(
    request,
    *,
    modal_id: str,
    titulo: str,
    erro: Any,
    descricao: str = '',
    form_body_template: str = '',
    confirm_label: str = 'Confirmar',
    confirm_variant: str = 'primary',
    cancel_label: str = 'Voltar',
    icon_variant: str | None = None,
    acao_erro: str = '',
    contexto_form: dict | None = None,
) -> HttpResponse:
```

Renderiza `components/_modal_body.html` direto e devolve 422.

Duas diferenças deliberadas em relação ao `_render_modal_erro` de hoje:

- **`erro` deixa de ser `str`.** `{% erros_do_formulario %}` (`core_tags.py:456`) aceita Form,
  FormSet **ou** string como fonte, e `coletar_erros` achata as três do mesmo jeito. Passar o
  Form ligado em vez de um texto pré-formatado é o que faz o critério 4 sair sem inventar
  formatação: o texto vem do Form, com âncora por campo, e nunca com o asterisco de log do
  `as_text()`.
- **`icon_variant` default `None`, não `'danger'`.** A assinatura atual reclassificaria como
  perigo qualquer modal que passasse por ali sem dizer o contrário — e dois dos consumidores
  novos (SCPI é `warning`, estorno de saída não tem ícone) cairiam nessa armadilha. Os dois
  chamadores existentes (cancelar, recusar) já passam `icon_variant='danger'` explicitamente,
  então nenhum render muda.

### Passo 2 — `_render_modal_erro` delega

`apps/requisicoes/views.py:221` passa a chamar `render_modal_erro`. Como o core renderiza
`components/_modal_body.html` direto, `requisicoes/partials/_modal_body_fragment.html` fica sem
consumidor (é o único `{% include %}` de 7 linhas sobre o mesmo parcial) e é removido junto.
Verificar a ausência de outra referência antes de apagar.

### Passo 3 — `estornar_saida_excepcional_view`

```python
except ErroDominio as exc:
    if request.htmx:
        return render_modal_erro(
            request,
            modal_id='estornar-saida',
            titulo='Estornar saída excepcional',
            descricao='Esta ação é irreversível. …',
            erro=str(exc),
            form_body_template='estoque/partials/_modal_form_estorno_saida.html',
            confirm_label='Confirmar estorno',
            confirm_variant='danger',
            contexto_form={'justificativa': justificativa},
        )
    pres = traduz_erro_dominio(exc)
    getattr(messages, pres.severity)(request, str(exc))
    return redirect('estoque:detalhe_saida_excepcional', pk=pk)

messages.success(request, f'Saída {saida.numero_publico} estornada com sucesso.')
return htmx_redirect(request, reverse('estoque:detalhe_saida_excepcional', args=[pk]))
```

Título, descrição, rótulo e variante são copiados de `detalhe_saida_excepcional.html:177` — o
modal que reabre com erro precisa ser o mesmo modal, não um parente. Sem `icon_variant`, porque
o render inicial também não tem.

`_modal_form_estorno_saida.html` ganha `>{{ justificativa|default_if_none:'' }}</textarea>`. Sem
isso, o 422 devolve a caixa aberta e o texto digitado apagado — é o que `recusar` já evita com
`motivo_recusa`. O `id="justificativa"` sem namespace continua como está: é dívida da Etapa 6.

### Passo 4 — `confirmar_importacao_scpi_view`

Os três ramos de erro (`sem preview na sessão`, `sem estoque ativo`, `ConflitoDominio` /
`DadosInvalidos`) ganham `if request.htmx: return render_modal_erro(...)` antes do `render()` de
página, com `modal_id='confirmar-importacao-scpi'`, `icon_variant='warning'` e
`confirm_label='Confirmar importação'` — os mesmos de `preview_importacao_scpi.html:313`.

**Decisão:** o fragment 422 vai **sem** `form_body_template`. O corpo do modal é
`_modal_corpo_confirmar_importacao.html`, uma recapitulação de `novos`/`divergencias`/`total` do
preview. No ramo mais comum de erro a sessão de preview já foi consumida, e recomputar a
contagem exigiria re-parsear o CSV. Repetir números de uma pré-visualização que não existe mais
seria a segunda evidência contraditória que a issue descreve. O 422 leva o título, a caixa de
erro e o rodapé — que é exatamente a pergunta respondida: não gravou, e o modal continua de pé.

O sucesso troca `HttpResponseRedirect` por `htmx_redirect(request, reverse('estoque:sucesso_importacao_scpi', kwargs={'pk': importacao.pk}))`.

### Passo 5 — devolução e estorno de requisição

```python
if not form.is_valid():
    if request.htmx:
        return render_modal_erro(request, modal_id=..., erro=form, ...)
    messages.error(request, ' '.join(m for ms in form.errors.values() for m in ms))
    return redirect('requisicoes:detalhe', pk=pk)
```

`redirect(...)` e não `htmx_redirect(...)` neste ramo. Os dois produzem a mesma resposta aqui —
`htmx_redirect` (`core/http.py:23`) só devolve 204 quando `request.htmx` é verdadeiro, e dentro
de um `else` de `if request.htmx:` ele é provadamente falso —, mas escrever o helper de HTMX no
ramo que existe justamente por não ser HTMX obriga quem lê a provar a equivalência para saber
qual status sai dali. O ramo não-HTMX chama o redirect não-HTMX.

- Devolução: `modal_id=f'devolver-{item_pk}'`,
  `form_body_template='requisicoes/partials/_modal_form_devolucao.html'`,
  `contexto_form={'form': form, 'item': item, 'entregue_liquida': …}`. O parcial lê
  `item.material.nome` e `entregue_liquida`, então a view precisa buscar o item e chamar
  `entregue_liquida_por_requisicao(requisicao_id=pk)` — o mesmo selector que `_detalhe_context`
  (`views.py:143`) usa para montar o modal na primeira vez, já importado em `views.py:43`. A
  busca do item é `get_object_or_404(requisicao.itens.select_related('material'), pk=item_pk)`
  **dentro do ramo de erro**, e não no topo da view: fora dali ela mudaria o código de resposta
  de rotas que hoje não olham o item antes de chamar o service.
- Estorno: `modal_id='estornar-modal'`,
  `form_body_template='requisicoes/partials/_modal_form_estorno.html'`,
  `contexto_form={'estorno_form': form}`.

O fallback sem HTMX segue redirecionando com mensagem, mas o texto passa a ser o do Form
("Este campo é obrigatório.") em vez do dump com asterisco. **`messages.error`, não
`messages.warning`**: formulário inválido é a mesma classe de falha que `DadosInvalidos`, que a
suíte já trava como `error` nos testes de drift 4 e 5
(`requisicoes/tests/test_views.py:3008,3135`).

### Passo 6 — guarda estática (`apps/core/tests/`)

`contrato_modal.py` (módulo de apoio, não coletado como teste):

- `rotas_de_modal()` varre `apps/*/templates/**/*.html` e, para cada `{% include %}` de
  `components/modal.html` ou de `requisicoes/partials/_confirmacao_acao.html`, lê
  `action_url=<var>` e resolve `<var>` pelo `{% url 'app:nome' … as <var> %}` do mesmo arquivo.
  Devolve o conjunto de nomes de rota.
  - `_confirmacao_acao.html` é ignorado como origem: lá `action_url=action_url` é repasse.
  - `action_url` que não resolva para um `{% url %}` falha com mensagem própria — literal em
    template é justamente o que tornaria a varredura cega.
  - `submit_form_id` sem `action_url` é ignorado (modo de form externo).
- `REGISTRO_CONTRATO_MODAL: dict[str, str]` — rota → app dono do teste HTTP. Fechado, com as 10
  entradas da tabela acima.
- `assert_contrato_modal(resposta, *, destino_esperado=None)` — 204 com `HX-Redirect`, ou 422 com
  `data-modal-body` no corpo. Qualquer outra coisa falha nomeando o status recebido.

  No ramo 204, **o valor do cabeçalho é comparado, não só a presença**. `HX-Redirect: ''` e
  `HX-Redirect` apontando para a tela errada são as duas falhas que a mera presença deixa passar,
  e a segunda é exatamente o sintoma que esta issue trata: a pessoa termina numa tela que não
  responde se gravou. `destino_esperado` é obrigatório sempre que o cenário puder terminar em
  204, e vem da função construtora do cenário, que já conhece o `pk` do objeto que criou. Quando
  `None`, o helper exige 422 — é o caso dos cenários que exercitam só o ramo de erro.

`test_contrato_modal.py` (sem DB): `rotas_de_modal() == set(REGISTRO_CONTRATO_MODAL)`. Modal novo
apontando para rota não registrada quebra aqui.

### Passo 7 — contrato HTTP por rota

Um arquivo por app dono, cada um parametrizado sobre as rotas que o registro atribui a ele. A
parametrização vem do registro, e o cenário vem de um `dict` local rota → função construtora; se
a construtora não existir, o teste chama `pytest.fail` nomeando a rota. É esse par que fecha o
critério 6: registrar a rota sem escrever o cenário não passa, e não registrar a rota não passa
no passo 6.

A construtora devolve `(url, payload, destino_esperado)`. Cada cenário faz um POST com
`HTTP_HX_REQUEST='true'` como ator autorizado e passa a resposta por `assert_contrato_modal`. A
carga escolhida é a que exercita o **ramo de erro** de cada rota (payload vazio, sessão sem
preview, estado que o service recusa) — é o ramo onde as violações desta issue viviam; o caminho
feliz das duas views corrigidas ganha teste próprio de 204 + `HX-Redirect` para o destino certo
ao lado, no arquivo de views do app.

**Segundo eixo: sem autenticação.** A mesma parametrização roda anônima e espera 302 com
`Location` igual a `f'{reverse("accounts:login")}?next={url}'` — o valor exato, pela mesma razão
do `HX-Redirect`: status sozinho não distingue "mandou para o login" de "mandou para outro
lugar", e `settings.LOGIN_URL` (`config/settings/base.py:109`) é um nome de rota, então o
destino é derivável sem literal na asserção. O `?next=` também é conteúdo do contrato: é ele que
devolve a pessoa à ação que ela tentou.

A ADR-0010 põe "sem login → 302 para login" no contrato de toda view de mutação, e hoje só 3 das
10 rotas têm esse caso escrito: `enviar_rascunho`, `confirmar_importacao_scpi` e
`estornar_saida_excepcional`. As outras sete dependem de `@login_required` sem nada travando.

O eixo anônimo assere também que **nada mudou**: o POST não pode ter tocado o objeto do cenário.
É a metade do contrato que o status não cobre — 302 para o login com a mutação já gravada seria
o pior resultado possível, e é a única asserção do eixo que exercita código do projeto (que o
decorador está na view, antes de qualquer chamada de service) em vez de exercitar o Django.
`estoque/tests/test_views.py:458` (`test_post_anonimo_redireciona_sem_persistencia`) já é esse
teste para uma rota; o eixo o generaliza para as 10.

**Isso obriga o eixo anônimo a usar as mesmas construtoras do eixo autorizado**, e não só a URL:
sem objeto real não há estado para comparar, e com `pk` inventado o teste provaria apenas que
`@login_required` dispara antes da busca — que é comportamento do Django, não deste projeto. O
cenário é construído, o estado do objeto é capturado antes do POST, e relido depois do 302. O
custo de fixture é o mesmo do eixo autorizado porque a construtora é a mesma; o que muda é só o
cliente não estar autenticado e a asserção ser de imobilidade.

## Estratégia de testes (ADR-0010)

Camada **Views** — contrato HTTP. Nada aqui revalida timeline, saldo ou matriz de policy.

| Caso | Onde | Espera |
|---|---|---|
| Caminho feliz de cada rota corrigida, HTMX | `estoque/tests/test_views.py`, `requisicoes/tests/test_views.py` | 204 + `HX-Redirect` para o destino certo |
| Erro de domínio no estorno de saída, HTMX | `estoque/tests/test_views.py` | 422 + `data-modal-body` + justificativa digitada preservada |
| SCPI sem preview na sessão, HTMX | `requisicoes/tests/test_views.py` | 422 + `data-modal-body` + texto do erro |
| Form inválido em devolução e estorno, HTMX | `requisicoes/tests/test_views.py` | 422 + texto do Form, sem `*` de `as_text()` |
| Fallback sem HTMX das quatro views | idem | 302 / 200 de página, como hoje |
| Permissão negada | já coberto | 403, inalterado |
| Contrato das 10 rotas, ator autorizado | `*/tests/test_contrato_modal_http.py` | 204 + `HX-Redirect` para o destino esperado, ou 422 + fragment |
| As mesmas 10 rotas, anônimo | `*/tests/test_contrato_modal_http.py` | 302 com `Location` == login + `?next=<url da ação>`, e nenhuma mutação (ADR-0010; 7 das 10 não tinham) |
| Registro fechado | `core/tests/test_contrato_modal.py` | conjunto varrido == registro |

Testes existentes que mudam de expectativa:

- `estoque/tests/test_views.py:652-666` — asserta `action="…"` no `<dialog>`; segue válido.
- `requisicoes/tests/test_views.py:3119` (`estornar sem justificativa`) — POST sem HTMX, assere
  só o texto da mensagem; continua passando com `messages.error`.
- Qualquer teste que dependa de `requisicoes/partials/_modal_body_fragment.html` por nome —
  verificar antes de apagar (hoje o único consumidor é `views.py:256`).

## Invariantes

- **A trilha é append-only e a confirmação é explícita.** A issue não muda o que grava; muda o
  que a tela responde depois de gravar. Nenhum service é tocado, logo nenhuma invariante de
  estoque, reserva ou máquina de estados é exercida por este PR.
- **Uma superfície de erro por tela.** `_modal_body.html` já obriga o uso de
  `{% erros_do_formulario %}` — travado em `core/tests/test_components.py:1922-1934`. Passar o
  Form como fonte usa a mesma porta; não nasce uma quarta grafia de "o formulário falhou".
- **PRG por `HX-Redirect`.** `htmx_redirect` (`core/http.py:23`) responde 204, e não 200 como o
  `HttpResponseClientRedirect` do `django_htmx`. As duas views corrigidas passam a usar o
  helper, e não a reimplementá-lo.
- **`hx-sync="this:drop"`** continua sendo o bloqueio de duplo envio; nada neste PR mexe no
  `<form>` do modal.

## Riscos

| Risco | Mitigação |
|---|---|
| A varredura estática dá falso verde se alguém escrever `action_url` literal | A varredura falha explicitamente nesse caso, em vez de ignorar |
| `render_modal_erro` no core criar dependência de camada errada | Ele é apresentação HTTP pura: renderiza template, não importa service nem model — mesma faixa de `core/http.py`. Não entra em `core/presentation.py`, que é declaradamente independente de Django/templates |
| Passar o Form como `erro` gerar âncora para `id` inexistente | Os campos do modal usam id próprio (`modal-devolver-quantidade-<pk>`), não `id_quantidade`. O sumário perde o link, não a mensagem — e `focar=False` já vale dentro do modal. Verificar no teste que a **mensagem** aparece; não prometer a âncora |
| SCPI 422 sem a recapitulação parecer perda de informação | Decidido no passo 4 e registrado aqui: repetir contagem de um preview consumido é pior que omiti-la |
| Remover `_modal_body_fragment.html` quebrar um teste por nome de parcial | Confirmar a ausência de referência ao caminho antes de apagar; hoje há um único consumidor vivo |
| Mudar `warning`→`error` no fallback sem HTMX | Nenhum teste assere o nível nesses dois casos; o alinhamento com os testes de drift 4/5 é o motivo |

## Fora de escopo declarado

`x-trap` morto (#134), id `-titulo` duplicado (#131), foco inicial (#132), fechamento com
requisição em voo (#133), fonte única de copy (#135), vocabulário de ícone (#136), rodapé e
rolagem (#137), identidade do registro no modal (#138). Nenhuma delas é pré-requisito desta, e
esta destrava 133/135/137.
