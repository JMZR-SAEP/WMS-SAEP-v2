"""Policies de notificações."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.notificacoes.models import Notificacao


def pode_ver_notificacao(usuario: 'User', notificacao: 'Notificacao') -> bool:
    return usuario.is_active and notificacao.destinatario_id == usuario.pk


def exigir_pode_ver_notificacao(usuario: 'User', notificacao: 'Notificacao') -> None:
    if not pode_ver_notificacao(usuario, notificacao):
        from apps.core.exceptions import PermissaoNegada

        raise PermissaoNegada(
            'Você não tem permissão para ver esta notificação.',
            code='permissao_negada',
        )
