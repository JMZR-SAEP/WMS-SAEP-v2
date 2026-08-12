# ADR-0018 — Lockout de login por matrícula com django-axes

## Status

Aceita

## Contexto

O login por matrícula é a única porta do sistema. `MatriculaLoginView` era um
`LoginView` puro: qualquer cliente podia postar matrícula e senha em laço, sem
limite, sem atraso e sem registro. O namespace de matrículas é curto e
adivinhável (`OBRAS001`, `ALMOX001`), então o único custo de uma força bruta era
largura de banda — achado R9 da auditoria.

Em rede interna com ~20 usuários o risco é baixo. Qualquer exposição além disso
torna a força bruta trivial, e a decisão precisava ser tomada antes do piloto.

Havia três saídas em avaliação (issue #116):

1. `django-axes`: lockout por combinação usuário+IP, configurável, com admin de
   tentativas. Adiciona dependência e tabelas.
2. Throttle no proxy reverso (`limit_req` do nginx/caddy na rota de login): zero
   mudança de código, mas depende de haver proxy no deploy do piloto.
3. Rate-limit artesanal via cache no `MatriculaAuthenticationForm`: sem
   dependência, mas reinventa roda de segurança.

## Decisão

Adotamos **`django-axes`** (opção 1), na versão 8.3 com o extra `ipware`.

A opção 2 foi descartada porque o piloto não garante proxy: estar atrás de proxy
TLS é *opt-in* em `config/settings/piloto.py`
(`PILOTO_ATRAS_DE_PROXY_TLS`, default `False`). Uma proteção que só existe
quando uma variável opcional está ligada não é proteção. Além disso `limit_req`
conta requisições por IP, não tentativas falhas por conta: ou aperta a ponto de
atrapalhar quem erra a senha duas vezes, ou afrouxa a ponto de permitir força
bruta lenta.

A opção 3 foi descartada porque o projeto não tem `CACHES` configurado: exigiria
montar backend de cache *e* escrever lógica de contagem, expiração e reset.

O mecanismo entra por `AUTHENTICATION_BACKENDS` mais middleware. A view e o
formulário de login não mudam — o contrário teria sido consequência da opção 3.

### Política

| Parâmetro | Valor | Razão |
|---|---|---|
| `AXES_LOCKOUT_PARAMETERS` | `[['username', 'ip_address']]` | Lista **aninhada** = bloqueia a combinação. A forma plana bloquearia por matrícula **ou** por IP, deixando qualquer um trancar a conta alheia de qualquer lugar. |
| `AXES_FAILURE_LIMIT` | 5 | Folga para erro humano sem dar margem útil a quem chuta. |
| `AXES_COOLOFF_TIME` | 15 min | Curto o bastante para não exigir suporte no caso legítimo. |
| `AXES_USE_ATTEMPT_EXPIRATION` | `True` | Janela deslizante: tentativa expirada deixa de contar. |
| `AXES_RESET_ON_SUCCESS` | `True` | Quem prova saber a própria senha zera o contador. |
| `AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT` | `True` (default, declarado) | Cada tentativa durante o bloqueio reinicia a janela. Com IP real por cliente, só prolonga o bloqueio de quem ataca. |
| `AXES_ENABLE_ACCESS_FAILURE_LOG` | `True` | Sem ele não há trilha auditável: `AccessAttempt` é agregado e some no primeiro login bem-sucedido. |
| `AXES_HTTP_RESPONSE_CODE` | 429 (default) | Código correto para limite de tentativas; 403 diria "proibido" a quem talvez seja o dono da conta. |

`AXES_USERNAME_FORM_FIELD = 'username'` é obrigatório e não é redundante. O
default do axes é `get_user_model().USERNAME_FIELD`, que aqui seria `matricula`;
mas quem posta é o `AuthenticationForm` do Django, cujo campo se chama sempre
`username`. Sem a linha, o axes procuraria `matricula`, não acharia, e agruparia
as falhas sob `(None, ip_address)` — um balde por IP, com a matrícula fora da
chave, em que erros de pessoas diferentes se somam e trancam todas elas.

### Resolução de IP

`django-axes[ipware]`, e não `django-axes` puro: desde a versão 6 o pacote só
resolve IP de cliente atrás de proxy quando `django-ipware` está instalado.

A leitura de `X-Forwarded-For` fica sob a mesma condição que já governa
`X-Forwarded-Proto` (`PILOTO_ATRAS_DE_PROXY_TLS`). Ligar uma sem a outra é
incoerente, e ligar qualquer uma sem proxy deixa o cliente escolher o próprio IP
e escapar do lockout trocando o cabeçalho a cada tentativa.

| Cenário | IP resolvido |
|---|---|
| Sem proxy, cliente envia `X-Forwarded-For` | `REMOTE_ADDR`; o cabeçalho é ignorado. |
| Com proxy, cadeia válida de um proxy | IP do cliente, extraído da cadeia. |
| Com proxy, requisição direta (sem cabeçalho, ou cabeçalho forjado com contagem errada) | `None`. |

O último caso merece nota, porque contraria a intuição: `REMOTE_ADDR` está na
precedência, mas **não** funciona como recuo geral. `AXES_IPWARE_PROXY_COUNT`
faz o ipware validar a contagem de proxies por origem, e `REMOTE_ADDR` sozinho
tem zero proxies — é descartado. O efeito é a tentativa ficar chaveada só pela
matrícula: ainda bloqueia, e não contamina outros usuários, mas sinaliza que
alguém alcançou o Django por fora do proxy. O GL-02 cobra que isso seja
impossível na implantação.

## Consequências

Quatro tabelas novas, criadas por migration do pacote: `AccessAttempt`,
`AccessAttemptExpiration`, `AccessLog` e `AccessFailureLog`. Todas recebem
linhas nesta configuração. Migration não aplicada em produção quebra o login
inteiro em vez de degradar — daí o `migrate` ser item explícito do GL-02.

Duas escritas por tentativa falha (`AccessAttempt` e `AccessFailureLog`).
Irrelevante nesta escala; a alternativa (handler em cache) exige `CACHES`.

`AccessFailureLog` e `AccessLog` guardam matrícula, IP e user-agent. O
crescimento de `AccessFailureLog` é limitado por
`AXES_ACCESS_FAILURE_LOG_PER_USER_LIMIT` (1000). O expurgo é manual e usa
comandos **distintos** — `axes_reset_logs --age` só cobre `AccessLog`,
`axes_reset_failure_logs --age` cobre `AccessFailureLog`. Não há rotina
agendada: o projeto não tem cron nem Celery.

O desbloqueio é ação explícita, nunca um bypass silencioso: superusuário não
tem isenção, porque não há whitelist configurada. Os comandos são
`axes_list_attempts`, `axes_reset_username <matricula>` e
`axes_reset_ip_username <ip> <matricula>`.

Nos testes, autenticação passa a exigir um `request`:
`AxesStandaloneBackend` recusa `authenticate()` sem ele. `client.force_login`
continua funcionando — o axes não expõe `get_user`, então o Django escolhe o
`ModelBackend` — e é o idioma da suíte. Onde um teste precisa exercitar a senha
de verdade, passa-se uma requisição real (`rf.post('/')`) em vez de desligar o
axes. Um teste futuro que faça 5+ logins falhos do mesmo usuário passa a receber
429; o escape é `override_settings(AXES_ENABLED=False)`, a ser usado só quando o
lockout for de fato irrelevante para o que está sob teste.

Ataque distribuído continua viável: com o parâmetro combinado, cada IP novo
ganha cinco tentativas contra a mesma matrícula. É trade-off consciente —
proteger contra IP rotativo exigiria bloqueio por matrícula pura, que devolve a
qualquer um o poder de trancar a conta alheia. Para ~20 usuários em rede
interna, botnet não é o cenário desta fase.

## Trade-off

O lockout troca disponibilidade por resistência a força bruta: passa a existir
um estado em que um usuário legítimo não entra, mesmo com a senha certa. As
mitigações são a janela curta, o reset no sucesso e o chaveamento pela
combinação matrícula+IP, que evita o pior caso (trancar alguém de qualquer
lugar). Aceita-se a indisponibilidade eventual de 15 minutos em favor de fechar
o vetor que a auditoria apontou.
