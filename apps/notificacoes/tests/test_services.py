"""Testes de services de notificações (ADR-0010)."""

from decimal import Decimal

import pytest

from apps.notificacoes.models import Notificacao, TipoNotificacao
from apps.notificacoes.services import (
    criar_notificacoes_para,
    criar_notificacoes_para_destinatarios,
)


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
# criar_notificacoes_para_destinatarios — primitivo de roteamento
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_criar_notificacoes_destinatarios_deduplica_repetidos(
    solicitante, outro_solicitante
):
    """Id repetido na entrada gera uma notificação só.

    Assere contagem e conjunto, não ordem: `dict.fromkeys` preserva a ordem de
    entrada no `bulk_create`, mas consulta sem `order_by` não tem ordem
    garantida pelo banco, e ordem de destinatário não é contrato deste fluxo.
    """
    criar_notificacoes_para_destinatarios(
        destinatarios_ids=[solicitante.pk, outro_solicitante.pk, solicitante.pk],
        requisicao_id=20,
        tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
    )
    notifs = Notificacao.objects.filter(requisicao_id=20)
    assert notifs.count() == 2
    assert set(notifs.values_list('destinatario_id', flat=True)) == {
        solicitante.pk,
        outro_solicitante.pk,
    }


@pytest.mark.django_db
def test_criar_notificacoes_destinatarios_ignora_none(solicitante):
    """`None` na entrada é descartado; o chamador não repete a guarda."""
    criar_notificacoes_para_destinatarios(
        destinatarios_ids=[None, solicitante.pk],
        requisicao_id=21,
        tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
    )
    notifs = Notificacao.objects.filter(requisicao_id=21)
    assert notifs.count() == 1
    assert notifs.first().destinatario_id == solicitante.pk


# ---------------------------------------------------------------------------
# Hooks em requisicoes.services — autorizar, recusar, atendimento
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_autorizar_requisicao_gera_notificacoes(
    chefe_obras, outro_solicitante, material_disponivel
):
    """autorizar_requisicao dispara notificações para criador e beneficiário."""
    from apps.requisicoes.services import (
        autorizar_requisicao,
        criar_requisicao,
        enviar_para_autorizacao,
    )

    # chefe_obras cria para outro_solicitante (mesmo setor → permitido)
    req = criar_requisicao(
        ator_id=chefe_obras.pk,
        beneficiario_id=outro_solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('2'),
            }
        ],
    )
    enviar_para_autorizacao(ator_id=chefe_obras.pk, requisicao_id=req.pk)
    autorizar_requisicao(ator_id=chefe_obras.pk, requisicao_id=req.pk)

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.AUTORIZACAO,
    )
    assert notifs.count() == 2
    destinatarios = set(notifs.values_list('destinatario_id', flat=True))
    assert destinatarios == {chefe_obras.pk, outro_solicitante.pk}


@pytest.mark.django_db(transaction=True)
def test_recusar_requisicao_gera_notificacoes(
    chefe_obras, outro_solicitante, material_disponivel
):
    """recusar_requisicao dispara notificações para criador e beneficiário."""
    from apps.requisicoes.services import (
        criar_requisicao,
        enviar_para_autorizacao,
        recusar_requisicao,
    )

    req = criar_requisicao(
        ator_id=chefe_obras.pk,
        beneficiario_id=outro_solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('1'),
            }
        ],
    )
    enviar_para_autorizacao(ator_id=chefe_obras.pk, requisicao_id=req.pk)
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
    destinatarios = set(notifs.values_list('destinatario_id', flat=True))
    assert destinatarios == {chefe_obras.pk, outro_solicitante.pk}


@pytest.mark.django_db(transaction=True)
def test_registrar_atendimento_gera_notificacoes(
    chefe_obras, chefe_almoxarifado, outro_solicitante, material_disponivel
):
    """registrar_atendimento dispara notificações para criador e beneficiário."""
    from apps.requisicoes.services import (
        autorizar_requisicao,
        criar_requisicao,
        enviar_para_autorizacao,
        registrar_atendimento,
        separar_para_retirada,
    )
    from apps.requisicoes.types import LinhaAtendimento

    req = criar_requisicao(
        ator_id=chefe_obras.pk,
        beneficiario_id=outro_solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('1'),
            }
        ],
    )
    enviar_para_autorizacao(ator_id=chefe_obras.pk, requisicao_id=req.pk)
    autorizar_requisicao(ator_id=chefe_obras.pk, requisicao_id=req.pk)
    separar_para_retirada(ator_id=chefe_almoxarifado.pk, requisicao_id=req.pk)

    item = req.itens.first()
    registrar_atendimento(
        ator_id=chefe_almoxarifado.pk,
        requisicao_id=req.pk,
        itens=[
            LinhaAtendimento(
                item_id=item.pk,
                quantidade_entregue=Decimal('1'),
                justificativa='',
            )
        ],
        retirante_nome='Fulano',
    )

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.ATENDIMENTO,
    )
    assert notifs.count() == 2
    destinatarios = set(notifs.values_list('destinatario_id', flat=True))
    assert destinatarios == {chefe_obras.pk, outro_solicitante.pk}


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
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('1'),
            }
        ],
    )
    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)
    autorizar_requisicao(ator_id=chefe_obras.pk, requisicao_id=req.pk)

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.AUTORIZACAO,
    )
    assert notifs.count() == 1


@pytest.mark.django_db(transaction=True)
def test_on_commit_nao_dispara_em_rollback(solicitante, outro_solicitante):
    """on_commit registrado dentro de atomic que faz rollback não persiste notificações."""
    from django.db import transaction

    from apps.notificacoes.services import criar_notificacoes_para

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            transaction.on_commit(
                lambda: criar_notificacoes_para(
                    criador_id=solicitante.pk,
                    beneficiario_id=outro_solicitante.pk,
                    requisicao_id=999,
                    tipo=TipoNotificacao.AUTORIZACAO,
                )
            )
            raise RuntimeError('forçar rollback')

    assert Notificacao.objects.count() == 0


# ---------------------------------------------------------------------------
# Hook em estoque.services — _registrar_atualizacao_estoque_relevante
# ---------------------------------------------------------------------------


def _criar_material_critico(estoque):
    """Material com saldo_fisico < saldo_reservado (divergência pré-existente)."""
    from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida

    m = Material.objects.create(
        codigo='000.001.001',
        nome='Material Crítico Teste',
        unidade=UnidadeMedida.UNIDADE,
        ativo=True,
    )
    SaldoEstoque.objects.create(
        estoque=estoque,
        material=m,
        saldo_fisico=2,
        saldo_reservado=5,
    )
    return m


def _criar_requisicao_autorizada(criador, beneficiario, setor, material):
    """Requisição em estado AUTORIZADA com item do material dado."""
    from decimal import Decimal

    from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AUTORIZADA,
        numero_publico='REQ-2099-000001',
        criador=criador,
        beneficiario=beneficiario,
        setor_beneficiario=setor,
    )
    ItemRequisicao.objects.create(
        requisicao=req,
        material=material,
        quantidade_solicitada=Decimal('3'),
        quantidade_autorizada=Decimal('3'),
    )
    return req


@pytest.mark.django_db(transaction=True)
def test_divergencia_estoque_gera_notificacoes_para_requisicao_afetada(
    chefe_obras, superuser, setor_obras, outro_solicitante, estoque_principal
):
    """Importação SCPI com divergência crítica → notifica criador e beneficiário."""
    from apps.estoque.services import confirmar_importacao_scpi
    from apps.requisicoes.services.ciclo_vida import (
        registrar_timeline_divergencia_importacao,
    )

    material = _criar_material_critico(estoque_principal)
    req = _criar_requisicao_autorizada(
        criador=chefe_obras,
        beneficiario=outro_solicitante,
        setor=setor_obras,
        material=material,
    )

    csv_bytes = (
        f'CADPRO;DENOMINACAO;QUAN3\n{material.codigo};Material Critico;001.000\n'
    ).encode('utf-8')
    confirmar_importacao_scpi(
        ator_id=superuser.pk,
        conteudo_bytes=csv_bytes,
        arquivo_nome='import_critico.csv',
        estoque_id=estoque_principal.pk,
        _pos_importacao_hook=registrar_timeline_divergencia_importacao,
    )

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.DIVERGENCIA_ESTOQUE,
    )
    assert notifs.count() == 2
    destinatarios = set(notifs.values_list('destinatario_id', flat=True))
    assert destinatarios == {chefe_obras.pk, outro_solicitante.pk}


@pytest.mark.django_db(transaction=True)
def test_divergencia_estoque_deduplica_criador_igual_beneficiario(
    chefe_obras, superuser, setor_obras, solicitante, estoque_principal
):
    """Divergência com criador == beneficiário → 1 notificação."""
    from apps.estoque.services import confirmar_importacao_scpi
    from apps.requisicoes.services.ciclo_vida import (
        registrar_timeline_divergencia_importacao,
    )

    material = _criar_material_critico(estoque_principal)
    # força codigo único para não colidir com outro teste
    material.codigo = '000.001.002'
    material.save(update_fields=['codigo'])
    req = _criar_requisicao_autorizada(
        criador=solicitante,
        beneficiario=solicitante,
        setor=setor_obras,
        material=material,
    )

    csv_bytes = (
        f'CADPRO;DENOMINACAO;QUAN3\n{material.codigo};Material Critico 2;001.000\n'
    ).encode('utf-8')
    confirmar_importacao_scpi(
        ator_id=superuser.pk,
        conteudo_bytes=csv_bytes,
        arquivo_nome='import_dedup.csv',
        estoque_id=estoque_principal.pk,
        _pos_importacao_hook=registrar_timeline_divergencia_importacao,
    )

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.DIVERGENCIA_ESTOQUE,
    )
    assert notifs.count() == 1


# ---------------------------------------------------------------------------
# Hook de envio para autorização — notifica o chefe do setor beneficiário
# ---------------------------------------------------------------------------


def _criar_rascunho(*, criador, beneficiario, material):
    from apps.requisicoes.services import criar_requisicao

    return criar_requisicao(
        ator_id=criador.pk,
        beneficiario_id=beneficiario.pk,
        itens=[
            {
                'material_id': material.pk,
                'quantidade_solicitada': Decimal('1'),
            }
        ],
    )


@pytest.mark.django_db(transaction=True)
def test_enviar_para_autorizacao_notifica_chefe(
    chefe_obras, solicitante, material_disponivel
):
    """Envio notifica o chefe do setor beneficiário, e só ele.

    Criador e beneficiário não recebem: sem esta segunda metade, um hook que
    chamasse `criar_notificacoes_para` por engano passaria, e quem enviou
    ganharia notificação do próprio envio.
    """
    from apps.requisicoes.services import enviar_para_autorizacao

    req = _criar_rascunho(
        criador=solicitante, beneficiario=solicitante, material=material_disponivel
    )
    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
    )
    assert notifs.count() == 1
    assert notifs.first().destinatario_id == chefe_obras.pk


@pytest.mark.django_db(transaction=True)
def test_enviar_para_autorizacao_auto_envio_do_chefe_nao_notifica(
    chefe_obras, material_disponivel
):
    """Chefe que envia a própria requisição não é notificado de si mesmo."""
    from apps.requisicoes.services import enviar_para_autorizacao

    req = _criar_rascunho(
        criador=chefe_obras, beneficiario=chefe_obras, material=material_disponivel
    )
    enviar_para_autorizacao(ator_id=chefe_obras.pk, requisicao_id=req.pk)

    assert not Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_reenvio_de_rascunho_retornado_gera_nova_notificacao(
    chefe_obras, solicitante, material_disponivel
):
    """TR-006 → TR-005: reenvio avisa o chefe de novo (sem dedup por requisição).

    Quem retorna para rascunho é o criador: `pode_retornar_para_rascunho`
    concede a criador/beneficiário, não à chefia.
    """
    from apps.requisicoes.services import (
        enviar_para_autorizacao,
        retornar_para_rascunho,
    )

    req = _criar_rascunho(
        criador=solicitante, beneficiario=solicitante, material=material_disponivel
    )
    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)
    retornar_para_rascunho(ator_id=solicitante.pk, requisicao_id=req.pk)
    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
        destinatario_id=chefe_obras.pk,
    )
    assert notifs.count() == 2


@pytest.mark.django_db
def test_chefe_desativado_antes_do_callback_nao_notifica(
    chefe_obras,
    solicitante,
    material_disponivel,
    django_capture_on_commit_callbacks,
):
    """Sem chefe ativo no momento do commit: não notifica, não quebra.

    Sem `transaction=True` de propósito: a captura só intercepta callbacks
    ainda pendentes num `atomic` aberto. Com commit real eles já teriam
    rodado.
    """
    from apps.requisicoes.models import EstadoRequisicao
    from apps.requisicoes.services import enviar_para_autorizacao

    req = _criar_rascunho(
        criador=solicitante, beneficiario=solicitante, material=material_disponivel
    )
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)

    chefe_obras.is_active = False
    chefe_obras.save(update_fields=['is_active'])
    for callback in callbacks:
        callback()

    req.refresh_from_db()
    assert req.estado == EstadoRequisicao.AGUARDANDO_AUTORIZACAO
    assert not Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_falha_ao_notificar_nao_desfaz_transicao(
    chefe_obras, solicitante, material_disponivel, monkeypatch, caplog
):
    """Fail-open: erro no hook é logado e a transição sobrevive.

    O patch mira o símbolo já ligado em `ciclo_vida`, não em
    `notificacoes.services`: o `from ... import` no topo do módulo consumidor
    deixa de consultar o módulo de origem em runtime.
    """
    import logging

    from apps.requisicoes.models import EstadoRequisicao
    from apps.requisicoes.services import enviar_para_autorizacao

    def _explode(**kwargs):
        raise RuntimeError('banco fora')

    monkeypatch.setattr(
        'apps.requisicoes.services.ciclo_vida.criar_notificacoes_para_destinatarios',
        _explode,
    )

    req = _criar_rascunho(
        criador=solicitante, beneficiario=solicitante, material=material_disponivel
    )
    with caplog.at_level(logging.ERROR):
        enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)

    req.refresh_from_db()
    assert req.estado == EstadoRequisicao.AGUARDANDO_AUTORIZACAO
    assert not Notificacao.objects.filter(requisicao_id=req.pk).exists()
    assert 'Falha ao criar notificação de envio pós-commit' in caplog.text


# ---------------------------------------------------------------------------
# Hook de separação para retirada — notifica criador e beneficiário
# ---------------------------------------------------------------------------


def _autorizar_nova_requisicao(*, criador, beneficiario, material, chefe):
    """Requisição em AUTORIZADA, um passo antes de TR-015."""
    from apps.requisicoes.services import (
        autorizar_requisicao,
        criar_requisicao,
        enviar_para_autorizacao,
    )

    req = criar_requisicao(
        ator_id=criador.pk,
        beneficiario_id=beneficiario.pk,
        itens=[
            {
                'material_id': material.pk,
                'quantidade_solicitada': Decimal('1'),
            }
        ],
    )
    enviar_para_autorizacao(ator_id=criador.pk, requisicao_id=req.pk)
    autorizar_requisicao(ator_id=chefe.pk, requisicao_id=req.pk)
    return req


@pytest.mark.django_db(transaction=True)
def test_separar_para_retirada_notifica_criador_e_beneficiario(
    chefe_obras, chefe_almoxarifado, outro_solicitante, material_disponivel
):
    """TR-015 avisa quem espera o material, não quem separou — e só após o commit.

    Duas garantias no mesmo cenário:

    1. **Destinatários.** Assere o conjunto exato, não só a contagem: um hook
       que roteasse para `{beneficiário, almoxarife}` também daria 2.
    2. **Momento.** A chamada roda dentro de um `atomic` externo, então o
       `atomic` do service vira savepoint e o `on_commit` só dispara no commit
       de fora. Asserir ausência *antes* e presença *depois* é o que distingue
       efeito pós-commit de criação síncrona: trocar
       `transaction.on_commit(...)` por uma chamada direta a
       `_notificar_pos_commit(...)` deixaria a notificação visível já dentro do
       bloco, e é aí que este teste quebra. Sem o bloco externo, as duas
       implementações são indistinguíveis.
    """
    from django.db import transaction

    from apps.requisicoes.services import separar_para_retirada

    req = _autorizar_nova_requisicao(
        criador=chefe_obras,
        beneficiario=outro_solicitante,
        material=material_disponivel,
        chefe=chefe_obras,
    )
    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.SEPARACAO_RETIRADA,
    )

    with transaction.atomic():
        separar_para_retirada(ator_id=chefe_almoxarifado.pk, requisicao_id=req.pk)
        assert not notifs.exists()

    assert notifs.count() == 2
    assert set(notifs.values_list('destinatario_id', flat=True)) == {
        chefe_obras.pk,
        outro_solicitante.pk,
    }


@pytest.mark.django_db(transaction=True)
def test_separar_para_retirada_criador_igual_beneficiario_uma_notificacao(
    chefe_obras, chefe_almoxarifado, solicitante, material_disponivel
):
    """criador == beneficiário → 1 notificação (deduplicação)."""
    from apps.requisicoes.services import separar_para_retirada

    req = _autorizar_nova_requisicao(
        criador=solicitante,
        beneficiario=solicitante,
        material=material_disponivel,
        chefe=chefe_obras,
    )
    separar_para_retirada(ator_id=chefe_almoxarifado.pk, requisicao_id=req.pk)

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.SEPARACAO_RETIRADA,
    )
    assert notifs.count() == 1
    assert notifs.first().destinatario_id == solicitante.pk


@pytest.mark.django_db(transaction=True)
def test_separacao_bloqueada_por_divergencia_nao_notifica(
    chefe_obras, chefe_almoxarifado, outro_solicitante, material_disponivel
):
    """TR-015B: separação bloqueada não avisa ninguém.

    Notificar aqui seria mandar o beneficiário buscar material que o
    Almoxarifado não separou.

    Assere só a ausência de notificação. O contrato de domínio do bloqueio —
    `code='separacao_bloqueada'`, estado preservado, saldos e timeline
    intocados — pertence a `requisicoes` e vive em
    `test_tr015b_bloqueia_por_divergencia_critica`; duplicá-lo aqui acoplaria
    este arquivo às regras do app dono do caso de uso.

    Sobre o que este teste trava, sem exagero: hoje o resultado é garantido
    *estruturalmente* pelo `@transaction.atomic` do service — a guarda levanta,
    a transação reverte e qualquer `on_commit` registrado é descartado. Mover o
    hook para antes das guardas **não** faz este teste falhar (verificado por
    mutação).

    O que sobra para ele é estreito, e vale dizer qual é: um despacho que
    escape da transação — `.delay()` de task, webhook, signal em `post_save` —
    dispara mesmo com rollback, e aí este teste acusa. A troca de
    `transaction.on_commit` por chamada síncrona **não** é pega aqui (o
    rollback desfaz a notificação junto); quem trava isso é
    `test_separar_para_retirada_notifica_criador_e_beneficiario`, que assere
    ausência antes e presença depois do commit externo.

    `transaction=True` é o que dá sentido à asserção negativa — sob a marca
    comum nenhum `on_commit` rodaria e a ausência de notificação não provaria
    nada.
    """
    from apps.core.exceptions import DadosInvalidos
    from apps.estoque.models import SaldoEstoque
    from apps.requisicoes.services import separar_para_retirada

    req = _autorizar_nova_requisicao(
        criador=chefe_obras,
        beneficiario=outro_solicitante,
        material=material_disponivel,
        chefe=chefe_obras,
    )
    # divergência crítica superveniente (EST-07): físico cai abaixo do reservado
    # pela autorização, que é o que a separação confere item a item.
    SaldoEstoque.objects.filter(material=material_disponivel).update(saldo_fisico=0)

    with pytest.raises(DadosInvalidos):
        separar_para_retirada(ator_id=chefe_almoxarifado.pk, requisicao_id=req.pk)

    assert not Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.SEPARACAO_RETIRADA,
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_separacao_sem_permissao_nao_notifica(
    chefe_obras, outro_solicitante, material_disponivel
):
    """Permissão negada não vaza notificação.

    `chefe_obras` chefia o setor beneficiário e criou a requisição, mas separar
    é do Almoxarifado — a policy nega, e nada deve ser anunciado. Mesmo alcance
    e mesma limitação do teste de TR-015B acima: trava o contrato de saída, não
    a posição do hook.

    A negação em si e a ausência de escrita são contrato de `requisicoes`, em
    `test_separar_para_retirada_permissao_negada_chefe_setor`. Aqui fica só a
    metade de notificação.
    """
    from apps.core.exceptions import PermissaoNegada
    from apps.requisicoes.services import separar_para_retirada

    req = _autorizar_nova_requisicao(
        criador=chefe_obras,
        beneficiario=outro_solicitante,
        material=material_disponivel,
        chefe=chefe_obras,
    )

    with pytest.raises(PermissaoNegada):
        separar_para_retirada(ator_id=chefe_obras.pk, requisicao_id=req.pk)

    assert not Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.SEPARACAO_RETIRADA,
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_segunda_separacao_nao_gera_notificacao_extra(
    chefe_obras, chefe_almoxarifado, outro_solicitante, material_disponivel
):
    """Repetir TR-015 falha com EstadoInvalido e não duplica o par."""
    from apps.core.exceptions import EstadoInvalido
    from apps.requisicoes.services import separar_para_retirada

    req = _autorizar_nova_requisicao(
        criador=chefe_obras,
        beneficiario=outro_solicitante,
        material=material_disponivel,
        chefe=chefe_obras,
    )
    separar_para_retirada(ator_id=chefe_almoxarifado.pk, requisicao_id=req.pk)

    with pytest.raises(EstadoInvalido):
        separar_para_retirada(ator_id=chefe_almoxarifado.pk, requisicao_id=req.pk)

    assert (
        Notificacao.objects.filter(
            requisicao_id=req.pk,
            tipo=TipoNotificacao.SEPARACAO_RETIRADA,
        ).count()
        == 2
    )


@pytest.mark.django_db(transaction=True)
def test_falha_ao_notificar_separacao_nao_desfaz_transicao(
    chefe_obras,
    chefe_almoxarifado,
    outro_solicitante,
    material_disponivel,
    monkeypatch,
    caplog,
):
    """Fail-open: erro no hook é logado e a separação sobrevive.

    O patch mira o símbolo já ligado em `atendimento`, não em
    `notificacoes.services`: o `from ... import` no topo do módulo consumidor
    deixa de consultar o módulo de origem em runtime.
    """
    import logging

    from apps.requisicoes.models import EstadoRequisicao
    from apps.requisicoes.services import separar_para_retirada

    req = _autorizar_nova_requisicao(
        criador=chefe_obras,
        beneficiario=outro_solicitante,
        material=material_disponivel,
        chefe=chefe_obras,
    )

    def _explode(**kwargs):
        raise RuntimeError('banco fora')

    monkeypatch.setattr(
        'apps.requisicoes.services.atendimento.criar_notificacoes_para',
        _explode,
    )

    with caplog.at_level(logging.ERROR):
        separar_para_retirada(ator_id=chefe_almoxarifado.pk, requisicao_id=req.pk)

    req.refresh_from_db()
    assert req.estado == EstadoRequisicao.PRONTA_PARA_RETIRADA
    assert 'Falha ao criar notificações pós-commit' in caplog.text
    assert not Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.SEPARACAO_RETIRADA,
    ).exists()


# ---------------------------------------------------------------------------
# Issue #111 — divergência criada por saída excepcional notifica os envolvidos
# ---------------------------------------------------------------------------


def _material_com_reserva(estoque, *, codigo, fisico, reservado):
    """Material com saldo controlado, para forçar (ou não) divergência na baixa."""
    from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida

    m = Material.objects.create(
        codigo=codigo,
        nome='Material Saída Excepcional',
        unidade=UnidadeMedida.UNIDADE,
        ativo=True,
    )
    SaldoEstoque.objects.create(
        estoque=estoque,
        material=m,
        saldo_fisico=fisico,
        saldo_reservado=reservado,
    )
    return m


def _baixar_com_aviso(*, ator, estoque, material, quantidade):
    from apps.estoque.services import registrar_saida_excepcional
    from apps.requisicoes.services.ciclo_vida import (
        registrar_timeline_divergencia_saida_excepcional,
    )

    return registrar_saida_excepcional(
        ator_id=ator.pk,
        estoque_id=estoque.pk,
        motivo='Descarte por avaria',
        observacao='Material avariado em vistoria',
        itens=[{'material_id': material.pk, 'quantidade': quantidade}],
        _pos_saida_hook=registrar_timeline_divergencia_saida_excepcional,
    )


@pytest.mark.django_db(transaction=True)
def test_saida_excepcional_com_divergencia_notifica_criador_e_beneficiario(
    chefe_obras, chefe_almoxarifado, setor_obras, outro_solicitante, estoque_principal
):
    """Baixa que cria EST-07 → notifica criador e beneficiário da requisição autorizada."""
    material = _material_com_reserva(
        estoque_principal, codigo='SXP.NOTIF.01', fisico=20, reservado=10
    )
    req = _criar_requisicao_autorizada(
        criador=chefe_obras,
        beneficiario=outro_solicitante,
        setor=setor_obras,
        material=material,
    )

    _baixar_com_aviso(
        ator=chefe_almoxarifado,
        estoque=estoque_principal,
        material=material,
        quantidade='15',
    )

    notifs = Notificacao.objects.filter(
        requisicao_id=req.pk,
        tipo=TipoNotificacao.DIVERGENCIA_ESTOQUE,
    )
    assert notifs.count() == 2
    assert set(notifs.values_list('destinatario_id', flat=True)) == {
        chefe_obras.pk,
        outro_solicitante.pk,
    }


@pytest.mark.django_db(transaction=True)
def test_saida_excepcional_deduplica_criador_igual_beneficiario(
    chefe_almoxarifado, setor_obras, solicitante, estoque_principal
):
    """Criador == beneficiário → 1 notificação."""
    material = _material_com_reserva(
        estoque_principal, codigo='SXP.NOTIF.02', fisico=20, reservado=10
    )
    req = _criar_requisicao_autorizada(
        criador=solicitante,
        beneficiario=solicitante,
        setor=setor_obras,
        material=material,
    )

    _baixar_com_aviso(
        ator=chefe_almoxarifado,
        estoque=estoque_principal,
        material=material,
        quantidade='15',
    )

    assert (
        Notificacao.objects.filter(
            requisicao_id=req.pk,
            tipo=TipoNotificacao.DIVERGENCIA_ESTOQUE,
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_saida_excepcional_sem_divergencia_nao_notifica(
    chefe_almoxarifado, setor_obras, solicitante, estoque_principal
):
    """Baixa que mantém físico >= reservado não gera notificação."""
    material = _material_com_reserva(
        estoque_principal, codigo='SXP.NOTIF.03', fisico=20, reservado=5
    )
    _criar_requisicao_autorizada(
        criador=solicitante,
        beneficiario=solicitante,
        setor=setor_obras,
        material=material,
    )

    _baixar_com_aviso(
        ator=chefe_almoxarifado,
        estoque=estoque_principal,
        material=material,
        quantidade='10',
    )

    assert not Notificacao.objects.filter(
        tipo=TipoNotificacao.DIVERGENCIA_ESTOQUE
    ).exists()
