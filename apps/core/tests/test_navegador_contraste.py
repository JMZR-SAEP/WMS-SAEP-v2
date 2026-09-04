"""Varredura de contraste WCAG 1.4.3 nas telas do produto (issue #166).

Fecha o limite conhecido de `test_nenhum_elemento_combina_par_de_cor_reprovado`
(`test_tokens_semanticos.py`): o guarda estático vê par de cor no **mesmo
elemento**, e o defeito que motivou a regra tinha o fundo no `<div>` pai e a cor
no `<span>` filho — passava por ele.

Critério de admissão da ADR-0019 atendido pelo item 4, "cascade resolvida e
pipeline de cor" — acrescentado à ADR pela Emenda de 2026-09-04, que este teste
motivou. Resolver o fundo efetivo subindo a cadeia de ancestrais, compor alpha e
converter `oklch()` para sRGB não cabia em nenhum dos três critérios originais e
nenhuma asserção sobre HTML renderizado alcança.

A medição em si vive em `apps/core/tests/navegador_contraste.js`; este arquivo
escolhe as telas, monta o cenário e nomeia a falha.
"""

import pytest
from django.urls import reverse

from apps.accounts.models import User, VinculoAuxiliar
from apps.core.tests.navegador import autenticar, medir_contraste
from apps.estoque.models import (
    Estoque,
    Material,
    MovimentacaoEstoque,
    SaldoEstoque,
    TipoMovimentacaoEstoque,
    UnidadeMedida,
)
from apps.estoque.services import registrar_saida_excepcional
from apps.notificacoes.models import Notificacao, TipoNotificacao
from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

pytestmark = pytest.mark.navegador


@pytest.fixture
def aux_almox(db, setor_almoxarifado):
    """Auxiliar de almoxarifado — papel derivado de `VinculoAuxiliar` ativo.

    Não existe fixture dele em `conftest.py` e não há model de papel: a
    condição é vínculo ativo cujo setor é o do almoxarifado (ADR-0001).
    """
    usuario = User.objects.create_user(
        matricula='022',
        nome='Auxiliar Almoxarifado',
        password='senha',
        setor=setor_almoxarifado,
    )
    VinculoAuxiliar.objects.create(
        usuario=usuario, setor=setor_almoxarifado, ativo=True
    )
    return usuario


@pytest.fixture
def cenario(db, setor_comum, setor_almoxarifado, chefe_comum, chefe_almox, solicitante):
    """Uma requisição por estado, uma movimentação por tipo, uma saída real.

    O objetivo é que cada variante de badge apareça pelo menos uma vez — é onde
    vive a maior parte do risco de contraste. São 8 requisições e 7
    movimentações: cabe folgado na primeira página das listagens (25 por
    página), então nenhuma tela precisa paginar para ser medida por inteiro.
    """
    estoque = Estoque.objects.create(codigo='EST01', nome='Estoque Principal')
    material = Material.objects.create(
        codigo='MAT001', nome='Parafuso sextavado M6', unidade=UnidadeMedida.UNIDADE
    )
    material_metro = Material.objects.create(
        codigo='MAT002', nome='Cabo flexível 2,5 mm²', unidade=UnidadeMedida.METRO
    )
    SaldoEstoque.objects.create(
        estoque=estoque, material=material, saldo_fisico=500, saldo_reservado=10
    )
    SaldoEstoque.objects.create(
        estoque=estoque, material=material_metro, saldo_fisico=250, saldo_reservado=0
    )

    requisicoes = {}
    for sequencia, estado in enumerate(EstadoRequisicao, start=1):
        requisicao = Requisicao.objects.create(
            estado=estado,
            # Rascunho não tem número emitido — e o template cai num caminho
            # próprio (`text-tertiary` em "Rascunho — nome"), que também precisa
            # ser medido.
            numero_publico=(
                None
                if estado == EstadoRequisicao.RASCUNHO
                else f'REQ-2026-{sequencia:06d}'
            ),
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_comum,
        )
        ItemRequisicao.objects.create(
            requisicao=requisicao, material=material, quantidade_solicitada='12.000'
        )
        ItemRequisicao.objects.create(
            requisicao=requisicao,
            material=material_metro,
            quantidade_solicitada='3.500',
        )
        requisicoes[estado] = requisicao

    saida = registrar_saida_excepcional(
        ator_id=chefe_almox.pk,
        estoque_id=estoque.pk,
        motivo='Material avariado no transporte.',
        observacao='Descarte autorizado pela chefia.',
        itens=[{'material_id': material.pk, 'quantidade': '4'}],
    )

    # Uma linha por tipo do ledger, para dar ao histórico todas as variantes de
    # `_badge_tipo_movimentacao.html` — inclusive `consumption` (índigo) e
    # `reversal` (violeta), as duas migradas na #177. A constraint
    # `movimentacao_tipo_origem_coerente` dita qual origem cada tipo aceita; o
    # tipo de saída já veio do service acima.
    referencia = requisicoes[EstadoRequisicao.ATENDIDA]
    for tipo, delta_fisico, delta_reservado in [
        (TipoMovimentacaoEstoque.RESERVA, 0, 12),
        (TipoMovimentacaoEstoque.LIBERACAO, 0, -12),
        (TipoMovimentacaoEstoque.CONSUMO, -12, 0),
        (TipoMovimentacaoEstoque.DEVOLUCAO, 3, 0),
        (TipoMovimentacaoEstoque.ESTORNO_REQUISICAO, 12, 0),
    ]:
        MovimentacaoEstoque.objects.create(
            tipo=tipo,
            material=material,
            estoque=estoque,
            delta_fisico=delta_fisico,
            delta_reservado=delta_reservado,
            requisicao=referencia,
            ator=chefe_almox,
        )
    MovimentacaoEstoque.objects.create(
        tipo=TipoMovimentacaoEstoque.ESTORNO_SAIDA,
        material=material,
        estoque=estoque,
        delta_fisico=4,
        saida_excepcional=saida,
        ator=chefe_almox,
    )

    pendente = requisicoes[EstadoRequisicao.AGUARDANDO_AUTORIZACAO]
    Notificacao.objects.create(
        destinatario=chefe_comum,
        tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
        requisicao_id=pendente.pk,
        lida=False,
    )
    Notificacao.objects.create(
        destinatario=chefe_comum,
        tipo=TipoNotificacao.ATENDIMENTO,
        requisicao_id=requisicoes[EstadoRequisicao.ATENDIDA].pk,
        lida=True,
    )

    return {
        'requisicao_pendente': pendente,
        'saida': saida,
        'estoque': estoque,
        'material': material,
    }


# Papel por tela conferido contra `docs/matriz-permissoes.md` e as policies: o
# papel escolhido é o que abre com 200 **e** vê a tela mais rica (mais botões,
# mais badges, mais faixas de dado). Papel mais pobre mediria menos superfície.
#
# `core:home` não entra: é dispatcher puro, sempre 302, e o destino varia por
# papel. Os destinos entram por nome próprio — `minhas` e `atendimentos`.
_TELAS = [
    ('requisicoes:minhas', None, 'solicitante'),
    ('requisicoes:historico', None, 'chefe_almox'),
    ('requisicoes:autorizacoes', None, 'chefe_comum'),
    ('requisicoes:atendimentos', None, 'chefe_almox'),
    ('requisicoes:nova_requisicao', None, 'aux_almox'),
    ('requisicoes:detalhe', 'requisicao_pendente', 'chefe_comum'),
    ('estoque:lista_materiais', None, 'chefe_almox'),
    ('estoque:historico_movimentacoes', None, 'chefe_almox'),
    ('estoque:listar_saidas_excepcionais', None, 'chefe_almox'),
    ('estoque:detalhe_saida_excepcional', 'saida', 'chefe_almox'),
    ('notificacoes:lista', None, 'chefe_comum'),
]


@pytest.mark.parametrize(
    ('rota', 'chave_pk', 'papel'), _TELAS, ids=[t[0] for t in _TELAS]
)
def test_nenhum_texto_visivel_reprova_o_contraste_minimo(
    live_server, context, page, cenario, request, rota, chave_pk, papel
):
    """Todo nó de texto visível atinge 4,5:1 (ou 3:1, se texto grande).

    A falha carrega o número medido e o par de cores: sem o número não é achado,
    é só uma reprovação sem endereço.
    """
    usuario = request.getfixturevalue(papel)
    autenticar(live_server, context, usuario)

    kwargs = {'pk': cenario[chave_pk].pk} if chave_pk else {}
    resposta = page.goto(f'{live_server.url}{reverse(rota, kwargs=kwargs)}')
    assert resposta.status == 200, (
        f'{rota} respondeu {resposta.status} para {papel} — o papel do parametrize '
        f'não abre esta tela, e nada foi medido.'
    )

    violacoes, nao_convertidas = medir_contraste(page)

    assert nao_convertidas == [], (
        f'O canvas recusou {len(nao_convertidas)} cor(es) em {rota}, então a '
        f'medição está cega nesses pontos: {nao_convertidas}'
    )
    assert violacoes == [], (
        f'{len(violacoes)} texto(s) abaixo do piso WCAG 1.4.3 em {rota}:\n'
        + '\n'.join(
            f'  "{v["texto"]}" ({v["seletor"]}): {v["corTexto"]} sobre '
            f'{v["corFundo"]} = {v["contraste"]}:1, piso {v["limiar"]}:1'
            for v in violacoes
        )
    )
