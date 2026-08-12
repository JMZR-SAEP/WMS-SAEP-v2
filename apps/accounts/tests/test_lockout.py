"""Testes do lockout de login por matrícula (django-axes).

Todos exercitam a rota real de login. Chamar helpers do axes diretamente
testaria a biblioteca; o que está sob teste aqui é a configuração do projeto.
"""

from datetime import timedelta

import pytest
from axes.models import AccessAttempt, AccessAttemptExpiration
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User

SENHA = 'senha-forte-123'
SENHA_ERRADA = 'errada'
IP = '10.0.0.7'
OUTRO_IP = '10.0.0.8'


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        matricula='OP-001',
        password=SENHA,
        nome='Operador Teste',
    )


@pytest.fixture
def colega(db):
    return User.objects.create_user(
        matricula='OP-002',
        password=SENHA,
        nome='Colega Teste',
    )


def _tentar_login(client, *, matricula, senha, ip=IP, **extra):
    return client.post(
        reverse('accounts:login'),
        {'username': matricula, 'password': senha},
        REMOTE_ADDR=ip,
        **extra,
    )


def _falhar(client, *, vezes, matricula='OP-001', ip=IP):
    """Tenta logar com senha errada `vezes` vezes; devolve a última resposta."""
    if vezes < 1:
        raise ValueError('vezes deve ser >= 1')
    for _ in range(vezes):
        resposta = _tentar_login(client, matricula=matricula, senha=SENHA_ERRADA, ip=ip)
    return resposta


def _envelhecer_tentativas(minutos):
    """Reproduz o estado do banco `minutos` depois.

    Envelhecer só `attempt_time` não basta: com `AXES_USE_ATTEMPT_EXPIRATION`,
    a limpeza filtra por `expiration__expires_at`, não pelo instante da
    tentativa.
    """
    instante = timezone.now() - timedelta(minutes=minutos)
    AccessAttempt.objects.update(attempt_time=instante)
    AccessAttemptExpiration.objects.update(expires_at=instante)


def test_abaixo_do_limite_nao_bloqueia(client, usuario):
    resposta = _falhar(client, vezes=4)

    assert resposta.status_code == 200
    assert 'accounts/login.html' in {t.name for t in resposta.templates}
    assert not resposta.wsgi_request.user.is_authenticated


def test_quinta_falha_bloqueia(client, usuario):
    resposta = _falhar(client, vezes=5)

    assert resposta.status_code == 429
    assert 'accounts/login_bloqueado.html' in {t.name for t in resposta.templates}


def test_bloqueio_recusa_ate_a_senha_correta(client, usuario):
    _falhar(client, vezes=5)

    resposta = _tentar_login(client, matricula='OP-001', senha=SENHA)

    assert resposta.status_code == 429
    assert not resposta.wsgi_request.user.is_authenticated


def test_bloqueio_nao_atinge_outra_matricula_no_mesmo_ip(client, usuario, colega):
    _falhar(client, vezes=5)

    resposta = _tentar_login(client, matricula='OP-002', senha=SENHA)

    assert resposta.status_code == 302
    assert resposta.wsgi_request.user.is_authenticated


def test_bloqueio_nao_atinge_a_mesma_matricula_de_outro_ip(client, usuario):
    _falhar(client, vezes=5)

    resposta = _tentar_login(client, matricula='OP-001', senha=SENHA, ip=OUTRO_IP)

    assert resposta.status_code == 302
    assert resposta.wsgi_request.user.is_authenticated


def test_login_bem_sucedido_zera_o_contador(client, usuario):
    _falhar(client, vezes=4)
    _tentar_login(client, matricula='OP-001', senha=SENHA)
    client.logout()

    resposta = _falhar(client, vezes=4)

    assert resposta.status_code == 200


def test_fim_da_janela_libera_o_acesso(client, usuario):
    _falhar(client, vezes=5)

    _envelhecer_tentativas(16)
    resposta = _tentar_login(client, matricula='OP-001', senha=SENHA)

    assert resposta.status_code == 302
    assert resposta.wsgi_request.user.is_authenticated


def test_sem_proxy_o_cabecalho_encaminhado_e_ignorado(client, usuario):
    """Cabeçalho forjado não pode virar rota de fuga do lockout.

    Fora do bloco de proxy do piloto, a precedência é o default do axes
    (`REMOTE_ADDR` apenas). Se o cliente pudesse escolher o próprio IP pelo
    cabeçalho, teria cinco tentativas novas a cada valor inventado.
    """
    _tentar_login(
        client,
        matricula='OP-001',
        senha=SENHA_ERRADA,
        HTTP_X_FORWARDED_FOR='203.0.113.9',
    )

    assert AccessAttempt.objects.get().ip_address == IP


def test_atras_de_proxy_usa_o_ip_da_cadeia(client, usuario, settings):
    settings.AXES_IPWARE_META_PRECEDENCE_ORDER = [
        'HTTP_X_FORWARDED_FOR',
        'REMOTE_ADDR',
    ]
    settings.AXES_IPWARE_PROXY_COUNT = 1

    _tentar_login(
        client,
        matricula='OP-001',
        senha=SENHA_ERRADA,
        HTTP_X_FORWARDED_FOR='203.0.113.9, 10.0.0.1',
    )

    assert AccessAttempt.objects.get().ip_address == '203.0.113.9'


def test_atras_de_proxy_requisicao_direta_fica_sem_ip(client, usuario, settings):
    """Requisição que não passou pelo proxy não rende IP de cliente.

    `AXES_IPWARE_PROXY_COUNT = 1` faz o ipware exigir exatamente um proxy na
    cadeia, e ele valida essa contagem por origem: `REMOTE_ADDR` sozinho tem
    zero proxies, então é descartado junto com o cabeçalho ausente e o IP sai
    `None` — o recuo para `REMOTE_ADDR` **não** cobre este caso.

    O resultado é seguro, não um furo: a tentativa passa a ser chaveada só pela
    matrícula, o que ainda bloqueia e não contamina outros usuários. Mas ele
    depende de o Django não ser alcançável por fora do proxy no piloto, o que é
    item do GL-02.
    """
    settings.AXES_IPWARE_META_PRECEDENCE_ORDER = [
        'HTTP_X_FORWARDED_FOR',
        'REMOTE_ADDR',
    ]
    settings.AXES_IPWARE_PROXY_COUNT = 1

    _tentar_login(client, matricula='OP-001', senha=SENHA_ERRADA)

    assert AccessAttempt.objects.get().ip_address is None


def test_atras_de_proxy_cabecalho_forjado_sem_cadeia_e_descartado(
    client, usuario, settings
):
    """Cliente que inventa um XFF de uma entrada só não vira dono do próprio IP.

    O proxy real acrescenta uma entrada à cadeia; um cabeçalho forjado
    diretamente tem contagem errada e é descartado pela mesma validação.
    """
    settings.AXES_IPWARE_META_PRECEDENCE_ORDER = [
        'HTTP_X_FORWARDED_FOR',
        'REMOTE_ADDR',
    ]
    settings.AXES_IPWARE_PROXY_COUNT = 1

    _tentar_login(
        client,
        matricula='OP-001',
        senha=SENHA_ERRADA,
        HTTP_X_FORWARDED_FOR='203.0.113.9',
    )

    assert AccessAttempt.objects.get().ip_address != '203.0.113.9'


def test_pagina_de_bloqueio_informa_prazo_e_nao_revela_a_matricula(client, usuario):
    matricula = 'ZZQX-9137'
    User.objects.create_user(matricula=matricula, password=SENHA, nome='Alvo')

    resposta = _falhar(client, vezes=5, matricula=matricula)
    conteudo = resposta.content.decode()

    assert resposta.status_code == 429
    # A janela mostrada tem de vir da configuração, não de um número digitado à
    # mão: mudar `AXES_COOLOFF_TIME` sem mexer no template deixaria a página
    # mentindo para o usuário.
    minutos = int(settings.AXES_COOLOFF_TIME.total_seconds() // 60)
    assert f'{minutos} minutos' in conteudo
    # Não pode virar oráculo de enumeração de contas.
    assert matricula not in conteudo


def test_tentativa_durante_o_bloqueio_prorroga_a_janela(client, usuario):
    _falhar(client, vezes=5)
    prazo_antes = AccessAttemptExpiration.objects.get().expires_at

    _falhar(client, vezes=1)

    prazo_depois = AccessAttemptExpiration.objects.get().expires_at
    assert prazo_depois > prazo_antes
