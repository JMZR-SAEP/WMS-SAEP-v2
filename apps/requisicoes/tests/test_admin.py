"""Testes do admin de requisições (issue #105).

O admin é válvula de emergência, não caminho de escrita: `estado`, as três
quantidades de `ItemRequisicao` e a timeline são governados pela máquina de
estados e pelos services. Estes testes fixam que o admin não os escreve, e
que a leitura continua aberta a quem o Django autoriza.
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts.models import User
from apps.requisicoes.admin import RequisicaoAdmin
from apps.requisicoes.models import EstadoRequisicao, Requisicao


@pytest.fixture
def request_de(rf: RequestFactory):
    """Devolve um request de admin já autenticado como o usuário dado."""

    def _request(usuario):
        req = rf.get('/admin/requisicoes/requisicao/')
        req.user = usuario
        return req

    return _request


@pytest.fixture
def requisicao_admin():
    return RequisicaoAdmin(Requisicao, AdminSite())


@pytest.fixture
def staff_de_requisicao(db, setor_obras):
    """Staff **não** superusuário, com todas as permissões Django de requisições.

    O Django, sozinho, autorizaria este usuário nos três models. Qualquer
    negação só pode vir dos guards deste issue — é o que separa o gate do
    plano do gate de permissões padrão.
    """
    usuario = User.objects.create_user(
        matricula='903',
        nome='Staff Requisicoes',
        password='senha',
        setor=setor_obras,
        is_staff=True,
    )
    usuario.user_permissions.set(
        Permission.objects.filter(
            content_type__in=ContentType.objects.get_for_models(
                Requisicao,
            ).values(),
        )
    )
    return usuario


def _payload_requisicao(requisicao, **overrides):
    """Corpo mínimo de POST para a change view de `Requisicao`.

    Inclui o `management_form` do inline `itens` (prefixo vindo do
    `related_name` em `ItemRequisicao.requisicao`), sem o qual o Django
    rejeita o POST antes de chegar ao formulário principal.
    """
    dados = {
        'criador': str(requisicao.criador_id),
        'beneficiario': str(requisicao.beneficiario_id),
        'setor_beneficiario': str(requisicao.setor_beneficiario_id),
        'observacao_geral': requisicao.observacao_geral,
        'itens-TOTAL_FORMS': '0',
        'itens-INITIAL_FORMS': '0',
        'itens-MIN_NUM_FORMS': '0',
        'itens-MAX_NUM_FORMS': '1000',
    }
    dados.update(overrides)
    return dados


def test_post_no_admin_nao_troca_estado_da_requisicao(
    client, superuser, req_historico_obras
):
    """O cenário do issue: o superusuário 'conserta' a requisição presa à mão.

    O POST é aceito (302) porque os demais campos seguem editáveis — a válvula
    de emergência continua funcionando. O que não pode acontecer é `estado`
    entrar no banco vindo do corpo da requisição, pulando timeline e ledger.
    """
    client.force_login(superuser)
    assert req_historico_obras.estado == EstadoRequisicao.AGUARDANDO_AUTORIZACAO

    resposta = client.post(
        reverse('admin:requisicoes_requisicao_change', args=[req_historico_obras.pk]),
        _payload_requisicao(req_historico_obras, estado=EstadoRequisicao.ATENDIDA),
    )

    assert resposta.status_code == 302
    req_historico_obras.refresh_from_db()
    assert req_historico_obras.estado == EstadoRequisicao.AGUARDANDO_AUTORIZACAO


def test_estado_declarado_readonly_em_requisicao_admin(requisicao_admin):
    assert 'estado' in requisicao_admin.readonly_fields


def test_estado_fora_do_formulario_de_requisicao(
    requisicao_admin, request_de, superuser, req_historico_obras
):
    """`readonly_fields` não é cosmético: `get_form` joga o campo em `exclude`.

    Sem este caso, um `get_readonly_fields` sobrescrito no futuro poderia
    devolver algo diferente do atributo de classe e o teste acima continuaria
    verde enquanto o campo voltava a ser editável.
    """
    formulario = requisicao_admin.get_form(
        request_de(superuser), obj=req_historico_obras
    )

    assert 'estado' not in formulario.base_fields


def test_estado_fora_do_formulario_tambem_para_staff_autorizado(
    requisicao_admin, request_de, staff_de_requisicao, req_historico_obras
):
    """O gate não é "superuser-only": vale para quem o Django já autorizaria."""
    formulario = requisicao_admin.get_form(
        request_de(staff_de_requisicao), obj=req_historico_obras
    )

    assert 'estado' not in formulario.base_fields


def test_post_no_admin_altera_campo_nao_derivado_da_requisicao(
    client, superuser, req_historico_obras
):
    """O caminho feliz da válvula de emergência.

    Sem este caso, um `has_change_permission = False` colado por engano em
    `RequisicaoAdmin` passaria em todos os outros testes e ninguém notaria que
    o admin virou vitrine.
    """
    client.force_login(superuser)

    resposta = client.post(
        reverse('admin:requisicoes_requisicao_change', args=[req_historico_obras.pk]),
        _payload_requisicao(req_historico_obras, observacao_geral='ajuste manual'),
    )

    assert resposta.status_code == 302
    req_historico_obras.refresh_from_db()
    assert req_historico_obras.observacao_geral == 'ajuste manual'


def test_change_view_de_requisicao_responde(client, superuser, req_historico_obras):
    """Smoke da change view — é onde o inline de itens é montado.

    `BaseModelAdmin.get_inline_instances` chama
    `inline.has_add_permission(request, obj)` com dois argumentos. Uma
    assinatura errada no inline derrubaria esta página com `TypeError`, que é
    a classe de regressão do #104.
    """
    client.force_login(superuser)

    resposta = client.get(
        reverse('admin:requisicoes_requisicao_change', args=[req_historico_obras.pk])
    )

    assert resposta.status_code == 200
