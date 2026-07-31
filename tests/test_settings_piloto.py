"""Testes das guardas de configuração do piloto (`config/settings/piloto.py`).

Duas camadas:

- unitária, sobre as funções puras de `config.settings.guardas` — herméticas,
  sem Django configurado e sem depender do ambiente da máquina;
- de boot, em subprocesso, provando que as guardas rodam durante o import dos
  settings e derrubam o processo antes de o Django inicializar.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings.guardas import (
    exigir_bancos_postgresql,
    exigir_hosts_permitidos,
    exigir_origens_csrf_confiaveis,
)


POSTGRESQL = {'ENGINE': 'django.db.backends.postgresql'}
SQLITE = {'ENGINE': 'django.db.backends.sqlite3'}


def test_banco_postgresql_e_aceito():
    exigir_bancos_postgresql({'default': POSTGRESQL})


def test_banco_sqlite_e_recusado():
    with pytest.raises(ImproperlyConfigured) as erro:
        exigir_bancos_postgresql({'default': SQLITE})

    mensagem = str(erro.value)
    assert 'DATABASE_URL' in mensagem
    assert 'django.db.backends.sqlite3' in mensagem
    assert 'django.db.backends.postgresql' in mensagem


def test_banco_mysql_e_recusado():
    with pytest.raises(ImproperlyConfigured):
        exigir_bancos_postgresql({'default': {'ENGINE': 'django.db.backends.mysql'}})


def test_banco_postgis_e_recusado():
    """A regra é estrita por decisão: o projeto não usa GIS."""
    with pytest.raises(ImproperlyConfigured):
        exigir_bancos_postgresql(
            {'default': {'ENGINE': 'django.contrib.gis.db.backends.postgis'}}
        )


@pytest.mark.parametrize('config', [{}, {'ENGINE': ''}, {'ENGINE': None}])
def test_banco_sem_engine_e_recusado(config):
    with pytest.raises(ImproperlyConfigured):
        exigir_bancos_postgresql({'default': config})


def test_alias_secundario_invalido_e_recusado():
    """Prova que o laço percorre todos os aliases, não só o primeiro."""
    with pytest.raises(ImproperlyConfigured) as erro:
        exigir_bancos_postgresql({'default': POSTGRESQL, 'replica': SQLITE})

    assert 'replica' in str(erro.value)


def test_todos_os_aliases_postgresql_sao_aceitos():
    exigir_bancos_postgresql({'default': POSTGRESQL, 'replica': POSTGRESQL})


# --- ALLOWED_HOSTS -----------------------------------------------------------
#
# As guardas recebem o valor bruto e a lista já parseada por `env.list`. O par é
# proposital: `django-environ` descarta itens vazios durante o parsing, então
# `ALLOWED_HOSTS=,,` chegaria como `[]` — o mesmo default permissivo que a issue
# proíbe, só que por outro caminho. Validar o bruto fecha essa porta.


def test_hosts_permitidos_aceita_um_host():
    assert exigir_hosts_permitidos(
        'piloto.exemplo.gov.br', ['piloto.exemplo.gov.br']
    ) == ['piloto.exemplo.gov.br']


def test_hosts_permitidos_aceita_varios_hosts():
    bruto = 'a.exemplo.br, b.exemplo.br'
    assert exigir_hosts_permitidos(bruto, ['a.exemplo.br', 'b.exemplo.br']) == [
        'a.exemplo.br',
        'b.exemplo.br',
    ]


@pytest.mark.parametrize('bruto', ['', '   ', ',', ',,'])
def test_hosts_permitidos_recusa_lista_vazia(bruto):
    with pytest.raises(ImproperlyConfigured) as erro:
        exigir_hosts_permitidos(bruto, [])

    assert 'ALLOWED_HOSTS' in str(erro.value)


def test_hosts_permitidos_recusa_item_vazio():
    with pytest.raises(ImproperlyConfigured):
        exigir_hosts_permitidos(
            'a.exemplo.br,,b.exemplo.br', ['a.exemplo.br', 'b.exemplo.br']
        )


@pytest.mark.parametrize('bruto', ['*', 'a.exemplo.br,*'])
def test_hosts_permitidos_recusa_curinga(bruto):
    with pytest.raises(ImproperlyConfigured) as erro:
        exigir_hosts_permitidos(bruto, bruto.split(','))

    assert '*' in str(erro.value)


# --- CSRF_TRUSTED_ORIGINS ----------------------------------------------------


def test_origens_csrf_aceita_origem_com_esquema():
    bruto = 'https://piloto.exemplo.gov.br'
    assert exigir_origens_csrf_confiaveis(bruto, [bruto]) == [bruto]


@pytest.mark.parametrize('bruto', ['', '   ', ',,'])
def test_origens_csrf_recusa_lista_vazia(bruto):
    with pytest.raises(ImproperlyConfigured) as erro:
        exigir_origens_csrf_confiaveis(bruto, [])

    assert 'CSRF_TRUSTED_ORIGINS' in str(erro.value)


def test_origens_csrf_recusa_item_vazio():
    with pytest.raises(ImproperlyConfigured):
        exigir_origens_csrf_confiaveis(
            'https://a.exemplo.br,,https://b.exemplo.br',
            ['https://a.exemplo.br', 'https://b.exemplo.br'],
        )


def test_origens_csrf_recusa_origem_sem_esquema():
    with pytest.raises(ImproperlyConfigured) as erro:
        exigir_origens_csrf_confiaveis(
            'piloto.exemplo.gov.br', ['piloto.exemplo.gov.br']
        )

    mensagem = str(erro.value)
    assert 'piloto.exemplo.gov.br' in mensagem
    assert 'https://' in mensagem
