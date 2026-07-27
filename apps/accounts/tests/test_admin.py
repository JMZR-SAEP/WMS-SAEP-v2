"""Testes do admin de accounts.

Roteamento da desativação de setor por `desativar_setor` (issue #107).
"""

import pytest
from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts.admin import SetorAdmin
from apps.accounts.models import Setor, SetorClassificacao, User
from apps.core.exceptions import ConflitoDominio

SENHA = 'senha123'


@pytest.fixture
def setor(db):
    return Setor.objects.create(
        codigo='SA', nome='Setor A', classificacao=SetorClassificacao.COMUM
    )


@pytest.fixture
def superusuario(db, setor):
    return User.objects.create_superuser(
        matricula='S01', nome='Super', password=SENHA, setor=setor
    )


@pytest.fixture
def setor_admin():
    return SetorAdmin(Setor, AdminSite())


@pytest.fixture
def request_de(rf: RequestFactory):
    """Devolve um request de admin já autenticado como o usuário dado."""

    def _request(usuario):
        req = rf.post(f'/admin/accounts/setor/{usuario.setor_id}/change/')
        req.user = usuario
        return req

    return _request


class _FormFake:
    """Stand-in de ModelForm: `save_model` só consulta `changed_data`."""

    def __init__(self, *campos):
        self.changed_data = list(campos)


@pytest.fixture
def requisicao_em_voo(db, superusuario):
    def _criar(setor_alvo):
        from apps.requisicoes.models import EstadoRequisicao, Requisicao

        return Requisicao.objects.create(
            estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
            criador=superusuario,
            beneficiario=superusuario,
            setor_beneficiario=setor_alvo,
        )

    return _criar


@pytest.fixture
def staff_com_permissao(db, setor):
    """Staff que o Django autorizaria a editar Setor, mas sem papel de cadastro."""
    from django.contrib.auth.models import Permission

    usuario = User.objects.create_user(
        matricula='ST1', nome='Staff', password=SENHA, setor=setor, is_staff=True
    )
    usuario.user_permissions.add(
        Permission.objects.get(
            codename='change_setor', content_type__app_label='accounts'
        )
    )
    return usuario


@pytest.mark.django_db
def test_save_model_desativa_setor_sem_requisicoes_em_voo(
    setor_admin, request_de, superusuario, setor
):
    setor.ativo = False

    setor_admin.save_model(request_de(superusuario), setor, _FormFake('ativo'), True)

    setor.refresh_from_db()
    assert setor.ativo is False


@pytest.mark.django_db
def test_save_model_aplica_policy_de_cadastro(
    setor_admin, request_de, setor, staff_com_permissao
):
    """A permissão padrão do Django não substitui `pode_gerir_cadastro`."""
    from apps.core.exceptions import PermissaoNegada

    setor.ativo = False

    with pytest.raises(PermissaoNegada):
        setor_admin.save_model(
            request_de(staff_com_permissao), setor, _FormFake('ativo'), True
        )

    setor.refresh_from_db()
    assert setor.ativo is True


@pytest.mark.django_db
def test_save_model_propaga_conflito_de_requisicao_em_voo(
    setor_admin, request_de, superusuario, setor, requisicao_em_voo
):
    """Sem o roteamento pelo service, o UPDATE direto passaria batido."""
    requisicao_em_voo(setor)
    setor.ativo = False

    with pytest.raises(ConflitoDominio) as exc_info:
        setor_admin.save_model(
            request_de(superusuario), setor, _FormFake('ativo'), True
        )

    assert exc_info.value.code == 'setor_com_requisicoes_em_voo'
    setor.refresh_from_db()
    assert setor.ativo is True


@pytest.mark.django_db
def test_save_model_recusa_desativacao_com_campos_extras(
    setor_admin, request_de, superusuario, setor
):
    """O `return` do ramo de desativação descartaria os outros campos em silêncio."""
    setor.ativo = False
    setor.nome = 'Setor A Renomeado'

    with pytest.raises(ConflitoDominio) as exc_info:
        setor_admin.save_model(
            request_de(superusuario), setor, _FormFake('ativo', 'nome'), True
        )

    assert exc_info.value.code == 'desativacao_setor_com_campos_extras'
    setor.refresh_from_db()
    assert setor.ativo is True
    assert setor.nome == 'Setor A'


@pytest.mark.django_db
def test_changeform_traduz_conflito_em_mensagem(
    client, superusuario, setor, requisicao_em_voo
):
    """Contrato HTTP: `_changeform_com_captura_dominio` evita o 500 e exibe o texto.

    O 302 sozinho não distingue este redirect do de um save bem-sucedido; a
    mensagem exibida é o que prova que a exceção virou retorno ao usuário.
    `ConflitoDominio` é `warning` pelo mapeamento de `docs/CONVENTIONS.md`.
    """
    requisicao_em_voo(setor)
    client.force_login(superusuario)

    resposta = client.post(
        reverse('admin:accounts_setor_change', args=[setor.pk]),
        {
            'codigo': setor.codigo,
            'nome': setor.nome,
            'classificacao': setor.classificacao,
            'chefe': '',
        },
        follow=True,
    )

    assert resposta.redirect_chain[-1][1] == 302
    avisos = [
        str(m) for m in resposta.context['messages'] if m.level == messages.WARNING
    ]
    assert avisos == [
        f"O setor '{setor.nome}' tem 1 requisição aguardando autorização. "
        'Conclua ou cancele antes de desativar o setor.'
    ]
    setor.refresh_from_db()
    assert setor.ativo is True


@pytest.mark.django_db
def test_changeform_traduz_dados_invalidos_em_erro(client, superusuario, setor):
    """`DadosInvalidos` segue em `error` — o mapeamento não é uniforme.

    Designar chefe inativo é dado errado do formulário, não conflito de estado.
    """
    chefe_inativo = User.objects.create_user(
        matricula='IN1', nome='Inativo', password=SENHA, setor=setor, is_active=False
    )
    client.force_login(superusuario)

    resposta = client.post(
        reverse('admin:accounts_setor_change', args=[setor.pk]),
        {
            'codigo': setor.codigo,
            'nome': setor.nome,
            'classificacao': setor.classificacao,
            'chefe': str(chefe_inativo.pk),
            'ativo': 'on',
        },
        follow=True,
    )

    assert resposta.redirect_chain[-1][1] == 302
    erros = [str(m) for m in resposta.context['messages'] if m.level == messages.ERROR]
    assert erros == [
        f"Usuário '{chefe_inativo.nome}' está inativo e não pode ser designado como chefe."
    ]
    setor.refresh_from_db()
    assert setor.chefe_id is None
