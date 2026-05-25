"""Comandos de domínio de estoque.

Toda mutação de ``SaldoEstoque`` passa por este módulo.
"""

from decimal import Decimal
from typing import TypedDict

from django.db import transaction

from apps.core.exceptions import ConflitoDominio, DadosInvalidos
from apps.estoque.models import SaldoEstoque


class ItemReservaEstoque(TypedDict):
    material_id: int
    quantidade_solicitada: Decimal


@transaction.atomic
def reservar_saldos_para_autorizacao(*, itens: list[ItemReservaEstoque]) -> None:
    """Reserva saldo integral para autorização de requisição.

    ``itens`` deve conter ``material_id`` e ``quantidade_solicitada`` por item.
    A função trava saldos afetados em ordem determinística e só grava após
    validar todos os itens. Se houver mais de um saldo para o mesmo material,
    falha antes de mutar qualquer linha.
    """
    if not itens:
        raise DadosInvalidos(
            'A requisição precisa ter ao menos um item para autorizar.',
            code='sem_itens',
        )

    material_ids: list[int] = []
    quantidade_por_material: dict[int, Decimal] = {}
    for item in itens:
        try:
            material_id = int(item['material_id'])
            quantidade = Decimal(str(item['quantidade_solicitada']))
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise DadosInvalidos(
                'Item inválido para reserva de estoque.',
                code='item_invalido',
            ) from exc

        if quantidade <= 0:
            raise DadosInvalidos(
                'Quantidade solicitada deve ser maior que zero.',
                code='quantidade_invalida',
            )

        if material_id in quantidade_por_material:
            quantidade_por_material[material_id] += quantidade
        else:
            material_ids.append(material_id)
            quantidade_por_material[material_id] = quantidade

    saldos = list(
        SaldoEstoque.objects.select_for_update()
        .select_related('estoque', 'material')
        .filter(material_id__in=material_ids)
        .order_by('estoque_id', 'material_id', 'id')
    )

    saldos_por_material: dict[int, list[SaldoEstoque]] = {}
    for saldo in saldos:
        saldos_por_material.setdefault(saldo.material_id, []).append(saldo)

    for material_id, quantidade in quantidade_por_material.items():
        saldos_do_material = saldos_por_material.get(material_id)
        if saldos_do_material is None:
            raise ConflitoDominio(
                'Saldo de estoque não encontrado para um dos materiais.',
                code='saldo_nao_encontrado',
            )
        if len(saldos_do_material) > 1:
            raise ConflitoDominio(
                (
                    f'Mais de um saldo encontrado para o material '
                    f"'{saldos_do_material[0].material.nome}'."
                ),
                code='saldo_ambiguo',
            )
        saldo_existente = saldos_do_material[0]
        if not saldo_existente.material.ativo:
            raise ConflitoDominio(
                f"Material '{saldo_existente.material.nome}' está inativo.",
                code='material_inativo',
            )
        if saldo_existente.divergente:
            raise ConflitoDominio(
                f"Saldo de estoque divergente para '{saldo_existente.material.nome}'.",
                code='saldo_divergente',
            )
        if saldo_existente.saldo_disponivel < quantidade:
            raise ConflitoDominio(
                f"Saldo insuficiente para reservar '{saldo_existente.material.nome}'.",
                code='saldo_insuficiente',
            )

    for material_id, quantidade in quantidade_por_material.items():
        saldo = saldos_por_material[material_id][0]
        saldo.saldo_reservado = saldo.saldo_reservado + quantidade
        saldo.save(update_fields=['saldo_reservado'])
