"""Configurações da suíte de testes (pytest-django).

A suíte roda contra PostgreSQL: o pytest-django cria a base de testes a
partir de ``DATABASE_URL``. Não usar SQLite.
"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR

# Hasher rápido apenas para testes — nunca usar em produção.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# A suíte confirma importações SCPI em dezenas de testes, e cada confirmação
# grava um CSV. Sem este desvio, o `media/` do desenvolvedor viraria depósito de
# resíduo de teste. O diretório é descartável: nenhum teste afirma caminho
# gravado, e testes que leem o arquivo apontam `MEDIA_ROOT` para `tmp_path`.
MEDIA_ROOT = BASE_DIR / '.pytest-media'
