import pytest

from apps.accounts.papeis import PapelEfetivo
from apps.accounts.policies import exigir_pode_gerir_cadastro, pode_gerir_cadastro
from apps.core.exceptions import PermissaoNegada


def _papel(
    *,
    ativo: bool = True,
    eh_superusuario: bool = False,
    ator_id: int = 1,
) -> PapelEfetivo:
    return PapelEfetivo(
        eh_almoxarifado=False,
        eh_chefe_de_almoxarifado=False,
        setores_em_escopo=(),
        setor_chefiado_ativo_id=None,
        pode_ser_beneficiario=True,
        ativo=ativo,
        eh_superusuario=eh_superusuario,
        ator_id=ator_id,
    )


def test_superusuario_ativo_pode_gerir_cadastro():
    assert pode_gerir_cadastro(_papel(ativo=True, eh_superusuario=True)) is True


def test_superusuario_inativo_nao_pode_gerir_cadastro():
    assert pode_gerir_cadastro(_papel(ativo=False, eh_superusuario=True)) is False


def test_usuario_ativo_comum_nao_pode_gerir_cadastro():
    assert pode_gerir_cadastro(_papel(ativo=True, eh_superusuario=False)) is False


def test_exigir_levanta_permissao_negada_para_nao_superusuario():
    with pytest.raises(PermissaoNegada):
        exigir_pode_gerir_cadastro(_papel(ativo=True, eh_superusuario=False))


def test_exigir_nao_levanta_para_superusuario():
    exigir_pode_gerir_cadastro(_papel(ativo=True, eh_superusuario=True))
