---
name: reset-schema
description: Recria o schema local do zero — apaga migrations locais, dropa o schema public do PostgreSQL, recria migrations, migra e carrega o seed canônico. Use após mudar models/schema ou quando o ambiente local estiver inconsistente.
disable-model-invocation: true
---

# Reset de schema local

Materializa o ciclo efêmero descrito em AGENTS.md: migrations locais são
artefatos descartáveis (`.gitignore:17`) e toda mudança em `models`/schema é
seguida de uma recriação limpa, simulando a primeira execução do app.

## Antes de rodar — confirme com o usuário

Este fluxo é **destrutivo e irreversível** no banco local:

- `DROP SCHEMA public CASCADE` no banco apontado por `DATABASE_URL` — **todos
  os dados locais são perdidos**;
- todos os arquivos em `apps/**/migrations/` (exceto `__init__.py`) são
  apagados;
- `staticfiles/`, `.pytest_cache/`, `.ruff_cache/` e `htmlcov/` são removidos.

Verifique com o usuário antes de executar, e confirme que `DATABASE_URL` no
`.env` aponta para o banco de desenvolvimento — **nunca** para um banco
compartilhado ou de produção:

```bash
uv run python -c "import environ, pathlib; print(environ.Env.read_env(pathlib.Path('.env')) or __import__('os').environ.get('DATABASE_URL'))"
```

Só prossiga com um "sim" explícito.

## Execução

Um alvo faz o ciclo inteiro (`clean` → `compile` → `makemigrations` →
`migrate --run-syncdb` → `seed-dev`):

```bash
make setup
```

Requer `psql` no PATH e `DATABASE_URL` definido no `.env` — o alvo aborta com
mensagem própria se faltar qualquer um.

Nunca use redirecionamento, pipe ou truncamento na saída (AGENTS.md); se
falhar, leia o `[full output: ...]` do RTK Tee System.

## Verificação

Depois do `make setup`, prove que o resultado está limpo — não presuma.

### 1. Models e migrations convergem

```bash
DJANGO_SETTINGS_MODULE=config.settings.dev uv run python manage.py makemigrations --check --dry-run
```

Saída sem mudança pendente. Este é o mesmo gate do job `migrations` do CI.

### 2. Seed é idempotente

```bash
SEED_DEV_HABILITADO=true DJANGO_SETTINGS_MODULE=config.settings.dev uv run python manage.py seed_dev
```

Rodar de novo sobre o banco já semeado tem que convergir sem erro — o CI roda
`seed_dev` duas vezes seguidas exatamente por isso (`.github/workflows/ci.yml`).
Falha aqui costuma ser `get_or_create` onde ADR-0009 exige `update_or_create`.

### 3. Suíte verde

```bash
uv run pytest -q -ra --tb=short --strict-markers --disable-warnings -n logical
```

## Limites

- Não crie nem edite arquivos de migration à mão — a fonte de verdade são
  `models`, constraints, índices, regras de domínio e testes. O hook
  `bloqueia_migrations` bloqueia essa escrita.
- Reset completo é obrigatório só para mudança de schema/model ou ambiente
  local inconsistente. Tarefa sem mudança estrutural segue fluxo incremental —
  não rode isto "por garantia".
- `make init` (recria `.venv`) é setup inicial de projeto, não faz parte deste
  ciclo.
