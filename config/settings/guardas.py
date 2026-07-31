"""Guardas aplicadas durante a carga dos settings.

Estas funções rodam no import do módulo de settings, antes de o Django
inicializar. Falhar aqui é intencional: configuração permissiva de banco ou de
host não produz exceção, log nem sintoma em produção — o dano só aparece depois,
e sem rastro que aponte para a causa.
"""

from collections.abc import Mapping
from typing import Any

from django.core.exceptions import ImproperlyConfigured


ENGINE_POSTGRESQL = 'django.db.backends.postgresql'


def exigir_bancos_postgresql(databases: Mapping[str, Mapping[str, Any]]) -> None:
    """Recusa a inicialização se algum alias de banco não for PostgreSQL.

    Em SQLite, ``select_for_update`` é um no-op silencioso: as transições de
    estado da ADR-0005 continuam "funcionando" e param de serializar, sem erro
    algum. Como ``env.db()`` aceita ``sqlite://`` sem reclamar, a única defesa é
    verificar o engine já resolvido.
    """
    for alias, config in databases.items():
        engine = config.get('ENGINE') or '(ausente)'
        if engine != ENGINE_POSTGRESQL:
            raise ImproperlyConfigured(
                f'Banco inválido para o alias {alias!r}: engine {engine!r} não é '
                f'PostgreSQL. O piloto exige DATABASE_URL apontando para PostgreSQL '
                f'(engine {ENGINE_POSTGRESQL!r}), porque em outros backends — SQLite '
                f'em especial — select_for_update vira no-op e as garantias de '
                f'concorrência da ADR-0005 deixam de valer sem nenhum sintoma. '
                f'Corrija para algo como '
                f'DATABASE_URL=postgres://USUARIO:SENHA@HOST:5432/BANCO.'
            )
