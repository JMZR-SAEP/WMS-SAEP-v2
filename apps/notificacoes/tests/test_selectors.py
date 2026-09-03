"""Testes unitários para seletores de notificações."""

import pytest

from apps.notificacoes.models import Notificacao, TipoNotificacao
from apps.notificacoes.selectors import (
    contagem_de_notificacoes_pendentes,
    notificacoes_para_exibicao,
    requisicoes_referidas,
)
from apps.requisicoes.models import EstadoRequisicao, Requisicao


def test_requisicoes_referidas_lista_vazia_retorna_dict_vazio():
    assert requisicoes_referidas([]) == {}


@pytest.mark.django_db
def test_requisicoes_referidas_resolve_ids_existentes(solicitante, setor_obras):
    requisicao = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-000050',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    resultado = requisicoes_referidas([requisicao.pk])
    assert list(resultado) == [requisicao.pk]
    assert resultado[requisicao.pk].numero_publico == 'REQ-2026-000050'


@pytest.mark.django_db
def test_requisicoes_referidas_ids_duplicados_nao_gera_erro(solicitante, setor_obras):
    requisicao = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-000051',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    resultado = requisicoes_referidas([requisicao.pk, requisicao.pk])
    assert list(resultado) == [requisicao.pk]


@pytest.mark.django_db
def test_requisicoes_referidas_mistura_existente_e_inexistente(
    solicitante, setor_obras
):
    requisicao = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-000052',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    resultado = requisicoes_referidas([requisicao.pk, 999999])
    # Id órfão simplesmente não aparece: é assim que o chamador o distingue de
    # um rascunho, que existe e só não tem número.
    assert list(resultado) == [requisicao.pk]


@pytest.mark.django_db
def test_requisicoes_referidas_rascunho_existe_sem_numero(solicitante, setor_obras):
    rascunho = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    resultado = requisicoes_referidas([rascunho.pk])
    assert resultado[rascunho.pk].numero_publico is None


@pytest.mark.django_db
def test_notificacoes_para_exibicao_decora_e_aplica_fallback(solicitante, setor_obras):
    requisicao = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-000060',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.AUTORIZACAO,
        requisicao_id=requisicao.pk,
    )
    rascunho = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.ATENDIMENTO,
        requisicao_id=rascunho.pk,
    )
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.ATENDIMENTO,
        requisicao_id=999999,
    )
    resultado = notificacoes_para_exibicao(solicitante.pk)
    exibicoes = {n.requisicao_id: n.numero_publico_exibicao for n in resultado}
    # Rascunho existe e ainda não tem número; id órfão não tem o que exibir —
    # o cartão nem chega a renderizar a linha, decidido por `requisicao_existe`.
    assert exibicoes == {
        requisicao.pk: 'REQ-2026-000060',
        rascunho.pk: 'Rascunho',
        999999: '',
    }


@pytest.mark.django_db
def test_id_orfao_nao_se_disfarca_de_rascunho(solicitante, setor_obras):
    """`requisicao_id` é `IntegerField` solto: id órfão e rascunho são iguais.

    Pelo valor do campo os dois casos são indistinguíveis, e o fallback comum
    `"Rascunho"` fazia o cartão prometer um link cujo detalhe devolve 404.
    `requisicao_existe` separa os dois.
    """
    rascunho = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        numero_publico=None,
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.AUTORIZACAO,
        requisicao_id=rascunho.pk,
    )
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.ATENDIMENTO,
        requisicao_id=999999,
    )
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.ATENDIMENTO,
        requisicao_id=None,
    )

    existe = {
        n.requisicao_id: n.requisicao_existe
        for n in notificacoes_para_exibicao(solicitante.pk)
    }

    # O rascunho existe — só ainda não tem número. Segue sendo destino válido.
    assert existe[rascunho.pk] is True
    assert existe[999999] is False
    assert existe[None] is False


class TestPendenciaDaNotificacao:
    """A notificação para de afirmar um estado que ela nunca reconsultava (#175).

    "Ainda pede ação?" é regra de domínio: a resposta é a interseção entre a
    operação que o aviso convoca e `acoes_disponiveis` — tabela de transições
    mais policies. Estes testes cobrem o seletor, não o template.
    """

    def _requisicao(self, estado, solicitante, setor_obras, numero='REQ-2026-000300'):
        return Requisicao.objects.create(
            estado=estado,
            numero_publico=numero,
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_obras,
        )

    @pytest.mark.django_db
    def test_aviso_de_envio_pede_acao_enquanto_a_requisicao_espera(
        self, chefe_obras, solicitante, setor_obras
    ):
        requisicao = self._requisicao(
            EstadoRequisicao.AGUARDANDO_AUTORIZACAO, solicitante, setor_obras
        )
        Notificacao.objects.create(
            destinatario=chefe_obras,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=requisicao.pk,
        )

        (notificacao,) = notificacoes_para_exibicao(chefe_obras.pk)

        assert notificacao.pede_acao is True
        assert notificacao.resolvida is False
        assert notificacao.requisicao_referida.estado == (
            EstadoRequisicao.AGUARDANDO_AUTORIZACAO
        )

    @pytest.mark.django_db
    def test_aviso_de_envio_fica_resolvido_quando_o_estado_andou(
        self, chefe_obras, solicitante, setor_obras
    ):
        """Três das quinze notificações do achado descreviam requisições que o
        próprio chefe já tinha autorizado."""
        requisicao = self._requisicao(
            EstadoRequisicao.ATENDIDA, solicitante, setor_obras
        )
        Notificacao.objects.create(
            destinatario=chefe_obras,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=requisicao.pk,
        )

        (notificacao,) = notificacoes_para_exibicao(chefe_obras.pk)

        # Some da contagem, continua na lista: `/notificacoes/` é o diário do
        # que aconteceu com as minhas requisições, não uma caixa de entrada.
        assert notificacao.pede_acao is False
        assert notificacao.resolvida is True
        assert contagem_de_notificacoes_pendentes(chefe_obras.pk) == 0

    @pytest.mark.django_db
    def test_quem_nao_pode_autorizar_nao_recebe_pendencia(
        self, solicitante, setor_obras
    ):
        """A policy é metade da resposta: estado certo, papel errado, sem pendência."""
        requisicao = self._requisicao(
            EstadoRequisicao.AGUARDANDO_AUTORIZACAO, solicitante, setor_obras
        )
        Notificacao.objects.create(
            destinatario=solicitante,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=requisicao.pk,
        )

        (notificacao,) = notificacoes_para_exibicao(solicitante.pk)

        assert notificacao.pede_acao is False

    @pytest.mark.django_db
    def test_aviso_informativo_nao_pede_acao_nem_se_diz_resolvido(
        self, solicitante, setor_obras
    ):
        """Narra um desfecho e nunca pediu ação: marcar "Resolvida" inventaria
        uma pendência que não houve."""
        requisicao = self._requisicao(
            EstadoRequisicao.ATENDIDA, solicitante, setor_obras
        )
        Notificacao.objects.create(
            destinatario=solicitante,
            tipo=TipoNotificacao.ATENDIMENTO,
            requisicao_id=requisicao.pk,
        )

        (notificacao,) = notificacoes_para_exibicao(solicitante.pk)

        assert notificacao.pede_acao is False
        assert notificacao.resolvida is False

    @pytest.mark.django_db
    def test_aviso_sem_requisicao_nunca_e_pendencia(self, chefe_obras):
        """Aviso sem link (existe no seed) e id órfão: sem destino não há ação.

        Nenhum dos dois pode se disfarçar de item acionável — nem no cartão nem
        na contagem do sino.
        """
        Notificacao.objects.create(
            destinatario=chefe_obras,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=None,
        )
        Notificacao.objects.create(
            destinatario=chefe_obras,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
            requisicao_id=999999,
        )

        notificacoes = notificacoes_para_exibicao(chefe_obras.pk)

        assert [n.pede_acao for n in notificacoes] == [False, False]
        assert [n.resolvida for n in notificacoes] == [False, False]
        assert [n.requisicao_existe for n in notificacoes] == [False, False]
        assert contagem_de_notificacoes_pendentes(chefe_obras.pk) == 0
