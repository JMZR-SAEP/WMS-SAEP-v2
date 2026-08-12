# Plano — Issue #116: rate-limit/lockout no login por matrícula (django-axes)

`MatriculaLoginView` é um `LoginView` puro: qualquer cliente pode postar
matrícula e senha em laço, sem limite, sem atraso e sem registro. O namespace de
matrículas é curto e adivinhável (`OBRAS001`, `ALMOX001`), então o único custo de
uma força bruta hoje é largura de banda — achado R9 da auditoria.

A issue é HITL e oferecia três saídas. **A decisão tomada é a opção 1:
`django-axes`.** Este documento é **só o plano**: registra a decisão e orienta a
implementação, que ainda não existe. Nada do que está descrito abaixo foi
codado — o PR que traz este arquivo não contém código.

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
sucesso, comandos de desbloqueio e trilha auditável. Custo: uma dependência e
**quatro** tabelas criadas por migration —

| Tabela | Escrita nesta configuração? | Papel |
|---|---|---|
| `AccessAttempt` | Sim | Agrega falhas por (matrícula, IP, user-agent). É o contador do lockout. Apagada por reset ou expiração. |
| `AccessAttemptExpiration` | Sim | Existe porque `AXES_USE_ATTEMPT_EXPIRATION=True`; guarda o `expires_at` de cada `AccessAttempt`, e é por esse campo que a limpeza filtra. |
| `AccessLog` | Sim | Login e logout bem-sucedidos. |
| `AccessFailureLog` | Sim, **por opção deste plano** | Registro durável de cada falha, `AXES_ENABLE_ACCESS_FAILURE_LOG=True` (default é `False`). Sem ele não há "trilha auditável": `AccessAttempt` é agregado e some no primeiro login bem-sucedido, por causa de `AXES_RESET_ON_SUCCESS`. |

Auditoria tem contrapartida de retenção e de dado pessoal: `AccessFailureLog` e
`AccessLog` guardam matrícula, IP e user-agent. O crescimento de
`AccessFailureLog` é limitado por `AXES_ACCESS_FAILURE_LOG_PER_USER_LIMIT`
(default 1000, mantido). O expurgo é manual e usa **comandos distintos** —
`manage.py axes_reset_logs --age <dias>` só apaga `AccessLog`;
`manage.py axes_reset_failure_logs --age <dias>` é o que apaga
`AccessFailureLog`. Ambos entram no item GL-02 do checklist. Nesta fase não há
rotina agendada: com ~20 usuários, o expurgo periódico manual basta, e agendar
tarefa (cron/Celery) seria infraestrutura que o projeto ainda não tem.

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
    AXES_ENABLE_ACCESS_FAILURE_LOG = True
    AXES_LOCKOUT_TEMPLATE = 'accounts/login_bloqueado.html'
    ```
    Uma versão anterior deste plano previa também
    `AXES_ENABLE_RETRY_AFTER_HEADER = True`, para que a resposta de bloqueio
    trouxesse `Retry-After`. **A setting não existe na 8.3.1** — é feature do
    master, ainda não lançada. O Django aceitaria o nome em silêncio e o header
    nunca apareceria; a linha ficou de fora, e o prazo é comunicado só pela
    página de bloqueio.
    `AXES_USERNAME_FORM_FIELD = 'username'` **não** é redundante, apesar de
    `'username'` parecer o óbvio: o default do axes é
    `get_user_model().USERNAME_FIELD`, que neste projeto é `'matricula'`. Mas
    quem posta é o `AuthenticationForm` do Django, cujo campo se chama sempre
    `username` — e é essa a chave que chega tanto em `request.POST` quanto no
    `credentials` de `authenticate()`. Sem a linha, o axes procuraria
    `'matricula'`, não acharia, e chavearia todas as falhas sob `username=None`.
    Com o parâmetro combinado, isso **não** produz um bucket global: as falhas
    passam a se agrupar por `(None, ip_address)` — um bucket por IP, com a
    matrícula fora da chave. O efeito é que todo mundo que compartilha um IP
    compartilha o mesmo contador: cinco erros de senha somados entre pessoas
    diferentes trancam todas elas naquele IP, e o bucket vira efetivamente
    global exatamente no cenário do risco 1 (rede atrás de um proxy, um IP só).
    O teste 5 (isolamento por matrícula, mesmo IP) é o que fixa isso.

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
  `AXES_IPWARE_META_PRECEDENCE_ORDER = ['HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR']`
  e `AXES_IPWARE_PROXY_COUNT = 1`. A condição é reusada de propósito: confiar em
  `X-Forwarded-For` para identificar o cliente tem o mesmo pré-requisito que
  confiar em `X-Forwarded-Proto` — um proxy na frente que sobrescreva o
  cabeçalho. Ligar um sem o outro é incoerente, e ligar qualquer um sem proxy
  deixa o cliente escolher o próprio IP (e, aqui, escapar do lockout trocando o
  cabeçalho a cada tentativa).

  `REMOTE_ADDR` fica na lista como **segundo** item porque a precedência
  substitui o default `('REMOTE_ADDR',)` em vez de estendê-lo. **Mas ele não é
  o recuo geral que uma versão anterior deste plano afirmava** — a
  implementação mostrou o contrário. `AXES_IPWARE_PROXY_COUNT` faz o ipware
  validar a contagem de proxies **por origem** (`is_proxy_count_valid`), e
  `REMOTE_ADDR` sozinho tem zero proxies: é descartado igual ao cabeçalho
  ausente, e o IP sai `None`. A tentativa então fica chaveada só pela matrícula.
  Isso ainda bloqueia e não contamina outros usuários, mas sinaliza que alguém
  alcançou o Django por fora do proxy — o GL-02 cobra que isso seja impossível.
  Fora do bloco de proxy, a precedência continua sendo o default do axes
  (`REMOTE_ADDR` apenas), o que faz um `X-Forwarded-For` forjado pelo cliente
  ser simplesmente ignorado.

  **Contrato de resolução de IP** (fixado pelos testes 10–13):

  | Cenário | IP usado |
  |---|---|
  | Proxy desligado, cliente envia `X-Forwarded-For` | `REMOTE_ADDR`; o cabeçalho é ignorado. |
  | Proxy ligado, cadeia válida com 1 proxy | IP do cliente, extraído da cadeia. |
  | Proxy ligado, requisição direta (sem cabeçalho) | `None` — chave só pela matrícula. |
  | Proxy ligado, cabeçalho forjado com contagem errada | `None` — descartado pela validação. |

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
  conferir, antes de liberar, que:
  1. `manage.py migrate` foi aplicado e as quatro tabelas do axes existem — o
     backend recusa operar sem elas, e o modo de falha é erro no login, a pior
     hora possível para descobrir;
  2. a resolução de IP bate com a topologia de implantação, conforme a tabela de
     contrato acima (com ou sem proxy);
  3. o lockout de fato dispara, por teste manual com uma matrícula descartável.

  O item traz também os comandos que a equipe vai precisar às 8h de uma
  segunda-feira: inspeção (`manage.py axes_list_attempts`), desbloqueio
  (`manage.py axes_reset_username <matricula>` e o mais cirúrgico
  `manage.py axes_reset_ip_username <ip> <matricula>`) e expurgo dos registros
  de auditoria (`manage.py axes_reset_logs --age <dias>` para `AccessLog`;
  `manage.py axes_reset_failure_logs --age <dias>` para `AccessFailureLog` — são
  comandos distintos, um não cobre o outro).

### O que não muda

- **`apps/accounts/views.py` e `forms.py`.** Nenhuma linha. Todo o mecanismo
  entra por backend + middleware; a view continua um `LoginView` e o formulário
  continua só cuidando de rótulo e acessibilidade. Registrado aqui porque a
  opção 3 da issue teria colocado a lógica dentro de
  `MatriculaAuthenticationForm`, e este plano deliberadamente não vai lá.
- **Autorização de domínio.** Nenhuma policy, nenhum service, nenhum selector.
  Lockout é controle de autenticação, anterior a papel; `docs/matriz-permissoes.md`
  não ganha linha.
- **Modelos de domínio.** Nenhum. As quatro tabelas novas (ver a tabela em
  "Decisão registrada") vêm com migrations do próprio pacote e não
  ficam sob `apps/**/migrations/` — a regra de migrations efêmeras do projeto
  não se aplica a elas.
- **Testes existentes.** Quase nenhum é editado — mas **dois** são, e a versão
  anterior deste plano errou ao afirmar que nenhum seria. A quase totalidade da
  suíte autentica via `client.force_login`, que não passa pelo pipeline de
  `authenticate()` e portanto não dispara o axes. As duas exceções autenticam
  por caminhos que o `AxesStandaloneBackend` recusa sem um `request`:

  - `apps/requisicoes/tests/test_views.py`, helper `_login` — usava
    `client.login()`, que o test client chama sem repassar `request`. Passa a
    usar `force_login`, idioma do resto da suíte. Uma linha; 363 testes
    dependiam dela.
  - `apps/core/tests/test_seed_dev.py` — chama `authenticate()` direto para
    provar que a senha do seed funciona. Passa a receber `rf.post('/')`, o que
    mantém o teste exercitando a cadeia de backends real em vez de desligar o
    axes para contorná-la.

  Os testes de `test_login.py` que postam senha errada fazem **uma** falha por
  teste, e cada teste roda em transação própria — nenhum se aproxima do limite
  de 5.
- **`config/settings/test.py`.** O axes fica **ligado** na suíte. `AXES_ENABLED =
  False` existe e é tentador, mas desligá-lo tornaria os testes de lockout deste
  plano impossíveis de escrever contra o comportamento real.
- **Admin.** O axes registra os próprios models no admin (`AXES_ENABLE_ADMIN`,
  default ligado) e isso fica como está: é a superfície de desbloqueio pela
  interface, e as permissões desses models não são atribuídas a papel nenhum —
  na prática, só superusuário enxerga. Nenhum `admin.py` do projeto é tocado.

## Arquivos a tocar

Nenhum destes arquivos foi alterado ainda; a tabela é o alvo da implementação,
não um registro do que já existe. `login_bloqueado.html`, `test_lockout.py`, o
ADR-0018 e a seção GL-02 ainda não existem no repositório.

| Arquivo | Mudança planejada |
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
  projeto). Os testes envelhecem as linhas gravadas, reproduzindo o estado do
  banco 16 minutos depois. Envelhecer **só** `AccessAttempt.attempt_time` não
  basta: com `AXES_USE_ATTEMPT_EXPIRATION=True`, a limpeza filtra por
  `expiration__expires_at__lte=now`, não por `attempt_time`. Um helper do
  módulo de teste move os dois campos de uma vez:

  ```python
  def _envelhecer_tentativas(minutos: int) -> None:
      instante = timezone.now() - timedelta(minutes=minutos)
      AccessAttempt.objects.update(attempt_time=instante)
      AccessAttemptExpiration.objects.update(expires_at=instante)
  ```

Comportamentos cobertos:

1. **Caminho feliz preservado** — login válido continua 302 e autentica, com o
   axes no meio do caminho. É o teste que pega uma configuração de backend
   trocada.
2. **Abaixo do limite não bloqueia** — 4 falhas seguidas e a 4ª ainda responde
   200 com o formulário de login, não a página de bloqueio. Fixa o limiar por
   baixo.
3. **No limite bloqueia** — a 5ª falha responde **429** e renderiza
   `accounts/login_bloqueado.html`. Sem asserção de `Retry-After`: a 8.3.1 não
   emite o header (ver acima).
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
8. **Fim da janela libera** — bloqueado, tentativas envelhecidas em 16 minutos
   pelo helper acima, login com senha correta volta a 302 e autentica.
9. **Tentativa durante o bloqueio prorroga a janela** — bloqueado, mais uma
   falha, e `AccessAttemptExpiration.expires_at` fica **maior** do que antes
   dessa falha. É o comportamento de
   `AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT=True` em forma executável — a
   asserção é sobre o campo, não só sobre o 429, porque o status seria 429 de
   qualquer jeito. A variante com `False` **não** é testada: o projeto não
   configura `False`, e afirmar o comportamento de uma configuração que não
   enviamos é testar a biblioteca, não a decisão.
10. **Proxy desligado ignora `X-Forwarded-For`** — POST com
    `HTTP_X_FORWARDED_FOR='203.0.113.9'` e `REMOTE_ADDR='10.0.0.7'` grava a
    tentativa com `ip_address='10.0.0.7'`. É o teste que impede um atacante de
    driblar o lockout forjando o cabeçalho, e roda com as settings padrão.
11. **Proxy ligado usa o IP da cadeia** — sob `override_settings` com a
    precedência e `AXES_IPWARE_PROXY_COUNT = 1`, cadeia
    `X-Forwarded-For: 203.0.113.9, 10.0.0.1` resolve `203.0.113.9`.
12. **Proxy ligado, requisição direta, fica sem IP** — mesmas settings, sem
    `X-Forwarded-For`: a tentativa é gravada com `ip_address=None`, e **não**
    com o `REMOTE_ADDR`. Documenta o limite real da precedência: com
    `AXES_IPWARE_PROXY_COUNT = 1`, o ipware descarta `REMOTE_ADDR` por ter zero
    proxies.
13. **Proxy ligado, cabeçalho forjado sem cadeia, é descartado** — cliente que
    inventa um `X-Forwarded-For` de uma entrada só não vira dono do próprio IP:
    o proxy real acrescentaria uma entrada, e a contagem errada reprova.
14. **Página de bloqueio** — 429, PT-BR, herda `base.html`, e **não** contém a
    matrícula tentada (não-oráculo), com uma matrícula que não aparece em
    nenhum outro lugar do HTML para a asserção não passar por acidente. A
    janela exibida é comparada contra `settings.AXES_COOLOFF_TIME`, não contra
    um número digitado no teste: mudar a setting sem mexer no template derruba
    o teste em vez de deixar a página mentindo.

Os testes 10–13 leem `AccessAttempt.ip_address` diretamente, sem passar do
limite de falhas: o que está sob teste é a **chave** da tentativa, não o
bloqueio.

### Contratos de login existentes

O axes entra no caminho do login, então os contratos que já valem hoje têm de
continuar valendo. Eles **já têm cobertura** em
`apps/accounts/tests/test_login.py` e não são reescritos aqui — a suíte inteira
verde é a asserção:

| Contrato | Teste que o guarda |
|---|---|
| Senha inválida continua erro **do formulário** (200, `role="alert"`, `aria-invalid`), não página de bloqueio | `test_login_senha_invalida`, `test_login_senha_invalida_exibe_erro_inline`, `test_login_senha_invalida_erro_usa_components_alert` |
| Usuário inativo não autentica | `test_login_usuario_inativo` |
| `next` preservado no formulário e no redirect | `test_login_preserva_next_no_formulario_e_redirect` |
| Logout encerra a sessão e redireciona | `test_logout` |

O teste 2 desta suíte reforça o primeiro contrato pelo lado novo: abaixo do
limite, a resposta continua sendo o formulário com erro, não o 429.

Duas ressalvas sobre contratos que a revisão sugeriu cobrir:

- **Logout com mensagem informativa não é contrato deste projeto.**
  `accounts:logout` é o `LogoutView` do Django sem customização e não emite
  `django.contrib.messages`. Criar essa mensagem é mudança de UX alheia à
  issue #116; se for desejada, é issue própria.
- **Redirect de acesso não autenticado** é `@login_required` do Django,
  exercitado à exaustão pelas suítes de view de `estoque` e `requisicoes`.
  Duplicar aqui não acrescentaria garantia — e este plano não toca nenhuma view
  protegida.

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
   do proxy: `[['username', 'ip_address']]` degenera em "só username", e um
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
4. **Dependência e superfície nova.** Quatro tabelas e um backend a mais no
   caminho crítico do login. `django-axes` 8.3 declara suporte a Django 6.0 e
   Python 3.13, que é a combinação do projeto; ainda assim, o pin `<9` evita que
   uma major nova entre sozinha num `uv lock` futuro. O modo de falha a temer é
   migration não aplicada em produção: o login quebra inteiro, não degrada. Daí
   o `migrate` ser item explícito do GL-02.
5. **Custo por tentativa falha.** O handler default grava em banco. Com
   `AXES_ENABLE_ACCESS_FAILURE_LOG=True` são duas escritas por falha
   (`AccessAttempt` mais `AccessFailureLog`), e não uma. Irrelevante nesta
   escala, e a alternativa (handler em cache) exige `CACHES`, que o projeto
   não tem.
6. **Dado pessoal em log de acesso.** `AccessFailureLog` e `AccessLog` guardam
   matrícula, IP e user-agent por tempo indeterminado — é o preço da trilha
   auditável, e o expurgo é manual (GL-02). Se o piloto passar a ter exigência
   formal de retenção, a rotina agendada vira issue própria.
7. **Suíte com o axes ligado.** Um teste futuro que faça 5+ logins falhos do
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
- Mensagem informativa no logout — o `LogoutView` de hoje não emite `messages`,
  e criar essa mensagem é mudança de UX que a issue #116 não pede.
- Rotina agendada de expurgo de `AccessLog`/`AccessFailureLog`; nesta fase o
  expurgo é manual, pelos comandos do GL-02.
