"""Testes do admin de accounts.

Roteamento da desativação de setor por `desativar_setor` (issue #107) e do
remanejamento de lotação por `remanejar_usuario` (issue #114), além da captura
seletiva de `OperationalError` compartilhada pelos admins do módulo.
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


# ---------------------------------------------------------------------------
# UserAdmin — roteamento do remanejamento de lotação (issue #114)
# ---------------------------------------------------------------------------


@pytest.fixture
def user_admin():
    from apps.accounts.admin import UserAdmin

    return UserAdmin(User, AdminSite())


@pytest.fixture
def setor_destino(db):
    return Setor.objects.create(
        codigo='SB', nome='Setor B', classificacao=SetorClassificacao.COMUM
    )


@pytest.fixture
def lotado(db, setor):
    return User.objects.create_user(
        matricula='U10', nome='Lotado', password=SENHA, setor=setor
    )


@pytest.mark.django_db
def test_user_save_model_remaneja_usuario_sem_chefia(
    user_admin, request_de, superusuario, setor_destino, lotado
):
    lotado.setor = setor_destino

    user_admin.save_model(request_de(superusuario), lotado, _FormFake('setor'), True)

    lotado.refresh_from_db()
    assert lotado.setor_id == setor_destino.pk


@pytest.mark.django_db
def test_user_save_model_bloqueia_remanejamento_de_chefe(
    user_admin, request_de, superusuario, setor, setor_destino, lotado
):
    """Sem o roteamento pelo service, o UPDATE direto passaria batido."""
    setor.chefe = lotado
    setor.save(update_fields=['chefe'])
    lotado.setor = setor_destino

    with pytest.raises(ConflitoDominio) as exc_info:
        user_admin.save_model(
            request_de(superusuario), lotado, _FormFake('setor'), True
        )

    assert exc_info.value.code == 'usuario_chefe_remanejado_sem_substituto'
    lotado.refresh_from_db()
    assert lotado.setor_id == setor.pk


@pytest.mark.django_db
def test_user_save_model_recusa_remanejamento_com_campos_extras(
    user_admin, request_de, superusuario, setor, setor_destino, lotado
):
    """O `return` do ramo de remanejamento descartaria os outros campos em silêncio."""
    lotado.setor = setor_destino
    lotado.nome = 'Lotado Renomeado'

    with pytest.raises(ConflitoDominio) as exc_info:
        user_admin.save_model(
            request_de(superusuario), lotado, _FormFake('setor', 'nome'), True
        )

    assert exc_info.value.code == 'remanejamento_com_campos_extras'
    lotado.refresh_from_db()
    assert lotado.setor_id == setor.pk
    assert lotado.nome == 'Lotado'


@pytest.mark.django_db
def test_user_save_model_desativacao_com_setor_recusa_antes_do_remanejamento(
    user_admin, request_de, superusuario, setor, setor_destino, lotado
):
    """`is_active` desmarcado tem precedência: o ramo de desativação vem primeiro."""
    lotado.setor = setor_destino
    lotado.is_active = False

    with pytest.raises(ConflitoDominio) as exc_info:
        user_admin.save_model(
            request_de(superusuario), lotado, _FormFake('is_active', 'setor'), True
        )

    assert exc_info.value.code == 'desativacao_com_campos_extras'
    lotado.refresh_from_db()
    assert lotado.setor_id == setor.pk
    assert lotado.is_active is True


@pytest.mark.django_db
def test_user_save_model_reativacao_com_setor_cai_no_remanejamento(
    user_admin, request_de, superusuario, setor, setor_destino, lotado
):
    """`is_active` marcado não entra no ramo de desativação; sobra o guard novo."""
    lotado.setor = setor_destino

    with pytest.raises(ConflitoDominio) as exc_info:
        user_admin.save_model(
            request_de(superusuario), lotado, _FormFake('is_active', 'setor'), True
        )

    assert exc_info.value.code == 'remanejamento_com_campos_extras'
    lotado.refresh_from_db()
    assert lotado.setor_id == setor.pk


class _ErroPsycopg(Exception):
    """Stand-in da exceção do driver: `_changeform_com_captura_dominio` lê `sqlstate`."""

    def __init__(self, sqlstate):
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


def _operational_error(sqlstate):
    from django.db import OperationalError

    erro = OperationalError('erro de banco')
    erro.__cause__ = _ErroPsycopg(sqlstate)
    return erro


@pytest.mark.django_db
def test_changeform_traduz_deadlock_em_mensagem(
    monkeypatch, client, superusuario, setor, lotado
):
    """`OperationalError` retentável não é `ErroDominio` e viraria HTTP 500."""
    from apps.accounts import admin as admin_module

    def _explode(self, request, obj, form, change):
        raise _operational_error('40P01')

    monkeypatch.setattr(admin_module.UserAdmin, 'save_model', _explode)
    client.force_login(superusuario)

    resposta = client.post(
        reverse('admin:accounts_user_change', args=[lotado.pk]),
        {
            'matricula': lotado.matricula,
            'password': lotado.password,
            'nome': lotado.nome,
            'email': '',
            'setor': str(setor.pk),
            'is_active': 'on',
            'last_login_0': '',
            'last_login_1': '',
            'date_joined_0': '2026-01-01',
            'date_joined_1': '00:00:00',
        },
        follow=True,
    )

    assert resposta.redirect_chain[-1][1] == 302
    erros = [str(m) for m in resposta.context['messages'] if m.level == messages.ERROR]
    assert erros == [
        'A operação não pôde ser concluída por concorrência com outra '
        'alteração de cadastro. Tente novamente.'
    ]


@pytest.mark.django_db
def test_changeform_propaga_operational_error_nao_retentavel(
    monkeypatch, client, superusuario, setor, lotado
):
    """Queda de conexão não é conflito de concorrência — não mascarar como retry."""
    from django.db import OperationalError

    from apps.accounts import admin as admin_module

    def _explode(self, request, obj, form, change):
        raise _operational_error('08006')  # connection_failure

    monkeypatch.setattr(admin_module.UserAdmin, 'save_model', _explode)
    client.force_login(superusuario)

    with pytest.raises(OperationalError):
        client.post(
            reverse('admin:accounts_user_change', args=[lotado.pk]),
            {
                'matricula': lotado.matricula,
                'password': lotado.password,
                'nome': lotado.nome,
                'email': '',
                'setor': str(setor.pk),
                'is_active': 'on',
                'last_login_0': '',
                'last_login_1': '',
                'date_joined_0': '2026-01-01',
                'date_joined_1': '00:00:00',
            },
        )


@pytest.mark.django_db
def test_changeform_traduz_bloqueio_de_remanejamento_em_mensagem(
    client, superusuario, setor, setor_destino, lotado
):
    """Contrato HTTP: o bloqueio vira mensagem, não 500.

    O 302 sozinho não distingue este redirect do de um save bem-sucedido; a
    mensagem exibida é o que prova que a exceção virou retorno ao usuário.
    """
    from django.utils import timezone

    setor.chefe = lotado
    setor.save(update_fields=['chefe'])
    client.force_login(superusuario)

    # `date_joined` usa `show_hidden_initial`, então o Django compara o POST com
    # os inputs ocultos `initial-date_joined_*` — não com o valor do banco. Sem
    # eles o campo entra em `changed_data` e dispara o guard de campos extras em
    # vez do bloqueio que este teste verifica.
    entrada = timezone.localtime(lotado.date_joined)
    data_entrada = entrada.strftime('%Y-%m-%d')
    hora_entrada = entrada.strftime('%H:%M:%S')

    resposta = client.post(
        reverse('admin:accounts_user_change', args=[lotado.pk]),
        {
            'matricula': lotado.matricula,
            'password': lotado.password,
            'nome': lotado.nome,
            'email': '',
            'setor': str(setor_destino.pk),
            'is_active': 'on',
            'last_login_0': '',
            'last_login_1': '',
            'date_joined_0': data_entrada,
            'date_joined_1': hora_entrada,
            'initial-date_joined_0': data_entrada,
            'initial-date_joined_1': hora_entrada,
        },
        follow=True,
    )

    assert resposta.redirect_chain[-1][1] == 302
    avisos = [
        str(m) for m in resposta.context['messages'] if m.level == messages.WARNING
    ]
    assert avisos == [
        f"Usuário '{lotado.nome}' é chefe do setor '{setor.nome}'. "
        'Troque a chefia do setor antes de remanejar a lotação.'
    ]
    lotado.refresh_from_db()
    assert lotado.setor_id == setor.pk
