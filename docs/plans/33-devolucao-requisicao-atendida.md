# Plano — Issue #33: Devolução de requisição atendida (TR-020)

## Scope

**O que muda:**
- `transitions.py` — ATENDIDA → {ATENDIDA} para TR-020
- `policies.py` — `pode_registrar_devolucao` / `exigir_pode_registrar_devolucao`
- `services.py` (requisicoes) — `registrar_devolucao`
- `forms.py` — `RegistrarDevolucaoForm`
- `views.py` — `registrar_devolucao_view`; `_detalhe_context` recebe `pode_devolver` e itens com entregue líquida
- `urls.py` — `<pk>/devolver/<item_pk>/`
- `partials/_modal_form_devolucao.html` — fragment modal com quantidade + observação
- `detalhe.html` — botão "Registrar devolução" por item quando atendida + entregue_liquida > 0

**O que NÃO muda:**
- Estorno de requisição (TR-021/022) — fora de escopo
- Devolução de saída excepcional (SAE-07) — já implementado separadamente
- Estado da requisição — permanece ATENDIDA

## Ficheiros tocados

| Arquivo | Motivo |
|---|---|
| `apps/requisicoes/transitions.py` | Adicionar ATENDIDA no mapa |
| `apps/requisicoes/policies.py` | Novas funções pode_*/exigir_pode_* |
| `apps/requisicoes/services.py` | `registrar_devolucao` |
| `apps/requisicoes/forms.py` | `RegistrarDevolucaoForm` |
| `apps/requisicoes/views.py` | view + contexto detalhe |
| `apps/requisicoes/urls.py` | URL `<pk>/devolver/<item_pk>/` |
| `apps/requisicoes/templates/requisicoes/partials/_modal_form_devolucao.html` | Fragment modal |
| `apps/requisicoes/templates/requisicoes/detalhe.html` | Botão por item |
| `apps/requisicoes/tests/test_services.py` | Testes de `registrar_devolucao` |
| `apps/requisicoes/tests/test_policies.py` | Testes de `pode_registrar_devolucao` |
| `apps/requisicoes/tests/test_views.py` | Testes de `registrar_devolucao_view` |

## Contrato de `registrar_devolucao`

```python
@transaction.atomic
def registrar_devolucao(
    *,
    ator_id: int,
    requisicao_id: int,
    item_id: int,
    quantidade: Decimal,
    observacao: str = '',
) -> Requisicao:
```

Fluxo interno:
1. `User.objects.get(pk=ator_id)` — DadosInvalidos se não encontrado
2. `Requisicao.objects.select_for_update().get(pk=requisicao_id)` — DadosInvalidos se não encontrado
3. Valida `estado == ATENDIDA` → EstadoInvalido
4. `exigir_pode_registrar_devolucao(ator, requisicao)` → PermissaoNegada
5. `verificar_transicao_valida(ATENDIDA, ATENDIDA)` — declarativo
6. Valida `quantidade > 0` → DadosInvalidos
7. `entregue_liquida = entregue_liquida_por_item(requisicao_id, item_id)` — DadosInvalidos se item não pertence
8. Valida `quantidade <= entregue_liquida` → ConflitoDominio (código `quantidade_excede_entregue_liquida`)
9. `ItemRequisicao.objects.get(pk=item_id)` para obter `material_id`
10. `SaldoEstoque.objects.select_for_update().get(material_id=..., estoque__classificacao=ALMOXARIFADO)` — ConflitoDominio se não encontrado
11. Valida `material.ativo` → ConflitoDominio
12. `saldo.saldo_fisico += quantidade; saldo.save(update_fields=[...])`
13. `_registrar_movimentacao(tipo=DEVOLUCAO, delta_fisico=+quantidade, delta_reservado=0, origem=OrigemMovimentacaoEstoque.de_requisicao(requisicao), ator_id=ator_id)`
14. `TimelineRequisicao.objects.create(evento=DEVOLUCAO_REGISTRADA, estado_resultante=ATENDIDA, metadata={'quantidade': str(quantidade), 'item_id': item_id, 'observacao': observacao_limpa})`
15. Retorna `requisicao`

**Lock order (ADR-0005):** Requisicao primeiro, depois SaldoEstoque.

## Test strategy

### test_services.py
- Caminho feliz: saldo_fisico sobe, estado permanece ATENDIDA, timeline criada com DEVOLUCAO_REGISTRADA, MovimentacaoEstoque(tipo=devolucao, delta_fisico=+quantidade)
- Bloqueio: quantidade > entregue_liquida → ConflitoDominio
- Bloqueio double-count: devolução anterior reduz entregue_liquida, nova devolução respeita limite restante
- Estado inválido: devolução em rascunho → EstadoInvalido
- Permissão negada: solicitante comum → PermissaoNegada
- Material inativo → ConflitoDominio
- quantidade zero → DadosInvalidos
- item_id não pertence à requisição → DadosInvalidos
- ator inexistente → DadosInvalidos
- requisicao inexistente → DadosInvalidos

### test_policies.py
- `pode_registrar_devolucao`: aux_almoxarifado → True, chefe_almoxarifado → True, superuser → True, solicitante → False, inativo → False

### test_views.py
- POST com dados válidos → redirect detalhe + mensagem success
- POST com quantidade > entregue_liquida → warning + redirect
- POST ator sem permissão → PermissionDenied 403
- GET não permitido → 405

## Invariants (ADR-0005, EST-01, EST-06)

- Lock: Requisicao primeiro, SaldoEstoque depois, mesma transação
- saldo_fisico nunca negativo após devolução (devolução só soma)
- saldo_reservado inalterado
- estado da requisição permanece ATENDIDA
- ledger emitido na mesma transação do saldo

## Risks

- `entregue_liquida_por_item` lê o ledger sem lock — leitura pura dentro da transação que já travou Requisicao (ADR-0015 §8, correto)
- Stoque com múltiplos saldos por material (saldo_ambiguo) — coberto por ConflitoDominio
