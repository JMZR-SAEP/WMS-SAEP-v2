"""Testes de views de notificações (ADR-0010)."""

import pytest
from django.urls import reverse

from apps.notificacoes.models import Notificacao, TipoNotificacao
from apps.requisicoes.models import EstadoRequisicao, Requisicao
from apps.requisicoes.selectors import fila_autorizacao


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
def test_badge_do_sino_conta_pendencia_e_ignora_aviso_informativo(
    client, chefe_obras, solicitante, setor_obras
):
    """O sino conta o que ainda pede ação, não o histórico de avisos (#175).

    Duas notificações do mesmo tipo para o mesmo chefe: uma sobre requisição
    ainda na fila, outra sobre requisição já atendida. A segunda não pede mais
    nada — quem decide isso é `acoes_disponiveis`, não o tipo congelado.
    """
    na_fila = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-000201',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    ja_atendida = Requisicao.objects.create(
        estado=EstadoRequisicao.ATENDIDA,
        numero_publico='REQ-2026-000202',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    for requisicao in (na_fila, ja_atendida):
        Notificacao.objects.create(
            destinatario=chefe_obras,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=requisicao.pk,
            lida=False,
        )
    # Aviso informativo: narra um desfecho e nunca pediu ação a quem o recebeu.
    Notificacao.objects.create(
        destinatario=chefe_obras,
        tipo=TipoNotificacao.ATENDIMENTO,
        requisicao_id=ja_atendida.pk,
        lida=False,
    )
    client.force_login(chefe_obras)

    resp = client.get('/notificacoes/')

    assert resp.context['notificacoes_pendentes'] == 1


@pytest.mark.django_db
def test_contagem_do_sino_bate_com_a_fila_de_autorizacao(
    client, chefe_obras, solicitante, setor_obras
):
    """A conta do sino e a da fila passam a poder ser conferidas uma contra a outra.

    Era o sintoma da #175: 14 no sino, 4 na Fila de autorização, na mesma tela.
    """
    for indice, estado in enumerate(
        [
            EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
            EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
            EstadoRequisicao.ATENDIDA,
            EstadoRequisicao.CANCELADA,
            EstadoRequisicao.RECUSADA,
        ]
    ):
        requisicao = Requisicao.objects.create(
            estado=estado,
            numero_publico=f'REQ-2026-00021{indice}',
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_obras,
        )
        Notificacao.objects.create(
            destinatario=chefe_obras,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=requisicao.pk,
        )
    client.force_login(chefe_obras)

    resp = client.get('/notificacoes/')

    assert (
        resp.context['notificacoes_pendentes']
        == fila_autorizacao(chefe_obras.pk).count()
    )
    assert resp.context['notificacoes_pendentes'] == 2


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
    # é `test_todo_tipo_de_notificacao_tem_evento`, que lê o enum.
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
    # membro novo é `test_todo_tipo_de_notificacao_tem_evento`, que lê o enum.
    # Evento no passado + estado atual: o registro é do que aconteceu, e quem
    # diz como as coisas estão agora é a segunda metade do título.
    assert 'Sua requisição foi separada para retirada · Pronta para retirada' in corpo
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

    def test_todo_tipo_de_notificacao_tem_evento(self):
        """O que os testes por tipo protegiam antes, agora lido do enum.

        O título saiu de `get_tipo_display` para um mapa por tipo, e um mapa é
        exatamente onde um membro novo se perde em silêncio — o aviso voltaria a
        exibir o rótulo da categoria sem ninguém notar.
        """
        from apps.notificacoes.models import TipoNotificacao
        from apps.notificacoes.presentation import EVENTO_POR_TIPO

        faltando = [t for t in TipoNotificacao if t not in EVENTO_POR_TIPO]
        assert faltando == [], (
            f'TipoNotificacao sem evento em presentation.py: {faltando}'
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


class TestCartaoReconsultaOEstado:
    """A notificação afirmava um estado que nunca reconsultava (issue #175)."""

    URL = '/notificacoes/'

    def _requisicao(self, estado, solicitante, setor_obras, numero):
        return Requisicao.objects.create(
            estado=estado,
            numero_publico=numero,
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_obras,
        )

    @pytest.mark.django_db
    def test_titulo_e_evento_mais_estado_atual(
        self, client, chefe_obras, solicitante, setor_obras
    ):
        """O aviso é de quando a requisição entrou na fila; ela já foi atendida."""
        requisicao = self._requisicao(
            EstadoRequisicao.ATENDIDA, solicitante, setor_obras, 'REQ-2026-000301'
        )
        Notificacao.objects.create(
            destinatario=chefe_obras,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=requisicao.pk,
        )
        client.force_login(chefe_obras)

        html = client.get(self.URL).content.decode('utf-8')

        assert 'Aguardava sua autorização · Atendida' in html
        # O presente do indicativo é uma cobrança, e aqui não há o que cobrar.
        assert 'Uma requisição aguarda sua autorização' not in html

    @pytest.mark.django_db
    def test_titulo_cobra_enquanto_a_acao_ainda_cabe(
        self, client, chefe_obras, solicitante, setor_obras
    ):
        requisicao = self._requisicao(
            EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
            solicitante,
            setor_obras,
            'REQ-2026-000302',
        )
        Notificacao.objects.create(
            destinatario=chefe_obras,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=requisicao.pk,
        )
        client.force_login(chefe_obras)

        html = client.get(self.URL).content.decode('utf-8')

        assert 'Uma requisição aguarda sua autorização · Aguardando autorização' in html
        assert 'Resolvida' not in html

    @pytest.mark.django_db
    def test_cartao_carimba_o_estado_pelo_partial_de_dominio(
        self, client, chefe_obras, solicitante, setor_obras
    ):
        """Mesmo `_estado_badge.html` das filas e do detalhe.

        O `DESIGN.md` proíbe ensinar semântica de domínio ao componente global:
        um segundo mapa estado -> cor aqui seria a segunda fonte da mesma
        verdade. `amber-strong` é o carimbo de `aguardando_autorizacao` lá.
        """
        requisicao = self._requisicao(
            EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
            solicitante,
            setor_obras,
            'REQ-2026-000303',
        )
        Notificacao.objects.create(
            destinatario=chefe_obras,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=requisicao.pk,
        )
        client.force_login(chefe_obras)

        html = client.get(self.URL).content.decode('utf-8')

        assert 'Estado: ' in html
        assert 'bg-warning-muted-strong' in html

    @pytest.mark.django_db
    def test_notificacao_resolvida_continua_visivel_marcada(
        self, client, chefe_obras, solicitante, setor_obras
    ):
        """A decisão de produto da issue: fica na lista, marcada como resolvida.

        `/notificacoes/` é o diário do que aconteceu com as minhas requisições,
        não uma caixa de entrada — a chamada à ação já tem duas telas dedicadas.
        """
        requisicao = self._requisicao(
            EstadoRequisicao.RECUSADA, solicitante, setor_obras, 'REQ-2026-000304'
        )
        Notificacao.objects.create(
            destinatario=chefe_obras,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=requisicao.pk,
        )
        client.force_login(chefe_obras)

        resp = client.get(self.URL)
        html = resp.content.decode('utf-8')

        assert len(resp.context['notificacoes']) == 1
        assert 'REQ-2026-000304' in html
        assert 'Resolvida' in html
        assert resp.context['notificacoes_pendentes'] == 0

    @pytest.mark.django_db
    def test_aviso_sem_link_nao_ganha_carimbo_de_estado(
        self, client_logado, solicitante
    ):
        """Sem requisição não há estado a afirmar nem pendência a resolver."""
        Notificacao.objects.create(
            destinatario=solicitante,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=None,
        )

        resp = client_logado.get(self.URL)
        html = resp.content.decode('utf-8')

        assert 'Estado: ' not in html
        assert 'Resolvida' not in html
        assert 'Ver detalhes' not in html
        assert resp.context['notificacoes_pendentes'] == 0
