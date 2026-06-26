# Plano #50 — Seam de saldo por comandos de negócio; entregue_liquida por referência; quebra import reverso

## Scope

**O que muda:**
- Novos comandos públicos `registrar_devolucao_estoque` e `estornar_requisicao_estoque` em `apps/estoque/services.py`
- `apps/estoque/types.py` criado com os TypedDicts do seam (`ItemReservaEstoque`, `ItemLiberacaoReserva`, `ItemAtendimentoSaldo`)
- `entregue_liquida_por_item` renomeado para `entregue_liquida_por_material` com assinatura `(*, requisicao_id, material_id)` — remove importação reversa de `requisicoes.models`
- `_registrar_atualizacao_estoque_relevante` movida de `estoque/services.py` para `requisicoes/services/ciclo_vida.py` como `registrar_timeline_divergencia_importacao` — remove a segunda importação reversa
- `requisicoes/services/atendimento.py` e `ciclo_vida.py` migrados para os novos comandos; removem `SaldoEstoque`, `TipoMovimentacaoEstoque` e `_registrar_movimentacao` diretos
- `confirmar_importacao_scpi` retorna `(importacao, linhas)` para o VIEW coordenar o hook de timeline
- VIEW `confirmar_importacao_scpi_view` passa a ser `@transaction.atomic`, chama ambos os serviços

**O que NÃO muda:**
- `OrigemMovimentacaoEstoque` permanece em `estoque/services.py`
- Comportamento de saldo, contratos de reserva/liberação/consumo
- `liberar_reservas_para_cancelamento` (já é comando público, cancelamento.py não precisa mudar)
- URL contracts, templates, forms

## Dependências atuais (o problema)

### Importações reversas `estoque → requisicoes` (bloqueadores)

| Arquivo | Símbolo | Importa de |
|---------|---------|-----------|
| `apps/estoque/selectors.py::entregue_liquida_por_item` | `ItemRequisicao` | `apps.requisicoes.models` |
| `apps/estoque/services.py::_registrar_atualizacao_estoque_relevante` | `EstadoRequisicao, EventoTimeline, ItemRequisicao, TimelineRequisicao` | `apps.requisicoes.models` |

### Importações de private `_registrar_movimentacao` por `requisicoes`

| Arquivo | Causa |
|---------|-------|
| `apps/requisicoes/services/atendimento.py::registrar_devolucao` | lock manual de `SaldoEstoque` + chamada direta |
| `apps/requisicoes/services/ciclo_vida.py::estornar_requisicao` | lock manual de `SaldoEstoque` + chamada direta |

## Files touched

| Arquivo | Tipo de mudança |
|---------|----------------|
| `apps/estoque/types.py` | CRIAR — TypedDicts do seam |
| `apps/estoque/selectors.py` | MODIFICAR — renomear `entregue_liquida_por_item` → `entregue_liquida_por_material`; remover `ItemRequisicao` import |
| `apps/estoque/services.py` | MODIFICAR — add `registrar_devolucao_estoque`, `estornar_requisicao_estoque`; remover `_registrar_atualizacao_estoque_relevante`; mudar return de `confirmar_importacao_scpi` para `(importacao, linhas)` |
| `apps/estoque/tests/test_selectors.py` | MODIFICAR — atualizar chamadas `entregue_liquida_por_item` → `entregue_liquida_por_material(material_id=...)` |
| `apps/estoque/tests/test_services.py` | MODIFICAR — unpack `(importacao, linhas)` no retorno de `confirmar_importacao_scpi`; add testes dos novos comandos |
| `apps/requisicoes/services/atendimento.py` | MODIFICAR — `registrar_devolucao` usa `registrar_devolucao_estoque`; resolve `item.material_id` antes de chamar |
| `apps/requisicoes/services/ciclo_vida.py` | MODIFICAR — `estornar_requisicao` usa `estornar_requisicao_estoque`; add `registrar_timeline_divergencia_importacao`; remove imports privados de estoque |
| `apps/requisicoes/views.py` | MODIFICAR — `entregue_liquida_por_material(material_id=item.material_id)` |
| `apps/requisicoes/tests/test_services.py` | MODIFICAR — atualizar chamadas do seletor renomeado |
| `apps/estoque/tests/test_selectors.py` | MODIFICAR — atualizar assinatura |
| `apps/notificacoes/tests/test_services.py` | MODIFICAR — unpack `(importacao, linhas)` |
| `apps/estoque/views.py` | MODIFICAR — `@transaction.atomic`; unpack `(importacao, linhas)`; chamar `registrar_timeline_divergencia_importacao` |

## Novos comandos de estoque

### `registrar_devolucao_estoque`

```python
@transaction.atomic
def registrar_devolucao_estoque(
    *,
    requisicao_id: int,
    material_id: int,
    quantidade: Decimal,
    ator_id: int,
) -> None:
```

**Responsabilidade:** lock de `SaldoEstoque`, validação de material ativo e saldo único, validação `quantidade <= entregue_liquida`, incremento de `saldo_fisico`, emissão de `MovimentacaoEstoque(DEVOLUCAO)`.

**Pré-condições do chamador:** Requisicao já travada (`select_for_update`); `ator_id` e `item` já validados.

**Fluxo interno:**
1. Lock `SaldoEstoque` para `material_id` em ordem `(estoque_id, material_id, id)`
2. Validar saldo existe e não é ambíguo (`ConflitoDominio`)
3. Validar `material.ativo` (`ConflitoDominio`)
4. Computar `entregue_liquida = entregue_liquida_por_material(requisicao_id, material_id)`
5. Validar `quantidade > 0` e `quantidade <= entregue_liquida` (`DadosInvalidos` / `ConflitoDominio`)
6. `saldo.saldo_fisico += quantidade; saldo.save(update_fields=['saldo_fisico'])`
7. `_registrar_movimentacao(DEVOLUCAO, origem=OrigemMovimentacaoEstoque(requisicao_id=requisicao_id), ...)`

### `estornar_requisicao_estoque`

```python
@transaction.atomic
def estornar_requisicao_estoque(
    *,
    requisicao_id: int,
    material_ids: list[int],
    ator_id: int,
) -> None:
```

**Responsabilidade:** para cada material com `entregue_liquida > 0`, restaura `saldo_fisico` e emite `MovimentacaoEstoque(ESTORNO_REQUISICAO)`. Levanta `ConflitoDominio` se nenhum material tem entregue líquida > 0.

**Pré-condições do chamador:** Requisicao já travada; `ator_id` validado; `material_ids` extraídos dos itens da requisicao.

**Fluxo interno:**
1. Computar `entregue_liquida_por_material` para cada `material_id` (leitura ledger, sem lock)
2. Filtrar `itens_com_liquida = [(mid, liq) for ... if liq > 0]`
3. Se `itens_com_liquida` vazio → `ConflitoDominio('Não há entregue líquida a estornar.', code='sem_liquida_para_estorno')`
4. Lock `SaldoEstoque` para os `material_ids` com liquida > 0, ordem `(estoque_id, material_id, id)`
5. Para cada: validar saldo único; `saldo.saldo_fisico += liquida; saldo.save(...)`
6. `_registrar_movimentacao(ESTORNO_REQUISICAO, origem=..., ...)`

### Mudança de assinatura: `entregue_liquida_por_material`

```python
def entregue_liquida_por_material(*, requisicao_id: int, material_id: int) -> Decimal:
```

Remove importação de `apps.requisicoes.models.ItemRequisicao`. O cálculo via `MovimentacaoEstoque` permanece idêntico — apenas não resolve mais `item_id → material_id`, pois o chamador já passa `material_id` diretamente.

**Callers que precisam de `item.material_id` antes de chamar:**
- `atendimento.py::registrar_devolucao` — já tem `item = ItemRequisicao.objects.get(...)`; usa `item.material_id`
- `ciclo_vida.py::estornar_requisicao` — itera `requisicao.itens`; usa `item.material_id`
- `views.py::detalhe_requisicao_view` — itera `itens`; usa `item.material_id`
- Testes em `test_selectors.py` e `test_services.py` — passam `material_id` direto

### Quebra da aresta `estoque → requisicoes`

#### `entregue_liquida_por_item` → `entregue_liquida_por_material`

O seletor deixa de importar `ItemRequisicao`. A referência por `material_id` é exatamente o contrato do ADR-0015 §3 ("granularidade por material; sem FK de item").

#### `_registrar_atualizacao_estoque_relevante` → `registrar_timeline_divergencia_importacao`

Movida para `apps/requisicoes/services/ciclo_vida.py` (ou novo `apps/requisicoes/services/hooks_estoque.py`). Mantém a mesma lógica: encontra requisições AUTORIZADAS afetadas por divergência crítica de saldo e cria `TimelineRequisicao`.

`confirmar_importacao_scpi` passa a retornar `tuple[ImportacaoSCPI, list]` — `(importacao, linhas)` — e não chama mais o hook internamente.

`confirmar_importacao_scpi_view` em `apps/estoque/views.py` adiciona `@transaction.atomic`, faz unpack, chama `registrar_timeline_divergencia_importacao(linhas=linhas, estoque=estoque, importacao=importacao, ator=ator)`. O VIEW pode importar de `requisicoes` (é a camada de adaptação — ADR-0004).

As views podem coordenar entre domínios; services não cruzam dependências.

## `apps/estoque/types.py`

```python
from typing import TypedDict
from decimal import Decimal

class ItemReservaEstoque(TypedDict):
    material_id: int
    quantidade_solicitada: Decimal

class ItemLiberacaoReserva(TypedDict):
    material_id: int
    quantidade_reservada: Decimal

class ItemAtendimentoSaldo(TypedDict):
    material_id: int
    quantidade_autorizada: Decimal
    quantidade_entregue: Decimal
```

`services.py` importa de `types.py` para evitar duplicação; as importações atuais em `requisicoes` passam a importar de `apps.estoque.types`.

## Test strategy

### Novos testes em `apps/estoque/tests/test_services.py`

**`registrar_devolucao_estoque`:**
- Happy path: saldo_fisico incrementado + MovimentacaoEstoque DEVOLUCAO criada
- Erro: `material_id` sem saldo → `ConflitoDominio`
- Erro: material inativo → `ConflitoDominio`
- Erro: `quantidade > entregue_liquida` → `ConflitoDominio`
- Erro: mais de um saldo para o material → `ConflitoDominio`

**`estornar_requisicao_estoque`:**
- Happy path: saldo_fisico restaurado + MovimentacaoEstoque ESTORNO_REQUISICAO por item
- Erro: nenhum material com entregue_liquida > 0 → `ConflitoDominio`
- Erro: material_id sem saldo → `ConflitoDominio`
- Atomicidade: falha em saldo_item.save deve rollback toda a operação

### Testes de `entregue_liquida_por_material`

Mesmos cenários existentes dos testes de `entregue_liquida_por_item` em `test_selectors.py`, com `material_id=item.material_id`.

### Testes de integração dos services migrados

- `registrar_devolucao` em `atendimento.py` — comportamento externo inalterado
- `estornar_requisicao` em `ciclo_vida.py` — comportamento externo inalterado
- `confirmar_importacao_scpi` — retorno tuple; hook de timeline via VIEW

### Permissões / estado inválido

Cobertura existente mantida. Não há mudança de policy ou transição de estado.

## Invariantes (ADR-0015)

- Todo `SaldoEstoque.saldo_fisico` mutado emite `MovimentacaoEstoque` na mesma transação
- `Σ delta_fisico` por `(estoque, material)` = `saldo_fisico`
- `entregue_liquida = -Σ delta_fisico(CONSUMO, DEVOLUCAO, ESTORNO_REQUISICAO)` por `(requisicao, material)`

## Risks

**Atomicidade da VIEW:** `confirmar_importacao_scpi_view` precisa de `@transaction.atomic` para que timeline e saldos commits juntos. `confirmar_importacao_scpi` já usa `with transaction.atomic()` internamente — o decorator externo cria savepoint, o comportamento de on_commit segue o outer commit.

**Renomeação de `entregue_liquida_por_item`:** função referenciada em 3 services + 2 views + ~15 testes. Renomeação mecânica sem risco lógico — verificar por `grep 'entregue_liquida_por_item'` pós-migração.

**Retorno de `confirmar_importacao_scpi`:** chamado em ~15 testes. Callers que ignoravam o retorno (`importacao = confirmar_importacao_scpi(...)`) precisam fazer unpack. Os que salvavam só `importacao` ficam `importacao, _ = confirmar_importacao_scpi(...)` ou `importacao, linhas = ...`.
