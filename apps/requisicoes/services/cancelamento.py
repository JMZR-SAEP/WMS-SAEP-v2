"""Services de cancelamento e descarte de requisições."""

from __future__ import annotations

import logging

from django.db import transaction

from apps.accounts.models import User
from apps.accounts.papeis import papel_efetivo
from apps.core.exceptions import DadosInvalidos, EstadoInvalido
from apps.estoque.services import (
    ItemLiberacaoReserva,
    OrigemMovimentacaoEstoque,
    liberar_reservas_para_cancelamento,
)
from apps.requisicoes.models import (
    EstadoRequisicao,
    EventoTimeline,
    Requisicao,
    TimelineRequisicao,
)
from apps.requisicoes.policies import exigir_pode_cancelar_requisicao
from apps.requisicoes.transitions import verificar_transicao_valida

logger = logging.getLogger(__name__)


def _descartar_rascunho_impl(
    *,
    requisicao: Requisicao,
    ator_id: int,
    justificativa: str | None = None,
) -> None:
    try:
        ator = User.objects.get(pk=ator_id)
    except User.DoesNotExist:
        raise DadosInvalidos(
            'Ator não encontrado.', code='ator_nao_encontrado'
        ) from None

    if requisicao.estado != EstadoRequisicao.RASCUNHO:
        raise EstadoInvalido(
            'Esta requisição não está em rascunho.',
            code='estado_origem_invalido',
        )
    if requisicao.numero_publico is not None:
        raise EstadoInvalido(
            'Este rascunho já foi enviado e não pode ser descartado.',
            code='estado_origem_invalido',
        )

    papel = papel_efetivo(ator)
    exigir_pode_cancelar_requisicao(papel, requisicao)
    requisicao.delete()


@transaction.atomic
def descartar_rascunho(*, ator_id: int, requisicao_id: int) -> None:
    """Descarta rascunho nunca enviado sem registrar timeline (TR-003)."""
    try:
        requisicao = Requisicao.objects.select_for_update().get(pk=requisicao_id)
    except Requisicao.DoesNotExist:
        raise DadosInvalidos(
            'Requisição não encontrada.', code='requisicao_nao_encontrada'
        ) from None

    _descartar_rascunho_impl(requisicao=requisicao, ator_id=ator_id)


@transaction.atomic
def cancelar_ou_descartar_requisicao(
    *,
    ator_id: int,
    requisicao_id: int,
    justificativa: str | None = None,
) -> Requisicao | None:
    """Cancela ou descarta requisição antes da retirada final."""
    try:
        requisicao = Requisicao.objects.select_for_update().get(pk=requisicao_id)
    except Requisicao.DoesNotExist:
        raise DadosInvalidos(
            'Requisição não encontrada.', code='requisicao_nao_encontrada'
        ) from None

    if (
        requisicao.estado == EstadoRequisicao.RASCUNHO
        and requisicao.numero_publico is None
    ):
        _descartar_rascunho_impl(
            requisicao=requisicao,
            ator_id=ator_id,
            justificativa=justificativa,
        )
        return None

    return _cancelar_requisicao_impl(
        requisicao=requisicao,
        ator_id=ator_id,
        justificativa=justificativa or '',
    )


def _cancelar_requisicao_impl(
    *,
    requisicao: Requisicao,
    ator_id: int,
    justificativa: str | None = None,
) -> Requisicao:
    try:
        ator = User.objects.get(pk=ator_id)
    except User.DoesNotExist:
        raise DadosInvalidos(
            'Ator não encontrado.', code='ator_nao_encontrado'
        ) from None

    if requisicao.estado not in (
        EstadoRequisicao.RASCUNHO,
        EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        EstadoRequisicao.AUTORIZADA,
        EstadoRequisicao.PRONTA_PARA_RETIRADA,
    ):
        raise EstadoInvalido(
            'Esta requisição não pode ser cancelada.',
            code='estado_origem_invalido',
        )

    papel = papel_efetivo(ator)
    exigir_pode_cancelar_requisicao(papel, requisicao)

    justificativa_limpa = (justificativa or '').strip()

    if requisicao.estado == EstadoRequisicao.RASCUNHO:
        if requisicao.numero_publico is None:
            raise EstadoInvalido(
                'Este rascunho ainda não foi enviado e deve ser descartado.',
                code='estado_origem_invalido',
            )
        verificar_transicao_valida(requisicao.estado, EstadoRequisicao.CANCELADA)
        requisicao.estado = EstadoRequisicao.CANCELADA
        requisicao.save(update_fields=['estado', 'atualizado_em'])

        TimelineRequisicao.objects.create(
            requisicao=requisicao,
            evento=EventoTimeline.CANCELAMENTO,
            ator=ator,
            estado_resultante=EstadoRequisicao.CANCELADA,
            justificativa=justificativa_limpa,
        )

        return requisicao

    if requisicao.estado == EstadoRequisicao.AGUARDANDO_AUTORIZACAO:
        verificar_transicao_valida(requisicao.estado, EstadoRequisicao.CANCELADA)
        requisicao.estado = EstadoRequisicao.CANCELADA
        requisicao.save(update_fields=['estado', 'atualizado_em'])

        TimelineRequisicao.objects.create(
            requisicao=requisicao,
            evento=EventoTimeline.CANCELAMENTO,
            ator=ator,
            estado_resultante=EstadoRequisicao.CANCELADA,
            justificativa=justificativa_limpa,
        )

        return requisicao

    if not justificativa_limpa:
        raise DadosInvalidos(
            'Informe a justificativa do cancelamento.',
            code='justificativa_cancelamento_obrigatoria',
        )

    if requisicao.estado not in (
        EstadoRequisicao.AUTORIZADA,
        EstadoRequisicao.PRONTA_PARA_RETIRADA,
    ):
        raise EstadoInvalido(
            'Esta requisição não pode ser cancelada.',
            code='estado_origem_invalido',
        )
    verificar_transicao_valida(requisicao.estado, EstadoRequisicao.CANCELADA)

    itens_reservados = list(
        requisicao.itens.select_related('material')
        .filter(quantidade_autorizada__gt=0)
        .order_by('id')
    )
    if not itens_reservados:
        raise DadosInvalidos(
            'A requisição precisa ter itens autorizados para ser cancelada.',
            code='sem_itens_autorizados',
        )

    itens_liberacao: list[ItemLiberacaoReserva] = []
    for item in itens_reservados:
        quantidade_autorizada = item.quantidade_autorizada
        assert quantidade_autorizada is not None
        itens_liberacao.append(
            {
                'material_id': item.material_id,
                'quantidade_reservada': quantidade_autorizada,
            }
        )

    liberar_reservas_para_cancelamento(
        itens=itens_liberacao,
        ator_id=ator.pk,
        origem=OrigemMovimentacaoEstoque.de_requisicao(requisicao),
    )

    requisicao.estado = EstadoRequisicao.CANCELADA
    requisicao.save(update_fields=['estado', 'atualizado_em'])

    TimelineRequisicao.objects.create(
        requisicao=requisicao,
        evento=EventoTimeline.CANCELAMENTO,
        ator=ator,
        estado_resultante=EstadoRequisicao.CANCELADA,
        justificativa=justificativa_limpa,
        metadata={'liberou_reserva': True},
    )

    return requisicao


@transaction.atomic
def cancelar_requisicao(
    *,
    ator_id: int,
    requisicao_id: int,
    justificativa: str = '',
) -> Requisicao:
    """Cancela requisição antes da retirada final (TR-004/TR-012/TR-013/TR-014)."""
    try:
        requisicao = Requisicao.objects.select_for_update().get(pk=requisicao_id)
    except Requisicao.DoesNotExist:
        raise DadosInvalidos(
            'Requisição não encontrada.', code='requisicao_nao_encontrada'
        ) from None

    justificativa_cancelamento = (
        ''
        if requisicao.estado == EstadoRequisicao.AGUARDANDO_AUTORIZACAO
        else justificativa
    )

    return _cancelar_requisicao_impl(
        requisicao=requisicao,
        ator_id=ator_id,
        justificativa=justificativa_cancelamento,
    )
