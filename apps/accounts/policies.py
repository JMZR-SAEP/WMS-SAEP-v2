"""Políticas de autorização contextual de contas e setores."""

from apps.accounts.models import Setor, SetorClassificacao, User
from apps.core.exceptions import PermissaoNegada


def _usuario_ativo(usuario: User) -> bool:
    return bool(usuario.is_active)


def _tem_vinculo_auxiliar_ativo(usuario: User, setor_id: int) -> bool:
    return usuario.vinculos_auxiliares.filter(
        ativo=True,
        setor_id=setor_id,
        setor__ativo=True,
    ).exists()


def _opera_almoxarifado(usuario: User) -> bool:
    return (
        usuario.vinculos_auxiliares.filter(
            ativo=True,
            setor__ativo=True,
            setor__classificacao=SetorClassificacao.ALMOXARIFADO,
        ).exists()
        or Setor.objects.filter(
            chefe=usuario,
            ativo=True,
            classificacao=SetorClassificacao.ALMOXARIFADO,
        ).exists()
    )


def pode_criar_requisicao_para(ator: User, beneficiario: User) -> bool:
    """Retorna True se ator pode criar requisição para beneficiário."""

    if not _usuario_ativo(ator) or not _usuario_ativo(beneficiario):
        return False
    if ator.is_superuser:
        return True
    if not beneficiario.setor_id or not beneficiario.setor.ativo:
        return False
    if ator.id == beneficiario.id:
        return bool(ator.setor_id and ator.setor.ativo)
    if _opera_almoxarifado(ator):
        return True
    if ator.setor_id == beneficiario.setor_id and _tem_vinculo_auxiliar_ativo(
        ator,
        beneficiario.setor_id,
    ):
        return True
    return Setor.objects.filter(
        id=beneficiario.setor_id,
        chefe=ator,
        ativo=True,
    ).exists()


def exigir_pode_criar_requisicao_para(ator: User, beneficiario: User) -> None:
    """Lança PermissaoNegada se ator não pode criar para beneficiário."""

    if not pode_criar_requisicao_para(ator, beneficiario):
        raise PermissaoNegada(
            'Você não pode criar requisição para este beneficiário.',
            code='criacao_beneficiario_negada',
        )
