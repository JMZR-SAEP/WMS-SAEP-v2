# Plano — Issue #38: Testes dispatcher + views accounts + sync docs

## Escopo

### O que muda
- `apps/core/tests/__init__.py` — novo (pacote de testes)
- `apps/core/tests/test_views.py` — novo: 5 testes para os 4 caminhos do dispatcher + unauthenticated
- `apps/accounts/tests/test_views.py` — novo: testes de view HTTP para `MatriculaLoginView` não cobertos em `test_login.py`
- `README.md` — novo: propósito, setup, testes, mapa de apps
- `.design/TASKS.md` — atualizar percentual de tarefas concluídas para refletir UI construída
- `AGENTS.md` linha 82 — remover ressalva obsoleta sobre `make seed-dev`

### O que NÃO muda
- `apps/notificacoes` (aguarda #45)
- Views existentes — nenhuma refatoração
- Modelos, migrations, serviços
- Testes existentes em `test_login.py` (não mover, não duplicar)

---

## Arquivos tocados

| Arquivo | Ação |
|---|---|
| `apps/core/tests/__init__.py` | Criar (vazio) |
| `apps/core/tests/test_views.py` | Criar — testes dispatcher |
| `apps/accounts/tests/test_views.py` | Criar — testes HTTP view |
| `README.md` | Criar — doc mínima |
| `.design/TASKS.md` | Atualizar status UI |
| `AGENTS.md` | Remover linha obsoleta seed-dev |

Mapeamento via Serena confirmado:
- `apps/core/views.py::home` — dispatcher com 4 branches (superuser, almox, chefe, solicitante)
- `apps/requisicoes/policies.py::pode_ver_fila_atendimento` / `pode_ver_fila_autorizacao` — políticas que determinam o branch
- `apps/accounts/views.py::MatriculaLoginView` — `LoginView` com `redirect_authenticated_user=True`
- Fixtures reutilizáveis em `apps/requisicoes/tests/conftest.py`: `superuser`, `chefe_almoxarifado`, `chefe_obras`, `solicitante`, `setor_almoxarifado`, `setor_obras`

---

## Estratégia de testes

### `apps/core/tests/test_views.py`

Testes usando `pytest-django` com `client` fixture. Sem factory_boy (ADR-0010).

| Teste | Setup | Assert |
|---|---|---|
| `test_superuser_vai_para_admin` | `superuser` autenticado, GET `/` | 302 → `/admin/` |
| `test_almox_vai_para_atendimentos` | `chefe_almoxarifado` autenticado, GET `/` | 302 → `/requisicoes/atendimentos/` |
| `test_chefe_vai_para_autorizacoes` | `chefe_obras` autenticado (setor COMUM com chefe), GET `/` | 302 → `/requisicoes/autorizacoes/` |
| `test_solicitante_vai_para_minhas` | `solicitante` sem papel especial, GET `/` | 302 → `/requisicoes/minhas/` |
| `test_nao_autenticado_vai_para_login` | sem login, GET `/` | 302 → URL com `/accounts/login/` |

**Fixtures importadas de** `apps/requisicoes/tests/conftest.py` via `conftest.py` local ou importação direta no arquivo.

### `apps/accounts/tests/test_views.py`

Foco em comportamentos de view HTTP que NÃO estão em `test_login.py`:

| Teste | Setup | Assert |
|---|---|---|
| `test_usuario_autenticado_e_redirecionado` | usuário logado, GET `/accounts/login/` | 302 (redirect_authenticated_user=True) |
| `test_login_post_valido_redireciona_para_home` | POST válido sem `next` | redirect → `/` (dispatcher) |
| `test_matricula_invalida_retorna_form_com_erro` | POST com matrícula inexistente | status 200, form com erros |
| `test_usuario_inativo_bloqueado` | POST com usuário inativo | status 200, não autentica |
| `test_logout_encerra_sessao` | usuário logado, POST logout | 302, usuário não autenticado |

---

## Invariantes verificados

Da `docs/design-acesso-rapido/matriz-invariantes.md` §5 check-list:
- Dispatcher respeita hierarquia: superuser > almox > chefe > solicitante
- `@login_required` protege `home` — unauthenticated → login redirect
- `redirect_authenticated_user=True` em `MatriculaLoginView` — usuário logado não acessa login

---

## Riscos

- **Ordem dos branches no dispatcher**: superuser tem precedência sobre almox e chefe (superuser passa por `pode_ver_fila_atendimento` como True mas redireciona antes). Testar `chefe_almoxarifado` que também é superuser não — usar fixture `chefe_almoxarifado` (não superuser).
- **Fixtures cross-app**: `conftest.py` dos requisicoes usa `@pytest.fixture` local. Os testes de `core/test_views.py` precisarão recriar fixtures equivalentes localmente ou importar do conftest de requisicoes via `conftest.py` na raiz/core.
- **Sem schema changes** — sem necessidade de `make setup`.

---

## Sequência de entrega

1. Criar `apps/core/tests/__init__.py` + `test_views.py` (RED → GREEN — dispatcher)
2. Criar `apps/accounts/tests/test_views.py` (RED → GREEN — views HTTP)
3. Criar `README.md`
4. Atualizar `.design/TASKS.md`
5. Remover linha obsoleta de `AGENTS.md`
6. `ruff format . && ruff check .`
7. Suíte completa verde
