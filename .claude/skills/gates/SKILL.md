---
name: gates
description: Roda localmente os cinco gates do CI, na mesma ordem do pipeline, e para no primeiro vermelho. Use antes de abrir ou atualizar um PR.
disable-model-invocation: true
---

# Gates do CI — execução local

Reproduz `.github/workflows/ci.yml` na ordem real do pipeline. Os três
primeiros gates são pré-requisito dos dois últimos no CI (`needs:`), então
formatação errada derruba tudo antes de qualquer teste rodar — daí a ordem
importar.

## Regras de execução

- **Pare no primeiro gate vermelho.** Não siga para o próximo; corrija e
  recomece do gate que falhou.
- **Nunca use redirecionamento, pipe, `tail`, `head`, `grep` ou truncamento**
  na saída destes comandos (AGENTS.md). Quando um comando falhar, abra o
  caminho `[full output: ...]` emitido pelo RTK Tee System para ler a saída
  bruta completa — não reexecute o comando só para ver o erro.
- Rode da raiz do projeto.

## Sequência

### 1. `ruff format --check`

```bash
uv run ruff format --check .
```

Falhou? `uv run ruff format .` e volte ao passo 1. Atenção: `quote-style` é
`single` (`pyproject.toml`), diferente do padrão do ruff.

### 2. `ruff check`

```bash
uv run ruff check .
```

Falhou? `uv run ruff check --fix .` resolve a parte automática; o resto é
manual. Não silencie com `# noqa` sem justificar.

### 3. `mypy`

```bash
uv run mypy apps
```

`pyproject.toml` já exclui `views.py`, `models.py`, `forms.py`, `admin.py`,
`urls.py`, `tests/` e `management/` — um erro aqui está em código de domínio
(`services`, `policies`, `selectors`, `transitions`, `papeis`).

### 4. Migrations em dia

```bash
DJANGO_SETTINGS_MODULE=config.settings.dev uv run python manage.py makemigrations --check --dry-run
```

Saída limpa = models e migrations locais convergem. Se acusar mudança
pendente, **não** crie a migration à mão (o hook `bloqueia_migrations` bloqueia
e o `.gitignore` a descarta): rode `make setup` e volte ao passo 4.

### 5. pytest

```bash
uv run pytest -q -ra --tb=short --strict-markers --disable-warnings -n logical
```

Comando idêntico ao do CI, `-n logical` inclusive. Se um teste falhar só em
paralelo, reproduza sem `-n` antes de concluir que é flake.

## Fechamento

Quando os cinco passarem, relate qual gate rodou e o resultado — sem
generalizar para além do que os comandos provaram. Migrations e pytest exigem
PostgreSQL disponível via `DATABASE_URL`; se o banco local estiver
inconsistente, use `/reset-schema` antes de repetir os passos 4 e 5.
