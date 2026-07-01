"""Testes de policies de estoque — sem banco (PapelEfetivo puro)."""

import pytest

from apps.accounts.papeis import PapelEfetivo
from apps.core.exceptions import PermissaoNegada
from apps.estoque.policies import (
    exigir_pode_consultar_catalogo_estoque,
    exigir_pode_consultar_historico_scpi,
    exigir_pode_consultar_movimentacoes_estoque,
    exigir_pode_consultar_saidas_excepcionais,
    exigir_pode_confirmar_importacao_scpi,
    exigir_pode_estornar_saida_excepcional,
    exigir_pode_gerir_catalogo,
    exigir_pode_registrar_saida_excepcional,
    exigir_pode_visualizar_preview_scpi,
    pode_consultar_catalogo_estoque,
    pode_consultar_historico_scpi,
    pode_consultar_movimentacoes_estoque,
    pode_consultar_saidas_excepcionais,
    pode_confirmar_importacao_scpi,
    pode_estornar_saida_excepcional,
    pode_gerir_catalogo,
    pode_registrar_saida_excepcional,
    pode_visualizar_preview_scpi,
)


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def _papel(
    *,
    ativo: bool = True,
    eh_superusuario: bool = False,
    eh_almoxarifado: bool = False,
    eh_chefe_de_almoxarifado: bool = False,
    setores_em_escopo: tuple[int, ...] = (),
    setor_chefiado_ativo_id: int | None = None,
    pode_ser_beneficiario: bool = True,
    ator_id: int = 1,
) -> PapelEfetivo:
    return PapelEfetivo(
        ativo=ativo,
        eh_superusuario=eh_superusuario,
        eh_almoxarifado=eh_almoxarifado,
        eh_chefe_de_almoxarifado=eh_chefe_de_almoxarifado,
        setores_em_escopo=setores_em_escopo,
        setor_chefiado_ativo_id=setor_chefiado_ativo_id,
        pode_ser_beneficiario=pode_ser_beneficiario,
        ator_id=ator_id,
    )


CHEFE_ALMOX = _papel(
    eh_almoxarifado=True, eh_chefe_de_almoxarifado=True, setor_chefiado_ativo_id=10
)
AUX_ALMOX = _papel(eh_almoxarifado=True, eh_chefe_de_almoxarifado=False)
SUPERUSER = _papel(eh_superusuario=True)
SOLICITANTE = _papel()
CHEFE_OBRAS = _papel(setores_em_escopo=(5,), setor_chefiado_ativo_id=5)
AUX_OBRAS = _papel(setores_em_escopo=(5,))
INATIVO = _papel(ativo=False)
SUPERUSER_INATIVO = _papel(ativo=False, eh_superusuario=True)


@pytest.mark.parametrize(
    'policy',
    [
        pode_consultar_saidas_excepcionais,
        pode_registrar_saida_excepcional,
        pode_estornar_saida_excepcional,
        pode_visualizar_preview_scpi,
        pode_confirmar_importacao_scpi,
        pode_consultar_historico_scpi,
        pode_gerir_catalogo,
        pode_consultar_movimentacoes_estoque,
    ],
)
def test_superusuario_inativo_nao_pode_em_nenhuma_policy(policy):
    assert policy(SUPERUSER_INATIVO) is False


# ---------------------------------------------------------------------------
# pode_consultar_saidas_excepcionais
# ---------------------------------------------------------------------------


class TestPodeConsultarSaidasExcepcionais:
    def test_chefe_almoxarifado_pode(self):
        assert pode_consultar_saidas_excepcionais(CHEFE_ALMOX) is True

    def test_aux_almoxarifado_pode(self):
        assert pode_consultar_saidas_excepcionais(AUX_ALMOX) is True

    def test_superuser_pode(self):
        assert pode_consultar_saidas_excepcionais(SUPERUSER) is True

    def test_solicitante_nao_pode(self):
        assert pode_consultar_saidas_excepcionais(SOLICITANTE) is False

    def test_inativo_nao_pode(self):
        assert pode_consultar_saidas_excepcionais(INATIVO) is False

    def test_superusuario_inativo_nao_pode(self):
        assert pode_consultar_saidas_excepcionais(SUPERUSER_INATIVO) is False


class TestExigirPodeConsultarSaidasExcepcionais:
    def test_chefe_almox_nao_lanca(self):
        exigir_pode_consultar_saidas_excepcionais(CHEFE_ALMOX)

    def test_solicitante_lanca(self):
        with pytest.raises(PermissaoNegada):
            exigir_pode_consultar_saidas_excepcionais(SOLICITANTE)


# ---------------------------------------------------------------------------
# pode_registrar_saida_excepcional
# ---------------------------------------------------------------------------


class TestPodeRegistrarSaidaExcepcional:
    def test_chefe_almoxarifado_pode(self):
        assert pode_registrar_saida_excepcional(CHEFE_ALMOX) is True

    def test_superuser_pode(self):
        assert pode_registrar_saida_excepcional(SUPERUSER) is True

    def test_aux_almox_nao_pode(self):
        assert pode_registrar_saida_excepcional(AUX_ALMOX) is False

    def test_solicitante_nao_pode(self):
        assert pode_registrar_saida_excepcional(SOLICITANTE) is False

    def test_inativo_nao_pode(self):
        assert pode_registrar_saida_excepcional(INATIVO) is False


class TestExigirPodeRegistrarSaidaExcepcional:
    def test_chefe_almoxarifado_nao_lanca(self):
        exigir_pode_registrar_saida_excepcional(CHEFE_ALMOX)

    def test_superuser_nao_lanca(self):
        exigir_pode_registrar_saida_excepcional(SUPERUSER)

    def test_aux_almox_lanca_permissao_negada(self):
        with pytest.raises(PermissaoNegada):
            exigir_pode_registrar_saida_excepcional(AUX_ALMOX)

    def test_solicitante_lanca_permissao_negada(self):
        with pytest.raises(PermissaoNegada):
            exigir_pode_registrar_saida_excepcional(SOLICITANTE)

    def test_usuario_inativo_lanca_permissao_negada(self):
        with pytest.raises(PermissaoNegada):
            exigir_pode_registrar_saida_excepcional(INATIVO)


# ---------------------------------------------------------------------------
# pode_estornar_saida_excepcional
# ---------------------------------------------------------------------------


class TestPodeEstornarSaidaExcepcional:
    def test_chefe_almoxarifado_pode(self):
        assert pode_estornar_saida_excepcional(CHEFE_ALMOX) is True

    def test_superuser_pode(self):
        assert pode_estornar_saida_excepcional(SUPERUSER) is True

    def test_aux_almox_nao_pode(self):
        assert pode_estornar_saida_excepcional(AUX_ALMOX) is False

    def test_inativo_nao_pode(self):
        assert pode_estornar_saida_excepcional(INATIVO) is False


class TestExigirPodeEstornarSaidaExcepcional:
    def test_chefe_almoxarifado_nao_lanca(self):
        exigir_pode_estornar_saida_excepcional(CHEFE_ALMOX)

    def test_solicitante_lanca(self):
        with pytest.raises(PermissaoNegada):
            exigir_pode_estornar_saida_excepcional(SOLICITANTE)


# ---------------------------------------------------------------------------
# pode_visualizar_preview_scpi
# ---------------------------------------------------------------------------


class TestPodeVisualizarPreviewScpi:
    def test_superuser_pode(self):
        assert pode_visualizar_preview_scpi(SUPERUSER) is True

    def test_chefe_almox_nao_pode(self):
        assert pode_visualizar_preview_scpi(CHEFE_ALMOX) is False

    def test_inativo_nao_pode(self):
        assert pode_visualizar_preview_scpi(INATIVO) is False

    def test_solicitante_nao_pode(self):
        assert pode_visualizar_preview_scpi(SOLICITANTE) is False


class TestExigirPodeVisualizarPreviewScpi:
    def test_superuser_nao_lanca(self):
        exigir_pode_visualizar_preview_scpi(SUPERUSER)

    def test_solicitante_lanca(self):
        with pytest.raises(PermissaoNegada):
            exigir_pode_visualizar_preview_scpi(SOLICITANTE)


# ---------------------------------------------------------------------------
# pode_confirmar_importacao_scpi
# ---------------------------------------------------------------------------


class TestPodeConfirmarImportacaoScpi:
    def test_superuser_pode(self):
        assert pode_confirmar_importacao_scpi(SUPERUSER) is True

    def test_chefe_almox_nao_pode(self):
        assert pode_confirmar_importacao_scpi(CHEFE_ALMOX) is False

    def test_inativo_nao_pode(self):
        assert pode_confirmar_importacao_scpi(INATIVO) is False


class TestExigirPodeConfirmarImportacaoScpi:
    def test_superuser_nao_lanca(self):
        exigir_pode_confirmar_importacao_scpi(SUPERUSER)

    def test_solicitante_lanca(self):
        with pytest.raises(PermissaoNegada):
            exigir_pode_confirmar_importacao_scpi(SOLICITANTE)


# ---------------------------------------------------------------------------
# pode_consultar_historico_scpi
# ---------------------------------------------------------------------------


class TestPodeConsultarHistoricoScpi:
    def test_superuser_pode(self):
        assert pode_consultar_historico_scpi(SUPERUSER) is True

    def test_chefe_almoxarifado_pode(self):
        assert pode_consultar_historico_scpi(CHEFE_ALMOX) is True

    def test_inativo_nao_pode(self):
        assert pode_consultar_historico_scpi(INATIVO) is False

    def test_aux_almoxarifado_nao_pode(self):
        assert pode_consultar_historico_scpi(AUX_ALMOX) is False

    def test_solicitante_nao_pode(self):
        assert pode_consultar_historico_scpi(SOLICITANTE) is False


class TestExigirPodeConsultarHistoricoScpi:
    def test_superuser_nao_lanca(self):
        exigir_pode_consultar_historico_scpi(SUPERUSER)

    def test_chefe_almox_nao_lanca(self):
        exigir_pode_consultar_historico_scpi(CHEFE_ALMOX)

    def test_solicitante_lanca(self):
        with pytest.raises(PermissaoNegada):
            exigir_pode_consultar_historico_scpi(SOLICITANTE)


# ---------------------------------------------------------------------------
# pode_consultar_catalogo_estoque
# ---------------------------------------------------------------------------


class TestPodeConsultarCatalogoEstoque:
    def test_chefe_almoxarifado_pode(self):
        assert pode_consultar_catalogo_estoque(CHEFE_ALMOX) is True

    def test_aux_almoxarifado_pode(self):
        assert pode_consultar_catalogo_estoque(AUX_ALMOX) is True

    def test_superuser_pode(self):
        assert pode_consultar_catalogo_estoque(SUPERUSER) is True

    def test_solicitante_pode(self):
        assert pode_consultar_catalogo_estoque(SOLICITANTE) is True

    def test_inativo_nao_pode(self):
        assert pode_consultar_catalogo_estoque(INATIVO) is False


class TestExigirPodeConsultarCatalogoEstoque:
    def test_ativo_nao_lanca(self):
        exigir_pode_consultar_catalogo_estoque(SOLICITANTE)

    def test_inativo_lanca(self):
        with pytest.raises(PermissaoNegada):
            exigir_pode_consultar_catalogo_estoque(INATIVO)


# ---------------------------------------------------------------------------
# pode_gerir_catalogo
# ---------------------------------------------------------------------------


class TestPodeGerirCatalogo:
    def test_superuser_pode(self):
        assert pode_gerir_catalogo(SUPERUSER) is True

    def test_chefe_almox_nao_pode(self):
        assert pode_gerir_catalogo(CHEFE_ALMOX) is False

    def test_inativo_nao_pode(self):
        assert pode_gerir_catalogo(INATIVO) is False


class TestExigirPodeGerirCatalogo:
    def test_superuser_nao_lanca(self):
        exigir_pode_gerir_catalogo(SUPERUSER)

    def test_chefe_almox_lanca(self):
        with pytest.raises(PermissaoNegada):
            exigir_pode_gerir_catalogo(CHEFE_ALMOX)


# ---------------------------------------------------------------------------
# pode_consultar_movimentacoes_estoque
# ---------------------------------------------------------------------------


class TestPodeConsultarMovimentacoesEstoque:
    def test_superuser_pode(self):
        assert pode_consultar_movimentacoes_estoque(SUPERUSER) is True

    def test_chefe_almoxarifado_pode(self):
        assert pode_consultar_movimentacoes_estoque(CHEFE_ALMOX) is True

    def test_aux_almoxarifado_pode(self):
        assert pode_consultar_movimentacoes_estoque(AUX_ALMOX) is True

    def test_chefe_setor_nao_almox_pode(self):
        assert pode_consultar_movimentacoes_estoque(CHEFE_OBRAS) is True

    def test_aux_setor_nao_almox_pode(self):
        assert pode_consultar_movimentacoes_estoque(AUX_OBRAS) is True

    def test_solicitante_puro_nao_pode(self):
        assert pode_consultar_movimentacoes_estoque(SOLICITANTE) is False

    def test_inativo_nao_pode(self):
        assert pode_consultar_movimentacoes_estoque(INATIVO) is False


class TestExigirPodeConsultarMovimentacoesEstoque:
    def test_superuser_nao_lanca(self):
        exigir_pode_consultar_movimentacoes_estoque(SUPERUSER)

    def test_solicitante_lanca(self):
        with pytest.raises(PermissaoNegada):
            exigir_pode_consultar_movimentacoes_estoque(SOLICITANTE)
