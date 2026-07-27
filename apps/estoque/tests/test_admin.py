"""Testes do admin de estoque.

- Guard de estoque único em `EstoqueAdmin` (issue #102, ADR-0017).
- Derivação de `PapelEfetivo` antes da policy em `MaterialAdmin` (issue #104).
- Nível das mensagens de erro de domínio (issue #107).
"""

import pytest
from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts.models import User
from apps.estoque.admin import EstoqueAdmin, MaterialAdmin
from apps.estoque.models import Estoque, Material


@pytest.fixture
def estoque_admin():
    return EstoqueAdmin(Estoque, AdminSite())


@pytest.fixture
def request_de(rf: RequestFactory):
    """Devolve um request de admin já autenticado como o usuário dado."""

    def _request(usuario):
        req = rf.get('/admin/estoque/estoque/add/')
        req.user = usuario
        return req

    return _request


def test_nao_permite_adicionar_segundo_estoque(
    estoque_admin, request_de, superuser, estoque_principal
):
    assert estoque_admin.has_add_permission(request_de(superuser)) is False


def test_permite_adicionar_o_primeiro_estoque(estoque_admin, request_de, superuser):
    assert Estoque.objects.exists() is False

    assert estoque_admin.has_add_permission(request_de(superuser)) is True


def test_estoque_inativo_tambem_bloqueia_adicao(estoque_admin, request_de, superuser):
    """O guard não filtra por `ativo`.

    Os services localizam `SaldoEstoque` por `material_id` sem olhar
    `estoque.ativo`: um segundo estoque inativo com saldo quebraria a
    autorização do mesmo jeito.
    """
    Estoque.objects.create(codigo='EST99', nome='Estoque Desativado', ativo=False)

    assert estoque_admin.has_add_permission(request_de(superuser)) is False


def test_guard_nao_concede_permissao_a_quem_nao_tem(
    estoque_admin, request_de, chefe_almoxarifado
):
    """O guard compõe com a checagem padrão do Django, não a substitui."""
    assert Estoque.objects.exists() is False

    assert estoque_admin.has_add_permission(request_de(chefe_almoxarifado)) is False


# ---------------------------------------------------------------------------
# MaterialAdmin — derivação de papel antes da policy (issue #104)
# ---------------------------------------------------------------------------


def test_admin_index_responde_para_superusuario(client, superuser):
    """Regressão #104: o admin inteiro caía em 500, não só as telas de Material.

    `AdminSite.each_context` monta o menu lateral via `get_app_list`, que
    consulta as permissões de todo `ModelAdmin` registrado. Um erro em
    `MaterialAdmin` derruba `admin:index`, destino do redirect pós-login.
    """
    client.force_login(superuser)

    assert client.get(reverse('admin:index')).status_code == 200


@pytest.fixture
def material_admin():
    return MaterialAdmin(Material, AdminSite())


def test_material_changelist_responde_para_superusuario(client, superuser):
    client.force_login(superuser)

    resposta = client.get(reverse('admin:estoque_material_changelist'))

    assert resposta.status_code == 200


def test_material_add_responde_para_superusuario(client, superuser):
    client.force_login(superuser)

    resposta = client.get(reverse('admin:estoque_material_add'))

    assert resposta.status_code == 200


def test_pode_gerir_autoriza_superusuario(material_admin, request_de, superuser):
    assert material_admin._pode_gerir(request_de(superuser)) is True


def test_pode_gerir_nega_quem_nao_e_superusuario(
    material_admin, request_de, chefe_almoxarifado
):
    """Sem este caso, um `_pode_gerir` que sempre devolvesse `True` passaria
    nos smokes acima — trocando o 500 por uma brecha de permissão."""
    assert material_admin._pode_gerir(request_de(chefe_almoxarifado)) is False


@pytest.fixture
def staff_de_material(db, setor_obras):
    """Staff **não** superusuário, com as permissões Django de `Material`.

    O Django, sozinho, autorizaria este usuário. Qualquer 403 nas telas de
    `Material` só pode vir de `pode_gerir_catalogo` — é o que separa o gate da
    policy do gate de permissões padrão.
    """
    usuario = User.objects.create_user(
        matricula='902',
        nome='Staff Catalogo',
        password='senha',
        setor=setor_obras,
        is_staff=True,
    )
    usuario.user_permissions.set(
        Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Material),
            codename__in=('add_material', 'change_material', 'view_material'),
        )
    )
    return usuario


def test_add_de_material_nega_staff_sem_autorizacao(client, staff_de_material):
    """`has_add_permission` consome `_pode_gerir`, e não só a permissão Django."""
    client.force_login(staff_de_material)

    resposta = client.get(reverse('admin:estoque_material_add'))

    assert resposta.status_code == 403


def test_change_de_material_nega_staff_sem_autorizacao(
    client, staff_de_material, material_disponivel
):
    """`has_change_permission` consome `_pode_gerir`.

    O POST é deliberado: `ModelAdmin._changeform_view` só consulta
    `has_change_permission` no POST; no GET consultaria
    `has_view_or_change_permission`, que `MaterialAdmin` não sobrescreve.
    """
    client.force_login(staff_de_material)

    resposta = client.post(
        reverse('admin:estoque_material_change', args=[material_disponivel.pk]), {}
    )

    assert resposta.status_code == 403


def test_changelist_de_material_permanece_legivel_para_staff(
    client, staff_de_material, material_disponivel
):
    """A policy gateia escrita, não leitura.

    `has_view_permission` não é sobrescrito, então a consulta ao catálogo segue
    governada pelas permissões Django. Fixar o 200 aqui impede que uma mudança
    futura amplie o gate para leitura sem que ninguém perceba.
    """
    client.force_login(staff_de_material)

    resposta = client.get(reverse('admin:estoque_material_changelist'))

    assert resposta.status_code == 200


# ---------------------------------------------------------------------------
# Nível das mensagens de erro de domínio (issue #107)
# ---------------------------------------------------------------------------


def test_changeform_traduz_conflito_em_warning(client, superuser, material_disponivel):
    """`ConflitoDominio` é `warning` pelo mapeamento de `docs/CONVENTIONS.md`.

    A ação não foi aplicada, mas o estado atual — material com saldo — é
    compreensível e não exige correção de dado pelo usuário.
    """
    client.force_login(superuser)

    resposta = client.post(
        reverse('admin:estoque_material_change', args=[material_disponivel.pk]),
        {
            'codigo': material_disponivel.codigo,
            'nome': material_disponivel.nome,
            'unidade': material_disponivel.unidade,
            'observacao_interna': '',
        },
        follow=True,
    )

    assert resposta.redirect_chain[-1][1] == 302
    avisos = [
        str(m) for m in resposta.context['messages'] if m.level == messages.WARNING
    ]
    assert avisos == [
        f"Material '{material_disponivel.nome}' possui saldo físico (100.000). "
        'Zere o saldo antes de desativar.'
    ]
    material_disponivel.refresh_from_db()
    assert material_disponivel.ativo is True
