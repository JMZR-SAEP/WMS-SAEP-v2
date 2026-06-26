# Plano — Issue #49: PapelEfetivo VO + papel_efetivo() resolver

## Escopo

### O que muda

- **Novo**: `apps/accounts/papeis.py` — módulo com `PapelEfetivo` (frozen dataclass, sem ORM) e
  `papel_efetivo(usuario)` (único boundary de IO).
- **Modificado**: 4 arquivos têm suas duplicações de `_eh_almoxarifado` e helpers de escopo
  substituídas por delegação ao resolver:
  - `apps/requisicoes/policies.py`
  - `apps/requisicoes/selectors.py`
  - `apps/estoque/policies.py`
  - `apps/estoque/selectors.py`
- **Novo**: `apps/accounts/tests/test_papeis.py` — cobertura do módulo sem banco (VO puro) e com
  banco (derivação completa).

### O que NÃO muda

- Assinaturas de policy/selector (`pode_*`, `exigir_pode_*`, seletores públicos).
- Comportamento de autorização observável: cada helper privado delegará ao resolver e retornará o
  mesmo resultado que retornava antes.
- Modelos, migrations, views, services, URLs.
- O flip de contrato (fazer as policies receberem `PapelEfetivo` em vez de recalculá-lo) é a
  fatia seguinte — fora do escopo desta issue.

---

## Arquivos tocados

| Arquivo | Ação |
|---------|------|
| `apps/accounts/papeis.py` | Criar |
| `apps/accounts/tests/test_papeis.py` | Criar |
| `apps/requisicoes/policies.py` | Modificar — remover 3 helpers privados, delegar |
| `apps/requisicoes/selectors.py` | Modificar — remover 2 helpers privados, delegar |
| `apps/estoque/policies.py` | Modificar — remover 2 helpers privados, delegar |
| `apps/estoque/selectors.py` | Modificar — remover 2 helpers privados, delegar |

Mapeamento simbólico (via Serena):

- `requisicoes/policies._eh_almoxarifado` (L26–44, `except Exception`)
- `requisicoes/policies._setores_escopo_setor` (L47–71)
- `requisicoes/policies._setor_chefiado_ativo` (L74–82)
- `requisicoes/selectors._eh_almoxarifado` (L48–61, `except Exception`)
- `requisicoes/selectors._setores_chefiados_nao_almox` (L37–45)
- `estoque/policies._eh_almoxarifado` (L6–21, `except (AttributeError, ObjectDoesNotExist)`)
- `estoque/policies._eh_chefe_ou_aux_setor_nao_almox` (L154–165)
- `estoque/selectors._eh_almoxarifado` (L309–322, `except Exception`)
- `estoque/selectors._setores_visiveis_nao_almox` (L325–343)

---

## Design de `PapelEfetivo`

```python
@dataclass(frozen=True)
class PapelEfetivo:
    eh_almoxarifado: bool
    eh_chefe_de_almoxarifado: bool
    setores_em_escopo: tuple[int, ...]   # não-almox ativos; chief + auxiliar
    setor_chefiado_ativo_id: int | None  # PK do setor ativo chefiado; None se não chefia nenhum
    pode_ser_beneficiario: bool
```

- `frozen=True` → hashable, imutável, seguro para reuso dentro do caso de uso.
- `setores_em_escopo` usa `tuple` (não `list`) para manter a imutabilidade em runtime.
- `setor_chefiado_ativo_id`: campo escalar (PK inteiro); o resolver extrai `setor_chefiado.pk`
  antes de construir o VO. O VO não carrega referência viva de ORM — permanece puro e frozen.
- `pode_ser_beneficiario`: puro Python (`is_active and setor_id is not None`), sem query extra.

### Distinção `eh_almoxarifado` vs `eh_chefe_de_almoxarifado`

| Campo | True quando |
|-------|-------------|
| `eh_chefe_de_almoxarifado` | `setor_chefiado` ativo e classificado como ALMOXARIFADO |
| `eh_almoxarifado` | `eh_chefe_de_almoxarifado` OR auxiliar ativo de almoxarifado |

Chefe implica almoxarifado; auxiliar não é chefe.

---

## Design de `papel_efetivo(usuario)`

Único boundary de IO:

1. **Acesso a `setor_chefiado`** (RelatedObjectDoesNotExist ⊂ AttributeError ∩ ObjectDoesNotExist):
   ```python
   try:
       setor_chefiado = usuario.setor_chefiado
   except (AttributeError, ObjectDoesNotExist):
       setor_chefiado = None
   ```

2. **Uma query a `VinculoAuxiliar`** — particionada em Python:
   ```python
   vinculos = list(
       VinculoAuxiliar.objects.filter(usuario=usuario, ativo=True, setor__ativo=True)
       .values('setor_id', 'setor__classificacao')
   )
   ```
   Sem query separada para almox e outra para não-almox.

3. **Derivações em Python** (sem queries adicionais):
   - `setor_ativo = setor_chefiado if (setor_chefiado and setor_chefiado.ativo) else None`
   - `setor_chefiado_ativo_id = setor_ativo.pk if setor_ativo else None`
   - `eh_chefe_de_almoxarifado = setor_ativo is not None and setor_ativo.classificacao == ALMOXARIFADO`
   - `eh_auxiliar_de_almoxarifado = any(v['setor__classificacao'] == ALMOXARIFADO for v in vinculos)`
   - `eh_almoxarifado = eh_chefe_de_almoxarifado or eh_auxiliar_de_almoxarifado`
   - `setores_em_escopo` = IDs não-almox dos vínculos + `setor_chefiado_ativo_id` se não-almox

---

## Delegação nos helpers privados existentes

Cada helper privado nas 4 localizações passa a:

```python
# antes:
def _eh_almoxarifado(usuario: User) -> bool:
    try:
        setor_chefiado = usuario.setor_chefiado
        if setor_chefiado.classificacao == ... and setor_chefiado.ativo:
            return True
    except Exception:  # ← impreciso em 3 dos 4 casos
        pass
    return VinculoAuxiliar.objects.filter(...).exists()

# depois:
def _eh_almoxarifado(usuario: User) -> bool:
    return papel_efetivo(usuario).eh_almoxarifado
```

Mapeamento completo:

| Helper (antes) | Delegação (depois) |
|----------------|--------------------|
| `_eh_almoxarifado` (×4) | `papel_efetivo(u).eh_almoxarifado` |
| `_setores_escopo_setor` | `list(papel_efetivo(u).setores_em_escopo)` |
| `_setor_chefiado_ativo` | `papel_efetivo(u).setor_chefiado_ativo_id` (retorna `int \| None`) |
| `_setores_chefiados_nao_almox` | `[p.setor_chefiado_ativo_id] if p.setor_chefiado_ativo_id and not p.eh_chefe_de_almoxarifado else []` |
| `_setores_visiveis_nao_almox` | `list(papel_efetivo(u).setores_em_escopo)` |
| `_eh_chefe_ou_aux_setor_nao_almox` | `bool(papel_efetivo(u).setores_em_escopo)` |

**Nota sobre `_setores_chefiados_nao_almox`**: este helper é intencionalmente mais restrito que
`setores_em_escopo` (só cobre chefe, não auxiliar). A delegação usa `setor_chefiado_ativo_id`
combinada com `eh_chefe_de_almoxarifado` para preservar comportamento idêntico. Esse narrowing é
documentado pelo comentário existente no selector de estoque.

---

## Estratégia de testes

Arquivo: `apps/accounts/tests/test_papeis.py`

### Sem banco (VO puro)

- `PapelEfetivo` pode ser construído com valores literais sem `@pytest.mark.django_db`.
- Verificar imutabilidade: `frozen=True` lança `FrozenInstanceError` na tentativa de atribuição.

### Com banco — happy paths

| Cenário | `eh_almoxarifado` | `eh_chefe_de_almoxarifado` | `setores_em_escopo` | `setor_chefiado_ativo_id` |
|---------|-------------------|---------------------------|---------------------|--------------------------|
| Sem chefia, sem vínculo | False | False | () | None |
| Chefe de almoxarifado ativo | True | True | () | setor_almox.pk |
| Auxiliar de almoxarifado (sem chefia) | True | False | () | None |
| Chefe de setor comum ativo | False | False | (setor.pk,) | setor.pk |
| Auxiliar de setor comum (sem chefia) | False | False | (setor.pk,) | None |
| Chefe de setor comum inativo | False | False | () | None |
| Setor chefiado inativo, auxiliar de almox | True | False | () | None |

### Invariantes e contrato

- `except (AttributeError, ObjectDoesNotExist)` captura `RelatedObjectDoesNotExist` (subclasse de ambos).
- `pode_ser_beneficiario`: usuário ativo com setor → True; inativo → False; sem setor → False.
- Usuário com vínculo de setor não-almox E chefe de almoxarifado: `eh_almoxarifado=True`,
  `setores_em_escopo=()`, `setor_chefiado_ativo_id=setor_almox.pk`.

---

## Riscos

| Risco | Mitigação |
|-------|-----------|
| `_setores_chefiados_nao_almox` mais restrito que `setores_em_escopo` | Delegação usa `setor_chefiado_ativo_id` + `eh_chefe_de_almoxarifado`, preserva comportamento |
| Desempenho: 1 query por chamada de helper (antes 0–1, agora 1) | Esta fatia não otimiza desempenho — fatia seguinte recebe `PapelEfetivo` pronto no controller |
| Testes de req/estoque já cobrem comportamento de autorização | Suíte deve permanecer verde; qualquer regressão detectada imediatamente |
| Importação circular (`accounts/papeis` → `accounts/models`) | Sem risco; `models.py` não importa `papeis.py` |
