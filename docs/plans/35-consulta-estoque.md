# Plano — Issue #35: Consulta de estoque e catálogo de materiais (PR-E)

## Escopo

**Muda:**
- `apps/estoque/policies.py` — adicionar `pode_consultar_catalogo_estoque` + `exigir_pode_consultar_catalogo_estoque`
- `apps/estoque/selectors.py` — adicionar `listar_materiais_com_saldo`
- `apps/estoque/views.py` — adicionar `lista_materiais_view`
- `apps/estoque/urls.py` — rota `materiais/`
- `apps/requisicoes/context_processors.py` — expor `pode_consultar_catalogo_estoque`
- `apps/estoque/templates/estoque/_topbar_nav.html` — link "Catálogo de materiais"
- `apps/estoque/templates/estoque/lista_materiais.html` — nova tela (lista + busca inline)

**Não muda:**
- Edição/desativação de material (fora de escopo)
- Entrada/recebimento de estoque
- Histórico de movimentações (issue #41 não existe ainda)
- Modelos/migrações — nenhuma mudança de schema

## Arquivos tocados

| Arquivo | Ação |
|---------|------|
| `apps/estoque/policies.py` | Adicionar 2 funções |
| `apps/estoque/selectors.py` | Adicionar `listar_materiais_com_saldo` |
| `apps/estoque/views.py` | Adicionar `lista_materiais_view` |
| `apps/estoque/urls.py` | Adicionar path `materiais/` |
| `apps/requisicoes/context_processors.py` | Expor nova flag |
| `apps/estoque/templates/estoque/_topbar_nav.html` | Adicionar link nav |
| `apps/estoque/templates/estoque/lista_materiais.html` | Criar template |
| `apps/estoque/tests/test_policies.py` | Cobertura de `pode_consultar_catalogo_estoque` |
| `apps/estoque/tests/test_selectors.py` | Cobertura de `listar_materiais_com_saldo` |
| `apps/estoque/tests/test_views.py` | Cobertura de `lista_materiais_view` |

## Design das interfaces

### Policy
```python
def pode_consultar_catalogo_estoque(usuario: User) -> bool
def exigir_pode_consultar_catalogo_estoque(usuario: User) -> None
```
Critério: `_eh_almoxarifado(usuario) or usuario.is_superuser`

### Selector
```python
def listar_materiais_com_saldo(
    ator_id: int,
    *,
    busca: str = '',
) -> QuerySet[SaldoEstoque]
```
- JOIN `SaldoEstoque → Material → Estoque`
- Annotate `saldo_disponivel = saldo_fisico - saldo_reservado`
- Annotate `divergente = Case(When(saldo_fisico__lt=saldo_reservado, then=True), default=False)`
- Filtro `busca` em `material__codigo__icontains | material__nome__icontains`
- `select_related('material', 'estoque')`
- `order_by('material__nome')`

### View
```python
@login_required
@require_GET
def lista_materiais_view(request):
    exigir_pode_consultar_catalogo_estoque(request.user)
    busca = request.GET.get('busca', '').strip()
    saldos = listar_materiais_com_saldo(request.user.pk, busca=busca)
    return render(request, 'estoque/lista_materiais.html', {'saldos': saldos, 'busca': busca})
```

### URL
`path('materiais/', views.lista_materiais_view, name='lista_materiais')`

## Estratégia de testes (ADR-0010)

| Comportamento | Tipo | Fixture |
|---------------|------|---------|
| `pode_consultar_catalogo_estoque`: chefe_almoxarifado → True | Unitário policy | `chefe_almoxarifado` |
| `pode_consultar_catalogo_estoque`: aux_almoxarifado → True | Unitário policy | `aux_almoxarifado` |
| `pode_consultar_catalogo_estoque`: superuser → True | Unitário policy | `superuser` |
| `pode_consultar_catalogo_estoque`: solicitante → False | Unitário policy | `solicitante` |
| `listar_materiais_com_saldo`: retorna saldos corretos | Integração selector | `material_disponivel`, `estoque_principal` |
| `listar_materiais_com_saldo`: saldo_disponivel = físico − reservado | Integração selector | |
| `listar_materiais_com_saldo`: divergente True quando físico < reservado | Integração selector | `material_scpi_critico` |
| `listar_materiais_com_saldo`: busca por código | Integração selector | |
| `listar_materiais_com_saldo`: busca por nome | Integração selector | |
| `lista_materiais_view` GET 200 chefe_almoxarifado | View | |
| `lista_materiais_view` GET 200 superuser | View | |
| `lista_materiais_view` GET 403 solicitante | View | |
| `lista_materiais_view` busca filtra resultados | View | |
| `lista_materiais_view` flag divergente visível no contexto | View | |

## Invariantes relevantes

| ID | Regra |
|----|-------|
| EST-07 | Divergência crítica: físico < reservado → flag divergente visível |
| EST-08 | Material divergente → estado crítico exposto na UI |
| PER-05 | Superusuário tem consulta ampla |
| PER-08 | View e service/policy chamam mesma policy contextual |

## Riscos

- Nenhuma mutação de estoque → sem risco de concorrência ou lock
- Sem mudança de schema → sem necessidade de migração
- Context processor já existe — basta adicionar a nova flag sem quebrar as existentes
