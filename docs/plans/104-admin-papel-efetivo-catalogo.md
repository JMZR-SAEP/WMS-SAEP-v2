# Plano — Admin de material deriva `PapelEfetivo` antes da policy (#104)

## Escopo

Corrigir a regressão que derruba **todo** o Django admin com HTTP 500:
`MaterialAdmin._pode_gerir` passa um `User` para `pode_gerir_catalogo`, que desde
o flip de contrato do commit `81df7a0` espera um `PapelEfetivo`.

**Muda:**

- `apps/estoque/admin.py` — `MaterialAdmin._pode_gerir` deriva o papel com
  `papel_efetivo(request.user)` antes de chamar a policy.
- `apps/estoque/tests/test_admin.py` — arquivo já existente (guard de estoque
  único, #102); ganha um bloco novo para `MaterialAdmin`: smoke de páginas do
  admin e testes de unidade de `_pode_gerir`.

**Não muda:**

- `apps/estoque/policies.py` — `pode_gerir_catalogo(papel: PapelEfetivo)` está
  correta e é o contrato vigente da ADR-0011. Reverter a policy para aceitar
  `User` reintroduziria IO dentro da camada de policy.
- `apps/accounts/papeis.py` — `papel_efetivo` é o único boundary de IO para
  derivação de papel e já cobre superusuário (`eh_superusuario`) e usuário
  inativo (`ativo=False`).
- `apps/accounts/admin.py` — as ocorrências de `request.user` ali passam
  `ator_id=request.user.pk` para services, que derivam o papel internamente.
  Nenhuma delas chama policy com `User`. Confirmado por varredura de
  `request.user` em todos os `admin.py` do projeto.
- `apps/estoque/services.py:750` — `exigir_pode_gerir_catalogo(papel)` já recebe
  `PapelEfetivo`. O caminho `save_model` → `desativar_material` continua íntegro.
- `EstoqueAdmin.has_add_permission` (guard de estoque único, #102) — não toca
  policies; segue como está.
- Schema, migrations, seed. Sem mudança estrutural → sem `make setup`.

## Arquivos alterados

| Arquivo | Ação |
|---|---|
| `apps/estoque/admin.py` | `MaterialAdmin/_pode_gerir` — deriva papel antes da policy |
| `apps/estoque/tests/test_admin.py` | Acrescenta cobertura de `MaterialAdmin`; atualiza o docstring do módulo, hoje restrito ao escopo do #102 |

## Implementação

```python
def _pode_gerir(self, request):
    from apps.accounts.papeis import papel_efetivo
    from apps.estoque.policies import pode_gerir_catalogo

    return pode_gerir_catalogo(papel_efetivo(request.user))
```

O import fica local ao método, seguindo o padrão já estabelecido no próprio
arquivo (`pode_gerir_catalogo`, `desativar_material`, `PermissionDenied` são
todos importados dentro dos métodos que os usam).

Por que o bug derruba o admin inteiro, e não só as telas de `Material`:
`AdminSite.each_context()` chama `get_app_list()` na renderização de **qualquer**
página do admin, e `get_app_list` consulta `has_add_permission` /
`has_change_permission` de cada `ModelAdmin` registrado para montar o menu
lateral. Um `AttributeError` em `MaterialAdmin` propaga para todas as 13 URLs
reproduzidas no issue, incluindo `/admin/` — destino do redirect pós-login do
superusuário.

## Estratégia de testes

Arquivo `apps/estoque/tests/test_admin.py`, já existente desde #102 (o desvio
aditivo em relação à organização de arquivos da ADR-0010 foi registrado naquele
plano; este plano apenas acrescenta casos ao arquivo).

Fixtures reaproveitadas de `apps/estoque/tests/conftest.py`: `superuser`
(`create_superuser`, portanto `is_staff=True`) e `chefe_almoxarifado`. A fixture
`request_de`, já no arquivo, monta requests via `RequestFactory` para os testes
de unidade.

Duas camadas, deliberadamente:

| # | Caso | Setup | Esperado |
|---|---|---|---|
| 1 | `admin:index` responde | `client.force_login(superuser)` | 200 |
| 2 | `admin:estoque_material_changelist` responde | idem | 200 |
| 3 | `admin:estoque_material_add` responde | idem | 200 |
| 4 | `_pode_gerir` autoriza superusuário | `RequestFactory` + `superuser` | `True` |
| 5 | `_pode_gerir` nega quem não é superusuário | `RequestFactory` + `chefe_almoxarifado` | `False` |

Os casos 1–3 são o critério de aceite literal do issue e reproduzem a regressão:
antes da correção falham com `AttributeError`. O caso 1 é o que prova o blast
radius — `admin:index` não é uma tela de `Material`.

Os casos 4–5 existem porque os smokes sozinhos não fixam a regra: um
`_pode_gerir` que retornasse `True` incondicionalmente passaria nos três. O caso
5 é o que ancora a autorização real, e é a única defesa contra uma "correção"
que troque o 500 por uma brecha de permissão.

Não coberto (fora da camada): que o Django esconda o botão "Add" quando
`has_add_permission` é falso — default de framework, a ADR-0010 proíbe testar.

## Invariantes

| ID | Relação com esta mudança |
|---|---|
| PER-05 | "Superusuário tem permissões totais, incluindo administração." Hoje **violado na prática**: o superusuário não consegue abrir nenhuma página do admin. A correção restaura o invariante; os casos 1–4 são sua verificação. |
| PER-08 | "Views e services chamam a mesma policy contextual." Preservado e reforçado: admin e `desativar_material` passam a convergir na mesma `pode_gerir_catalogo` com o mesmo tipo de argumento. Antes do fix, o admin chamava a policy com um tipo que ela não aceita — a convergência era só aparente. |
| USR-01 | "Usuário inativo não acessa nem opera." Preservado sem código novo: `papel_efetivo` devolve `ativo=False` para usuário inativo, e `pode_gerir_catalogo` testa `papel.ativo` primeiro. Já coberto em `test_policies.py`; não se duplica aqui. |
| EST-10, EST-11 | Regras de material inativo/desativação. Intocadas — vivem em services e querysets, não no admin. |

Nenhuma linha da matriz de invariantes ou da matriz de permissões precisa ser
reescrita: esta é uma correção de regressão para o comportamento já documentado.

## Riscos

| Risco | Avaliação |
|---|---|
| Queries extras por request do admin | `papel_efetivo` faz uma consulta a `VinculoAuxiliar` e pode tocar `setor_chefiado`. `get_app_list` chama `_pode_gerir` ao menos duas vezes por página (via `get_model_perms`: add + change), e as telas de `Material` chamam mais. Sem cache por request. Aceito: o admin é válvula de emergência de baixa frequência, e o issue pede uma correção de 1 linha. Introduzir cache por request seria expandir escopo. |
| `request.user` anônimo em `_pode_gerir` | Não ocorre: todas as views do admin passam por `AdminSite.admin_view`, que exige autenticação e `is_staff` antes de renderizar. `papel_efetivo` nunca recebe `AnonymousUser` por este caminho. |
| Troca de 500 por brecha de permissão | Coberto pelo caso 5 (`chefe_almoxarifado` → `False`), que falharia em qualquer correção que apenas silenciasse a exceção. |
| Outros callers com o mesmo defeito | Varredura de `request.user` em todos os `admin.py`: único caller de policy é este. Os demais passam `ator_id` para services. |
| Máquina de estados / transições | Não tocada. |
| Contrato OpenAPI | Projeto server-rendered sem camada REST. Não se aplica. |
| Migrations / dados existentes | Sem mudança de schema. Nada a resetar. |
