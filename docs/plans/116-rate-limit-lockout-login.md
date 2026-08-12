# Plano — Issue #116: rate-limit/lockout no login por matrícula (django-axes)

`MatriculaLoginView` é um `LoginView` puro: qualquer cliente pode postar
matrícula e senha em laço, sem limite, sem atraso e sem registro. O namespace de
matrículas é curto e adivinhável (`OBRAS001`, `ALMOX001`), então o único custo de
uma força bruta hoje é largura de banda — achado R9 da auditoria.

A issue é HITL e oferecia três saídas. **A decisão tomada é a opção 1:
`django-axes`.** Este plano registra a decisão em ADR e implementa o lockout.

## Decisão registrada

**Opção escolhida: `django-axes` 8.x (`django-axes[ipware]`).**

Por que não as outras duas:

- **Throttle no proxy reverso** (opção 2) tem custo zero de código, mas o piloto
  não garante proxy: `config/settings/piloto.py` trata estar atrás de proxy TLS
  como *opt-in* (`PILOTO_ATRAS_DE_PROXY_TLS`, default `False`). Uma proteção que
  só existe quando uma variável de ambiente opcional está ligada não é
  proteção — é sorte. Além disso, `limit_req` no nginx conta requisições por IP,
  não tentativas falhas por conta: ou aperta a ponto de atrapalhar quem erra a
  senha duas vezes, ou afrouxa a ponto de permitir força bruta lenta.
- **Rate-limit artesanal em cache** (opção 3) foi desaconselhada na própria
  issue, e com razão: o projeto não tem `CACHES` configurado hoje, então a opção
  exigiria montar backend de cache *e* escrever lógica de contagem, expiração e
  reset — reinventando exatamente o que a opção 1 traz testado.

`django-axes` cobre o que as duas outras não cobrem: conta tentativa **falha**
(não requisição), chaveia por matrícula + IP, expira sozinha, tem reset por
sucesso, comando de desbloqueio e trilha auditável de tentativas. Custo: uma
dependência e duas tabelas.

A decisão vira **ADR-0018**, não nota de runbook, porque muda o pipeline de
autenticação do projeto (`AUTHENTICATION_BACKENDS`, middleware) — é decisão
estrutural, não parâmetro de implantação.

## Escopo

### O que muda

- **`pyproject.toml`** — nova dependência de produção
  `django-axes[ipware]>=8.3,<9`. O extra `ipware` **não** é opcional para este
  projeto: a partir da versão 6, `django-axes` só resolve IP de cliente atrás de
  proxy quando `django-ipware` está instalado; sem ele o IP é sempre
  `REMOTE_ADDR`. `uv lock` acompanha o commit.
- **`config/settings/base.py`** —
  - `'axes'` em `INSTALLED_APPS`;
  - `'axes.middleware.AxesMiddleware'` como **último** item de `MIDDLEWARE`
    (exigência do pacote: ele só formata a resposta de bloqueio, na fase de
    resposta);
  - `AUTHENTICATION_BACKENDS = ['axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend']`. Hoje a chave não existe e o
    Django usa o default implícito (`ModelBackend`); passa a ser explícita, com
    o backend do axes **primeiro** — é ele que aborta a autenticação de um
    cliente já bloqueado antes de qualquer verificação de senha.
    `AxesStandaloneBackend` (e não `AxesBackend`) porque o projeto não precisa
    que o axes encadeie a autenticação real; ele só barra.
  - política de bloqueio:
    ```python
    AXES_USERNAME_FORM_FIELD = 'username'
    AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]
    AXES_FAILURE_LIMIT = 5
    AXES_COOLOFF_TIME = timedelta(minutes=15)
    AXES_USE_ATTEMPT_EXPIRATION = True
    AXES_RESET_ON_SUCCESS = True
    AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = True
    AXES_ENABLE_RETRY_AFTER_HEADER = True
    AXES_LOCKOUT_TEMPLATE = 'accounts/login_bloqueado.html'
    ```
    `AXES_USERNAME_FORM_FIELD = 'username'` **não** é redundante, apesar de
    `'username'` parecer o óbvio: o default do axes é
    `get_user_model().USERNAME_FIELD`, que neste projeto é `'matricula'`. Mas
    quem posta é o `AuthenticationForm` do Django, cujo campo se chama sempre
    `username` — e é essa a chave que chega tanto em `request.POST` quanto no
    `credentials` de `authenticate()`. Sem a linha, o axes procuraria
    `'matricula'`, não acharia, e chavearia **todas** as falhas do sistema sob
    `username=None`: um bucket global, em que cinco erros de senha de qualquer
    pessoa trancam todo mundo. O teste 5 (isolamento por matrícula) é o que
    fixa isso.

    `AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT` é declarado explicitamente
    embora `True` seja o default: é ele que faz cada tentativa durante o
    bloqueio reiniciar os 15 minutos, e a escolha tem consequência de segurança
    (ver risco 1). Deixar implícito esconderia a decisão.

    O parâmetro de bloqueio é a **lista aninhada** `[['username', 'ip_address']]`, não
    `['username', 'ip_address']`: aninhado significa "bloqueia a combinação",
    plano significaria "bloqueia por matrícula **ou** por IP, o que vier
    primeiro". Só a forma aninhada atende o critério de aceite de não trancar
    usuário legítimo por engano — com a forma plana, um atacante que conhece a
    matrícula de alguém tranca essa pessoa de qualquer lugar.
- **`config/settings/piloto.py`** — dentro do bloco `if
  env_piloto.bool('PILOTO_ATRAS_DE_PROXY_TLS', ...)` que já existe, acrescenta
  `AXES_IPWARE_META_PRECEDENCE_ORDER = ['HTTP_X_FORWARDED_FOR']` e
  `AXES_IPWARE_PROXY_COUNT = 1`. A condição é reusada de propósito: confiar em
  `X-Forwarded-For` para identificar o cliente tem exatamente o mesmo
  pré-requisito que confiar em `X-Forwarded-Proto` — um proxy na frente que
  sobrescreva o cabeçalho. Ligar um sem o outro é incoerente, e ligar qualquer
  um sem proxy deixa o cliente escolher o próprio IP (e, aqui, escapar do
  lockout trocando o cabeçalho a cada tentativa).
- **`apps/accounts/templates/accounts/login_bloqueado.html`** — nova página de
  bloqueio, servida pelo `AxesMiddleware` com status **429 Too Many Requests**
  (default de `AXES_HTTP_RESPONSE_CODE`, mantido: 429 é o código correto para
  limite de tentativas, e 403 diria "proibido" para quem talvez seja o dono da
  conta). Estende `base.html` e reusa `components/alert.html`
  (`variant="danger"`), no mesmo enquadramento visual da tela de login. Copy em
  PT-BR informando que o acesso está temporariamente bloqueado por tentativas
  repetidas, quanto tempo dura a janela e a quem recorrer.
  O axes injeta no contexto `failure_limit`, `failure_count`, `username`,
  `cooloff_time` (duração em ISO 8601, ex. `PT15M`) e `cooloff_timedelta`. O
  template renderiza a janela como texto fixo em PT-BR ("15 minutos") em vez de
  imprimir `cooloff_time` cru, e **ignora** `username`: repetir a matrícula
  tentada transformaria a página em oráculo de enumeração de contas.
- **`docs/adr/0018-lockout-login-django-axes.md`** — ADR novo, status Aceita,
  registrando decisão, alternativas descartadas, limiares e o procedimento de
  desbloqueio manual.
- **`docs/checklist-go-live.md`** — seção "Autenticação" com item **GL-02**:
  conferir, antes de liberar, que o lockout está ativo e que a resolução de IP
  bate com a topologia de implantação (com ou sem proxy). O item traz os comandos
  de inspeção e desbloqueio — `manage.py axes_list_attempts`,
  `manage.py axes_reset_username <matricula>` e o mais cirúrgico
  `manage.py axes_reset_ip_username <ip> <matricula>` —, que é o que a equipe
  vai precisar às 8h de uma segunda-feira.

### O que não muda

- **`apps/accounts/views.py` e `forms.py`.** Nenhuma linha. Todo o mecanismo
  entra por backend + middleware; a view continua um `LoginView` e o formulário
  continua só cuidando de rótulo e acessibilidade. Registrado aqui porque a
  opção 3 da issue teria colocado a lógica dentro de
  `MatriculaAuthenticationForm`, e este plano deliberadamente não vai lá.
- **Autorização de domínio.** Nenhuma policy, nenhum service, nenhum selector.
  Lockout é controle de autenticação, anterior a papel; `docs/matriz-permissoes.md`
  não ganha linha.
- **Modelos de domínio.** Nenhum. As tabelas novas (`AccessAttempt`,
  `AccessLog`, `AccessFailureLog`) vêm com migrations do próprio pacote e não
  ficam sob `apps/**/migrations/` — a regra de migrations efêmeras do projeto
  não se aplica a elas.
- **Testes existentes.** Nenhum é editado. Toda a suíte autentica via
  `client.force_login`, que não passa pelo pipeline de `authenticate()` e
  portanto não dispara o axes; e não há uma única chamada a `client.login()` no
  repositório (que seria o caso problemático, por não repassar `request` ao
  backend). Os testes de `test_login.py` que postam senha errada fazem **uma**
  falha por teste, e cada teste roda em transação própria — nenhum se aproxima
  do limite de 5.
- **`config/settings/test.py`.** O axes fica **ligado** na suíte. `AXES_ENABLED =
  False` existe e é tentador, mas desligá-lo tornaria os testes de lockout deste
  plano impossíveis de escrever contra o comportamento real.
- **Admin.** O axes registra os próprios models no admin (`AXES_ENABLE_ADMIN`,
  default ligado) e isso fica como está: é a superfície de desbloqueio pela
  interface, e as permissões desses models não são atribuídas a papel nenhum —
  na prática, só superusuário enxerga. Nenhum `admin.py` do projeto é tocado.

## Arquivos tocados

| Arquivo | Mudança |
|---|---|
| `pyproject.toml` | Dependência `django-axes[ipware]>=8.3,<9`. |
| `uv.lock` | Resolução da dependência nova. |
| `config/settings/base.py` | App, middleware, `AUTHENTICATION_BACKENDS` e política `AXES_*`. |
| `config/settings/piloto.py` | Resolução de IP via `X-Forwarded-For` sob a flag de proxy já existente. |
| `apps/accounts/templates/accounts/login_bloqueado.html` | Página de bloqueio (429). |
| `apps/accounts/tests/test_lockout.py` | Suíte nova do lockout. |
| `docs/adr/0018-lockout-login-django-axes.md` | ADR da decisão. |
| `docs/checklist-go-live.md` | Item GL-02 e procedimento de desbloqueio. |

## Estratégia de testes

Arquivo novo `apps/accounts/tests/test_lockout.py`, uma fatia vertical por
comportamento (RED → GREEN → REFACTOR), sempre pela rota real
(`client.post(reverse('accounts:login'), ...)`) — nunca chamando helpers do axes
diretamente, que testariam a biblioteca em vez da configuração do projeto.

Duas técnicas usadas em vez de dependências novas:

- **IP do cliente**: `client.post(..., REMOTE_ADDR='10.0.0.7')`, que é o que o
  ipware lê quando não há proxy configurado.
- **Passagem do tempo**: sem `freezegun`/`time-machine` (não são dependências do
  projeto). Para simular o fim da janela, os testes envelhecem as linhas
  gravadas — `AccessAttempt.objects.update(attempt_time=timezone.now() -
  timedelta(minutes=16))` — que é exatamente o estado do banco 16 minutos
  depois.

Comportamentos cobertos:

1. **Caminho feliz preservado** — login válido continua 302 e autentica, com o
   axes no meio do caminho. É o teste que pega uma configuração de backend
   trocada.
2. **Abaixo do limite não bloqueia** — 4 falhas seguidas e a 4ª ainda responde
   200 com o formulário de login, não a página de bloqueio. Fixa o limiar por
   baixo.
3. **No limite bloqueia** — a 5ª falha responde **429**, renderiza
   `accounts/login_bloqueado.html` e traz `Retry-After: 900`.
4. **Bloqueio vale contra senha correta** — depois de bloqueado, POST com a
   senha **certa** ainda responde 429 e
   `resposta.wsgi_request.user.is_authenticated` é falso. Este é o teste que
   prova que existe lockout, e não apenas uma mensagem de erro diferente.
5. **Isolamento por matrícula** — usuário A bloqueado; usuário B, do **mesmo
   IP**, entra normalmente. Prova a metade `username` do parâmetro combinado.
6. **Isolamento por IP** — a mesma matrícula bloqueada em `10.0.0.7` entra
   normalmente a partir de `10.0.0.8`. Prova a metade `ip_address` e é o teste
   que quebraria se alguém trocasse a lista aninhada pela plana.
7. **Reset por sucesso** — 4 falhas, 1 sucesso, mais 4 falhas: a última ainda
   responde 200. Sem `AXES_RESET_ON_SUCCESS`, esta oitava falha bloquearia um
   usuário que provou saber a própria senha no meio do caminho — é o critério
   de aceite "não trancar usuário legítimo" em forma executável.
8. **Fim da janela libera** — bloqueado, tentativas envelhecidas em 16 minutos,
   login com senha correta volta a 302 e autentica.
9. **Página de bloqueio** — 429, PT-BR, herda `base.html`, traz a janela de 15
   minutos no texto, e **não** contém a matrícula tentada (não-oráculo). A
   asserção de ausência usa uma matrícula que não aparece em nenhum outro
   lugar do HTML, para não passar por acidente.

Fora deste arquivo, o critério real de regressão é a suíte inteira continuar
verde: qualquer teste que autenticasse por um caminho incompatível com o axes
falharia em bloco.

## Invariantes relevantes (`docs/matriz-invariantes.md`)

A matriz não tem hoje nenhuma linha sobre autenticação — ela começa em
permissões de domínio (PER-\*), que pressupõem usuário já autenticado. Este
plano **não** acrescenta linha: criar uma família nova de invariantes a partir
de uma issue de infraestrutura seria decisão de escopo maior que a issue.

| Invariante | Efeito |
|---|---|
| **PER-01 … PER-08** | Intocados. Nenhuma policy, service ou selector muda; o lockout age antes de existir usuário autenticado, logo antes de existir papel. |
| **PER-05** | Preservado. Superusuário não ganha isenção de lockout — não há whitelist configurada. O desbloqueio é ação explícita (comando ou admin), não um bypass silencioso. |
| **EST-\*, LED-\*** | Intocados. Nenhuma mutação de estoque ou de razão entra no caminho. |

## Riscos

1. **Proxy sem `X-Forwarded-For` confiável.** Se o piloto subir atrás de proxy
   com `PILOTO_ATRAS_DE_PROXY_TLS` desligado, todos os usuários chegam com o IP
   do proxy: `['username', 'ip_address']` degenera em "só username", e um
   atacante passa a conseguir trancar qualquer matrícula que conheça — um DoS
   por conta. O inverso é pior: ligar a leitura do cabeçalho **sem** proxy que o
   sobrescreva deixa o atacante trocar o próprio IP a cada tentativa e nunca
   bater no limite. Não há default seguro para os dois cenários; por isso o item
   GL-02 do checklist de go-live exige conferir a topologia, e por isso a
   configuração fica amarrada à flag de proxy que já existe.
   No cenário degenerado, `AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = True`
   agrava: um atacante que continue tentando reinicia a janela a cada falha e
   mantém a vítima trancada indefinidamente. Ainda assim o valor fica `True`,
   porque no cenário **correto** (IP real por cliente) ele só prolonga o bloqueio
   de quem ataca; abrir mão dele seria pagar segurança no caso bom para amenizar
   justamente o caso que o GL-02 existe para impedir.
2. **Ataque distribuído continua viável.** Com o parâmetro combinado, cada IP
   novo ganha 5 tentativas contra a mesma matrícula. Contra botnet, isso não
   segura. É trade-off consciente: proteger contra IP rotativo exigiria bloqueio
   por matrícula pura, que reintroduz o DoS do risco 1. Para ~20 usuários em
   rede interna, o vetor de força bruta distribuída não é o cenário desta fase.
3. **Bloqueio legítimo em uso compartilhado.** Terminal de almoxarifado usado
   por várias pessoas com a mesma matrícula operacional concentra falhas num par
   (matrícula, IP) só. Mitigado por `AXES_RESET_ON_SUCCESS` e pela janela curta
   (15 min), mas o desbloqueio manual precisa estar documentado onde a equipe
   ache — daí o comando entrar no checklist, não só no ADR.
4. **Dependência e superfície nova.** Duas tabelas e um backend a mais no
   caminho crítico do login. `django-axes` 8.3 declara suporte a Django 6.0 e
   Python 3.13, que é a combinação do projeto; ainda assim, o pin `<9` evita que
   uma major nova entre sozinha num `uv lock` futuro.
5. **Custo por tentativa falha.** O handler default grava em banco: uma escrita
   por falha. Irrelevante nesta escala, e a alternativa (handler em cache) exige
   `CACHES`, que o projeto não tem.
6. **Suíte com o axes ligado.** Um teste futuro que faça 5+ logins falhos do
   mesmo usuário passa a receber 429 em vez de 200. É um efeito real de manter o
   axes ativo nos testes, e é o preço de testar a configuração de verdade; o ADR
   registra `override_settings(AXES_ENABLED=False)` como escape para esse caso.

## Fora de escopo

- Backend de cache (`CACHES`) e troca do handler de banco pelo de cache.
- Rate-limit em outras rotas além do login (admin, downloads, importação SCPI).
- CAPTCHA, 2FA, política de expiração ou de complexidade de senha.
- Alerta/notificação para o administrador quando uma conta é bloqueada.
- Configuração de `limit_req` no proxy — descartada como solução desta issue e
  não retomada como camada extra.
- Linha nova na matriz de invariantes para autenticação.
