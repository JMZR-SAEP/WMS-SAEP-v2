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
  `filter(requisicao__setor_beneficiario_id__in=setores)` para
  `filter(Q(requisicao__criador_id=ator.pk) | Q(requisicao__setor_beneficiario_id=setor_chefiado_ativo_id))`,
  com o segundo termo presente apenas quando `setor_chefiado_ativo_id is not None`.
- `apps/estoque/policies.py::pode_consultar_movimentacoes_estoque` — **corpo inalterado**; só a
  docstring, que hoje afirma espelhar o universo do selector. Passa a explicitar, nos moldes de
  `pode_consultar_historico_requisicoes`, que decide apenas o acesso à página e que o auxiliar de
  setor entra mas vê só o que criou.
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
| `apps/estoque/tests/conftest.py` | novas fixtures | `movimentacao_requisicao_do_aux` e `movimentacao_criada_pelo_chefe` |
| `apps/estoque/tests/test_selectors.py` | `TestMovimentacoesVisiveisPara` | Reescrever caso do auxiliar; reforçar caso do chefe |
| `apps/estoque/tests/test_views.py` | `TestHistoricoMovimentacoesView` | Caso de view para auxiliar de setor |

## Estratégia de testes

Fronteira de segurança vive no selector, então o peso dos testes fica em `test_selectors.py`; a view
ganha apenas o caso de contrato HTTP.

Duas fixtures novas em `apps/estoque/tests/conftest.py`, ambas montando requisição em `AUTORIZADA`
mais uma `MovimentacaoEstoque` vinculada:

- `movimentacao_requisicao_do_aux` — `criador=aux_obras`, `setor_beneficiario=setor_obras`.
  Necessária porque a fixture `requisicao_autorizada` tem `criador=solicitante`; sob a regra nova ela
  deixa de ser visível ao auxiliar, e sem esta fixture não haveria caso positivo para ele.
- `movimentacao_criada_pelo_chefe` — `criador=chefe_obras`, `setor_beneficiario` em um setor que ele
  **não** chefia. Cobre o termo `Q(requisicao__criador_id=...)` no ramo do chefe.

Selector (`TestMovimentacoesVisiveisPara`):

1. **Auxiliar de setor vê o que criou** — com `movimentacao_requisicao_do_aux`, o selector para
   `aux_obras` contém essa movimentação.
2. **Auxiliar de setor não vê o resto do setor** (regressão da #112) — a movimentação de
   `requisicao_autorizada` (criada pelo `solicitante`, mesmo setor obras) **não** aparece para
   `aux_obras`. Substitui o `test_aux_setor_ve_so_proprio_setor` atual, que asseverava o oposto.
3. **Auxiliar de setor não vê saída excepcional** — mantido.
4. **Chefe de setor mantém a visão de setor** — `requisicao_autorizada` continua visível ao
   `chefe_obras`; sem saída excepcional; sem `movimentacao_outro_setor`.
5. **Chefe de setor vê também o que criou fora do setor chefiado** — movimentação de requisição
   criada pelo `chefe_obras` com `setor_beneficiario` = outro setor aparece. Fecha o espelho com
   `historico_requisicoes_visiveis_para`.
6. **Almoxarifado (chefe e auxiliar) e superusuário** — inalterados, veem tudo incluindo saídas
   excepcionais.
7. **Solicitante puro, inativo, inexistente** — inalterados, vazio.

View (`TestHistoricoMovimentacoesView`):

8. **Auxiliar de setor recebe 200** — acesso à página preservado (a policy não mudou).
9. **`page_obj.paginator.count` do auxiliar bate com `movimentacoes_visiveis_para(aux_obras.pk)`** e
   é menor que o do `chefe_obras` no mesmo cenário — prova de que o recorte chegou à tela.

Policies (`test_policies.py`): sem mudança de asserção — `pode_consultar_movimentacoes_estoque(AUX_OBRAS)`
continua `True`. Os testes existentes seguem verdes e viram regressão da decisão.

## Invariantes

- **Fronteira de segurança no selector** (ADR-0004 / `docs/CONVENTIONS.md`): a view e o template
  nunca decidem visibilidade. A mudança fica inteiramente no selector.
- **Não-ampliação para o auxiliar de setor**: o universo novo é subconjunto estrito do anterior.
  Para o chefe de setor há uma ampliação deliberada e delimitada — as requisições que ele mesmo criou
  com `setor_beneficiario` fora do setor que chefia, que `historico_requisicoes_visiveis_para` já lhe
  concede desde a #106. Alinhar as duas fronteiras é o objetivo da entrega, e o ganho é restrito a
  requisições de autoria do próprio ator. Nenhum outro papel muda.
- **Coerência com o detalhe (#106)**: o ledger deixa de listar metadados de requisições cujo detalhe
  devolve 404 ao auxiliar.
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
- **Performance**: o `Q(...)` novo troca um `IN` por um `OR` de duas colunas indexadas
  (`requisicao__criador_id`, `requisicao__setor_beneficiario_id`) sobre um queryset já `select_related`.
  Sem mudança de plano relevante no volume do MVP.
- **Sem risco de concorrência, contrato OpenAPI, mutação de estoque ou transição de estado**: a
  mudança é somente de leitura.
