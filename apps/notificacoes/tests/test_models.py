"""Testes de model Notificacao (ADR-0010)."""

import pytest

from apps.notificacoes.models import Notificacao, TipoNotificacao


@pytest.mark.django_db
def test_notificacao_criada_nao_lida_por_padrao(solicitante):
    n = Notificacao.objects.create(
        destinatario=solicitante,
        tipo=TipoNotificacao.AUTORIZACAO,
        requisicao_id=42,
    )
    assert n.pk is not None
    assert n.lida is False
    assert n.criado_em is not None


@pytest.mark.django_db
def test_notificacao_str_representa_tipo_e_destinatario(notificacao_nao_lida):
    assert str(notificacao_nao_lida)
