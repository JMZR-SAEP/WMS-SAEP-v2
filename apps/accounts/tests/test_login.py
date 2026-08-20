"""Testes da fatia de autenticação por matrícula."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.forms import MatriculaAuthenticationForm
from apps.accounts.models import User

SENHA = 'senha-forte-123'


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        matricula='OP-001',
        password=SENHA,
        nome='Operador Teste',
    )


def test_get_tela_login(client):
    resposta = client.get(reverse('accounts:login'))
    assert resposta.status_code == 200
    assert 'accounts/login.html' in {t.name for t in resposta.templates}


def test_tela_login_exibe_identidade_e_campos_acessiveis(client):
    resposta = client.get(reverse('accounts:login'))
    conteudo = resposta.content.decode()

    assert 'WMS SAEP' in conteudo
    assert 'Sistema interno de gestão de materiais' in conteudo
    assert 'Acesse com sua matrícula e senha.' in conteudo
    assert 'Acesso restrito a funcionários autorizados.' in conteudo
    assert 'for="id_username"' in conteudo
    assert 'for="id_password"' in conteudo
    assert 'autofocus' in conteudo
    assert 'role="alert"' not in conteudo
    assert 'min-h-screen' in conteudo
    assert 'max-w-5xl' not in conteudo
    assert '<header' not in conteudo


def test_login_valido_por_matricula(client, usuario):
    resposta = client.post(
        reverse('accounts:login'),
        {'username': 'OP-001', 'password': SENHA},
    )
    assert resposta.status_code == 302
    assert resposta.wsgi_request.user.is_authenticated


def test_login_preserva_next_no_formulario_e_redirect(client, usuario):
    resposta_get = client.get(
        reverse('accounts:login'), {'next': '/requisicoes/minhas/'}
    )
    conteudo = resposta_get.content.decode()

    assert 'name="next" value="/requisicoes/minhas/"' in conteudo

    resposta_post = client.post(
        reverse('accounts:login'),
        {
            'username': 'OP-001',
            'password': SENHA,
            'next': '/requisicoes/minhas/',
        },
    )
    assert resposta_post.status_code == 302
    assert resposta_post['Location'] == '/requisicoes/minhas/'


def test_login_senha_invalida(client, usuario):
    resposta = client.post(
        reverse('accounts:login'),
        {'username': 'OP-001', 'password': 'errada'},
    )
    assert resposta.status_code == 200
    assert not resposta.wsgi_request.user.is_authenticated


def test_login_senha_invalida_exibe_erro_inline(client, usuario):
    resposta = client.post(
        reverse('accounts:login'),
        {'username': 'OP-001', 'password': 'errada'},
    )
    conteudo = resposta.content.decode()

    assert 'role="alert"' in conteudo
    assert 'senha corretos' in conteudo
    assert 'aria-invalid="true"' in conteudo


def test_login_senha_invalida_erro_usa_components_alert(client, usuario):
    resposta = client.post(
        reverse('accounts:login'),
        {'username': 'OP-001', 'password': 'errada'},
    )
    conteudo = resposta.content.decode()

    assert 'id="login-error"' in conteudo
    assert 'border-danger-border' in conteudo
    assert 'bg-danger-subtle' in conteudo
    assert conteudo.count('aria-live') == 0


class FormularioComErroDeCampoEGlobal(MatriculaAuthenticationForm):
    def clean(self):
        raise ValidationError('Erro global de autenticação.')


def test_login_marca_os_dois_campos_quando_a_falha_e_do_par(rf):
    """Credencial recusada não diz qual das duas errou — os dois são suspeitos.

    É a única marcação de erro que continua sendo do Form depois da unificação:
    nenhum dos dois campos tem `errors` (por decisão de segurança), então o
    components/form_field.html, que só olha o campo, não marcaria nenhum.

    A fiação de `aria-describedby` que este teste guardava saiu daqui: os ids
    de erro inline são emitidos por components/field_error.html e costurados
    por components/form_field.html — mantê-los também no Form era a mesma
    decisão em dois arquivos. O sumário (`login-error`) deixou de entrar no
    `aria-describedby` dos campos de propósito: ele se anuncia por
    `role="alert"`, e apontar cada campo para a caixa inteira faria o leitor de
    tela reler a lista de problemas a cada campo focado.

    Os dois campos vão preenchidos de propósito. Com eles vazios o teste era
    vácuo: o `BoundField` do Django já emite `aria-invalid` sozinho quando o
    campo tem `errors`, então a asserção passava mesmo que o Form não marcasse
    nada. Preenchidos, os campos validam, `errors` fica vazio, e o único que
    pode ter escrito o atributo é o `full_clean()` daqui.
    """
    form = FormularioComErroDeCampoEGlobal(
        request=rf.post(reverse('accounts:login')),
        data={'username': 'OP-001', 'password': 'qualquer-senha'},
    )

    form.is_valid()

    assert not form['username'].errors
    assert not form['password'].errors
    assert form.non_field_errors()

    assert 'aria-invalid="true"' in str(form['username'])
    assert 'aria-invalid="true"' in str(form['password'])


def test_login_form_nao_valida_ao_ser_construido(rf):
    """Instanciar o formulário não pode disparar `authenticate()`.

    A marcação de suspeita vivia no `__init__`, e ler `non_field_errors()` ali
    chama `full_clean()` antes da hora. No `AuthenticationForm` isso significa
    consulta ao banco, hash de senha e o sinal `user_login_failed` que o
    django-axes conta — por construir o objeto, sem ninguém ter pedido validação.
    """
    form = MatriculaAuthenticationForm(
        request=rf.post(reverse('accounts:login')),
        data={'username': 'OP-001', 'password': 'errada'},
    )

    assert form._errors is None, (
        'o formulário validou dentro do __init__ — `authenticate()` roda por '
        'instanciação, e o axes conta a tentativa'
    )


@pytest.mark.django_db
def test_login_costura_o_erro_inline_pelo_componente(client, usuario):
    """O `aria-describedby` do campo aponta para o erro que o componente emitiu.

    Campo vazio é erro *de campo* — este é o caminho em que o
    components/form_field.html assume a fiação inteira.
    """
    resposta = client.post(reverse('accounts:login'), {'username': '', 'password': ''})
    conteudo = resposta.content.decode()

    assert 'aria-describedby="id_username-erro"' in conteudo
    assert 'id="id_username-erro"' in conteudo


@pytest.mark.django_db
def test_login_erro_de_credencial_leva_ao_campo_matricula(client, usuario):
    """Credencial recusada não pertence a campo nenhum — mas tem por onde começar.

    Sem `ancora_geral` a frase ficaria como texto solto no sumário: a caixa
    anunciava a falha e não oferecia nenhum caminho de volta ao formulário. O
    alvo é a matrícula porque é o primeiro campo a reconferir.
    """
    resposta = client.post(
        reverse('accounts:login'),
        {'username': 'OP-001', 'password': 'errada'},
    )
    conteudo = resposta.content.decode()

    assert 'href="#id_username"' in conteudo
    assert 'id="id_username"' in conteudo


def test_login_usuario_inativo(client, usuario):
    usuario.is_active = False
    usuario.save()
    resposta = client.post(
        reverse('accounts:login'),
        {'username': 'OP-001', 'password': SENHA},
    )
    assert resposta.status_code == 200
    assert not resposta.wsgi_request.user.is_authenticated


def test_logout(client, usuario):
    client.force_login(usuario)
    resposta = client.post(reverse('accounts:logout'))
    assert resposta.status_code == 302
    assert not resposta.wsgi_request.user.is_authenticated
