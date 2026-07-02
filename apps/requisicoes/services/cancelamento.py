"""Service de cancelamento de requisições — entrada única dirigida por variante.

ADR-0011 (emenda 2026-06-26): `cancelar_requisicao` resolve a variante via
`cancelamento_info` (fonte única, também consumida por `_detalhe_context` na
view) e despacha para o handler correspondente em `_HANDLERS`. Os handlers
executam só **efeitos** — nenhuma decisão de estado dentro deles; quem decide
é a tabela `TRANSICOES` (via `cancelamento_info`) e as flags de
`CancelamentoInfo` (`requer_justificativa`, `libera_reserva`).
"""

from __future__ import annotations

from collections.abc import Callable

from django.db import transaction

from apps.accounts.models import User
from apps.accounts.papeis import papel_efetivo
from apps.core.exceptions import DadosInvalidos
from apps.estoque.services import (
    ItemLiberacaoReserva,
    OrigemMovimentacaoEstoque,
    liberar_reservas_para_cancelamento,
)
from apps.requisicoes.models import (
    CancelamentoVariant,
    EstadoRequisicao,
    EventoTimeline,
    Requisicao,
    TimelineRequisicao,
)
from apps.requisicoes.policies import exigir_pode_cancelar_requisicao
from apps.requisicoes.transitions import CancelamentoInfo, cancelamento_info


def _efeito_descarte(
    *,
    requisicao: Requisicao,
    ator: User,
    justificativa: str,
    info: CancelamentoInfo,
) -> Requisicao:
    """TR-003: rascunho nunca enviado é removido sem registrar timeline."""
    requisicao.delete()
    return requisicao


def _efeito_cancelamento(
    *,
    requisicao: Requisicao,
    ator: User,
    justificativa: str,
    info: CancelamentoInfo,
) -> Requisicao:
    """TR-004/TR-012/TR-013/TR-014: transição + timeline; libera reserva quando `info.libera_reserva`."""
    justificativa_limpa = justificativa.strip()
    if info.requer_justificativa:
        if not justificativa_limpa:
            raise DadosInvalidos(
                'Informe a justificativa do cancelamento.',
                code='justificativa_cancelamento_obrigatoria',
            )
    else:
        justificativa_limpa = ''

    metadata: dict[str, bool] = {}
    if info.libera_reserva:
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
        metadata['liberou_reserva'] = True

    requisicao.estado = EstadoRequisicao.CANCELADA
    requisicao.save(update_fields=['estado', 'atualizado_em'])

    TimelineRequisicao.objects.create(
        requisicao=requisicao,
        evento=EventoTimeline.CANCELAMENTO,
        ator=ator,
        estado_resultante=EstadoRequisicao.CANCELADA,
        justificativa=justificativa_limpa,
        metadata=metadata,
    )

    return requisicao


_HANDLERS: dict[
    CancelamentoVariant,
    Callable[..., Requisicao],
] = {
    CancelamentoVariant.DESCARTE: _efeito_descarte,
    CancelamentoVariant.CANCELAMENTO: _efeito_cancelamento,
}


@transaction.atomic
def cancelar_requisicao(
    *,
    ator_id: int,
    requisicao_id: int,
    justificativa: str = '',
) -> Requisicao:
    """Cancela ou descarta requisição, dirigido pela variante de `cancelamento_info` (TR-003/TR-004/TR-012/TR-013/TR-014)."""
    try:
        requisicao = Requisicao.objects.select_for_update().get(pk=requisicao_id)
    except Requisicao.DoesNotExist:
        raise DadosInvalidos(
            'Requisição não encontrada.', code='requisicao_nao_encontrada'
        ) from None

    try:
        ator = User.objects.get(pk=ator_id)
    except User.DoesNotExist:
        raise DadosInvalidos(
            'Ator não encontrado.', code='ator_nao_encontrado'
        ) from None

    info = cancelamento_info(requisicao)

    papel = papel_efetivo(ator)
    exigir_pode_cancelar_requisicao(papel, requisicao)

    handler = _HANDLERS[info.variante]
    return handler(
        requisicao=requisicao,
        ator=ator,
        justificativa=justificativa,
        info=info,
    )
