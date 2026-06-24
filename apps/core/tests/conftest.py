import pytest

from apps.accounts.models import Setor, SetorClassificacao, User


@pytest.fixture
def setor_comum(db):
    return Setor.objects.create(
        codigo='OBR', nome='Obras', classificacao=SetorClassificacao.COMUM
    )


@pytest.fixture
def setor_almoxarifado(db):
    return Setor.objects.create(
        codigo='ALM', nome='Almoxarifado', classificacao=SetorClassificacao.ALMOXARIFADO
    )


@pytest.fixture
def superusuario(db, setor_comum):
    return User.objects.create_superuser(
        matricula='900',
        nome='Super Usuário',
        password='senha',
        setor=setor_comum,
    )


@pytest.fixture
def chefe_almox(db, setor_almoxarifado):
    u = User.objects.create_user(
        matricula='021',
        nome='Chefe Almoxarifado',
        password='senha',
        setor=setor_almoxarifado,
    )
    setor_almoxarifado.chefe = u
    setor_almoxarifado.save(update_fields=['chefe'])
    return u


@pytest.fixture
def chefe_comum(db, setor_comum):
    u = User.objects.create_user(
        matricula='010',
        nome='Chefe Comum',
        password='senha',
        setor=setor_comum,
    )
    setor_comum.chefe = u
    setor_comum.save(update_fields=['chefe'])
    return u


@pytest.fixture
def solicitante(db, setor_comum):
    return User.objects.create_user(
        matricula='001',
        nome='Solicitante Comum',
        password='senha',
        setor=setor_comum,
    )
