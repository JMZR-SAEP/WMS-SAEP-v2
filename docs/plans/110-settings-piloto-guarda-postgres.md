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
| `config/settings/guardas.py` | novo | funções puras, sem efeito colateral de import: `exigir_bancos_postgresql(databases)`, `exigir_hosts_permitidos(bruto)` e `exigir_origens_csrf_confiaveis(bruto)` |
| `config/settings/piloto.py` | novo | herda de `base`, aplica endurecimento de segurança e chama as guardas |
| `tests/test_settings_piloto.py` | novo | testes unitários da guarda + testes de boot em subprocesso + `check --deploy` |
| `.env.example` | edição | bloco comentado com as variáveis exigidas pelo piloto |
| `README.md` | edição | subseção "Implantação piloto" em `Configuração`, documentando as variáveis e o motivo da guarda |

### Por que a guarda mora em módulo separado

`piloto.py` é um módulo de settings: importá-lo executa `base`, que por sua vez exige `SECRET_KEY` e `DATABASE_URL` no ambiente. Um teste unitário das funções de validação não deve depender disso.

Isolar as funções em `config/settings/guardas.py` — sem execução no import — permite testar as regras diretamente, e deixa o teste de boot em subprocesso responsável apenas por provar que as guardas de fato rodam durante a carga dos settings.

**Corolário sobre a varredura de aliases:** o laço sobre `DATABASES` mora dentro de `exigir_bancos_postgresql`, não em `piloto.py`. `base` só constrói o alias `default`, então um teste de boot nunca conseguiria exercitar um segundo alias sem inventar uma variável de ambiente que a issue não pede. Com o laço na função pura, o contrato "todos os aliases são verificados" é provado por teste unitário (`default` PostgreSQL + `replica` SQLite deve falhar citando `replica`), e o teste de boot cobre o que o boot real tem: `default`.

## Decisões de implementação

### Variáveis obrigatórias sem default permissivo

`base.py` declara o schema `environ.Env(DEBUG=(bool, False), ALLOWED_HOSTS=(list, []))`. Reusar essa instância `env` no piloto faria `env.list('ALLOWED_HOSTS')` cair no default `[]` silenciosamente — exatamente o default permissivo que a issue proíbe.

O piloto cria a própria instância `environ.Env()` **sem schema** e lê as duas variáveis com `env.list(...)` — nunca com `env(...)`, que devolveria uma string crua e faria o Django iterar caractere a caractere. Nessa instância, variável ausente levanta `ImproperlyConfigured` no boot. O arquivo `.env` já foi lido por `base` via `read_env`, que usa `os.environ.setdefault` — os valores continuam disponíveis para a nova instância.

Ausência, porém, não é a única forma de configuração permissiva. `django-environ` descarta itens vazios ao fazer o parsing, então `ALLOWED_HOSTS=` e `ALLOWED_HOSTS=,,` viram `[]` silenciosamente — o mesmo default permissivo por outro caminho. As guardas validam o **valor bruto**, antes do parsing:

| Variável | Rejeitado | Motivo |
|---|---|---|
| `ALLOWED_HOSTS` | ausente, vazia, só separadores, item vazio | `[]` desliga a proteção de Host header sem sintoma |
| `ALLOWED_HOSTS` | qualquer item `*` | curinga aceita qualquer Host; a validação passaria a depender de um proxy que o piloto não garante ter |
| `CSRF_TRUSTED_ORIGINS` | ausente, vazia, só separadores, item vazio | mesma classe de falha silenciosa |
| `CSRF_TRUSTED_ORIGINS` | item sem esquema (`exemplo.com`) | o Django exige `https://exemplo.com`; falhar no boot com mensagem nomeando o item é mais acionável que o system check genérico |

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

`SECRET_KEY` (W009) já vem do ambiente via `base`; o boot só exige que a variável exista. Quem valida a **qualidade** da chave é o `check --deploy`, e a regra é executável, não conselho: `security.W009` dispara com menos de 50 caracteres, menos de 5 caracteres distintos, ou prefixo `django-insecure-`. Isso é o que o README e o `.env.example` devem registrar, e o teste de `check --deploy` com chave fraca prova que a regra chega ao operador.

### `SECURE_PROXY_SSL_HEADER` é opt-in

Confiar em `X-Forwarded-Proto` incondicionalmente é um buraco de segurança quando não há proxy que sobrescreva o cabeçalho: qualquer cliente pode se declarar HTTPS. Mas sem ele, atrás de um proxy que termina TLS, `SECURE_SSL_REDIRECT=True` produz laço de redirecionamento.

Fica atrás da variável booleana `PILOTO_ATRAS_DE_PROXY_TLS`, default `False`. Ligar só quando o piloto estiver de fato atrás de um proxy que reescreve o cabeçalho.

### Escopo da guarda

Estrita: só `django.db.backends.postgresql` passa. `postgis`, `mysql`, `sqlite3` e engine ausente são recusados. O projeto não usa GIS, e afrouxar a regra reabre a porta que a issue quer fechar.

`exigir_bancos_postgresql` percorre todos os aliases de `DATABASES` (hoje só `default`), e a mensagem de erro nomeia o alias, o engine encontrado e a correção esperada.

## Estratégia de testes

Camada de configuração — não há regra de domínio envolvida, então os testes vivem em `tests/`, junto de `test_ci_workflow.py`, e não em `apps/*/tests/`.

### Unitários da guarda (função pura, sem banco, sem Django configurado)

**`exigir_bancos_postgresql`** — recebe o dicionário inteiro de `DATABASES`:

| Caso | Expectativa |
|---|---|
| `{default: postgresql}` | não levanta |
| `{default: sqlite3}` | `ImproperlyConfigured`; mensagem cita `DATABASE_URL`, PostgreSQL e o engine encontrado |
| `{default: mysql}` | `ImproperlyConfigured` |
| `{default: postgis}` | `ImproperlyConfigured` — a regra é estrita por decisão |
| `{default: {}}` — `ENGINE` ausente / vazio | `ImproperlyConfigured` |
| `{default: postgresql, replica: sqlite3}` | `ImproperlyConfigured`; mensagem cita **`replica`** — prova que o laço percorre todos os aliases, não só o primeiro |
| `{default: postgresql, replica: postgresql}` | não levanta |

**`exigir_hosts_permitidos`** — recebe o valor bruto da variável:

| Caso | Expectativa |
|---|---|
| `'piloto.exemplo.gov.br'` | devolve `['piloto.exemplo.gov.br']` |
| `'a.exemplo.br, b.exemplo.br'` | devolve os dois itens, sem espaços |
| `''` / `'   '` / `',,'` | `ImproperlyConfigured` — lista vazia é default permissivo |
| `'*'` / `'a.exemplo.br,*'` | `ImproperlyConfigured` — curinga citado na mensagem |
| `'a.exemplo.br,,b.exemplo.br'` | `ImproperlyConfigured` — item vazio |

**`exigir_origens_csrf_confiaveis`** — mesmas regras de vazio, mais o esquema:

| Caso | Expectativa |
|---|---|
| `'https://piloto.exemplo.gov.br'` | devolve o item |
| `'piloto.exemplo.gov.br'` | `ImproperlyConfigured`; mensagem cita o item e exige esquema |
| `''` / `',,'` | `ImproperlyConfigured` |

### Boot em subprocesso (prova que as guardas rodam no import dos settings)

Cada caso roda `python -c "import django; django.setup()"` com `DJANGO_SETTINGS_MODULE=config.settings.piloto` e um ambiente montado do zero — nunca `os.environ.copy()`, para que o `DATABASE_URL` de PostgreSQL do pytest não mascare o caso SQLite.

**Hermeticidade:** `base.py` chama `read_env(BASE_DIR / '.env')` com `overwrite=False`, isto é, `os.environ.setdefault`. Um `.env` local que defina `ALLOWED_HOSTS` alimentaria o subprocesso e faria um caso de "variável ausente" passar por acidente numa máquina e falhar noutra. Por isso os casos de configuração permissiva são expressos com a variável **explicitamente definida como valor vazio ou inválido** — valor explícito vence o `setdefault`, então o caso é hermético em qualquer máquina e no CI. A ausência pura continua coberta, hermeticamente, pelos testes unitários das guardas.

| Caso | Expectativa |
|---|---|
| `DATABASE_URL=sqlite:///...` | exit ≠ 0, stderr com a mensagem da guarda de banco |
| `DATABASE_URL=postgres://...` | exit 0 |
| `ALLOWED_HOSTS=` (vazia) | exit ≠ 0, stderr cita `ALLOWED_HOSTS` |
| `ALLOWED_HOSTS=*` | exit ≠ 0, stderr cita o curinga |
| `CSRF_TRUSTED_ORIGINS=` (vazia) | exit ≠ 0, stderr cita `CSRF_TRUSTED_ORIGINS` |
| `CSRF_TRUSTED_ORIGINS=piloto.exemplo.gov.br` (sem esquema) | exit ≠ 0, stderr exige esquema |

`django.setup()` não abre conexão com o banco, então o caso PostgreSQL passa sem servidor de pé — o teste roda em qualquer máquina e no CI.

### Valores efetivos de segurança

`check --deploy` prova que não há warning, mas não prova *qual* valor produziu esse resultado — uma regressão que troque `SECURE_HSTS_SECONDS` por um valor menor, ou que remova `SECURE_PROXY_SSL_HEADER`, passaria despercebida. Um subprocesso separado carrega os settings de piloto e imprime em JSON os valores efetivos; o teste compara com a tabela de cabeçalhos de segurança, item a item: `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`, `X_FRAME_OPTIONS`.

`SECURE_PROXY_SSL_HEADER` é verificado nos dois estados: ausente por padrão, e igual a `('HTTP_X_FORWARDED_PROTO', 'https')` quando `PILOTO_ATRAS_DE_PROXY_TLS=true`.

### `check --deploy` (trava o critério de aceite 1)

`manage.py check --deploy` com settings de piloto, `SECRET_KEY` forte e as variáveis obrigatórias preenchidas: exit code 0 e nenhuma ocorrência de `security.W0` em `stdout` **nem** em `stderr` — o `check` escreve os warnings em `stderr`, então capturar só `stdout` daria um verde falso. `check` não abre conexão com o banco.

Um segundo caso roda o mesmo comando com `SECRET_KEY` fraca e espera `security.W009` na saída. Isso prova que o caminho de verificação está de fato ligado; a fronteira exata de 49 vs. 50 caracteres não é testada, porque é regra interna do Django, não deste repositório.

## Invariantes

- **ADR-0005 (concorrência)** — é a invariante que a issue protege. Toda transição de estado depende de `select_for_update` sob `transaction.atomic`. Em SQLite, `select_for_update` é no-op silencioso: nenhuma exceção, nenhum log, e duas transições concorrentes podem ler o mesmo estado de origem e ambas gravar. A guarda transforma essa falha silenciosa em falha de boot.
- **ADR-0010 (testes)** — sem `factory_boy`; testes de configuração não tocam banco nem fixtures de domínio.
- **ADR-0012 (CI)** — o job de pytest continua rodando com `config.settings.test` e `DATABASE_URL` de PostgreSQL; os testes novos não exigem variável nova no workflow.
- `dev` e `test` continuam sem fallback para SQLite — validado pela ausência de diff nesses arquivos.

## Riscos

| Risco | Mitigação |
|---|---|
| Teste de subprocesso herdar `DATABASE_URL` do pytest e mascarar o caso SQLite | nunca usar `os.environ.copy()`; montar o `env` do subprocesso do zero, com apenas `PATH`, `HOME` e as variáveis do caso |
| `.env` da máquina local alimentar o subprocesso e mascarar um caso de "variável ausente" | `read_env` usa `overwrite=False` (`setdefault`), então valor explícito vence; os casos de boot usam valores vazios/inválidos explícitos em vez de ausência, e a ausência pura fica nos testes unitários das guardas |
| `SECURE_SSL_REDIRECT=True` gerar laço de redirecionamento atrás de proxy | `PILOTO_ATRAS_DE_PROXY_TLS` documentado no `.env.example` e no README |
| HSTS com `preload` ser difícil de reverter no piloto | `preload` apenas emite a diretiva no cabeçalho; a inclusão na lista dos navegadores exige submissão manual — registrado no README |
| Guarda estrita recusar um engine PostgreSQL legítimo no futuro (ex.: PostGIS) | recusa é explícita e a mensagem nomeia o engine encontrado; afrouxar exige decisão consciente, não acidente |
| Contrato OpenAPI / mutação de estoque / máquina de estados | não aplicável — a mudança é só de configuração |

## Fora de escopo

- Dockerfile, systemd unit, script de deploy ou pipeline de publicação do piloto.
- `STATICFILES_STORAGE` / WhiteNoise, logging estruturado, cache e configuração de e-mail — pertencem a issues próprias de operação.
- Remoção do `db.sqlite3` local.
