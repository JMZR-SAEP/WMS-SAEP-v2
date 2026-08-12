"""Testes do lockout de login por matrícula (django-axes).

Todos exercitam a rota real de login. Chamar helpers do axes diretamente
testaria a biblioteca; o que está sob teste aqui é a configuração do projeto.
"""

import pytest
from django.urls import reverse

from apps.accounts.models import User

SENHA = 'senha-forte-123'
SENHA_ERRADA = 'errada'
IP = '10.0.0.7'


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        matricula='OP-001',
        password=SENHA,
        nome='Operador Teste',
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


def test_quinta_falha_bloqueia(client, usuario):
    resposta = _falhar(client, vezes=5)

    assert resposta.status_code == 429
