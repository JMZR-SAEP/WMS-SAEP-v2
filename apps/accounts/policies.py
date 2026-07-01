"""Policies de acesso para gestão de cadastro (accounts)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.accounts.papeis import PapelEfetivo


def pode_gerir_cadastro(papel: 'PapelEfetivo') -> bool:
    """Superusuário pode gerir usuários, setores e vínculos auxiliares."""
    return papel.ativo and papel.eh_superusuario


def exigir_pode_gerir_cadastro(papel: 'PapelEfetivo') -> None:
    from apps.core.exceptions import PermissaoNegada

    if not pode_gerir_cadastro(papel):
        raise PermissaoNegada('Apenas superusuários podem gerir cadastros.')
