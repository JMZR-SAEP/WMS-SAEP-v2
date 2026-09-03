"""Testes unitários para seletores de notificações."""

import pytest

from apps.notificacoes.models import Notificacao, TipoNotificacao
from apps.notificacoes.selectors import (
    notificacoes_com_numero_publico,
    numeros_publicos_por_requisicao,
)
from apps.requisicoes.models import EstadoRequisicao, Requisicao


def test_numeros_publicos_lista_vazia_retorna_dict_vazio():
    assert numeros_publicos_por_requisicao([]) == {}


@pytest.mark.django_db
def test_numeros_publicos_resolve_ids_existentes(solicitante, setor_obras):
    requisicao = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-000050',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    resultado = numeros_publicos_por_requisicao([requisicao.pk])
    assert resultado == {requisicao.pk: 'REQ-2026-000050'}


@pytest.mark.django_db
def test_numeros_publicos_ids_duplicados_nao_gera_erro(solicitante, setor_obras):
    requisicao = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-000051',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    resultado = numeros_publicos_por_requisicao([requisicao.pk, requisicao.pk])
    assert resultado == {requisicao.pk: 'REQ-2026-000051'}


@pytest.mark.django_db
def test_numeros_publicos_mistura_existente_e_inexistente(solicitante, setor_obras):
    requisicao = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-000052',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    resultado = numeros_publicos_por_requisicao([requisicao.pk, 999999])
    assert resultado == {requisicao.pk: 'REQ-2026-000052'}


@pytest.mark.django_db
def test_numeros_publicos_id_de_rascunho_resolve_para_none(solicitante, setor_obras):
    rascunho = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    resultado = numeros_publicos_por_requisicao([rascunho.pk])
    assert resultado == {rascunho.pk: None}


@pytest.mark.django_db
def test_notificacoes_com_numero_publico_decora_e_aplica_fallback(
    solicitante, setor_obras
):
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
    Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.ATENDIMENTO,
        requisicao_id=999999,
    )
    resultado = notificacoes_com_numero_publico(solicitante.pk)
    exibicoes = {n.requisicao_id: n.numero_publico_exibicao for n in resultado}
    assert exibicoes == {requisicao.pk: 'REQ-2026-000060', 999999: 'Rascunho'}


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
        for n in notificacoes_com_numero_publico(solicitante.pk)
    }

    # O rascunho existe — só ainda não tem número. Segue sendo destino válido.
    assert existe[rascunho.pk] is True
    assert existe[999999] is False
    assert existe[None] is False
