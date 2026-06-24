![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/JMZR-SAEP/WMS-SAEP-v2?utm_source=oss&utm_medium=github&utm_campaign=JMZR-SAEP%2FWMS-SAEP-v2&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)

# WMS-SAEP v2

Sistema de gestão de requisições de material para a SAEP. Controla o fluxo completo: rascunho → autorização → atendimento → retirada, com integração ao SCPI para atualização de estoque.

## Setup

```bash
make init      # cria .venv e instala dependências (primeira vez)
make setup     # recria banco, aplica migrations e seed de dev
make seed-dev  # carrega dados de desenvolvimento
```

## Rodar testes

```bash
uv run pytest -q -ra --tb=short --strict-markers --disable-warnings
```

## Mapa de apps

| App | Responsabilidade |
|---|---|
| `accounts` | Autenticação por matrícula, modelo de usuário, setores, vínculos auxiliares |
| `core` | Dispatcher pós-login, base templates, componentes globais |
| `requisicoes` | Fluxo principal: rascunho, autorização, fila de atendimento, separação, retirada |
| `estoque` | Saldo de materiais, entradas, saídas excepcionais, integração SCPI |
| `notificacoes` | Notificações in-app (em construção — aguarda #45) |
