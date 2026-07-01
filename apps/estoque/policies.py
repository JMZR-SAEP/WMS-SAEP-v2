from __future__ import annotations

from typing import TYPE_CHECKING

from apps.core.exceptions import PermissaoNegada

if TYPE_CHECKING:
    from apps.accounts.papeis import PapelEfetivo


def _eh_almoxarifado(papel: 'PapelEfetivo') -> bool:
    return papel.eh_almoxarifado


def pode_consultar_saidas_excepcionais(papel: 'PapelEfetivo') -> bool:
    if not papel.ativo:
        return False
    if papel.eh_superusuario:
        return True
    return papel.eh_almoxarifado


def exigir_pode_consultar_saidas_excepcionais(papel: 'PapelEfetivo') -> None:
    if not pode_consultar_saidas_excepcionais(papel):
        raise PermissaoNegada('Apenas almoxarifado pode consultar saídas excepcionais.')


def pode_registrar_saida_excepcional(papel: 'PapelEfetivo') -> bool:
    """Apenas chefe de almoxarifado e superuser podem registrar."""
    if not papel.ativo:
        return False
    if papel.eh_superusuario:
        return True
    return papel.eh_chefe_de_almoxarifado


def exigir_pode_registrar_saida_excepcional(papel: 'PapelEfetivo') -> None:
    if not pode_registrar_saida_excepcional(papel):
        raise PermissaoNegada(
            'Apenas chefe de almoxarifado pode registrar saídas excepcionais.'
        )


def pode_estornar_saida_excepcional(papel: 'PapelEfetivo') -> bool:
    """Apenas chefe de almoxarifado e superuser podem estornar."""
    return pode_registrar_saida_excepcional(papel)


def exigir_pode_estornar_saida_excepcional(papel: 'PapelEfetivo') -> None:
    if not pode_estornar_saida_excepcional(papel):
        raise PermissaoNegada(
            'Apenas chefe de almoxarifado pode estornar saídas excepcionais.'
        )


def pode_visualizar_preview_scpi(papel: 'PapelEfetivo') -> bool:
    if not papel.ativo:
        return False
    return papel.eh_superusuario


def exigir_pode_visualizar_preview_scpi(papel: 'PapelEfetivo') -> None:
    if not pode_visualizar_preview_scpi(papel):
        raise PermissaoNegada(
            'Apenas superusuários podem visualizar pré-visualizações de importação SCPI.',
            code='permissao_negada',
        )


def pode_confirmar_importacao_scpi(papel: 'PapelEfetivo') -> bool:
    return papel.ativo and papel.eh_superusuario


def exigir_pode_confirmar_importacao_scpi(papel: 'PapelEfetivo') -> None:
    if not pode_confirmar_importacao_scpi(papel):
        raise PermissaoNegada(
            'Apenas superusuários podem confirmar importações SCPI.',
            code='permissao_negada',
        )


def pode_consultar_historico_scpi(papel: 'PapelEfetivo') -> bool:
    if not papel.ativo:
        return False
    if papel.eh_superusuario:
        return True
    return papel.eh_chefe_de_almoxarifado


def exigir_pode_consultar_historico_scpi(papel: 'PapelEfetivo') -> None:
    if not pode_consultar_historico_scpi(papel):
        raise PermissaoNegada(
            'Apenas superusuários e chefes de almoxarifado podem consultar o histórico de importações SCPI.',
            code='permissao_negada',
        )


def pode_consultar_catalogo_estoque(papel: 'PapelEfetivo') -> bool:
    return papel.ativo


def exigir_pode_consultar_catalogo_estoque(papel: 'PapelEfetivo') -> None:
    if not pode_consultar_catalogo_estoque(papel):
        raise PermissaoNegada(
            'Apenas usuários ativos podem consultar o catálogo de estoque.',
            code='permissao_negada',
        )


def pode_gerir_catalogo(papel: 'PapelEfetivo') -> bool:
    """Superusuário pode gerir (ativar/desativar) materiais do catálogo."""
    return papel.ativo and papel.eh_superusuario


def exigir_pode_gerir_catalogo(papel: 'PapelEfetivo') -> None:
    if not pode_gerir_catalogo(papel):
        raise PermissaoNegada(
            'Apenas superusuários podem gerir o catálogo de materiais.'
        )


def _eh_chefe_ou_aux_setor_nao_almox(papel: 'PapelEfetivo') -> bool:
    return bool(papel.setores_em_escopo)


def pode_consultar_movimentacoes_estoque(papel: 'PapelEfetivo') -> bool:
    """Pode navegar o ledger de movimentações = tem visibilidade por papel.

    Espelha o universo de ``movimentacoes_visiveis_para``: superuser, almoxarifado
    (chefe/aux) ou chefe/aux de setor não-almox. Solicitante puro e inativo: não.
    """
    if not papel.ativo:
        return False
    if papel.eh_superusuario:
        return True
    return papel.eh_almoxarifado or bool(papel.setores_em_escopo)


def exigir_pode_consultar_movimentacoes_estoque(papel: 'PapelEfetivo') -> None:
    if not pode_consultar_movimentacoes_estoque(papel):
        raise PermissaoNegada(
            'Você não tem permissão para consultar movimentações de estoque.',
            code='permissao_negada',
        )
