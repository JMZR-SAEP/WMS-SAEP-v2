# Plano de implementação — #112: escopo do ledger de movimentações para auxiliar de setor

## Decisão (HITL)

O issue exigia decisão humana entre restringir o selector ou emendar a matriz. **Decisão tomada:
restringir o selector, alinhando o ledger à decisão da #106.**

- No ramo de setor não-almox, a visão de setor passa a ser exclusiva do **chefe**
  (`setor_chefiado_ativo_id`).
- O **auxiliar de setor** continua com acesso à página, mas só enxerga movimentações de
  requisições que **ele mesmo criou** — espelho exato de
  `requisicoes/selectors.py::historico_requisicoes_visiveis_para`.
- Motivo: "ser auxiliar não é supervisionar o setor" (#106). Hoje o auxiliar vê no ledger o
  `numero_publico`, material, quantidades e datas de requisições cujo detalhe lhe devolve 404 e que
  o histórico de requisições já lhe nega. A §3 da matriz de permissões lista "estoque" como
  bloqueado para o auxiliar de setor; a exceção só sobrevivia na §4/§5.

Consequência documental: a matriz de permissões passa a divergir do texto atual ("Apenas próprio
setor" para auxiliar de setor, ratificado em US-17/#6) e precisa ser emendada nesta entrega, com
registro explícito de que a decisão da #106 prevalece sobre a ratificação anterior.

## Escopo

### Muda

- `apps/estoque/selectors.py::movimentacoes_visiveis_para` — ramo de setor não-almox passa de
  `filter(requisicao__setor_beneficiario_id__in=setores)` para o predicado completo
  `filter((Q(requisicao__criador_id=ator.pk) | Q(requisicao__setor_beneficiario_id=setor_chefiado_ativo_id)) & ~Q(requisicao__estado=EstadoRequisicao.RASCUNHO))`,
  com o termo do setor chefiado presente apenas quando `setor_chefiado_ativo_id is not None`.
  A exclusão de rascunho é explícita, e não presumida: `MovimentacaoEstoque.requisicao` é anulável e
  o model não tem constraint de estado, então o predicado não pode depender de nenhum service se
  comportar bem. Espelha o `nao_rascunho` de `historico_requisicoes_visiveis_para` (#106). Os ramos de
  almoxarifado e superusuário seguem sem filtro de estado — lá a regra é "vê tudo", e é justamente o
  ramo de setor que precisa de não-vazamento.
  Forma do import: `from apps.requisicoes.models import EstadoRequisicao` **no topo** de
  `apps/estoque/selectors.py`. Não há risco de ciclo: `apps/requisicoes/models.py` e
  `apps/estoque/models.py` não importam nada de `apps.*` (verificado), então a aresta nova
  `estoque.selectors → requisicoes.models` não fecha ciclo algum. O import lazy de
  `apps/estoque/views.py:221` é para `services.ciclo_vida`, que de fato importa estoque de volta —
  caso diferente, não precedente aqui. Verificação: `uv run mypy apps` mais a suíte completa.
- `apps/estoque/policies.py::pode_consultar_movimentacoes_estoque` — **corpo inalterado**; só a
  docstring, que hoje afirma espelhar o universo do selector. Passa a explicitar, nos moldes de
  `pode_consultar_historico_requisicoes`, que a policy decide apenas o acesso à página; o auxiliar de
  setor entra, mas vê apenas o que criou.
- `docs/matriz-permissoes.md` — §4 (linha "Consultar histórico de movimentações"), §5 (bullet do
  ledger) e §7 (item resolvido da US-17, que hoje repete a regra antiga).
- Testes: `apps/estoque/tests/conftest.py`, `test_selectors.py`, `test_views.py`.

### Não muda

- `pode_filtrar_movimentacoes_por_setor` — já é exclusivo de almoxarifado/superusuário; chefe e
  auxiliar de setor nunca tiveram o filtro de setor.
- `apps/requisicoes/context_processors.py` e `apps/core/templatetags/core_tags.py` — consomem a flag
  `pode_consultar_movimentacoes_estoque`, cujo resultado não muda. O item de menu continua visível
  para o auxiliar de setor.
- `historico_movimentacoes_view` — continua delegando o escopo ao selector; nenhuma linha muda.
- Visibilidade de saídas excepcionais (ficam fora do ramo de setor por construção: `requisicao`
  nulo), superusuário, almoxarifado, solicitante puro e inativo.
- Timeline da requisição, detalhe de requisição, `requisicoes_visiveis_para`.
- Schema, models, migrations.

## Arquivos tocados

| Arquivo | Símbolo | Ação |
|---|---|---|
| `apps/estoque/selectors.py` | `movimentacoes_visiveis_para` | Restringir ramo de setor + atualizar docstring RBAC |
| `apps/estoque/policies.py` | `pode_consultar_movimentacoes_estoque` | Só docstring (deixa de prometer espelho exato) |
| `docs/matriz-permissoes.md` | §4, §5, §7 | Emendar a regra e registrar a decisão da #112 |
| `apps/estoque/tests/conftest.py` | novas fixtures | `movimentacao_requisicao_do_aux`, `movimentacao_criada_pelo_chefe`, `movimentacao_requisicao_rascunho`, `aux_lotacao_divergente` |
| `apps/estoque/tests/test_selectors.py` | `TestMovimentacoesVisiveisPara` | Reescrever caso do auxiliar; reforçar caso do chefe; converter asserções para conjuntos exatos de IDs |
| `apps/estoque/tests/test_views.py` | `TestHistoricoMovimentacoesView` | Caso de view para auxiliar de setor |

## Estratégia de testes

Fronteira de segurança vive no selector, então o peso dos testes fica em `test_selectors.py`; a view
ganha apenas o caso de contrato HTTP.

Quatro fixtures novas em `apps/estoque/tests/conftest.py`. Cada uma monta uma requisição mais a
`MovimentacaoEstoque` vinculada; o estado é `AUTORIZADA`, salvo onde indicado:

- `movimentacao_requisicao_do_aux` — `criador=aux_obras`, `setor_beneficiario=setor_obras`.
  Necessária porque a fixture `requisicao_autorizada` tem `criador=solicitante`; sob a regra nova ela
  deixa de ser visível ao auxiliar, e sem esta fixture não haveria caso positivo para ele.
- `movimentacao_criada_pelo_chefe` — `criador=chefe_obras`, `setor_beneficiario` em um setor que ele
  **não** chefia. Cobre o termo `Q(requisicao__criador_id=...)` no ramo do chefe.
- `movimentacao_requisicao_rascunho` — requisição em `RASCUNHO` com `criador=aux_obras`, mais uma
  `MovimentacaoEstoque` construída direto no model (nenhum service produz esse par). Cobre o termo
  `~Q(requisicao__estado=RASCUNHO)`.
- `aux_lotacao_divergente` — usuário com `User.setor` = setor TI e `VinculoAuxiliar` ativo em obras,
  mais uma requisição criada por ele para si (`setor_beneficiario` = TI) e a movimentação
  correspondente. Materializa o contraexemplo da invariante de ampliação.

**Forma das asserções**: todo caso do selector compara o **conjunto exato de IDs** retornado com o
conjunto esperado (`set(qs.values_list('pk', flat=True)) == {...}`), nunca `exists()` /
`filter(...).exists()` isolados. Asserção de inclusão deixa passar movimentação extra vazada, que é
exatamente a classe de bug desta issue. Os casos existentes de `TestMovimentacoesVisiveisPara` que
hoje usam inclusão/ausência isolada são convertidos junto.

**Cenário base**: os casos 1, 4 e 5 compartilham exatamente o mesmo conjunto de fixtures, para que os
conjuntos esperados sejam comparáveis entre papéis — `requisicao_autorizada` (criador `solicitante`,
setor obras), `movimentacao_requisicao_do_aux` (criador `aux_obras`, setor obras), `saida_registrada`
(sem requisição), `movimentacao_outro_setor` (setor TI) e `movimentacao_requisicao_rascunho`. O caso 6
usa o cenário base **acrescido** de `movimentacao_criada_pelo_chefe`, e é o único que a inclui. Cada
caso declara o conjunto esperado por completo, nomeando as fixtures. Os casos 3, 7 e 8 montam
cenários próprios, declarados no próprio teste.

Selector (`TestMovimentacoesVisiveisPara`):

1. **Auxiliar de setor vê o que criou** — no cenário canônico, o conjunto de `aux_obras` é
   exatamente `{movimentacao_requisicao_do_aux.pk}`.
2. **Auxiliar de setor não vê o resto do setor** (regressão da #112) — coberto pela igualdade do
   caso 1: a movimentação de `requisicao_autorizada` (criada pelo `solicitante`, mesmo setor obras)
   fica fora do conjunto. Substitui o `test_aux_setor_ve_so_proprio_setor` atual, que asseverava o
   oposto.
3. **Auxiliar lotado e vinculado em setores distintos** — cenário com `aux_lotacao_divergente`
   (lotação em TI, vínculo de auxiliar em obras, requisição criada para si com `setor_beneficiario` =
   TI) **mais** `requisicao_autorizada`, que é de terceiro (`solicitante`) no setor obras, onde ele
   tem o vínculo. O conjunto esperado é exatamente `{movimentação própria de aux_lotacao_divergente}`.
   Sem a movimentação de terceiro no cenário, o teste passaria mesmo se o selector devolvesse todo o
   setor obras — é ela que torna a asserção capaz de falhar. Prova, em um só caso, a ampliação
   intencional descrita nas invariantes e o não-vazamento de obras.
4. **Movimentação vinculada a rascunho não aparece** — `movimentacao_requisicao_rascunho` fica fora
   do conjunto tanto de `aux_obras` (que criou o rascunho) quanto de `chefe_obras` (que chefia o
   setor). Coberto pelas igualdades dos casos 1 e 5; o caso 4 existe para nomear o termo
   `~Q(...RASCUNHO)` como comportamento asseverado, e não como efeito colateral.
5. **Chefe de setor mantém a visão de setor** — no cenário canônico, o conjunto de `chefe_obras` é
   exatamente `{movimentacoes de requisicao_autorizada} | {movimentacao_requisicao_do_aux.pk}`. A
   segunda entra porque `movimentacao_requisicao_do_aux` tem `setor_beneficiario = setor_obras`, que
   é o setor chefiado — o chefe supervisiona o setor, incluindo o que o auxiliar criou. Ficam de fora
   `saida_registrada`, `movimentacao_outro_setor` e `movimentacao_requisicao_rascunho`.
6. **Chefe de setor vê também o que criou fora do setor chefiado** — acrescentando
   `movimentacao_criada_pelo_chefe` ao cenário canônico, o conjunto de `chefe_obras` é o do caso 5
   mais exatamente esse ID. Fecha o espelho com `historico_requisicoes_visiveis_para`.
7. **Almoxarifado (chefe e auxiliar) e superusuário** — conjunto igual ao de todas as
   `MovimentacaoEstoque` do cenário, incluindo saídas excepcionais e a de rascunho (esses ramos não
   filtram estado). Inalterado no comportamento.
8. **Solicitante puro, inativo, inexistente** — conjunto vazio. Inalterados.

View (`TestHistoricoMovimentacoesView`):

9. **Auxiliar de setor recebe 200** — acesso à página preservado (a policy não mudou).
10. **IDs em `page_obj.object_list` do auxiliar** batem exatamente com
    `movimentacoes_visiveis_para(aux_obras.pk)`, e o conjunto do `chefe_obras` no mesmo cenário é
    estritamente maior — prova de que o recorte chegou à tela.

Policies (`test_policies.py`): sem mudança de asserção — `pode_consultar_movimentacoes_estoque(AUX_OBRAS)`
continua `True`. Os testes existentes seguem verdes e viram regressão da decisão.

## Invariantes

- **Fronteira de segurança no selector** (ADR-0004 / `docs/CONVENTIONS.md`): a view e o template
  nunca decidem visibilidade. A mudança fica inteiramente no selector.
- **Recorte por autoria, não subconjunto estrito**: o universo do auxiliar de setor **não** é
  subconjunto estrito do anterior. `VinculoAuxiliar` é independente de `User.setor`
  (`apps/accounts/papeis.py::papel_efetivo` monta `setores_em_escopo` a partir dos vínculos ativos e
  do setor chefiado, nunca da lotação), e `pode_criar_para_beneficiario` deixa qualquer usuário com
  setor criar para si. Logo, um auxiliar lotado no setor A e vinculado ao setor B pode criar uma
  requisição para si com `setor_beneficiario = A`: o filtro antigo por `setores_em_escopo` = {B} a
  excluía; o termo `Q(requisicao__criador_id=ator.pk)` a inclui. **A ampliação é intencional** — é
  exatamente o que `historico_requisicoes_visiveis_para` já concede ao auxiliar desde a #106, e o
  detalhe da requisição também abre para o criador, então não há metadado listado que o detalhe
  negue. O mesmo vale para o chefe de setor com requisições que criou fora do setor que chefia.
  O ganho, nos dois casos, é restrito a requisições de **autoria do próprio ator**; para requisições
  de terceiros o recorte só encolhe. Nenhum outro papel muda.
- **Coerência com o detalhe (#106)**: o ledger deixa de listar metadados de requisições cujo detalhe
  devolve 404 ao auxiliar.
- **Rascunho fora do ramo de setor**: o predicado exclui `EstadoRequisicao.RASCUNHO` explicitamente,
  sem depender de nenhum service se comportar bem — o model aceita `requisicao` anulável e não tem
  constraint de estado. Mesma regra do histórico de requisições (#106).
- **Saída excepcional fora do escopo de setor**: preservado por construção (`requisicao` nulo nunca
  casa com os dois termos do `Q`).
- **Policy ≠ selector é intencional e documentado**: `pode_consultar_movimentacoes_estoque` decide
  acesso à página; o quanto se vê é do selector. Mesmo contrato já aceito em
  `pode_consultar_historico_requisicoes`.

## Riscos

- **Página vazia para o auxiliar de setor que nunca criou requisição.** Aceito: é exatamente o
  comportamento já em produção no histórico de requisições desde a #106, e o empty state do ledger
  já existe (`test_empty_state_quando_ledger_vazio`).
- **Divergência documental viva.** A §4/§5 da matriz e o `.design/movimentacoes-estoque/DESIGN_BRIEF.md`
  citam a ratificação de grill da US-17. A emenda precisa dizer explicitamente que a #112 substitui
  aquela regra, senão a próxima auditoria reabre o mesmo achado. O brief de design é handoff de UI e
  não normativo sobre RBAC — não será reescrito; a matriz é a fonte.
- **Performance a verificar, não a presumir**: o predicado novo troca um `IN` por um `OR` entre duas
  colunas mais um `NOT` de estado. `OR` entre colunas indexadas pode virar plano diferente (varredura
  em vez de uso de índice), e `select_related` não influencia o filtro. Critério: rodar
  `movimentacoes_visiveis_para(<chefe>).explain()` e `.explain()` do auxiliar contra o volume do
  `seed_dev`, comparando com o predicado antigo; o que se checa é se o acesso a
  `requisicao__setor_beneficiario_id` deixou de usar índice e virou varredura sequencial. Se virar,
  fica registrado aqui como dívida com número medido — não se afirma ausência de impacto sem esse
  passo.
- **Sem risco de concorrência, contrato OpenAPI, mutação de estoque ou transição de estado**: a
  mudança é somente de leitura.
