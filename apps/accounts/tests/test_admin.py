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


# ---------------------------------------------------------------------------
# UserAdmin — senha com hash na criação e troca de senha (issue #217)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_criar_usuario_pelo_admin_grava_hash_e_autentica(client, superusuario, setor):
    """Reprodução da issue: o form do admin gravava o texto digitado cru."""
    from django.contrib.auth.hashers import identify_hasher
    from django.test import Client

    nova_senha = 'SenhaForte@2026'
    client.force_login(superusuario)

    resposta = client.post(
        reverse('admin:accounts_user_add'),
        {
            'matricula': 'NOVO1',
            'nome': 'Usuário Novo',
            'email': '',
            'setor': str(setor.pk),
            'password1': nova_senha,
            'password2': nova_senha,
        },
    )

    assert resposta.status_code == 302, (
        resposta.context['adminform'].form.errors
        if resposta.status_code == 200
        else None
    )
    criado = User.objects.get(matricula='NOVO1')
    identify_hasher(criado.password)  # não levanta -> hash reconhecido
    assert criado.password != nova_senha
    assert criado.check_password(nova_senha)

    # cliente novo e sem sessão: o client acima está autenticado como
    # superusuário, e `redirect_authenticated_user=True` na view de login
    # pularia a autenticação de verdade.
    resposta_login = Client().post(
        reverse('accounts:login'),
        {'username': 'NOVO1', 'password': nova_senha},
    )
    assert resposta_login.status_code == 302
    assert resposta_login.wsgi_request.user.is_authenticated
    assert resposta_login.wsgi_request.user.matricula == 'NOVO1'


@pytest.mark.django_db
def test_criar_usuario_pelo_admin_com_confirmacao_divergente_nao_salva(
    client, superusuario
):
    client.force_login(superusuario)

    resposta = client.post(
        reverse('admin:accounts_user_add'),
        {
            'matricula': 'NOVO2',
            'nome': 'Usuário Novo',
            'email': '',
            'setor': '',
            'password1': 'SenhaForte@2026',
            'password2': 'outra-coisa-qualquer',
        },
    )

    assert resposta.status_code == 200
    assert not User.objects.filter(matricula='NOVO2').exists()


@pytest.mark.django_db
def test_edicao_de_usuario_nao_oferece_input_de_texto_para_senha(
    client, superusuario, lotado
):
    client.force_login(superusuario)

    resposta = client.get(reverse('admin:accounts_user_change', args=[lotado.pk]))
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'name="password1"' not in conteudo
    assert 'name="password2"' not in conteudo
    assert '<input type="text" name="password"' not in conteudo
    assert '<input type="password" name="password"' not in conteudo


@pytest.mark.django_db
def test_trocar_senha_pelo_admin_atualiza_hash_e_autentica(
    client, superusuario, lotado
):
    from django.test import Client

    client.force_login(superusuario)
    nova_senha = 'OutraSenhaForte@2026'
    url_troca_senha = reverse('admin:auth_user_password_change', args=[lotado.pk])

    resposta_tela = client.get(url_troca_senha)
    assert resposta_tela.status_code == 200
    assert 'name="password1"' in resposta_tela.content.decode()

    resposta = client.post(
        url_troca_senha,
        {'password1': nova_senha, 'password2': nova_senha},
    )

    assert resposta.status_code == 302
    lotado.refresh_from_db()
    assert lotado.check_password(nova_senha)
    assert not lotado.check_password(SENHA)

    cliente_novo = Client()
    resposta_antiga = cliente_novo.post(
        reverse('accounts:login'),
        {'username': lotado.matricula, 'password': SENHA},
    )
    assert resposta_antiga.status_code == 200
    assert not resposta_antiga.wsgi_request.user.is_authenticated

    resposta_nova = cliente_novo.post(
        reverse('accounts:login'),
        {'username': lotado.matricula, 'password': nova_senha},
    )
    assert resposta_nova.status_code == 302
    assert resposta_nova.wsgi_request.user.is_authenticated


@pytest.mark.django_db
def test_troca_de_senha_nao_oferece_desativar_autenticacao_por_senha(
    client, superusuario, lotado
):
    """O template do Django 6 mostra `unset-password` a quem tem senha utilizável.

    `AdminPasswordChangeForm` sempre grava a senha digitada, então o botão
    prometeria desativar a autenticação e, no POST, trocaria a senha.
    """
    client.force_login(superusuario)

    resposta = client.get(reverse('admin:auth_user_password_change', args=[lotado.pk]))
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert lotado.has_usable_password()
    assert 'name="set-password"' in conteudo
    assert 'name="password1"' in conteudo
    assert 'name="password2"' in conteudo
    assert 'unset-password' not in conteudo
    assert 'usable_password' not in conteudo


@pytest.mark.django_db
def test_changeform_traduz_erro_operacional_na_criacao_em_mensagem(
    monkeypatch, client, superusuario
):
    """A criação (`add_view`) também passa por `_changeform_com_captura_dominio`.

    Sem isso, um `OperationalError` retentável durante `save_model` na
    criação viraria HTTP 500 em vez de mensagem — o mesmo contrato já
    coberto para edição em `test_changeform_traduz_deadlock_em_mensagem`.
    """
    from apps.accounts import admin as admin_module

    def _explode(self, request, obj, form, change):
        raise _operational_error('40P01')

    monkeypatch.setattr(admin_module.UserAdmin, 'save_model', _explode)
    client.force_login(superusuario)

    resposta = client.post(
        reverse('admin:accounts_user_add'),
        {
            'matricula': 'NOVO3',
            'nome': 'Usuário Novo',
            'email': '',
            'setor': '',
            'password1': 'SenhaForte@2026',
            'password2': 'SenhaForte@2026',
        },
        follow=True,
    )

    assert resposta.redirect_chain[-1][1] == 302
    erros = [str(m) for m in resposta.context['messages'] if m.level == messages.ERROR]
    assert erros == [
        'A operação não pôde ser concluída por concorrência com outra '
        'alteração de cadastro. Tente novamente.'
    ]
    assert not User.objects.filter(matricula='NOVO3').exists()
