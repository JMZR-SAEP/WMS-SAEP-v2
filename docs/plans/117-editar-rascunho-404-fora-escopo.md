# Plano — fix(requisicoes): 404 para rascunho fora do escopo em `editar_rascunho_view` (Issue #117)

## Escopo

**O que muda:** `editar_rascunho_view` em `apps/requisicoes/views.py` passa a buscar a
requisição pelo selector de visibilidade `requisicoes_visiveis_para(request.user.pk)` em vez
do queryset cru `Requisicao.objects`. Objeto fora do escopo de visibilidade do ator passa a
retornar `404` em vez de `403`, alinhando a view à fronteira do ADR-0010 (§ "Para objects
sensíveis (detail view fora do escopo de visibilidade do ator): `404` para não revelar
existência. Para ação proibida em objeto visível: `403`.").

**O que NÃO muda:**

- `pode_editar_rascunho` / `exigir_pode_editar_rascunho` em `apps/requisicoes/policies.py`;
- o selector `requisicoes_visiveis_para` em `apps/requisicoes/selectors.py`;
- o service `editar_rascunho` e as transições;
- a ordem das checagens dentro da view (policy de ator antes da checagem de estado);
- os dois `403` legítimos: ator visível mas não-criador, e criador com estado ≠ rascunho;
- o literal `'rascunho'` da checagem de estado da view. O resto do arquivo usa
  `EstadoRequisicao.RASCUNHO` (ex. `apps/requisicoes/views.py:119`), mas trocar aqui é
  mudança de legibilidade sem relação com a fronteira 404/403 desta issue — fica para uma
  varredura própria;
- templates, forms, URLs, models e schema.

## Critérios de aceite (da issue)

1. Rascunho fora do escopo de visibilidade → `404` (hoje `403`)
2. Requisição visível mas ator não é criador → `403` (comportamento atual mantido)
3. Requisição visível, criador, estado ≠ rascunho → `403` (comportamento atual mantido)
4. Testes em `apps/requisicoes/tests/test_views.py` cobrindo os três casos

## Arquivos tocados

| Arquivo | Mudança |
|---------|---------|
| `apps/requisicoes/views.py` | `editar_rascunho_view`: troca do queryset cru pelo selector de visibilidade + docstring registrando a fronteira |
| `apps/requisicoes/tests/test_views.py` | atualiza o teste do caso "não-criador" para `404`; adiciona teste do `403` de ator visível não-criador e teste do `404` fora do escopo via POST |
| `docs/plans/117-editar-rascunho-404-fora-escopo.md` | este arquivo |

## Implementação

Estado atual (`apps/requisicoes/views.py:327-330`):

```python
requisicao = get_object_or_404(
    Requisicao.objects.select_related('beneficiario__setor', 'setor_beneficiario'),
    pk=pk,
)
```

Estado alvo:

```python
requisicao = get_object_or_404(requisicoes_visiveis_para(request.user.pk), pk=pk)
```

Duas observações sobre a troca:

- **`select_related`.** O selector já aplica
  `select_related('criador', 'beneficiario', 'setor_beneficiario')`. O template
  `requisicoes/rascunho_form.html` só acessa `requisicao.beneficiario.nome`,
  `requisicao.beneficiario.matricula` e `requisicao.setor_beneficiario.nome` — todos
  cobertos. O `beneficiario__setor` do queryset cru não tem consumidor no template, então
  a troca não introduz N+1 e ainda elimina um join morto.
- **`requisicoes_visiveis_para` já é o idioma da view.** O símbolo já está importado em
  `apps/requisicoes/views.py:62` e é usado por `detalhe_view`, `autorizar_requisicao_view`,
  `separar_retirada_view`, `registrar_atendimento_view`, `cancelar_requisicao_view`,
  `registrar_devolucao_view` e `estornar_requisicao_view`. `editar_rascunho_view` era a
  exceção.

### Por que os dois `403` sobrevivem

O selector devolve rascunho apenas para o criador (`Q(criador_id=ator.pk)`, sem o filtro
`nao_rascunho`) e para superusuário. Beneficiário, chefe de setor e almoxarifado só enxergam
requisições fora de rascunho. Consequências:

- **Rascunho fora do escopo do ator** — isto é, rascunho de terceiro para ator não
  superusuário → fora do queryset → `404`. Vale para `GET` e `POST`, já que o
  `get_object_or_404` está acima do `if request.method == 'POST'`. É o critério 1 e fecha o
  probing de pk descrito na issue.
- **Requisição visível, ator não-criador** → só é possível fora de rascunho (beneficiário,
  chefia, almoxarifado). Passa pelo `get_object_or_404`, cai em
  `exigir_pode_editar_rascunho`, que exige criador ou superusuário → `PermissaoNegada` →
  `PermissionDenied` → `403`. É o critério 2.
- **Criador, estado ≠ rascunho** → passa pelo selector (criador vê tudo que criou) e pela
  policy (é o criador), e é barrado na checagem explícita `requisicao.estado != 'rascunho'`
  → `403`. É o critério 3.

Superusuário sobre rascunho de terceiro continua com acesso: está no selector e é aprovado
pela policy. Comportamento atual preservado.

A ordem policy-antes-de-estado precisa ser mantida: invertê-la faria o beneficiário de uma
requisição não-rascunho receber "Esta requisição não está em rascunho" em vez de "Apenas o
criador pode editar um rascunho", vazando a razão errada.

## Estratégia de testes

Alinhada ao ADR-0010: teste de view verifica status code e fronteira de autorização, sem
inspecionar HTML.

| Caso | Ator | Objeto | Esperado |
|------|------|--------|----------|
| Fora do escopo (rascunho de terceiro) | `outro_usuario_obras` | `rascunho_solicitante` | `404` |
| Visível, ator não é criador | `outro_usuario_obras` (beneficiário) | requisição em `aguardando_autorizacao` criada por `solicitante` | `403` |
| Visível, criador, estado ≠ rascunho | `solicitante` | requisição própria em `aguardando_autorizacao` | `403` |
| pk inexistente | `solicitante` | `pk=99999` | `404` |
| Happy path | `solicitante` | `rascunho_solicitante` | `200` |
| POST fora do escopo (rascunho de terceiro) | `outro_usuario_obras` | `rascunho_solicitante` | `404` |

Mudanças concretas em `apps/requisicoes/tests/test_views.py`:

- `test_editar_rascunho_get_nao_criador_retorna_403` passa a asserir `404` e é renomeado
  para `test_editar_rascunho_get_fora_do_escopo_retorna_404` — o nome antigo passaria a
  descrever o comportamento errado. É o único teste existente cuja expectativa muda.
- Novo `test_editar_rascunho_get_visivel_nao_criador_retorna_403`: requisição em
  `aguardando_autorizacao` com `criador=solicitante` e `beneficiario=outro_usuario_obras`;
  login como `outro_usuario_obras`; espera `403`. Cobre o critério 2, que hoje não tem teste
  próprio — o teste antigo cobria o `403` genérico via rascunho de terceiro, cenário que
  agora vira `404`.
- `test_editar_rascunho_get_estado_diferente_retorna_403` já cobre o critério 3 e permanece
  intacto: `criador=beneficiario=solicitante`, logo o objeto continua visível pelo selector.
- `test_editar_rascunho_get_pk_inexistente_retorna_404` e
  `test_editar_rascunho_get_criador_retorna_200` permanecem intactos.

- Novo `test_editar_rascunho_post_fora_do_escopo_retorna_404`: mesmo cenário do primeiro
  caso, via POST. O `get_object_or_404` está acima do `if request.method == 'POST'`, logo a
  fronteira vale para os dois verbos — a view aceita `GET` e `POST`
  (`@require_http_methods(['GET', 'POST'])`) e o contrato "fora do escopo → `404`" precisa de
  teste em ambos, senão uma regressão que reintroduza o queryset cru só no caminho de POST
  passaria despercebida.

Os testes de POST existentes (`test_editar_rascunho_post_*`) usam o criador sobre o próprio
rascunho: continuam passando pelo selector e não mudam de comportamento.

## Invariantes

Nenhuma entrada de `docs/matriz-invariantes.md` muda: a alteração é de fronteira HTTP, não
de regra de domínio. REQ-06 ("após envio, não há edição direta de itens") continua garantida
pela checagem de estado da view e pelo service.

A regra de visibilidade de `docs/matriz-permissoes.md` §5 é a que passa a ser respeitada
pela view — antes ela era contornada pelo queryset cru.

Após a implementação planejada, ADR-0010 (fronteira 404 vs 403) passará a ser respeitado
nesta view — hoje ela ainda o viola. Nenhum ADR precisa ser alterado ou suplementado: a
mudança implementa uma decisão já aceita.

## Riscos

- **Baixo — mudança de contrato HTTP visível ao usuário.** Um ator que hoje recebe `403` ao
  fazer probing de pk de rascunho alheio passa a receber `404`. É exatamente o efeito
  desejado, mas altera o status code de uma rota já em uso. Nenhum consumidor programático
  depende disso: o projeto é server-rendered, sem camada de API (ADR-0008), e o link para
  `requisicoes:editar_rascunho` só é renderizado no detalhe quando `pode_editar` é `True`
  (coberto por `test_detalhe_nao_exibe_link_editar_para_nao_criador`).
- **Nenhum risco de concorrência, migration ou mutação de estoque.** A mudança é uma troca de
  queryset de leitura; não há alteração de schema, de transição ou de saldo.
- **Sem risco de N+1.** Ver a nota sobre `select_related` acima.
