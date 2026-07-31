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


def _exigir_lista_util(bruto: str, itens: list[str], *, variavel: str) -> list[str]:
    """Valida o valor bruto de uma variável de lista antes de aceitar o parsing.

    ``env.list`` descarta itens vazios, então ``VAR=`` e ``VAR=,,`` chegam aqui
    como ``[]`` — indistinguíveis de uma lista legítima vazia, que é justamente o
    default permissivo que o piloto não pode ter. Por isso a validação olha o
    texto original, não só o resultado do parsing.

    ``env.list`` também não faz ``strip``: ``VAR=a.exemplo.br, b.exemplo.br`` — a
    forma natural de escrever — chega como ``['a.exemplo.br', ' b.exemplo.br']``.
    Como o Django compara host e origem por igualdade exata, esse espaço
    rejeitaria toda requisição legítima do segundo item, sem erro visível. Por
    isso os itens são normalizados aqui, e não na chamada.
    """
    if not bruto.strip(', \t'):
        raise ImproperlyConfigured(
            f'{variavel} está vazia. O piloto exige a variável preenchida: uma '
            f'lista vazia desliga a proteção em vez de configurá-la. Defina '
            f'{variavel} com os valores reais da implantação, separados por vírgula.'
        )

    if any(not parte.strip() for parte in bruto.split(',')):
        raise ImproperlyConfigured(
            f'{variavel} tem item vazio: {bruto!r}. Itens vazios são descartados '
            f'silenciosamente no parsing, então a lista efetiva fica menor do que '
            f'a configurada. Remova as vírgulas sobrando.'
        )

    normalizados = [item.strip() for item in itens]

    if not normalizados:
        raise ImproperlyConfigured(
            f'{variavel} não produziu nenhum item a partir de {bruto!r}.'
        )

    return normalizados


def exigir_hosts_permitidos(bruto: str, itens: list[str]) -> list[str]:
    """Valida ``ALLOWED_HOSTS``: lista útil e sem curinga.

    O curinga é recusado porque delega a validação de Host header a um proxy que
    o piloto não garante ter na frente — e sem esse proxy, ``*`` equivale a não
    ter proteção nenhuma.
    """
    hosts = _exigir_lista_util(bruto, itens, variavel='ALLOWED_HOSTS')

    if any(host == '*' for host in hosts):
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS contém o curinga '*', que aceita qualquer Host header. "
            'No piloto isso só seria seguro se um proxy à frente já validasse o '
            'Host, o que esta configuração não garante. Liste os domínios reais, '
            'como ALLOWED_HOSTS=piloto.exemplo.gov.br.'
        )

    return hosts


def exigir_origens_csrf_confiaveis(bruto: str, itens: list[str]) -> list[str]:
    """Valida ``CSRF_TRUSTED_ORIGINS``: lista útil e com esquema em cada origem."""
    origens = _exigir_lista_util(bruto, itens, variavel='CSRF_TRUSTED_ORIGINS')

    sem_esquema = [origem for origem in origens if '://' not in origem]
    if sem_esquema:
        raise ImproperlyConfigured(
            f'CSRF_TRUSTED_ORIGINS exige o esquema em cada origem, e estas estão '
            f'sem ele: {sem_esquema}. Use a forma completa, como '
            f'CSRF_TRUSTED_ORIGINS=https://piloto.exemplo.gov.br.'
        )

    return origens
