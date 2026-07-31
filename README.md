![CI](https://github.com/JMZR-SAEP/WMS-SAEP-v2/actions/workflows/ci.yml/badge.svg)
![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/JMZR-SAEP/WMS-SAEP-v2?utm_source=oss&utm_medium=github&utm_campaign=JMZR-SAEP%2FWMS-SAEP-v2&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![Django](https://img.shields.io/badge/django-6.0-092E20?logo=django&logoColor=white)

# WMS-SAEP v2

Sistema de gestão de requisições de material para a SAEP (Superintendência de Administração e Engenharia de Pátios). Controla o fluxo completo de uma requisição — **rascunho → autorização → atendimento → separação → retirada** — com integração ao SCPI para atualização de estoque e regras de visibilidade por setor/perfil (RBAC).

Aplicação **server-rendered** construída com Django + HTMX + Alpine.js, sem camada de API REST.

## Índice

- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Rodando o projeto](#rodando-o-projeto)
- [Rodando testes](#rodando-testes)
- [Qualidade de código](#qualidade-de-código)
- [Mapa de apps](#mapa-de-apps)
- [Arquitetura e documentação](#arquitetura-e-documentação)
- [Fluxo de contribuição](#fluxo-de-contribuição)
- [Licença](#licença)

## Requisitos

| Ferramenta | Versão | Uso |
|---|---|---|
| [Python](https://www.python.org/) | 3.13+ | runtime da aplicação |
| [uv](https://docs.astral.sh/uv/) | mais recente | gerenciamento de dependências e venv |
| [PostgreSQL](https://www.postgresql.org/) | 14+ | banco de dados |
| [Node.js](https://nodejs.org/) | 18+ | build do Tailwind CSS v4 |
| `make` | — | orquestração dos comandos de setup |
| `psql` (CLI) | — | usado pelo `make setup` para recriar o schema |

## Instalação

Clone o repositório e crie o ambiente Python (venv + dependências via `uv`):

```bash
git clone https://github.com/JMZR-SAEP/WMS-SAEP-v2.git
cd WMS-SAEP-v2
make init
```

`make init` também materializa o arquivo `.env` a partir de `.env.example`, caso ainda não exista.

Instale as dependências de front-end (Tailwind CSS v4, HTMX, Alpine.js):

```bash
npm install
```

## Configuração

Edite o `.env` gerado no passo anterior com os valores do seu ambiente local:

```bash
# Django settings
SECRET_KEY=your-secret-key-here-change-in-production
DJANGO_SETTINGS_MODULE=config.settings.dev

# Database
DATABASE_URL=postgres://saep:saep@localhost:5432/wms_saep

# CORS (development only)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

`DATABASE_URL` precisa apontar para uma instância PostgreSQL acessível — o `make setup` derruba e recria o schema `public` a partir dela.

### Implantação piloto

O piloto usa um módulo de settings próprio, `config.settings.piloto`. Ele existe porque nenhum dos outros serve: `dev` publicaria `DEBUG=True` em rede, e `base` não sobe com `ALLOWED_HOSTS=[]`.

O piloto **recusa a inicialização** quando a configuração está ausente, vazia ou permissiva — falhar no boot é deliberado, porque o modo de falha oposto é silencioso:

| Variável | Regra | O que acontece se relaxar |
|---|---|---|
| `SECRET_KEY` | ≥ 50 caracteres, ≥ 5 distintos, sem prefixo `django-insecure-` | `check --deploy` acusa `security.W009` |
| `ALLOWED_HOSTS` | obrigatória, sem default; `*` recusado | lista vazia ou curinga desliga a proteção de Host header |
| `CSRF_TRUSTED_ORIGINS` | obrigatória, sem default; esquema em cada origem | origem sem esquema não é reconhecida pelo Django |
| `DATABASE_URL` | obrigatoriamente PostgreSQL | em SQLite, `select_for_update` vira no-op e as garantias da [ADR-0005](docs/adr/0005-concorrencia-transicoes-requisicao.md) somem sem sintoma |
| `PILOTO_ATRAS_DE_PROXY_TLS` | opcional, default `false` | ver abaixo |

O `.env.example` traz o bloco comentado com todas elas.

Ligue `PILOTO_ATRAS_DE_PROXY_TLS=true` **apenas** quando houver um proxy à frente que termine TLS e sobrescreva `X-Forwarded-Proto`. Ligado sem esse proxy, qualquer cliente consegue se declarar HTTPS; desligado atrás de um proxy, o `SECURE_SSL_REDIRECT` entra em laço de redirecionamento.

O piloto envia HSTS com `preload`. A diretiva no cabeçalho não coloca o domínio na lista dos navegadores por si só — isso exige submissão manual —, mas indica essa intenção, então confirme o domínio antes de expor o piloto.

Antes de publicar, valide a configuração:

```bash
DJANGO_SETTINGS_MODULE=config.settings.piloto uv run python manage.py check --deploy
```

Compile o CSS do Tailwind ao menos uma vez antes de subir o servidor:

```bash
npm run css:build
```

## Rodando o projeto

O ambiente local é **efêmero por design**: banco, migrations locais e artefatos de build podem ser apagados e recriados a qualquer momento.

```bash
make setup     # limpa artefatos, recria banco/schema, aplica migrations e carrega seed de dev
make run       # sobe o servidor de desenvolvimento em http://localhost:8000
```

`make setup` executa, em sequência: limpeza de caches e migrations locais → reset do schema PostgreSQL → `makemigrations`/`migrate` → `make seed-dev`.

Rotinas individuais úteis no dia a dia:

```bash
make seed-dev   # recarrega apenas o seed canônico de desenvolvimento
make css-dev    # compila o Tailwind em modo watch
make clean      # limpa caches e migrations locais sem afetar o banco
make help       # lista todas as rotinas disponíveis
```

> Como migrations locais não são versionadas (`.gitignore`), qualquer alteração em `models` deve ser seguida de `make setup` para regenerar o schema do zero.

## Rodando testes

```bash
uv run pytest -q -ra --tb=short --strict-markers --disable-warnings -n logical
```

`-n logical` roda a suíte em paralelo via `pytest-xdist`, no mesmo formato usado pelo CI.

## Qualidade de código

```bash
uv run ruff format .          # formatar
uv run ruff format --check .  # checar formatação (CI)
uv run ruff check .           # lint
uv run mypy apps              # checagem de tipos
```

## Mapa de apps

| App | Responsabilidade |
|---|---|
| `accounts` | Autenticação por matrícula, modelo de usuário, setores, vínculos auxiliares |
| `core` | Dispatcher pós-login, base templates, componentes globais |
| `requisicoes` | Fluxo principal: rascunho, autorização, fila de atendimento, separação, retirada, histórico |
| `estoque` | Saldo de materiais, entradas, saídas excepcionais, integração SCPI |
| `notificacoes` | Notificações in-app (em construção — aguarda [#45](https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/45)) |

## Arquitetura e documentação

Decisões arquiteturais e contratos de domínio ficam registrados em ADRs e documentação viva no repositório:

- [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) — arquitetura em camadas e convenções de implementação
- `docs/adr/` — Architecture Decision Records (contrato service/policy/exceção, estratégia de testes, seed de dev, design system)
- [`docs/design-system.md`](docs/design-system.md) — frontend server-rendered e sistema de design
- `.design/` — handoff de design (information architecture, briefs por área)
- `CONTEXT.md` — glossário e linguagem ubíqua do domínio

## Fluxo de contribuição

- Nunca commitar direto na `main` — sempre criar uma branch de feature.
- Convenção de nomes: `feat/{desc}`, `fix/{desc}`, `refactor/{desc}`, `test/{desc}`, `docs/{desc}`, `chore/{desc}`.
- Commits pequenos, coesos e reversíveis — uma unidade lógica por commit.
- Abra um Pull Request contra `main`; o CI roda lint, testes e checagem de tipos automaticamente.

## Licença

Projeto interno — sem licença de código aberto definida no momento.
