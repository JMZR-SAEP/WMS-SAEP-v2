"""Testes do service composto de requisições (ADR-0004, ADR-0010).

`criar_e_enviar_requisicao` orquestra `criar_requisicao` + `enviar_para_autorizacao`
sob uma única fronteira transacional. Não repete a matriz de policy/estado já
coberta em `test_services.py` para os atômicos — cobre apenas a orquestração.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.core.exceptions import ConflitoDominio, DadosInvalidos, PermissaoNegada
from apps.requisicoes.models import (
    EstadoRequisicao,
    EventoTimeline,
    Requisicao,
    TimelineRequisicao,
)
from apps.requisicoes.services.composites import criar_e_enviar_requisicao


@pytest.mark.django_db
def test_criar_e_enviar_requisicao_cria_e_envia_em_uma_chamada(
    solicitante, chefe_obras, material_disponivel
):
    req = criar_e_enviar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('5'),
            }
        ],
    )

    assert req.estado == EstadoRequisicao.AGUARDANDO_AUTORIZACAO
    assert req.numero_publico is not None

    eventos = list(req.eventos.order_by('criado_em').values_list('evento', flat=True))
    assert eventos == [EventoTimeline.CRIACAO, EventoTimeline.ENVIO_AUTORIZACAO]


@pytest.mark.django_db
def test_criar_e_enviar_requisicao_rollback_total_se_envio_falhar(
    solicitante, material_disponivel
):
    with patch(
        'apps.requisicoes.services.composites.enviar_para_autorizacao',
        side_effect=PermissaoNegada('falha simulada', code='falha_simulada'),
    ):
        with pytest.raises(PermissaoNegada):
            criar_e_enviar_requisicao(
                ator_id=solicitante.pk,
                beneficiario_id=solicitante.pk,
                itens=[
                    {
                        'material_id': material_disponivel.pk,
                        'quantidade_solicitada': Decimal('3'),
                    }
                ],
            )

    assert not Requisicao.objects.exists()
    assert not TimelineRequisicao.objects.exists()


@pytest.mark.django_db
def test_criar_e_enviar_requisicao_setor_sem_autorizador_rollback_total(
    solicitante, material_disponivel
):
    """Guard de #103 é herdado do atômico; nada é persistido no fluxo composto."""
    with pytest.raises(ConflitoDominio) as exc_info:
        criar_e_enviar_requisicao(
            ator_id=solicitante.pk,
            beneficiario_id=solicitante.pk,
            itens=[
                {
                    'material_id': material_disponivel.pk,
                    'quantidade_solicitada': Decimal('3'),
                }
            ],
        )

    assert exc_info.value.code == 'setor_sem_autorizador'
    assert not Requisicao.objects.exists()
    assert not TimelineRequisicao.objects.exists()


@pytest.mark.django_db
def test_criar_e_enviar_requisicao_propaga_dados_invalidos_sem_itens(solicitante):
    with pytest.raises(DadosInvalidos):
        criar_e_enviar_requisicao(
            ator_id=solicitante.pk,
            beneficiario_id=solicitante.pk,
            itens=[],
        )

    assert not Requisicao.objects.exists()
