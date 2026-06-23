"""Fixtures compartilhadas para testes de notificações."""

import pytest

from apps.accounts.models import Setor, SetorClassificacao, User
from apps.estoque.models import Estoque, Material, SaldoEstoque, UnidadeMedida
from apps.notificacoes.models import Notificacao, TipoNotificacao


@pytest.fixture
def setor_obras(db):
    return Setor.objects.create(nome='Obras', codigo='OBR')


@pytest.fixture
def setor_almoxarifado(db):
    return Setor.objects.create(
        nome='Almoxarifado',
        codigo='ALM',
        classificacao=SetorClassificacao.ALMOXARIFADO,
    )


@pytest.fixture
def chefe_obras(db, setor_obras):
    u = User.objects.create_user(
        matricula='010',
        nome='Chefe Obras',
        password='senha',
        setor=setor_obras,
    )
    setor_obras.chefe = u
    setor_obras.save(update_fields=['chefe'])
    return u


@pytest.fixture
def solicitante(db, setor_obras):
    return User.objects.create_user(
        matricula='001',
        nome='João Solicitante',
        password='senha',
        setor=setor_obras,
    )


@pytest.fixture
def outro_solicitante(db, setor_obras):
    return User.objects.create_user(
        matricula='002',
        nome='Maria Solicitante',
        password='senha',
        setor=setor_obras,
    )


@pytest.fixture
def chefe_almoxarifado(db, setor_almoxarifado):
    u = User.objects.create_user(
        matricula='020',
        nome='Chefe Almox',
        password='senha',
        setor=setor_almoxarifado,
    )
    setor_almoxarifado.chefe = u
    setor_almoxarifado.save(update_fields=['chefe'])
    return u


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        matricula='999',
        nome='Admin',
        password='senha',
    )


@pytest.fixture
def estoque_principal(db):
    return Estoque.objects.create(nome='Principal', codigo='ESTQ-001')


@pytest.fixture
def material_disponivel(db, estoque_principal):
    m = Material.objects.create(
        codigo='000.000.001',
        nome='Parafuso M6',
        unidade=UnidadeMedida.UNIDADE,
        ativo=True,
    )
    SaldoEstoque.objects.create(
        estoque=estoque_principal,
        material=m,
        saldo_fisico=100,
        saldo_reservado=0,
    )
    return m


@pytest.fixture
def notificacao_nao_lida(db, solicitante):
    return Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.AUTORIZACAO,
        requisicao_id=1,
        lida=False,
    )
