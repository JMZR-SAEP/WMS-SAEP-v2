"""Testes de integração para o dispatcher pós-login (apps/core/views.home)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.models import Setor, SetorClassificacao, VinculoAuxiliar


@pytest.mark.django_db
def test_home_nao_autenticado_redireciona_login(client):
    resposta = client.get(reverse('core:home'))
    assert resposta.status_code == 302
    assert '/login' in resposta['Location'] or 'accounts' in resposta['Location']


@pytest.mark.django_db
def test_home_superuser_redireciona_admin(client):
    User = get_user_model()
    usuario = User.objects.create_superuser(
        matricula='SUPER-001',
        password='senha-forte-123',
        nome='Super Admin',
    )
    client.force_login(usuario)
    resposta = client.get(reverse('core:home'))
    assert resposta.status_code == 302
    assert resposta['Location'] == '/admin/'


@pytest.mark.django_db
def test_home_chefe_almoxarifado_redireciona_atendimentos(client):
    User = get_user_model()
    setor = Setor.objects.create(
        codigo='ALM', nome='Almoxarifado', classificacao=SetorClassificacao.ALMOXARIFADO
    )
    usuario = User.objects.create_user(
        matricula='ALMX-001',
        password='senha-forte-123',
        nome='Chefe Almox',
        setor=setor,
    )
    setor.chefe = usuario
    setor.save(update_fields=['chefe'])
    client.force_login(usuario)
    resposta = client.get(reverse('core:home'))
    assert resposta.status_code == 302
    assert resposta['Location'] == reverse('requisicoes:atendimentos')


@pytest.mark.django_db
def test_home_auxiliar_almoxarifado_redireciona_atendimentos(client):
    User = get_user_model()
    setor = Setor.objects.create(
        codigo='ALM2',
        nome='Almoxarifado',
        classificacao=SetorClassificacao.ALMOXARIFADO,
    )
    usuario = User.objects.create_user(
        matricula='ALMX-002',
        password='senha-forte-123',
        nome='Aux Almox',
        setor=setor,
    )
    VinculoAuxiliar.objects.create(usuario=usuario, setor=setor, ativo=True)
    client.force_login(usuario)
    resposta = client.get(reverse('core:home'))
    assert resposta.status_code == 302
    assert resposta['Location'] == reverse('requisicoes:atendimentos')


@pytest.mark.django_db
def test_home_chefe_setor_comum_redireciona_autorizacoes(client):
    User = get_user_model()
    setor = Setor.objects.create(
        codigo='OBR2', nome='Obras', classificacao=SetorClassificacao.COMUM
    )
    usuario = User.objects.create_user(
        matricula='CHEF-001',
        password='senha-forte-123',
        nome='Chefe Obras',
        setor=setor,
    )
    setor.chefe = usuario
    setor.save(update_fields=['chefe'])
    client.force_login(usuario)
    resposta = client.get(reverse('core:home'))
    assert resposta.status_code == 302
    assert resposta['Location'] == reverse('requisicoes:autorizacoes')


@pytest.mark.django_db
def test_home_solicitante_redireciona_minhas(client):
    User = get_user_model()
    setor = Setor.objects.create(
        codigo='OBR3', nome='Obras', classificacao=SetorClassificacao.COMUM
    )
    usuario = User.objects.create_user(
        matricula='SOL-001',
        password='senha-forte-123',
        nome='Solicitante',
        setor=setor,
    )
    client.force_login(usuario)
    resposta = client.get(reverse('core:home'))
    assert resposta.status_code == 302
    assert resposta['Location'] == reverse('requisicoes:minhas')


@pytest.mark.django_db
def test_home_staff_com_papel_almox_vai_para_atendimentos(client):
    """is_staff não bypassa o dispatcher — papel operacional tem prioridade."""
    User = get_user_model()
    setor = Setor.objects.create(
        codigo='ALM3',
        nome='Almoxarifado',
        classificacao=SetorClassificacao.ALMOXARIFADO,
    )
    usuario = User.objects.create_user(
        matricula='STAF-001',
        password='senha-forte-123',
        nome='Staff Almox',
        setor=setor,
        is_staff=True,
    )
    VinculoAuxiliar.objects.create(usuario=usuario, setor=setor, ativo=True)
    client.force_login(usuario)
    resposta = client.get(reverse('core:home'))
    assert resposta.status_code == 302
    assert resposta['Location'] == reverse('requisicoes:atendimentos')


@pytest.mark.django_db
def test_home_multi_papel_almox_chefe_vai_para_atendimentos(client):
    """Usuário com almoxarifado E chefe de setor comum → almox ganha (prioridade)."""
    User = get_user_model()
    setor_almox = Setor.objects.create(
        codigo='ALM4',
        nome='Almoxarifado',
        classificacao=SetorClassificacao.ALMOXARIFADO,
    )
    setor_comum = Setor.objects.create(
        codigo='OBR4', nome='Obras', classificacao=SetorClassificacao.COMUM
    )
    usuario = User.objects.create_user(
        matricula='MULT-001',
        password='senha-forte-123',
        nome='Multi Papel',
        setor=setor_almox,
    )
    VinculoAuxiliar.objects.create(usuario=usuario, setor=setor_almox, ativo=True)
    setor_comum.chefe = usuario
    setor_comum.save(update_fields=['chefe'])
    client.force_login(usuario)
    resposta = client.get(reverse('core:home'))
    assert resposta.status_code == 302
    assert resposta['Location'] == reverse('requisicoes:atendimentos')
