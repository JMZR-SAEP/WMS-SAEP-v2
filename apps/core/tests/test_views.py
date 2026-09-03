"""Testes de integração para o dispatcher pós-login (apps/core/views.home)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.models import Setor, SetorClassificacao, VinculoAuxiliar
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


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


# ---------------------------------------------------------------------------
# Páginas de erro (Etapa 8)
# ---------------------------------------------------------------------------


class TestPaginasDeErro:
    """403/404/500 eram o HTML cru do Django — sem chrome e sem volta.

    O 403 do produto é rotina, não incidente: papel efetivo é derivado do ator
    diante de cada registro, então uma tela visível a um papel pode apontar para
    uma ação que só outro executa.
    """

    def test_403_e_404_trazem_codigo_titulo_e_saida(self, client, django_user_model):
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        usuario = django_user_model.objects.create_user(
            matricula='ERR001', nome='Usuário Erro', password='x'
        )
        request = RequestFactory().get('/rota-inexistente/')
        request.user = usuario

        for template, codigo in (('403.html', '403'), ('404.html', '404')):
            html = render_to_string(template, {}, request=request)
            assert f'Erro {codigo}' in html
            assert 'Ir para o início' in html
            assert '<h1' in html

    def test_500_nao_depende_de_context_processor(self):
        """`django.views.defaults.server_error` renderiza com contexto vazio e
        sem context processors: `user`, `{% url %}` e as tags da barra não
        existem ali. Renderizar sem request é o teste."""
        from django.template.loader import render_to_string

        html = render_to_string('500.html', {})
        assert 'Erro 500' in html
        assert 'Ir para o início' in html
        assert 'app-bar' not in html


class TestEstaticosComHash:
    """`app.css` e os dez arquivos de JS eram servidos sempre na mesma URL.

    O navegador que já os tinha em cache continuava com a versão antiga depois
    do deploy, e o defeito que aparecia era o pior tipo: template novo com CSS
    velho, ou um `x-data` referenciando uma factory Alpine que o JS em cache não
    registra — `saldoLinha is not defined` no console, com a tela renderizando
    quase certa. Aconteceu duas vezes durante a própria Etapa 8.
    """

    def test_o_piloto_usa_storage_com_hash(self):
        from apps.core.staticfiles import EstaticosComHash

        assert issubclass(EstaticosComHash, ManifestStaticFilesStorage)

    def test_a_configuracao_do_piloto_seleciona_esse_storage(self, monkeypatch):
        """A herança da classe não prova que o piloto a escolhe.

        Sem esta asserção, apagar `STORAGES` de `config/settings/piloto.py`
        deixava a suíte verde e o deploy voltava a servir `app.css` e os dez
        arquivos de JS sempre na mesma URL — que é o defeito inteiro.

        O módulo é importado à parte porque as guardas do piloto recusam o boot
        sem hosts, origens e Postgres; os valores abaixo só as satisfazem.
        """
        import importlib

        for chave, valor in {
            'ALLOWED_HOSTS': 'piloto.exemplo',
            'CSRF_TRUSTED_ORIGINS': 'https://piloto.exemplo',
            'DATABASE_URL': 'postgres://usuario:senha@localhost:5432/wms',
        }.items():
            monkeypatch.setenv(chave, valor)

        piloto = importlib.reload(importlib.import_module('config.settings.piloto'))

        assert (
            piloto.STORAGES['staticfiles']['BACKEND']
            == 'apps.core.staticfiles.EstaticosComHash'
        )

    def test_a_fonte_do_tailwind_fica_fora_da_reescrita(self):
        """`input.css` começa com `@import "tailwindcss"`, que não é caminho de
        arquivo: o `collectstatic` morria com
        `The file 'core/css/tailwindcss' could not be found`. O artefato servido
        é o `app.css` compilado; a fonte só é coletada porque vive dentro de
        `static/`, onde o CLI do Tailwind a aponta.
        """
        from apps.core.staticfiles import EstaticosComHash

        assert 'core/css/input.css' in EstaticosComHash.NAO_REESCREVER

    def test_o_artefato_servido_continua_sendo_reescrito(self):
        from apps.core.staticfiles import EstaticosComHash

        assert 'core/css/app.css' not in EstaticosComHash.NAO_REESCREVER
