"""Service de cópia de requisições."""

from __future__ import annotations

import logging

from django.db import transaction

from apps.accounts.models import User
from apps.accounts.papeis import papel_efetivo
from apps.core.exceptions import DadosInvalidos, EstadoInvalido
from apps.requisicoes.models import (
    EstadoRequisicao,
    EventoTimeline,
    ItemRequisicao,
    Requisicao,
    TimelineRequisicao,
)
from apps.requisicoes.policies import (
    exigir_pode_copiar_requisicao,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TR-019: copiar requisição
# ---------------------------------------------------------------------------


@transaction.atomic
def copiar_requisicao(
    *,
    ator_id: int,
    requisicao_id: int,
) -> Requisicao:
    """Cria rascunho copiando todos os itens de requisição atendida ou recusada.

    REQ-09: não copia quantidade_autorizada nem quantidade_entregue.
    Itens inelegíveis são incluídos — elegibilidade é validada no envio (TR-005).
    """
    try:
        ator = User.objects.get(pk=ator_id)
    except User.DoesNotExist:
        raise DadosInvalidos('Ator não encontrado.', code='ator_nao_encontrado')

    try:
        origem = (
            Requisicao.objects.select_for_update(of=('self',))
            .select_related('beneficiario__setor', 'setor_beneficiario')
            .get(pk=requisicao_id)
        )
    except Requisicao.DoesNotExist:
        raise DadosInvalidos(
            'Requisição não encontrada.', code='requisicao_nao_encontrada'
        )

    estados_copiavel = {EstadoRequisicao.ATENDIDA, EstadoRequisicao.RECUSADA}
    if origem.estado not in estados_copiavel:
        raise EstadoInvalido(
            'Só é possível copiar requisições atendidas ou recusadas.',
            code='estado_invalido',
        )

    papel = papel_efetivo(ator)

    beneficiario = origem.beneficiario
    if not (beneficiario.is_active and beneficiario.setor_id is not None):
        raise DadosInvalidos(
            f'{beneficiario.nome} não pode ser beneficiário: usuário inativo ou sem setor.',
            code='beneficiario_inelegivel',
        )

    exigir_pode_copiar_requisicao(papel, origem)

    setor_beneficiario = beneficiario.setor
    if setor_beneficiario is None:
        raise DadosInvalidos(
            f'{beneficiario.nome} não tem setor atribuído.',
            code='beneficiario_inelegivel',
        )

    itens_origem = list(origem.itens.all())
    if not itens_origem:
        raise DadosInvalidos(
            'A requisição de origem não possui itens.',
            code='sem_itens',
        )

    novo_rascunho = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        numero_publico=None,
        criador=ator,
        beneficiario=beneficiario,
        setor_beneficiario=setor_beneficiario,
        observacao_geral=origem.observacao_geral,
    )

    ItemRequisicao.objects.bulk_create(
        [
            ItemRequisicao(
                requisicao=novo_rascunho,
                material_id=item.material_id,
                quantidade_solicitada=item.quantidade_solicitada,
            )
            for item in itens_origem
        ]
    )

    TimelineRequisicao.objects.create(
        requisicao=novo_rascunho,
        evento=EventoTimeline.CRIACAO,
        ator=ator,
        estado_resultante=EstadoRequisicao.RASCUNHO,
    )

    return novo_rascunho
