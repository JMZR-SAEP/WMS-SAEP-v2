# Plano — Issue #110: settings de piloto com guarda anti-SQLite

## Escopo

### O que muda

Criar `config/settings/piloto.py`, o módulo de configuração da implantação piloto. Hoje só existem `base`, `dev` e `test`: subir o piloto com `dev` publica `DEBUG=True` em rede, e subir com `base` falha porque `ALLOWED_HOSTS` é `[]`.

A fatia entrega três coisas juntas:

1. **Endurecimento de segurança** — `DEBUG=False`, hosts e origens confiáveis obrigatórios via ambiente, cookies `Secure`, cabeçalhos de segurança suficientes para `check --deploy` passar limpo.
2. **Guarda anti-SQLite** — recusar a inicialização, no import dos settings, se o engine derivado de `DATABASE_URL` não for `django.db.backends.postgresql`.
3. **Verificação automatizada** — testes que travam a guarda e o resultado de `check --deploy`.

### O que NÃO muda

- `config/settings/dev.py` e `config/settings/test.py` permanecem intocados. Continuam sem fallback para SQLite (herdam `DATABASES` de `base`, que exige `DATABASE_URL`).
- `config/settings/base.py` não é alterado. A guarda vive no módulo de piloto, não na base, para que `dev` e `test` mantenham o comportamento atual sem nenhum efeito colateral.
- Nenhuma mudança de model, migration, schema, service, policy ou template.
- O `db.sqlite3` na raiz do repositório não é versionado (já coberto pelo `.gitignore`) — é artefato local. Removê-lo é higiene de máquina, não entrega desta issue.
- O workflow de CI não muda: ele roda com `config.settings.test`, e os testes novos exercitam o piloto em subprocesso com ambiente próprio.

## Arquivos tocados

| Arquivo | Ação | Conteúdo |
|---|---|---|
| `config/settings/guardas.py` | novo | `exigir_engine_postgresql(config_banco, *, alias)` — função pura, sem efeito colateral de import, que levanta `ImproperlyConfigured` quando o engine não é PostgreSQL |
| `config/settings/piloto.py` | novo | herda de `base`, aplica endurecimento de segurança e chama a guarda para cada alias de `DATABASES` |
| `tests/test_settings_piloto.py` | novo | testes unitários da guarda + testes de boot em subprocesso + `check --deploy` |
| `.env.example` | edição | bloco comentado com as variáveis exigidas pelo piloto |
| `README.md` | edição | subseção "Implantação piloto" em `Configuração`, documentando as variáveis e o motivo da guarda |

### Por que a guarda mora em módulo separado

`piloto.py` é um módulo de settings: importá-lo executa `base`, que por sua vez exige `SECRET_KEY` e `DATABASE_URL` no ambiente. Um teste unitário da função de validação não deve depender disso.

Isolar a função em `config/settings/guardas.py` — sem execução no import — permite testar a regra diretamente, e deixa o teste de boot em subprocesso responsável apenas por provar que a guarda de fato roda durante a carga dos settings.

## Decisões de implementação

### Variáveis obrigatórias sem default permissivo

`base.py` declara o schema `environ.Env(DEBUG=(bool, False), ALLOWED_HOSTS=(list, []))`. Reusar essa instância `env` no piloto faria `env.list('ALLOWED_HOSTS')` cair no default `[]` silenciosamente — exatamente o default permissivo que a issue proíbe.

O piloto cria a própria instância `environ.Env()` **sem schema**. Nela, `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` ausentes levantam `ImproperlyConfigured` no boot. O arquivo `.env` já foi lido por `base` via `read_env`, que usa `os.environ.setdefault` — os valores continuam disponíveis para a nova instância.

### Ordem de sobrescrita do `DEBUG`

`base` lê `DEBUG` do ambiente (`env('DEBUG')`, default `False`). O piloto atribui `DEBUG = False` **depois** do `from .base import *`, então a atribuição literal vence: exportar `DEBUG=true` no ambiente do piloto não reabre o modo debug. Isso é intencional e precisa continuar assim — a ordem das linhas é a garantia, e mover a atribuição para antes do import quebraria silenciosamente o critério de aceite 1.

### Cabeçalhos de segurança

Constantes fixas (não parametrizadas por ambiente) para que o critério de aceite 1 seja determinístico:

| Setting | Valor | Check silenciado |
|---|---|---|
| `DEBUG` | `False` | W018 |
| `ALLOWED_HOSTS` | do ambiente, obrigatório | W020 |
| `SESSION_COOKIE_SECURE` | `True` | W012 |
| `CSRF_COOKIE_SECURE` | `True` | W016 |
| `SECURE_CONTENT_TYPE_NOSNIFF` | `True` | W006 |
| `SECURE_SSL_REDIRECT` | `True` | W008 |
| `SECURE_HSTS_SECONDS` | `31536000` | W004 |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` | W005 |
| `SECURE_HSTS_PRELOAD` | `True` | W021 |
| `X_FRAME_OPTIONS` | `'DENY'` | W019 |

`SECRET_KEY` (W009) já vem do ambiente via `base`; o piloto não pode reforçá-la além de exigir a variável — a documentação registra o mínimo de 50 caracteres.

### `SECURE_PROXY_SSL_HEADER` é opt-in

Confiar em `X-Forwarded-Proto` incondicionalmente é um buraco de segurança quando não há proxy que sobrescreva o cabeçalho: qualquer cliente pode se declarar HTTPS. Mas sem ele, atrás de um proxy que termina TLS, `SECURE_SSL_REDIRECT=True` produz laço de redirecionamento.

Fica atrás da variável booleana `PILOTO_ATRAS_DE_PROXY_TLS`, default `False`. Ligar só quando o piloto estiver de fato atrás de um proxy que reescreve o cabeçalho.

### Escopo da guarda

Estrita: só `django.db.backends.postgresql` passa. `postgis`, `mysql`, `sqlite3` e engine ausente são recusados. O projeto não usa GIS, e afrouxar a regra reabre a porta que a issue quer fechar.

A guarda percorre todos os aliases de `DATABASES` (hoje só `default`), e a mensagem de erro nomeia o alias, o engine encontrado e a correção esperada.

## Estratégia de testes

Camada de configuração — não há regra de domínio envolvida, então os testes vivem em `tests/`, junto de `test_ci_workflow.py`, e não em `apps/*/tests/`.

### Unitários da guarda (função pura, sem banco, sem Django configurado)

| Caso | Expectativa |
|---|---|
| engine `django.db.backends.postgresql` | não levanta |
| engine `django.db.backends.sqlite3` | `ImproperlyConfigured`; mensagem cita `DATABASE_URL`, PostgreSQL e o engine encontrado |
| engine `django.db.backends.mysql` | `ImproperlyConfigured` |
| chave `ENGINE` ausente / vazia | `ImproperlyConfigured` |
| alias diferente de `default` | alias aparece na mensagem |

### Boot em subprocesso (prova que a guarda roda no import dos settings)

Cada caso roda `python -c "import django; django.setup()"` com `DJANGO_SETTINGS_MODULE=config.settings.piloto` e um ambiente controlado, montado explicitamente (sem herdar o ambiente do pytest, que já tem `DATABASE_URL` de PostgreSQL).

| Caso | Expectativa |
|---|---|
| `DATABASE_URL=sqlite:///...` | exit code ≠ 0, stderr com a mensagem da guarda |
| `DATABASE_URL=postgres://...` | exit code 0 |
| `ALLOWED_HOSTS` ausente | exit code ≠ 0, stderr cita `ALLOWED_HOSTS` |
| `CSRF_TRUSTED_ORIGINS` ausente | exit code ≠ 0, stderr cita `CSRF_TRUSTED_ORIGINS` |

`django.setup()` não abre conexão com o banco, então o caso PostgreSQL passa sem servidor de pé — o teste roda em qualquer máquina e no CI.

### `check --deploy` (trava o critério de aceite 1)

`manage.py check --deploy` com settings de piloto, `SECRET_KEY` forte e as variáveis obrigatórias preenchidas: exit code 0 e nenhuma linha `security.W0` na saída. `check` não abre conexão com o banco.

## Invariantes

- **ADR-0005 (concorrência)** — é a invariante que a issue protege. Toda transição de estado depende de `select_for_update` sob `transaction.atomic`. Em SQLite, `select_for_update` é no-op silencioso: nenhuma exceção, nenhum log, e duas transições concorrentes podem ler o mesmo estado de origem e ambas gravar. A guarda transforma essa falha silenciosa em falha de boot.
- **ADR-0010 (testes)** — sem `factory_boy`; testes de configuração não tocam banco nem fixtures de domínio.
- **ADR-0012 (CI)** — o job de pytest continua rodando com `config.settings.test` e `DATABASE_URL` de PostgreSQL; os testes novos não exigem variável nova no workflow.
- `dev` e `test` continuam sem fallback para SQLite — validado pela ausência de diff nesses arquivos.

## Riscos

| Risco | Mitigação |
|---|---|
| Teste de subprocesso herdar `DATABASE_URL` do pytest e mascarar o caso SQLite | nunca usar `os.environ.copy()`; montar o `env` do subprocesso do zero, com apenas `PATH`, `HOME` e as variáveis do caso |
| `.env` da máquina local sobrescrever o ambiente do subprocesso | `environ.Env.read_env` usa `os.environ.setdefault`, então o valor explícito do teste vence; o caso SQLite prova isso na prática |
| `SECURE_SSL_REDIRECT=True` gerar laço de redirecionamento atrás de proxy | `PILOTO_ATRAS_DE_PROXY_TLS` documentado no `.env.example` e no README |
| HSTS com `preload` ser difícil de reverter no piloto | `preload` apenas emite a diretiva no cabeçalho; a inclusão na lista dos navegadores exige submissão manual — registrado no README |
| Guarda estrita recusar um engine PostgreSQL legítimo no futuro (ex.: PostGIS) | recusa é explícita e a mensagem nomeia o engine encontrado; afrouxar exige decisão consciente, não acidente |
| Contrato OpenAPI / mutação de estoque / máquina de estados | não aplicável — a mudança é só de configuração |

## Fora de escopo

- Dockerfile, systemd unit, script de deploy ou pipeline de publicação do piloto.
- `STATICFILES_STORAGE` / WhiteNoise, logging estruturado, cache e configuração de e-mail — pertencem a issues próprias de operação.
- Remoção do `db.sqlite3` local.
