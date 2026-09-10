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
    """Chefe de almoxarifado é o dono do ritual de importação SCPI (PRODUCT.md);
    superusuário mantém acesso como override técnico."""
    if not papel.ativo:
        return False
    if papel.eh_superusuario:
        return True
    return papel.eh_chefe_de_almoxarifado


def exigir_pode_visualizar_preview_scpi(papel: 'PapelEfetivo') -> None:
    if not pode_visualizar_preview_scpi(papel):
        raise PermissaoNegada(
            'Apenas chefes de almoxarifado e superusuários podem visualizar '
            'pré-visualizações de importação SCPI.',
            code='permissao_negada',
        )


def pode_confirmar_importacao_scpi(papel: 'PapelEfetivo') -> bool:
    """A decisão sobre cada divergência é do chefe de almoxarifado
    (processos-almoxarifado.md); superusuário mantém acesso como override."""
    if not papel.ativo:
        return False
    if papel.eh_superusuario:
        return True
    return papel.eh_chefe_de_almoxarifado


def exigir_pode_confirmar_importacao_scpi(papel: 'PapelEfetivo') -> None:
    if not pode_confirmar_importacao_scpi(papel):
        raise PermissaoNegada(
            'Apenas chefes de almoxarifado e superusuários podem confirmar '
            'importações SCPI.',
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


def pode_consultar_divergencias_criticas(papel: 'PapelEfetivo') -> bool:
    """Pode ver o marcador de divergência crítica (invariante EST-07).

    ``docs/matriz-permissoes.md`` L89 ("Consultar divergências críticas"):
    auxiliar de almoxarifado, chefe de almoxarifado e superuser. Solicitante,
    auxiliar de setor e chefe de setor não — o marcador é informação de gestão
    de estoque, não de requisição.

    Policy própria, e não reuso de ``pode_consultar_saidas_excepcionais``, que
    hoje tem corpo idêntico: L77 e L89 são duas linhas distintas da matriz, e
    amarrá-las faria uma mudança futura em uma mover a outra em silêncio
    (ADR-0011: uma policy por decisão de domínio).

    Sem par ``exigir_pode_*``: esta policy não guarda endpoint nenhum. O acesso
    ao catálogo é da L72 e continua aberto a todo usuário ativo — aqui só se
    decide o *escopo do conteúdo*, consumido por
    ``selectors.listar_materiais_com_saldo`` e pelo template. Criar um
    ``exigir_*`` que ninguém chama plantaria de novo o defeito que a #181
    diagnosticou em ``pode_ver_notificacao``.
    """
    if not papel.ativo:
        return False
    if papel.eh_superusuario:
        return True
    return _eh_almoxarifado(papel)


def pode_gerir_catalogo(papel: 'PapelEfetivo') -> bool:
    """Chefe de almoxarifado e superusuário podem gerir (in/reativar) materiais do
    catálogo (matriz L74/§3, #180). Auxiliar de almoxarifado não — a matriz só
    concede ao chefe.

    Só decide o *domínio* (service `desativar_material`/`reativar_material`).
    O admin do Django tem gate próprio (`MaterialAdmin._pode_gerir`), superusuário
    apenas: a superfície do admin edita todos os campos do material, não só
    `ativo`, e permanece deliberadamente fora do que esta policy concede.
    """
    if not papel.ativo:
        return False
    if papel.eh_superusuario:
        return True
    return papel.eh_chefe_de_almoxarifado


def exigir_pode_gerir_catalogo(papel: 'PapelEfetivo') -> None:
    if not pode_gerir_catalogo(papel):
        raise PermissaoNegada(
            'Apenas chefes de almoxarifado e superusuários podem gerir o '
            'catálogo de materiais.'
        )


def pode_consultar_movimentacoes_estoque(papel: 'PapelEfetivo') -> bool:
    """Pode navegar o ledger de movimentações.

    Decide apenas o *acesso à página*: superuser, almoxarifado (chefe/aux) ou
    chefe/aux de setor não-almox (``setores_em_escopo`` não vazio). Solicitante
    puro e inativo: não.

    Quanto cada um vê é decisão de ``movimentacoes_visiveis_para``, e não
    coincide com esta: o auxiliar de setor entra na página, mas só enxerga
    movimentações de requisições que ele mesmo criou (#112, estendendo a #106).
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
