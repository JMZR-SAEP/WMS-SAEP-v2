"""Testes das guardas de configuração do piloto (`config/settings/piloto.py`).

Duas camadas:

- unitária, sobre as funções puras de `config.settings.guardas` — herméticas,
  sem Django configurado e sem depender do ambiente da máquina;
- de boot, em subprocesso, provando que as guardas rodam durante o import dos
  settings e derrubam o processo antes de o Django inicializar.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings.guardas import (
    exigir_bancos_postgresql,
    exigir_hosts_permitidos,
    exigir_origens_csrf_confiaveis,
)


POSTGRESQL = {'ENGINE': 'django.db.backends.postgresql'}
SQLITE = {'ENGINE': 'django.db.backends.sqlite3'}

RAIZ = Path(__file__).resolve().parent.parent

# 50 caracteres, mais de 5 distintos, sem o prefixo `django-insecure-`: o mínimo
# que `security.W009` aceita.
SECRET_KEY_FORTE = 'Ab1!xYz9Qw' * 5
SECRET_KEY_CURTA = SECRET_KEY_FORTE[:49]

AMBIENTE_VALIDO = {
    'DJANGO_SETTINGS_MODULE': 'config.settings.piloto',
    'SECRET_KEY': SECRET_KEY_FORTE,
    'DATABASE_URL': 'postgres://usuario:senha@localhost:5432/wms_saep_piloto',
    'ALLOWED_HOSTS': 'piloto.exemplo.gov.br',
    'CSRF_TRUSTED_ORIGINS': 'https://piloto.exemplo.gov.br',
}


def _rodar(codigo_ou_args, **sobrescritas):
    """Roda o piloto em subprocesso com ambiente montado do zero.

    Nunca `os.environ.copy()`: o ambiente do pytest já traz `DATABASE_URL` de
    PostgreSQL e mascararia o caso SQLite. Só `PATH` e `HOME` são herdados,
    porque o interpretador precisa deles.

    Um `.env` na raiz do repositório continua sendo lido por `base.py`, mas com
    `overwrite=False` (`os.environ.setdefault`) — então todo valor definido aqui
    vence, e os casos abaixo são herméticos em qualquer máquina.
    """
    ambiente = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': os.environ.get('HOME', ''),
        **AMBIENTE_VALIDO,
    }
    for chave, valor in sobrescritas.items():
        if valor is None:
            ambiente.pop(chave, None)
        else:
            ambiente[chave] = valor

    if isinstance(codigo_ou_args, str):
        args = [sys.executable, '-c', codigo_ou_args]
    else:
        args = [sys.executable, *codigo_ou_args]

    return subprocess.run(
        args, cwd=RAIZ, env=ambiente, capture_output=True, text=True, timeout=120
    )


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


# --- Boot em subprocesso -----------------------------------------------------
#
# Prova que as guardas rodam durante o import dos settings, e não só quando
# alguém chama a função. `django.setup()` não abre conexão com o banco, então o
# caso PostgreSQL passa sem servidor de pé — inclusive no CI.

BOOT = 'import django; django.setup()'


def test_boot_com_postgresql_funciona():
    resultado = _rodar(BOOT)

    assert resultado.returncode == 0, resultado.stderr


def test_boot_com_sqlite_falha():
    resultado = _rodar(BOOT, DATABASE_URL='sqlite:////tmp/db.sqlite3')

    assert resultado.returncode != 0
    assert 'django.db.backends.sqlite3' in resultado.stderr
    assert 'DATABASE_URL' in resultado.stderr


def test_boot_com_allowed_hosts_vazia_falha():
    resultado = _rodar(BOOT, ALLOWED_HOSTS='')

    assert resultado.returncode != 0
    assert 'ALLOWED_HOSTS' in resultado.stderr


def test_boot_com_allowed_hosts_curinga_falha():
    resultado = _rodar(BOOT, ALLOWED_HOSTS='*')

    assert resultado.returncode != 0
    assert '*' in resultado.stderr


def test_boot_com_origens_csrf_vazia_falha():
    resultado = _rodar(BOOT, CSRF_TRUSTED_ORIGINS='')

    assert resultado.returncode != 0
    assert 'CSRF_TRUSTED_ORIGINS' in resultado.stderr


def test_boot_com_origem_csrf_sem_esquema_falha():
    resultado = _rodar(BOOT, CSRF_TRUSTED_ORIGINS='piloto.exemplo.gov.br')

    assert resultado.returncode != 0
    assert 'CSRF_TRUSTED_ORIGINS' in resultado.stderr


# --- Valores efetivos de segurança -------------------------------------------
#
# `check --deploy` prova que não há warning, mas não prova qual valor produziu
# esse resultado: uma regressão que encurtasse `SECURE_HSTS_SECONDS` passaria
# despercebida. Aqui os valores são lidos um a um.

DESPEJO = """
import django, json
django.setup()
from django.conf import settings
campos = [
    'DEBUG', 'ALLOWED_HOSTS', 'CSRF_TRUSTED_ORIGINS', 'SESSION_COOKIE_SECURE',
    'CSRF_COOKIE_SECURE', 'SECURE_CONTENT_TYPE_NOSNIFF', 'SECURE_SSL_REDIRECT',
    'SECURE_HSTS_SECONDS', 'SECURE_HSTS_INCLUDE_SUBDOMAINS',
    'SECURE_HSTS_PRELOAD', 'X_FRAME_OPTIONS', 'SECURE_PROXY_SSL_HEADER',
]
print(json.dumps({campo: getattr(settings, campo, None) for campo in campos}))
"""


def _settings_efetivos(**sobrescritas):
    resultado = _rodar(DESPEJO, **sobrescritas)
    assert resultado.returncode == 0, resultado.stderr
    return json.loads(resultado.stdout)


def test_valores_efetivos_de_seguranca():
    efetivos = _settings_efetivos()

    assert efetivos['DEBUG'] is False
    assert efetivos['ALLOWED_HOSTS'] == ['piloto.exemplo.gov.br']
    assert efetivos['CSRF_TRUSTED_ORIGINS'] == ['https://piloto.exemplo.gov.br']
    assert efetivos['SESSION_COOKIE_SECURE'] is True
    assert efetivos['CSRF_COOKIE_SECURE'] is True
    assert efetivos['SECURE_CONTENT_TYPE_NOSNIFF'] is True
    assert efetivos['SECURE_SSL_REDIRECT'] is True
    assert efetivos['SECURE_HSTS_INCLUDE_SUBDOMAINS'] is True
    assert efetivos['SECURE_HSTS_PRELOAD'] is True
    assert efetivos['X_FRAME_OPTIONS'] == 'DENY'


def test_hsts_comeca_curto_no_piloto():
    """HSTS não é revogável remotamente: o piloto começa em 1h, não em 1 ano."""
    assert _settings_efetivos()['SECURE_HSTS_SECONDS'] == 3600


def test_hsts_pode_subir_por_variavel():
    efetivos = _settings_efetivos(PILOTO_HSTS_SECONDS='31536000')

    assert efetivos['SECURE_HSTS_SECONDS'] == 31536000


def test_check_deploy_continua_limpo_com_hsts_curto():
    """O `max-age` curto não pode reintroduzir o warning W004."""
    resultado, saida = _saida_do_check()

    assert resultado.returncode == 0, saida
    assert 'security.W004' not in saida


def test_debug_do_ambiente_nao_reabre_o_modo_debug():
    """`base` lê DEBUG do ambiente; o piloto atribui False depois do import."""
    assert _settings_efetivos(DEBUG='true')['DEBUG'] is False


def test_proxy_ssl_header_ausente_por_padrao():
    assert _settings_efetivos()['SECURE_PROXY_SSL_HEADER'] is None


def test_proxy_ssl_header_ligado_por_variavel():
    efetivos = _settings_efetivos(PILOTO_ATRAS_DE_PROXY_TLS='true')

    assert efetivos['SECURE_PROXY_SSL_HEADER'] == ['HTTP_X_FORWARDED_PROTO', 'https']


# --- check --deploy ----------------------------------------------------------

CHECK_DEPLOY = ['manage.py', 'check', '--deploy']


def _saida_do_check(**sobrescritas):
    """Junta stdout e stderr: o `check` escreve os warnings em stderr."""
    resultado = _rodar(CHECK_DEPLOY, **sobrescritas)
    return resultado, resultado.stdout + resultado.stderr


def test_check_deploy_passa_sem_warnings_de_seguranca():
    resultado, saida = _saida_do_check()

    assert resultado.returncode == 0, saida
    assert 'security.W0' not in saida


def test_check_deploy_acusa_secret_key_de_49_caracteres():
    _, saida = _saida_do_check(SECRET_KEY=SECRET_KEY_CURTA)

    assert 'security.W009' in saida


def test_check_deploy_aceita_secret_key_de_50_caracteres():
    _, saida = _saida_do_check(SECRET_KEY=SECRET_KEY_FORTE)

    assert 'security.W009' not in saida


# --- Normalização de espaços ------------------------------------------------
#
# `env.list` não faz strip: `ALLOWED_HOSTS=a.exemplo.br, b.exemplo.br` — a forma
# natural de escrever — chega como `['a.exemplo.br', ' b.exemplo.br']`. O Django
# compara host por igualdade exata, então o espaço faria o segundo domínio
# rejeitar toda requisição legítima, em silêncio. É a mesma classe de falha que
# esta issue existe para fechar, por isso os casos abaixo usam a saída real do
# `env.list`, não uma lista montada à mão.


@pytest.fixture
def env_list(monkeypatch):
    """Devolve exatamente o que `env.list` produziria para um valor bruto.

    Passa por `monkeypatch` para que a variável sentinela seja restaurada ao
    estado original ao fim de cada teste, inclusive quando ela já existir no
    ambiente do processo.
    """

    def _env_list(valor):
        monkeypatch.setenv('_LISTA_DE_TESTE', valor)
        return environ.Env().list('_LISTA_DE_TESTE')

    return _env_list


def test_env_list_realmente_preserva_espacos(env_list):
    """Trava a premissa: se o django-environ passar a fazer strip, isto avisa."""
    assert env_list('a.exemplo.br, b.exemplo.br') == ['a.exemplo.br', ' b.exemplo.br']


def test_hosts_permitidos_normaliza_espacos_do_env_list(env_list):
    bruto = 'a.exemplo.br, b.exemplo.br'

    assert exigir_hosts_permitidos(bruto, env_list(bruto)) == [
        'a.exemplo.br',
        'b.exemplo.br',
    ]


def test_origens_csrf_normaliza_espacos_do_env_list(env_list):
    bruto = 'https://a.exemplo.br, https://b.exemplo.br'

    assert exigir_origens_csrf_confiaveis(bruto, env_list(bruto)) == [
        'https://a.exemplo.br',
        'https://b.exemplo.br',
    ]


def test_curinga_com_espaco_ainda_e_recusado(env_list):
    bruto = 'a.exemplo.br, *'

    with pytest.raises(ImproperlyConfigured):
        exigir_hosts_permitidos(bruto, env_list(bruto))


def test_hosts_efetivos_no_boot_nao_tem_espacos():
    efetivos = _settings_efetivos(ALLOWED_HOSTS='a.exemplo.br, b.exemplo.br')

    assert efetivos['ALLOWED_HOSTS'] == ['a.exemplo.br', 'b.exemplo.br']
