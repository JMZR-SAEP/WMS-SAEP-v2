"""Testes de policy de notificações (ADR-0010)."""

import pytest

from apps.notificacoes.policies import pode_ver_notificacao


@pytest.mark.django_db
def test_destinatario_pode_ver_propria_notificacao(notificacao_nao_lida, solicitante):
    assert pode_ver_notificacao(solicitante, notificacao_nao_lida) is True


@pytest.mark.django_db
def test_outro_usuario_nao_pode_ver_notificacao(
    notificacao_nao_lida, outro_solicitante
):
    assert pode_ver_notificacao(outro_solicitante, notificacao_nao_lida) is False
