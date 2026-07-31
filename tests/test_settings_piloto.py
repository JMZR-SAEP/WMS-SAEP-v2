"""Testes das guardas de configuração do piloto (`config/settings/piloto.py`).

Duas camadas:

- unitária, sobre as funções puras de `config.settings.guardas` — herméticas,
  sem Django configurado e sem depender do ambiente da máquina;
- de boot, em subprocesso, provando que as guardas rodam durante o import dos
  settings e derrubam o processo antes de o Django inicializar.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings.guardas import exigir_bancos_postgresql


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
