"""Configurações da implantação piloto.

Herda de ``base`` e endurece o que ``dev`` afrouxa: ``DEBUG`` desligado, hosts e
origens confiáveis obrigatórios, cookies restritos a HTTPS e os cabeçalhos de
segurança que ``manage.py check --deploy`` cobra.

Também recusa a inicialização quando ``DATABASE_URL`` não aponta para
PostgreSQL — ver ``config.settings.guardas``. Falhar no boot é deliberado: o
modo de falha oposto (subir com SQLite) é silencioso.
"""

import environ

from .base import *  # noqa: F401,F403
from .base import DATABASES
from .guardas import (
    exigir_bancos_postgresql,
    exigir_hosts_permitidos,
    exigir_origens_csrf_confiaveis,
)


# Instância própria, sem o schema de `base`. Lá, `ALLOWED_HOSTS` tem default
# `[]`, e reusar aquele `env` faria a variável ausente virar lista vazia sem
# ruído — exatamente o default permissivo que o piloto não pode ter. Sem schema,
# variável ausente levanta `ImproperlyConfigured` no import.
env_piloto = environ.Env()

# A atribuição vem DEPOIS do `import *` de propósito: `base` lê `DEBUG` do
# ambiente, e é esta linha que garante que `DEBUG=true` no ambiente do piloto
# não reabra o modo debug. Mover isto para antes do import quebraria a garantia
# silenciosamente.
DEBUG = False

# `env.list` faz o parsing; as guardas validam o valor bruto antes, porque o
# parsing descarta itens vazios e transformaria `ALLOWED_HOSTS=,,` em `[]`.
ALLOWED_HOSTS = exigir_hosts_permitidos(
    env_piloto.str('ALLOWED_HOSTS'),
    env_piloto.list('ALLOWED_HOSTS'),
)
CSRF_TRUSTED_ORIGINS = exigir_origens_csrf_confiaveis(
    env_piloto.str('CSRF_TRUSTED_ORIGINS'),
    env_piloto.list('CSRF_TRUSTED_ORIGINS'),
)

exigir_bancos_postgresql(DATABASES)


# Cookies e cabeçalhos de segurança

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = True

SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# `preload` apenas emite a diretiva no cabeçalho; entrar de fato na lista dos
# navegadores exige submissão manual do domínio.
SECURE_HSTS_PRELOAD = True

X_FRAME_OPTIONS = 'DENY'

# Opt-in: confiar em `X-Forwarded-Proto` sem um proxy que sobrescreva o cabeçalho
# deixa qualquer cliente se declarar HTTPS. Sem isso, porém, `SECURE_SSL_REDIRECT`
# entra em laço de redirecionamento atrás de um proxy que termina TLS. Ligue
# apenas quando houver esse proxy na frente.
if env_piloto.bool('PILOTO_ATRAS_DE_PROXY_TLS', default=False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
