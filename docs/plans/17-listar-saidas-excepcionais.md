# Plano: Issue #17 — Listar saídas excepcionais

## Scope

**O que muda:**
- Modelos `SaidaExcepcional` e `ItemSaidaExcepcional` em `apps/estoque/models.py`
- `apps/estoque/policies.py` (novo): `pode_consultar_saidas_excepcionais` + `exigir_*`
- `apps/estoque/selectors.py` (novo): `listar_saidas_excepcionais`
- `apps/estoque/views.py`: `listar_saidas_excepcionais_view`
- `apps/estoque/urls.py` (novo): rota `/estoque/saidas-excepcionais/`
- `config/urls.py`: inclui `apps.estoque.urls`
- Templates: `estoque/base.html`, `estoque/_topbar_nav.html`, `estoque/lista_saidas_excepcionais.html`
- `apps/estoque/tests/` (novo): testes de policy, selector, view
- `make setup` para recriar migrations locais

**O que NÃO muda:**
- Formulário de novo registro (issue futura)
- Detalhe da saída excepcional (issue futura)
- Modal de estorno (issue futura)
- Serviços de mutação (registrar/estornar)
- Qualquer outra app

## Arquivos tocados

| Arquivo | Ação |
|---|---|
| `apps/estoque/models.py` | Adiciona `SaidaExcepcional`, `ItemSaidaExcepcional`, choices `EstadoSaidaExcepcional` |
| `apps/estoque/policies.py` | Novo: `pode_consultar_saidas_excepcionais`, `exigir_pode_consultar_saidas_excepcionais` |
| `apps/estoque/selectors.py` | Novo: `listar_saidas_excepcionais(ator_id)` |
| `apps/estoque/views.py` | Novo: `listar_saidas_excepcionais_view` |
| `apps/estoque/urls.py` | Novo: app_name="estoque", urlpatterns |
| `config/urls.py` | Inclui `apps.estoque.urls` em `estoque/` |
| `apps/estoque/templates/estoque/base.html` | Novo: extends base_auth, injeta topbar_domain |
| `apps/estoque/templates/estoque/_topbar_nav.html` | Novo: grupo Almoxarifado no drawer |
| `apps/estoque/templates/estoque/lista_saidas_excepcionais.html` | Novo: lista desktop/mobile + empty state |
| `apps/estoque/tests/__init__.py` | Novo |
| `apps/estoque/tests/test_policies.py` | Novo |
| `apps/estoque/tests/test_selectors.py` | Novo |
| `apps/estoque/tests/test_views.py` | Novo |

## Modelo: SaidaExcepcional

Campos:
- `numero_publico`: CharField, gerado no serviço (futuro), único, nullable por enquanto (para criação via seed/test)
- `criado_em`: DateTimeField auto
- `motivo`: TextField
- `observacao`: TextField blank
- `estado`: CharField choices `EstadoSaidaExcepcional` (registrada/estornada)
- `registrado_por`: FK User
- `estoque`: FK Estoque (qual almoxarifado registrou)
- `estornado_em`: DateTimeField null/blank
- `estornado_por`: FK User null/blank
- `justificativa_estorno`: TextField blank

Modelo: `ItemSaidaExcepcional`
- `saida`: FK SaidaExcepcional related_name="itens"
- `material`: FK Material
- `quantidade`: PositiveIntegerField

## Policy: pode_consultar_saidas_excepcionais

```python
def pode_consultar_saidas_excepcionais(ator: User) -> bool:
    if not ator.is_active:
        return False
    if ator.is_superuser:
        return True
    return _eh_almoxarifado(ator)
```

`_eh_almoxarifado` precisa ser extraída ou replicada de `requisicoes.policies`.
Decisão: replicar localmente para manter `estoque` sem dependência direta de `requisicoes`.

## Selector: listar_saidas_excepcionais

```python
def listar_saidas_excepcionais(ator_id: int) -> QuerySet:
    return (
        SaidaExcepcional.objects
        .select_related("registrado_por", "estoque")
        .annotate(quantidade_itens=Count("itens"))
        .order_by("-criado_em")
    )
```

## Test strategy

| Camada | Cenário |
|---|---|
| Policy | ativo+chefe_almox → True; ativo+aux_almox → True; superuser → True; solicitante → False; inativo+almox → False |
| Selector | retorna saídas ordenadas por -criado_em; sem saídas → qs vazio |
| View (GET) | 200 para aux_almox; 200 para chefe_almox; 200 para superuser; 403 para solicitante; redirect para anon |

## Invariants

Nenhuma invariante de estado ativa neste issue (apenas consulta, sem mutação).
Ref: `docs/matriz-invariantes.md`.

## Risks

- `numero_publico` pode ser None no seed inicial (sem serviço de criação ainda) — template precisa de fallback "—".
- `_eh_almoxarifado` duplicado — aceitável no MVP; será movido para `core` ou `accounts` quando houver terceira app que precise.
