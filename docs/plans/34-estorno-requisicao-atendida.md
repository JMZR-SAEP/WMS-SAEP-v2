# Plano — Issue #34: Estorno de requisição atendida (TR-021/022)

## Escopo

**O que muda:**
- `apps/requisicoes/transitions.py` — adicionar `ATENDIDA → ESTORNADA` (TR-021)
- `apps/requisicoes/policies.py` — `pode_estornar_requisicao` / `exigir_pode_estornar_requisicao` (chefe almox only)
- `apps/requisicoes/services.py` — `estornar_requisicao(*, ator_id, requisicao_id, justificativa)`
- `apps/requisicoes/forms.py` — `EstornarRequisicaoForm` (justificativa obrigatória)
- `apps/requisicoes/views.py` — `estornar_requisicao_view` + `pode_estornar` em `_detalhe_context`
- `apps/requisicoes/urls.py` — `<int:pk>/estornar/`
- `apps/requisicoes/templates/requisicoes/partials/_modal_form_estorno.html` — novo
- `apps/requisicoes/templates/requisicoes/detalhe.html` — botão + include do modal
- `apps/requisicoes/tests/test_services.py` — testes do service
- `apps/requisicoes/tests/test_policies.py` — testes da policy
- `apps/requisicoes/tests/test_views.py` — testes da view

**O que NÃO muda:**
- `apps/requisicoes/models.py` — `EstadoRequisicao.ESTORNADA` e `EventoTimeline.ESTORNO` já existem
- `apps/estoque/models.py` — `TipoMovimentacaoEstoque.ESTORNO_REQUISICAO` já existe
- `apps/estoque/selectors.py` — `TIPOS_MOVIMENTO_ENTREGA_LIQUIDA` já inclui `ESTORNO_REQUISICAO`
- `templates/requisicoes/partials/_estado_badge.html` — badge `estornada` já implementado
- Nenhuma mudança de schema/migration — campo `estado` já suporta `estornada`
- Estorno parcial fora de escopo (spec: estorno total da entregue líquida atual)

## Arquivos tocados — mapeamento Serena

| Arquivo | Símbolo | Operação |
|---|---|---|
| `apps/requisicoes/transitions.py` | `TRANSICOES_VALIDAS` | `replace_symbol_body` — adicionar `ESTORNADA` como destino de `ATENDIDA` |
| `apps/requisicoes/policies.py` | (último símbolo) | `insert_after_symbol` — `pode_estornar_requisicao` + `exigir_pode_estornar_requisicao` |
| `apps/requisicoes/services.py` | `copiar_requisicao` | `insert_after_symbol` — `estornar_requisicao` |
| `apps/requisicoes/forms.py` | `RegistrarDevolucaoForm` | `insert_after_symbol` — `EstornarRequisicaoForm` |
| `apps/requisicoes/views.py` | `_detalhe_context` | `replace_symbol_body` — adicionar `pode_estornar` no contexto |
| `apps/requisicoes/views.py` | `registrar_devolucao_view` | `insert_after_symbol` — `estornar_requisicao_view` |
| `apps/requisicoes/urls.py` | (arquivo inteiro) | `replace_content` — adicionar rota `/estornar/` |
| Templates | (novos/edits) | `Write` / `Edit` |
| `apps/requisicoes/tests/test_services.py` | `test_registrar_devolucao_requisicao_inexistente` | `insert_after_symbol` — bloco de testes estorno |
| `apps/requisicoes/tests/test_policies.py` | (último símbolo) | `insert_after_symbol` — testes da policy |
| `apps/requisicoes/tests/test_views.py` | (último símbolo) | `insert_after_symbol` — testes da view |

## Estratégia de testes

### Service `estornar_requisicao`

**Caminho feliz:**
- `test_estornar_requisicao_caminho_feliz`: saldo_fisico sobe por item, estado = ESTORNADA, timeline ESTORNO registrada, ledger ESTORNO_REQUISICAO emitido, entregue_liquida pós-estorno = 0.

**Bloqueios pós-estorno (TR-019/022):**
- `test_estornar_requisicao_ja_estornada_levanta_estado_invalido`: estornar estornada levanta `EstadoInvalido`.
- `test_registrar_devolucao_em_estornada_levanta_estado_invalido`: `registrar_devolucao` em estado `estornada` levanta `EstadoInvalido`.
- `test_cancelar_requisicao_em_estornada_levanta_estado_invalido`: cancelar em `estornada` levanta `EstadoInvalido`.

**Permissão:**
- `test_estornar_requisicao_auxiliar_almox_negado`: auxiliar almox → `PermissaoNegada`.
- `test_estornar_requisicao_criador_negado`: criador → `PermissaoNegada`.
- `test_estornar_requisicao_aceita_chefe_almox`: chefe almox → OK.
- `test_estornar_requisicao_aceita_superuser`: superuser → OK.

**Justificativa obrigatória:**
- `test_estornar_requisicao_sem_justificativa_levanta_dados_invalidos`: justificativa vazia/nula → `DadosInvalidos`.

**Entregue líquida correta sob devoluções:**
- `test_estornar_requisicao_respeita_liquida_pos_devolucao`: após devolução parcial, estorno só reverte o líquido restante, não o bruto.

**Casos de borda:**
- `test_estornar_requisicao_estado_invalido`: tentar em `autorizada` → `EstadoInvalido`.
- `test_estornar_requisicao_ator_inexistente`: ator_id inexistente → `DadosInvalidos`.
- `test_estornar_requisicao_requisicao_inexistente`: requisicao_id inexistente → `DadosInvalidos`.

### Policy `pode_estornar_requisicao`

- `test_pode_estornar_ativo_chefe_almox`: True.
- `test_pode_estornar_ativo_aux_almox`: False (não é chefe).
- `test_pode_estornar_usuario_inativo`: False.
- `test_pode_estornar_superuser`: True.
- `test_exigir_pode_estornar_levanta_permissao_negada`: auxiliar → PermissaoNegada.

### View `estornar_requisicao_view`

- `test_estornar_view_sucesso_redireciona`: POST com justificativa válida → redirect detalhe + mensagem success.
- `test_estornar_view_sem_justificativa_exibe_warning`: POST sem justificativa → redirect detalhe + warning.
- `test_estornar_view_sem_permissao_levanta_403`: auxiliar almox → 403.
- `test_estornar_view_get_nao_permitido`: GET → 405.

## Invariantes verificados

Da `docs/matriz-invariantes.md` / `docs/estado-transicoes-requisicao.md`:

- **ITEM-02 / EST-03**: estorno inverte a baixa — `saldo_fisico += entregue_liquida` por item.
- **EST-06**: lock order: `Requisicao` primeiro, depois `SaldoEstoque` em ordem `(estoque_id, material_id, id)` crescente.
- **TR-021**: só chefe de almoxarifado; justificativa obrigatória; calcula entregue líquida (não bruta) para cada item.
- **TR-022**: `ESTORNADA` não tem transições declaradas em `TRANSICOES_VALIDAS` → qualquer transição lança `EstadoInvalido`. Devolução bloqueada pela policy (`estado != ATENDIDA`). Cancelamento bloqueado pela policy (`estados_cancelaveis` whitelist não inclui `ESTORNADA`).
- **ADR-0005**: transação atômica, `select_for_update` na requisição, `select_for_update` nos saldos em ordem determinística.
- **ADR-0011**: service recebe `ator_id`/`requisicao_id` (nunca instâncias), keyword-only, lança exceções de domínio canônicas.

## Riscos

- Nenhum risco de concorrência adicional — lock pattern idêntico ao `registrar_devolucao`.
- `entregue_liquida_por_item` já inclui `ESTORNO_REQUISICAO` em `TIPOS_MOVIMENTO_ENTREGA_LIQUIDA`, então re-estorno (TR-022) seria bloqueado por `EstadoInvalido` antes de chegar ao cálculo de líquida — sem risco de double-count.
- Sem mudança de schema.
