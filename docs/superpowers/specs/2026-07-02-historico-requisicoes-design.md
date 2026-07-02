# Histórico de requisições — spec

Data: 2026-07-02
Status: aprovado para plano de implementação

## Contexto

O app `estoque` já tem uma lista de histórico paginada/filtrada/ordenável
(`historico_movimentacoes_view`, ADR-0015) sobre `MovimentacaoEstoque`. O app
`requisicoes` não tem equivalente: existe `TimelineRequisicao` (log de eventos
por requisição, visível só no detalhe de uma requisição) e `lista_minhas.html`
(lista não paginada, escopo restrito ao próprio ator). Não há tela system-wide
para almoxarifado/chefias consultarem o histórico de requisições do sistema
inteiro, filtrado e paginado.

## Decisão de unidade de linha

**1 linha = 1 `Requisicao`**, não 1 evento de `TimelineRequisicao`. Justifica-se
porque o pedido do usuário (quem requisitou, quando, material, quantidade,
status) mapeia naturalmente ao cabeçalho da requisição, e a tela de "ver
eventos individuais" já existe (timeline no detalhe). Não há necessidade de
duplicar essa granularidade aqui.

Consequência: **nenhum model novo**. `Requisicao` já tem todos os campos
necessários (`estado`, `criador`, `beneficiario`, `setor_beneficiario`,
`criado_em`, `numero_publico`). A coluna "material/quantidade" vira um resumo
textual derivado de `itens` (relação existente `ItemRequisicao`), não uma
coluna de schema.

## Escopo de visibilidade (RBAC)

Espelha a regra de `movimentacoes_visiveis_para` — mais restrita que
`requisicoes_visiveis_para` (que inclui visão "minhas requisições" de
qualquer solicitante):

- Superusuário: todas as requisições.
- Almoxarifado (chefe ou auxiliar): todas as requisições.
- Chefe de setor não-almoxarifado: só requisições do(s) seu(s) setor(es)
  (via `setor_beneficiario`).
- Qualquer outro papel (solicitante comum, sem chefia): **sem acesso** a esta
  tela — `PermissionDenied`. Continuam usando `requisicoes:minhas`.

## Colunas padrão

| Coluna | Origem | Observação |
|---|---|---|
| Data/hora | `criado_em` | ordenável (asc/desc), padrão desc (mais recente primeiro) |
| Número | `numero_publico` ou `"Rascunho #pk"` | link para `requisicoes:detalhe` |
| Solicitante | `criador` | nome + matrícula, como em `lista_minhas.html` |
| Beneficiário | `beneficiario` | idem |
| Setor | `setor_beneficiario` | |
| Material | `itens` | resumo: nome do item único se `quantidade_itens == 1`, senão `"N itens"` (via `annotate(Count('itens'))`, sem N+1) |
| Status | `estado` | badge reusando partial `_estado_badge.html` existente |
| Ação | — | link "Ver" para o detalhe |

## Filtros e ordenação

- **Texto**: `icontains` sobre nome/matrícula de `criador` OU `beneficiario`.
- **Estado**: multi-select (checkboxes) sobre `EstadoRequisicao.choices`.
- **Período**: `data_ini`/`data_fim` sobre `criado_em__date`, inclusive.
- **Setor**: visível/aplicável para almoxarifado e superusuário
  (`pode_filtrar_historico_por_setor`); chefe de setor não recebe esse filtro (já está
  implicitamente restrito ao próprio setor pelo selector de visibilidade).
- **Ordenação**: só por `criado_em`, asc/desc via clique no cabeçalho da coluna Data
  (`ordem` na querystring), padrão desc.
- **Paginação**: `Paginator`, mesmo tamanho de página de `PAGINA_MOVIMENTACOES_TAMANHO`
  (constante equivalente local em `requisicoes/views.py`).

Filtros nunca ampliam o universo definido pelo selector de visibilidade — são
aplicados em cima do queryset já escopado, exatamente como em
`filtrar_movimentacoes`.

## Fora de escopo (confirmado com o usuário)

- Nenhuma ação em lote / seleção múltipla — a tela é consulta, não fila de
  ação (isso já existe em `fila_autorizacao`/`fila_atendimento`).
- Nenhuma exportação (CSV/Excel) — não pedido explicitamente além do texto do
  requisito original; pode ser extensão futura, mas não faz parte desta
  entrega.
- Nenhum campo `numero_publico` como filtro dedicado — a busca textual cobre
  o caso de uso mais comum (por pessoa); busca por número específico é feita
  navegando pelo detalhe/link direto quando necessário.

## Estrutura técnica (camadas, ADR-0004/0011)

- `apps/requisicoes/models.py`: adicionar `Meta.indexes` em `Requisicao` para
  `(estado, criado_em)` e `(setor_beneficiario, criado_em)` — suporta os
  filtros mais comuns desta tela sem full scan. Sem novo model. Sem migração
  manual (ambiente efêmero — `make setup` recria).
- `apps/requisicoes/selectors.py`:
  - `historico_requisicoes_visiveis_para(ator_id) -> QuerySet[Requisicao]`
  - `filtrar_historico_requisicoes(qs, *, texto, estados, data_ini, data_fim, setor) -> QuerySet[Requisicao]`
  - `pode_filtrar_historico_por_setor(ator_id) -> bool`
  - `setores_do_historico(qs) -> QuerySet[Setor]` (setores distintos no queryset escopado, para popular o select de filtro)
- `apps/requisicoes/policies.py`:
  - `pode_consultar_historico_requisicoes(papel) -> bool` (almoxarifado, superusuário ou chefia/auxiliar de setor não-almoxarifado — mesma matriz de `historico_requisicoes_visiveis_para`)
  - `exigir_pode_consultar_historico_requisicoes(papel) -> None`
- `apps/requisicoes/views.py`:
  - `historico_requisicoes_view` (FBV, `@login_required`, `@require_GET`), estrutura
    idêntica a `historico_movimentacoes_view`: parse de querystring, selector,
    filtro, paginação, contexto, HTMX vs full page.
- `apps/requisicoes/urls.py`: `path('historico/', views.historico_requisicoes_view, name='historico')`
- Templates (`apps/requisicoes/templates/requisicoes/`):
  - `historico_requisicoes.html` (estende `requisicoes/base.html` — a confirmar
    nome exato do base template durante o plano)
  - `partials/_tabela_historico_requisicoes.html` (cards mobile + tabela desktop,
    reusa `partials/_estado_badge.html` já existente)
  - `partials/_paginacao_historico.html` (paginação local ao app, mesmo padrão
    visual do partial de estoque, sem importar entre apps)
- Nav: link para `requisicoes:historico` visível só quando
  `pode_consultar_historico_requisicoes` é verdadeiro.

## Alpine.js

Sem necessidade identificada — filtros são um `<form>` com `hx-get` padrão
(igual ao de movimentações), sem estado client-side complexo. Se o multi-select
de estado precisar de UX melhor que checkboxes simples (ex.: dropdown com
contagem de selecionados), isso pode ser adicionado depois via Alpine sem
mudar contrato de backend — não faz parte desta entrega inicial.

## Testes (ADR-0010)

- `apps/requisicoes/tests/test_selectors.py`:
  - `historico_requisicoes_visiveis_para`: almoxarifado vê tudo, chefe de setor
    só vê seu setor, solicitante comum vê vazio, superuser vê tudo, usuário
    inativo vê vazio.
  - `filtrar_historico_requisicoes`: cada filtro isoladamente + combinação,
    usando `values_list('pk', flat=True)`.
- `apps/requisicoes/tests/test_policies.py`:
  - matriz `pode_consultar_historico_requisicoes` para os papéis relevantes.
- `apps/requisicoes/tests/test_views.py` (novas classes):
  - `TestHistoricoRequisicoesView`: 200 para almox/superuser, 403 para
    solicitante comum, 302 para anônimo, `page_obj` no contexto, paginação
    server-side, empty state.
  - `TestHistoricoRequisicoesFiltros`: cada filtro reduz resultado
    corretamente, HTMX devolve só partial, GET normal devolve página
    completa, ordenação asc/desc, filtro de setor só aparece para almox,
    querystring inválida não quebra.

## Documentação

- Docstrings nas novas funções de selector/policy/view seguindo o padrão já
  usado no arquivo (ver `movimentacoes_visiveis_para`, `pode_consultar_movimentacoes_estoque`
  como referência de estilo).
- Sem novo ADR — esta feature não introduz decisão arquitetural nova, apenas
  aplica o padrão já registrado em ADR-0015 (ledger de movimentação) a uma
  segunda entidade.
