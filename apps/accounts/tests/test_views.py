"""Testes HTTP de MatriculaLoginView — comportamentos de view não cobertos em test_login.py."""

import pytest
from django.conf import settings
from django.urls import reverse

from apps.accounts.models import User

SENHA = 'senha123'


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        matricula='OP-002',
        password=SENHA,
        nome='Usuário View Test',
    )


@pytest.fixture
def usuario_inativo(db):
    return User.objects.create_user(
        matricula='OP-003',
        password=SENHA,
        nome='Usuário Inativo',
        is_active=False,
    )


@pytest.mark.django_db
def test_usuario_autenticado_redirecionado_ao_acessar_login(client, usuario):
    """MatriculaLoginView.redirect_authenticated_user=True deve redirecionar usuário logado."""
    client.force_login(usuario)
    resposta = client.get(reverse('accounts:login'))
    assert resposta.status_code == 302
    assert resposta.headers['Location'] != reverse('accounts:login')


@pytest.mark.django_db
def test_login_post_valido_redireciona(client, usuario):
    resposta = client.post(
        reverse('accounts:login'),
        {'username': 'OP-002', 'password': SENHA},
    )
    assert resposta.status_code == 302
    assert resposta.headers['Location'] == settings.LOGIN_REDIRECT_URL
    assert str(usuario.pk) == client.session.get('_auth_user_id')


@pytest.mark.django_db
def test_matricula_invalida_retorna_form_com_erro(client):
    resposta = client.post(
        reverse('accounts:login'),
        {'username': 'INEXISTENTE', 'password': SENHA},
    )
    assert resposta.status_code == 200
    assert not resposta.wsgi_request.user.is_authenticated


@pytest.mark.django_db
def test_usuario_inativo_nao_autentica(client, usuario_inativo):
    resposta = client.post(
        reverse('accounts:login'),
        {'username': 'OP-003', 'password': SENHA},
    )
    assert resposta.status_code == 200
    assert not resposta.wsgi_request.user.is_authenticated


@pytest.mark.django_db
def test_logout_encerra_sessao(client, usuario):
    client.force_login(usuario)
    resposta = client.post(reverse('accounts:logout'))
    assert resposta.status_code == 302
    assert not resposta.wsgi_request.user.is_authenticated
