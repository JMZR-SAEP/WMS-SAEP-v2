"""Policies de notificações."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.accounts.papeis import PapelEfetivo
    from apps.notificacoes.models import Notificacao


def pode_ver_notificacao(papel: 'PapelEfetivo', notificacao: 'Notificacao') -> bool:
    return papel.ativo and notificacao.destinatario_id == papel.ator_id


def exigir_pode_ver_notificacao(
    papel: 'PapelEfetivo', notificacao: 'Notificacao'
) -> None:
    if not pode_ver_notificacao(papel, notificacao):
        from apps.core.exceptions import PermissaoNegada

        raise PermissaoNegada(
            'Você não tem permissão para ver esta notificação.',
            code='permissao_negada',
        )
