"""Testes de policy de notificações — sem banco (PapelEfetivo puro)."""

import pytest
from types import SimpleNamespace

from apps.accounts.papeis import PapelEfetivo
from apps.core.exceptions import PermissaoNegada
from apps.notificacoes.policies import exigir_pode_ver_notificacao, pode_ver_notificacao


def _papel(*, ativo: bool = True, ator_id: int = 1) -> PapelEfetivo:
    return PapelEfetivo(
        eh_almoxarifado=False,
        eh_chefe_de_almoxarifado=False,
        setores_em_escopo=(),
        setor_chefiado_ativo_id=None,
        pode_ser_beneficiario=True,
        ativo=ativo,
        eh_superusuario=False,
        ator_id=ator_id,
    )


def _notificacao(destinatario_id: int) -> SimpleNamespace:
    return SimpleNamespace(destinatario_id=destinatario_id)


def test_destinatario_pode_ver_propria_notificacao():
    papel = _papel(ator_id=7)
    notificacao = _notificacao(destinatario_id=7)
    assert pode_ver_notificacao(papel, notificacao) is True


def test_outro_usuario_nao_pode_ver_notificacao():
    papel = _papel(ator_id=42)
    notificacao = _notificacao(destinatario_id=7)
    assert pode_ver_notificacao(papel, notificacao) is False


def test_inativo_nao_pode_ver_propria_notificacao():
    papel = _papel(ativo=False, ator_id=7)
    notificacao = _notificacao(destinatario_id=7)
    assert pode_ver_notificacao(papel, notificacao) is False


def test_exigir_nao_levanta_para_destinatario():
    papel = _papel(ator_id=7)
    notificacao = _notificacao(destinatario_id=7)
    exigir_pode_ver_notificacao(papel, notificacao)


def test_exigir_levanta_para_nao_destinatario():
    papel = _papel(ator_id=42)
    notificacao = _notificacao(destinatario_id=7)
    with pytest.raises(PermissaoNegada):
        exigir_pode_ver_notificacao(papel, notificacao)
