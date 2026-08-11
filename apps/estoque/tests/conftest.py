"""Fixtures compartilhadas pelos testes de estoque.

Sem factory_boy, sem seed_dev como pré-condição (ADR-0010).
"""

import pytest

from apps.accounts.models import Setor, SetorClassificacao, User, VinculoAuxiliar
from apps.estoque.models import Estoque


@pytest.fixture
def setor_almoxarifado(db):
    return Setor.objects.create(
        codigo='ALM', nome='Almoxarifado', classificacao=SetorClassificacao.ALMOXARIFADO
    )


@pytest.fixture
def setor_obras(db):
    return Setor.objects.create(
        codigo='OBR', nome='Obras', classificacao=SetorClassificacao.COMUM
    )


@pytest.fixture
def chefe_almoxarifado(db, setor_almoxarifado):
    u = User.objects.create_user(
        matricula='021',
        nome='Roberto Chefe Almox',
        password='senha',
        setor=setor_almoxarifado,
    )
    setor_almoxarifado.chefe = u
    setor_almoxarifado.save(update_fields=['chefe'])
    return u


@pytest.fixture
def aux_almoxarifado(db, setor_almoxarifado):
    u = User.objects.create_user(
        matricula='020',
        nome='Luisa Aux Almox',
        password='senha',
        setor=setor_almoxarifado,
    )
    VinculoAuxiliar.objects.create(usuario=u, setor=setor_almoxarifado, ativo=True)
    return u


@pytest.fixture
def solicitante(db, setor_obras):
    return User.objects.create_user(
        matricula='001',
        nome='Joao Solicitante',
        password='senha',
        setor=setor_obras,
    )


@pytest.fixture
def superuser(db, setor_obras):
    return User.objects.create_superuser(
        matricula='900',
        nome='Super Usuario',
        password='senha',
        setor=setor_obras,
    )


@pytest.fixture
def usuario_inativo(db, setor_almoxarifado):
    u = User.objects.create_user(
        matricula='098',
        nome='Inativo Almox',
        password='senha',
        setor=setor_almoxarifado,
        is_active=False,
    )
    setor_almoxarifado.chefe = u
    setor_almoxarifado.save(update_fields=['chefe'])
    return u


@pytest.fixture
def chefe_obras(db, setor_obras):
    u = User.objects.create_user(
        matricula='010',
        nome='Carla Chefe Obras',
        password='senha',
        setor=setor_obras,
    )
    setor_obras.chefe = u
    setor_obras.save(update_fields=['chefe'])
    return u


@pytest.fixture
def aux_obras(db, setor_obras):
    u = User.objects.create_user(
        matricula='011',
        nome='Bruno Aux Obras',
        password='senha',
        setor=setor_obras,
    )
    VinculoAuxiliar.objects.create(usuario=u, setor=setor_obras, ativo=True)
    return u


@pytest.fixture
def movimentacao_outro_setor(
    db, solicitante, material_disponivel, estoque_principal, chefe_almoxarifado
):
    """RESERVA de requisição de um setor distinto de obras (não-vazamento)."""
    from decimal import Decimal

    from apps.accounts.models import Setor, SetorClassificacao
    from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque
    from apps.requisicoes.models import EstadoRequisicao, Requisicao

    setor_ti = Setor.objects.create(
        codigo='TI', nome='TI', classificacao=SetorClassificacao.COMUM
    )
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AUTORIZADA,
        numero_publico='REQ-2025-000099',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_ti,
    )
    return MovimentacaoEstoque.objects.create(
        tipo=TipoMovimentacaoEstoque.RESERVA,
        material=material_disponivel,
        estoque=estoque_principal,
        delta_fisico=Decimal('0'),
        delta_reservado=Decimal('3'),
        requisicao=req,
        ator=chefe_almoxarifado,
    )


@pytest.fixture
def estoque_principal(db):
    return Estoque.objects.create(codigo='EST01', nome='Estoque Principal')


@pytest.fixture
def material_disponivel(db, estoque_principal):
    from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida

    m = Material.objects.create(
        codigo='MAT001', nome='Parafuso M6', unidade=UnidadeMedida.UNIDADE, ativo=True
    )
    SaldoEstoque.objects.create(
        estoque=estoque_principal, material=m, saldo_fisico=100, saldo_reservado=10
    )
    return m


@pytest.fixture
def saida_registrada(db, chefe_almoxarifado, estoque_principal, material_disponivel):
    from apps.estoque.services import registrar_saida_excepcional

    return registrar_saida_excepcional(
        ator_id=chefe_almoxarifado.pk,
        estoque_id=estoque_principal.pk,
        motivo='Descarte por avaria',
        observacao='Itens danificados',
        itens=[{'material_id': material_disponivel.pk, 'quantidade': '5'}],
    )


@pytest.fixture
def material_scpi(db, estoque_principal):
    """Material com código no formato real SCPI (000.000.000) para testes de preview."""
    from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida

    m = Material.objects.create(
        codigo='000.000.001',
        nome='Parafuso M6',
        unidade=UnidadeMedida.UNIDADE,
        ativo=True,
    )
    SaldoEstoque.objects.create(
        estoque=estoque_principal, material=m, saldo_fisico=100, saldo_reservado=0
    )
    return m


@pytest.fixture
def material_scpi_critico(db, estoque_principal):
    """Material com código SCPI e divergência crítica (físico < reservado)."""
    from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida

    m = Material.objects.create(
        codigo='000.000.002',
        nome='Tinta Branca 18L',
        unidade=UnidadeMedida.LITRO,
        ativo=True,
    )
    SaldoEstoque.objects.create(
        estoque=estoque_principal,
        material=m,
        saldo_fisico=2,
        saldo_reservado=5,
    )
    return m


@pytest.fixture
def requisicao_autorizada_critico(db, solicitante, setor_obras, material_scpi_critico):
    """Requisição autorizada com item do material_scpi_critico (qty_autorizada > 0)."""
    from decimal import Decimal

    from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AUTORIZADA,
        numero_publico='REQ-2025-000001',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req,
        material=material_scpi_critico,
        quantidade_solicitada=Decimal('3'),
        quantidade_autorizada=Decimal('3'),
    )
    return req


@pytest.fixture
def movimentacao_requisicao_do_aux(
    db, aux_obras, setor_obras, material_disponivel, estoque_principal
):
    """CONSUMO de requisição do setor obras criada pelo próprio ``aux_obras``."""
    from decimal import Decimal

    from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque
    from apps.requisicoes.models import EstadoRequisicao, Requisicao

    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AUTORIZADA,
        numero_publico='REQ-2025-000112',
        criador=aux_obras,
        beneficiario=aux_obras,
        setor_beneficiario=setor_obras,
    )
    return MovimentacaoEstoque.objects.create(
        tipo=TipoMovimentacaoEstoque.CONSUMO,
        material=material_disponivel,
        estoque=estoque_principal,
        delta_fisico=Decimal('-2'),
        delta_reservado=Decimal('-2'),
        requisicao=req,
        ator=aux_obras,
    )


@pytest.fixture
def movimentacao_criada_pelo_chefe(
    db, chefe_obras, material_disponivel, estoque_principal
):
    """Movimentação de requisição criada pelo chefe de obras para setor que ele não chefia."""
    from decimal import Decimal

    from apps.accounts.models import Setor, SetorClassificacao
    from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque
    from apps.requisicoes.models import EstadoRequisicao, Requisicao

    setor_adm = Setor.objects.create(
        codigo='ADM', nome='Administrativo', classificacao=SetorClassificacao.COMUM
    )
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AUTORIZADA,
        numero_publico='REQ-2025-000113',
        criador=chefe_obras,
        beneficiario=chefe_obras,
        setor_beneficiario=setor_adm,
    )
    return MovimentacaoEstoque.objects.create(
        tipo=TipoMovimentacaoEstoque.CONSUMO,
        material=material_disponivel,
        estoque=estoque_principal,
        delta_fisico=Decimal('-1'),
        delta_reservado=Decimal('-1'),
        requisicao=req,
        ator=chefe_obras,
    )


@pytest.fixture
def movimentacao_requisicao_rascunho(
    db, aux_obras, setor_obras, material_disponivel, estoque_principal
):
    """Par que nenhum service produz: movimentação sobre requisição em RASCUNHO.

    O model aceita (``requisicao`` é anulável, sem constraint de estado), então o
    não-vazamento do ledger não pode depender do comportamento dos services.
    """
    from decimal import Decimal

    from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque
    from apps.requisicoes.models import EstadoRequisicao, Requisicao

    req = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        numero_publico='REQ-2025-000114',
        criador=aux_obras,
        beneficiario=aux_obras,
        setor_beneficiario=setor_obras,
    )
    return MovimentacaoEstoque.objects.create(
        tipo=TipoMovimentacaoEstoque.RESERVA,
        material=material_disponivel,
        estoque=estoque_principal,
        delta_fisico=Decimal('0'),
        delta_reservado=Decimal('1'),
        requisicao=req,
        ator=aux_obras,
    )


@pytest.fixture
def aux_lotacao_divergente(db, setor_obras, material_disponivel, estoque_principal):
    """Auxiliar lotado num setor e com vínculo de auxiliar em outro.

    ``VinculoAuxiliar`` é independente de ``User.setor``: aqui a lotação é
    financeiro e o vínculo é obras. A requisição que ele cria para si fica em
    financeiro, fora de ``setores_em_escopo``.
    """
    from decimal import Decimal

    from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque
    from apps.requisicoes.models import EstadoRequisicao, Requisicao

    setor_financeiro = Setor.objects.create(
        codigo='FIN', nome='Financeiro', classificacao=SetorClassificacao.COMUM
    )
    usuario = User.objects.create_user(
        matricula='012',
        nome='Dora Aux Lotacao Divergente',
        password='senha',
        setor=setor_financeiro,
    )
    VinculoAuxiliar.objects.create(usuario=usuario, setor=setor_obras, ativo=True)
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AUTORIZADA,
        numero_publico='REQ-2025-000115',
        criador=usuario,
        beneficiario=usuario,
        setor_beneficiario=setor_financeiro,
    )
    movimentacao = MovimentacaoEstoque.objects.create(
        tipo=TipoMovimentacaoEstoque.CONSUMO,
        material=material_disponivel,
        estoque=estoque_principal,
        delta_fisico=Decimal('-1'),
        delta_reservado=Decimal('-1'),
        requisicao=req,
        ator=usuario,
    )
    return usuario, movimentacao


@pytest.fixture
def requisicao_autorizavel(db, solicitante, setor_obras, material_disponivel):
    """Requisição em AGUARDANDO_AUTORIZACAO pronta para reservar saldo."""
    from decimal import Decimal

    from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2025-000010',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req,
        material=material_disponivel,
        quantidade_solicitada=Decimal('5'),
    )
    return req


@pytest.fixture
def requisicao_autorizada(
    db, solicitante, setor_obras, material_disponivel, chefe_almoxarifado
):
    """Requisição em AUTORIZADA com saldo reservado (via service)."""
    from apps.estoque.services import (
        OrigemMovimentacaoEstoque,
        reservar_saldos_para_autorizacao,
    )
    from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AUTORIZADA,
        numero_publico='REQ-2025-000011',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    item = ItemRequisicao.objects.create(
        requisicao=req,
        material=material_disponivel,
        quantidade_solicitada=5,
        quantidade_autorizada=5,
    )
    from decimal import Decimal

    reservar_saldos_para_autorizacao(
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('5'),
            }
        ],
        ator_id=chefe_almoxarifado.pk,
        origem=OrigemMovimentacaoEstoque.de_requisicao(req),
    )
    return req, item
