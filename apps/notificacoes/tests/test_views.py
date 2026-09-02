"""Testes de views de notificações (ADR-0010)."""

import pytest
from django.urls import reverse

from apps.notificacoes.models import Notificacao, TipoNotificacao
from apps.requisicoes.models import EstadoRequisicao, Requisicao


@pytest.fixture
def client_logado(client, solicitante):
    client.force_login(solicitante)
    return client


@pytest.mark.django_db
def test_lista_notificacoes_requer_login(client):
    resp = client.get('/notificacoes/')
    assert resp.status_code == 302
    assert '/login/' in resp['Location']


@pytest.mark.django_db
def test_lista_notificacoes_retorna_200(client_logado):
    resp = client_logado.get('/notificacoes/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_lista_notificacoes_exibe_proprias(
    client_logado, solicitante, outro_solicitante
):
    n_propria = Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.AUTORIZACAO,
        requisicao_id=1,
    )
    Notificacao.objects.create(
        destinatario=outro_solicitante,
        tipo=TipoNotificacao.RECUSA,
        requisicao_id=2,
    )
    resp = client_logado.get('/notificacoes/')
    assert resp.status_code == 200
    notifs = resp.context['notificacoes']
    pks = [n.pk for n in notifs]
    assert n_propria.pk in pks
    assert all(n.destinatario_id == solicitante.pk for n in notifs)


@pytest.mark.django_db
def test_lista_notificacoes_exibe_numero_publico_e_link(
    client_logado, solicitante, setor_obras
):
    requisicao = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-000042',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.AUTORIZACAO,
        requisicao_id=requisicao.pk,
    )
    resp = client_logado.get('/notificacoes/')
    html = resp.content.decode('utf-8')
    assert 'REQ-2026-000042' in html
    assert f'Requisição #{requisicao.pk}' not in html
    assert reverse('requisicoes:detalhe', kwargs={'pk': requisicao.pk}) in html


@pytest.mark.django_db
def test_lista_notificacoes_id_orfao_nao_promete_destino(client_logado, solicitante):
    """Antes o cartão dizia "Rascunho" e linkava — para um detalhe que dá 404.

    `requisicao_id` é `IntegerField` solto, sem FK: pelo valor do campo um id
    órfão é idêntico a um rascunho, e o fallback comum apagava a diferença.
    """
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.ATENDIMENTO,
        requisicao_id=999999,
    )
    resp = client_logado.get('/notificacoes/')
    assert resp.status_code == 200
    html = resp.content.decode('utf-8')

    assert 'Rascunho' not in html
    assert 'Ver detalhes' not in html
    assert reverse('requisicoes:detalhe', kwargs={'pk': 999999}) not in html
    # A notícia continua legível: o que some é a promessa de destino.
    assert 'Sua requisição foi atendida' in html


@pytest.mark.django_db
def test_lista_notificacoes_rascunho_real_mostra_fallback(
    client_logado, solicitante, setor_obras
):
    requisicao = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.ATENDIMENTO,
        requisicao_id=requisicao.pk,
    )
    resp = client_logado.get('/notificacoes/')
    assert resp.status_code == 200
    html = resp.content.decode('utf-8')
    assert 'Rascunho' in html


@pytest.mark.django_db
def test_lista_notificacoes_sem_requisicao_preserva_altura_da_linha(
    client_logado, solicitante
):
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.ATENDIMENTO,
        requisicao_id=None,
    )
    resp = client_logado.get('/notificacoes/')
    html = resp.content.decode('utf-8')
    # Sem requisição não há o par `Requisição: <número>` nem link — o cartão
    # simplesmente não renderiza a `<dl>`. O `&nbsp;` que segurava a altura da
    # linha morreu junto com a lista de linhas: em grade de cartões a altura
    # vem do `stretch` da própria linha da grade (DESIGN.md, issue #160).
    assert 'Requisição:' not in html
    # Sem `requisicao_id` o título não vira link, então o cartão não tem alvo.
    # O `(?![-\w\]:])` separa a marcação real das ocorrências dentro dos
    # seletores `has-[a[data-cartao-link]]` que o chrome de cartão sempre emite
    # — mesmo recorte do guarda em `test_components.py`.
    import re

    assert not re.search(r'data-cartao-link(?![-\w\]:])', html)


@pytest.mark.django_db
def test_marcar_lida_marca_notificacao(client_logado, notificacao_nao_lida):
    resp = client_logado.post(f'/notificacoes/{notificacao_nao_lida.pk}/lida/')
    assert resp.status_code in (200, 302, 204)
    notificacao_nao_lida.refresh_from_db()
    assert notificacao_nao_lida.lida is True


@pytest.mark.django_db
def test_marcar_lida_outro_usuario_retorna_404(
    client, outro_solicitante, notificacao_nao_lida
):
    """Query escopada por destinatario — notificação alheia não existe para este usuário."""
    client.force_login(outro_solicitante)
    resp = client.post(f'/notificacoes/{notificacao_nao_lida.pk}/lida/')
    assert resp.status_code == 404
    notificacao_nao_lida.refresh_from_db()
    assert notificacao_nao_lida.lida is False


@pytest.mark.django_db
def test_marcar_todas_lidas(client_logado, solicitante):
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.AUTORIZACAO,
        requisicao_id=10,
    )
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.RECUSA,
        requisicao_id=11,
    )
    resp = client_logado.post('/notificacoes/marcar-todas-lidas/')
    assert resp.status_code in (200, 302, 204)
    assert Notificacao.objects.filter(destinatario=solicitante, lida=False).count() == 0


@pytest.mark.django_db
def test_badge_reflete_contagem_nao_lidas(client_logado, solicitante):
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.AUTORIZACAO,
        requisicao_id=20,
        lida=False,
    )
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.RECUSA,
        requisicao_id=21,
        lida=True,
    )
    resp = client_logado.get('/notificacoes/')
    assert resp.context['notificacoes_nao_lidas'] == 1


@pytest.mark.django_db
def test_lista_exibe_rotulo_e_link_de_envio_autorizacao(
    client, chefe_obras, solicitante, setor_obras
):
    """Rótulo PT-BR e link para o detalhe, sem edição de template.

    Substitui a edição de `lista.html`: o template já usa
    `get_tipo_display` genérico. Falha se o membro sumir, se o rótulo mudar,
    ou se alguém trocar o display genérico por um `if` por tipo que esqueça
    o membro novo.
    """
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-000108',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    Notificacao.objects.create(
        destinatario=chefe_obras,
        tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
        requisicao_id=req.pk,
    )
    client.force_login(chefe_obras)

    resp = client.get(reverse('notificacoes:lista'))
    corpo = resp.content.decode()

    assert resp.status_code == 200
    # O título é o DESFECHO, não o rótulo do tipo: "Envio para autorização" é a
    # categoria do aviso, não a notícia. O guarda contra esquecer um membro novo
    # é `test_todo_tipo_de_notificacao_tem_desfecho`, que lê o enum.
    assert 'Uma requisição aguarda sua autorização' in corpo
    assert reverse('requisicoes:detalhe', kwargs={'pk': req.pk}) in corpo
    assert 'REQ-2026-000108' in corpo


@pytest.mark.django_db
def test_lista_exibe_rotulo_e_link_de_separacao_retirada(
    client, outro_solicitante, solicitante, setor_obras
):
    """Rótulo PT-BR e link para o detalhe, sem edição de template.

    Falha se o membro sumir, se o rótulo mudar, ou se alguém trocar o
    `get_tipo_display` genérico de `lista.html` por um `if` por tipo que
    esqueça o membro novo.
    """
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.PRONTA_PARA_RETIRADA,
        numero_publico='REQ-2026-000109',
        criador=solicitante,
        beneficiario=outro_solicitante,
        setor_beneficiario=setor_obras,
    )
    Notificacao.objects.create(
        destinatario=outro_solicitante,
        tipo=TipoNotificacao.SEPARACAO_RETIRADA,
        requisicao_id=req.pk,
    )
    client.force_login(outro_solicitante)

    resp = client.get(reverse('notificacoes:lista'))
    corpo = resp.content.decode()

    assert resp.status_code == 200
    # O título é o DESFECHO, não o rótulo do tipo. O guarda contra esquecer um
    # membro novo é `test_todo_tipo_de_notificacao_tem_desfecho`, que lê o enum.
    assert 'Sua requisição está pronta para retirada' in corpo
    assert reverse('requisicoes:detalhe', kwargs={'pk': req.pk}) in corpo
    assert 'REQ-2026-000109' in corpo


class TestListaNotificacoesEtapa8:
    """Achados do passe de regressão da Etapa 8."""

    URL = '/notificacoes/'

    def test_timestamp_nao_usa_o_cinza_apagado(
        self, client, solicitante, notificacao_nao_lida
    ):
        """`text-disabled` (slate-400) mede 2,63:1 no branco e reprova o 4,5:1
        da WCAG 1.4.3. O mesmo achado já tinha sido corrigido nos dois
        autocompletes e no nome do arquivo do preview SCPI — este era o último
        sobrevivente, e aqui a data é o que ordena a lista.
        """
        client.force_login(solicitante)
        html = client.get(self.URL).content.decode('utf-8')
        # `text-text-disabled` segue legítimo em ícone decorativo (`aria-hidden`)
        # da side nav; o que não pode é carregar texto.
        data = notificacao_nao_lida.criado_em.strftime('%d/%m/%Y')
        linha = next(
            linha for linha in html.splitlines() if data in linha and '<p' in linha
        )
        assert 'text-text-disabled' not in linha
        # `text-secondary`, e não o cinza de metadado: a linha não lida veste
        # `bg-primary-subtle`, onde `text-tertiary` mede 4,38:1 e reprova.
        assert 'text-text-secondary' in linha

    def test_link_da_requisicao_nao_se_confunde_com_metadado(
        self, client, solicitante, notificacao_nao_lida
    ):
        """O link vinha em `text-xs text-text-tertiary hover:underline`, ou seja,
        tamanho, peso e cor idênticos ao carimbo de data logo abaixo: nada o
        distinguia de texto comum em repouso, enquanto `Marcar como lida` era o
        único azul da linha. E no fundo `bg-primary-subtle` da linha não lida o
        cinza reprova a AA (4,38:1)."""
        import re

        client.force_login(solicitante)
        html = client.get(self.URL).content.decode('utf-8')
        alvo = f'/requisicoes/{notificacao_nao_lida.requisicao_id}/'
        ancora = next(
            a for a in re.findall(r'<a\b[^>]*>', html, flags=re.S) if alvo in a
        )
        # A lista virou cartões: o link deixou de ser um texto de 12px cinza
        # perdido no meio da linha e passou a ser o TÍTULO, com o cartão inteiro
        # como alvo. Nada de cinza de metadado nele, e a afordância explícita.
        assert 'data-cartao-link' in ancora
        assert 'text-text-tertiary' not in ancora
        assert 'Ver detalhes' in html

    def test_todo_tipo_de_notificacao_tem_desfecho(self):
        """O que os testes por tipo protegiam antes, agora lido do enum.

        O título saiu de `get_tipo_display` para um mapa por tipo, e um mapa é
        exatamente onde um membro novo se perde em silêncio — o aviso voltaria a
        exibir o rótulo da categoria sem ninguém notar.
        """
        from apps.notificacoes.models import TipoNotificacao
        from apps.notificacoes.presentation import DESFECHO_POR_TIPO

        faltando = [t for t in TipoNotificacao if t not in DESFECHO_POR_TIPO]
        assert faltando == [], (
            f'TipoNotificacao sem desfecho em presentation.py: {faltando}'
        )

    def test_titulo_do_cartao_e_o_desfecho_nao_a_categoria(
        self, client, solicitante, notificacao_nao_lida
    ):
        """ "Autorização" é a categoria do aviso e não diz se foi autorizada."""
        client.force_login(solicitante)
        html = client.get(self.URL).content.decode('utf-8')
        assert 'Sua requisição foi autorizada' in html

    def test_lista_vazia_usa_o_componente_de_estado_vazio(self, client, solicitante):
        """Frase cinza solta era o estado vazio fora do componente; as outras
        listagens usam `empty_state.html`, que tem borda tracejada e ícone."""
        client.force_login(solicitante)
        html = client.get(self.URL).content.decode('utf-8')
        assert 'Nenhuma notificação' in html
        assert 'border-dashed' in html
