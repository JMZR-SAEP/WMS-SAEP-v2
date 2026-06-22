"""Testes de services de notificações (ADR-0010)."""

from decimal import Decimal

import pytest

from apps.notificacoes.models import Notificacao, TipoNotificacao
from apps.notificacoes.services import criar_notificacoes_para


# ---------------------------------------------------------------------------
# criar_notificacoes_para — helper de deduplicação
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_criar_notificacoes_criador_distinto_beneficiario(
    solicitante, outro_solicitante
):
    """criador ≠ beneficiário → 2 notificações."""
    criar_notificacoes_para(
        criador_id=solicitante.pk,
        beneficiario_id=outro_solicitante.pk,
        requisicao_id=10,
        tipo=TipoNotificacao.AUTORIZACAO,
    )
    notifs = Notificacao.objects.filter(requisicao_id=10)
    assert notifs.count() == 2
    destinatarios = set(notifs.values_list('destinatario_id', flat=True))
    assert destinatarios == {solicitante.pk, outro_solicitante.pk}


@pytest.mark.django_db
def test_criar_notificacoes_mesmo_usuario_uma_notificacao(solicitante):
    """criador == beneficiário → 1 notificação (deduplicação)."""
    criar_notificacoes_para(
        criador_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        requisicao_id=11,
        tipo=TipoNotificacao.AUTORIZACAO,
    )
    notifs = Notificacao.objects.filter(requisicao_id=11)
    assert notifs.count() == 1
    assert notifs.first().destinatario_id == solicitante.pk


# ---------------------------------------------------------------------------
# Hooks em requisicoes.services — autorizar, recusar, atendimento
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_autorizar_requisicao_gera_notificacoes(
    chefe_obras, solicitante, outro_solicitante, material_disponivel
):
    """autorizar_requisicao dispara notificações para criador e beneficiário."""
    from apps.requisicoes.services import (
        autorizar_requisicao,
        criar_requisicao,
        enviar_para_autorizacao,
    )

    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=outro_solicitante.pk,
        itens=[{'material_id': material_disponivel.pk, 'quantidade_solicitada': Decimal('2')}],
    )
    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)
    autorizar_requisicao(ator_id=chefe_obras.pk, requisicao_id=req.pk)

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.AUTORIZACAO,
    )
    assert notifs.count() == 2
    destinatarios = set(notifs.values_list('destinatario_id', flat=True))
    assert destinatarios == {solicitante.pk, outro_solicitante.pk}


@pytest.mark.django_db(transaction=True)
def test_recusar_requisicao_gera_notificacoes(
    chefe_obras, solicitante, outro_solicitante, material_disponivel
):
    """recusar_requisicao dispara notificações para criador e beneficiário."""
    from apps.requisicoes.services import (
        criar_requisicao,
        enviar_para_autorizacao,
        recusar_requisicao,
    )

    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=outro_solicitante.pk,
        itens=[{'material_id': material_disponivel.pk, 'quantidade_solicitada': Decimal('1')}],
    )
    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)
    recusar_requisicao(
        ator_id=chefe_obras.pk,
        requisicao_id=req.pk,
        motivo='Sem orçamento',
    )

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.RECUSA,
    )
    assert notifs.count() == 2


@pytest.mark.django_db(transaction=True)
def test_registrar_atendimento_gera_notificacoes(
    chefe_obras, chefe_almoxarifado, solicitante, outro_solicitante, material_disponivel
):
    """registrar_atendimento dispara notificações para criador e beneficiário."""
    from apps.requisicoes.services import (
        criar_requisicao,
        autorizar_requisicao,
        enviar_para_autorizacao,
        registrar_atendimento,
        separar_para_retirada,
    )

    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=outro_solicitante.pk,
        itens=[{'material_id': material_disponivel.pk, 'quantidade_solicitada': Decimal('1')}],
    )
    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)
    autorizar_requisicao(ator_id=chefe_obras.pk, requisicao_id=req.pk)
    separar_para_retirada(ator_id=chefe_almoxarifado.pk, requisicao_id=req.pk)

    item = req.itens.first()
    registrar_atendimento(
        ator_id=chefe_almoxarifado.pk,
        requisicao_id=req.pk,
        itens=[{'item_id': item.pk, 'quantidade_entregue': Decimal('1'), 'justificativa': ''}],
        retirante_nome='Fulano',
    )

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.ATENDIMENTO,
    )
    assert notifs.count() == 2


@pytest.mark.django_db(transaction=True)
def test_autorizar_requisicao_criador_igual_beneficiario_uma_notificacao(
    chefe_obras, solicitante, material_disponivel
):
    """criador == beneficiário → 1 notificação."""
    from apps.requisicoes.services import (
        autorizar_requisicao,
        criar_requisicao,
        enviar_para_autorizacao,
    )

    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[{'material_id': material_disponivel.pk, 'quantidade_solicitada': Decimal('1')}],
    )
    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)
    autorizar_requisicao(ator_id=chefe_obras.pk, requisicao_id=req.pk)

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.AUTORIZACAO,
    )
    assert notifs.count() == 1


@pytest.mark.django_db(transaction=True)
def test_rollback_sem_notificacoes(solicitante, material_disponivel):
    """Se transação rolar back, on_commit não dispara → zero notificações."""
    from apps.core.exceptions import EstadoInvalido
    from apps.requisicoes.services import autorizar_requisicao

    with pytest.raises(EstadoInvalido):
        autorizar_requisicao(ator_id=solicitante.pk, requisicao_id=99999)

    assert Notificacao.objects.count() == 0


# ---------------------------------------------------------------------------
# Hook em estoque.services — _registrar_atualizacao_estoque_relevante
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_divergencia_estoque_gera_notificacoes_para_requisicao_afetada(
    chefe_obras, chefe_almoxarifado, solicitante, outro_solicitante,
    material_disponivel, estoque_principal
):
    """Importação SCPI com divergência crítica → notifica criador e beneficiário."""
    from apps.estoque.services import confirmar_importacao_scpi, preview_importacao_scpi
    from apps.requisicoes.services import (
        autorizar_requisicao,
        criar_requisicao,
        enviar_para_autorizacao,
    )

    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=outro_solicitante.pk,
        itens=[{'material_id': material_disponivel.pk, 'quantidade_solicitada': Decimal('50')}],
    )
    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)
    autorizar_requisicao(ator_id=chefe_obras.pk, requisicao_id=req.pk)

    # Após autorização, saldo_reservado = 50. Vamos importar CSV com fisico=10 (< reservado).
    csv_content = f'CADPRO;DENOMINACAO;QUAN3\n{material_disponivel.codigo};Parafuso M6;000.000.010'
    preview = preview_importacao_scpi(
        ator_id=chefe_almoxarifado.pk,
        conteudo_csv=csv_content,
        estoque_id=estoque_principal.pk,
    )
    confirmar_importacao_scpi(
        ator_id=chefe_almoxarifado.pk,
        preview_id=preview.pk,
    )

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.DIVERGENCIA_ESTOQUE,
    )
    assert notifs.count() == 2
    destinatarios = set(notifs.values_list('destinatario_id', flat=True))
    assert destinatarios == {solicitante.pk, outro_solicitante.pk}


@pytest.mark.django_db(transaction=True)
def test_divergencia_estoque_deduplica_criador_igual_beneficiario(
    chefe_obras, chefe_almoxarifado, solicitante,
    material_disponivel, estoque_principal
):
    """Divergência com criador == beneficiário → 1 notificação."""
    from apps.estoque.services import confirmar_importacao_scpi, preview_importacao_scpi
    from apps.requisicoes.services import (
        autorizar_requisicao,
        criar_requisicao,
        enviar_para_autorizacao,
    )

    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[{'material_id': material_disponivel.pk, 'quantidade_solicitada': Decimal('50')}],
    )
    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)
    autorizar_requisicao(ator_id=chefe_obras.pk, requisicao_id=req.pk)

    csv_content = f'CADPRO;DENOMINACAO;QUAN3\n{material_disponivel.codigo};Parafuso M6;000.000.010'
    preview = preview_importacao_scpi(
        ator_id=chefe_almoxarifado.pk,
        conteudo_csv=csv_content,
        estoque_id=estoque_principal.pk,
    )
    confirmar_importacao_scpi(
        ator_id=chefe_almoxarifado.pk,
        preview_id=preview.pk,
    )

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.DIVERGENCIA_ESTOQUE,
    )
    assert notifs.count() == 1
