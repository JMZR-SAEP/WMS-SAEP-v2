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

    medicao = medir_contraste(page)

    assert medicao.nao_convertidas == [], (
        f'O canvas recusou {len(medicao.nao_convertidas)} cor(es) em {rota}, '
        f'então a medição está cega nesses pontos: {medicao.nao_convertidas}'
    )
    assert medicao.nao_suportados == [], (
        f'{rota} usa efeito de CSS que esta varredura não sabe medir, então o '
        f'contraste ali não está sendo guardado:\n'
        + '\n'.join(
            f'  {n["motivo"]} em {n["seletor"]}: {n["valor"]}'
            for n in medicao.nao_suportados
        )
        + '\n\nOu a varredura passa a cobrir o efeito, ou o elemento recebe '
        '`data-contraste-ignorar` com justificativa no template.'
    )
    assert medicao.violacoes == [], (
        f'{len(medicao.violacoes)} texto(s) abaixo do piso WCAG 1.4.3 em {rota}:\n'
        + '\n'.join(
            f'  "{v["texto"]}" ({v["seletor"]}): {v["corTexto"]} sobre '
            f'{v["corFundo"]} = {v["contraste"]}:1, piso {v["limiar"]}:1'
            for v in medicao.violacoes
        )
    )


@pytest.fixture
def pagina_medivel(live_server, context, page, solicitante):
    """Página logada e vazia, para injetar casos controlados.

    `requisicoes:minhas` sem nenhuma requisição: pouca marcação própria, então
    o que os controles abaixo injetam é o que domina a medição.
    """
    autenticar(live_server, context, solicitante)
    page.goto(f'{live_server.url}{reverse("requisicoes:minhas")}')
    return page


def _injetar(page, html):
    page.evaluate(
        '(html) => { const c = document.createElement("div");'
        ' c.innerHTML = html; document.body.appendChild(c); }',
        html,
    )


def test_a_varredura_reprova_texto_cuja_cor_esta_no_filho_e_o_fundo_no_pai(
    pagina_medivel,
):
    """Controle positivo — sem ele, os testes por tela passariam vazios.

    Onze telas que hoje não têm violação nenhuma continuariam verdes se o walker
    parasse de visitar texto ou a conta passasse a aceitar tudo. Este caso é o
    que distingue "não há defeito" de "não há medição": é a forma exata que o
    guarda estático não vê — `background` no pai, `color` no filho — e ela
    **precisa** ser reprovada, com o número medido.
    """
    _injetar(
        pagina_medivel,
        '<div style="background: oklch(0.968 0.007 247.896)">'
        '<span id="alvo" style="color: oklch(0.75 0.02 250)">quase ilegível</span>'
        '</div>',
    )

    medicao = medir_contraste(pagina_medivel)

    alvos = [v for v in medicao.violacoes if v['texto'] == 'quase ilegível']
    assert len(alvos) == 1, (
        'a varredura não reprovou o par pai/filho — é a forma que motivou a '
        f'issue #166. Violações vistas: {medicao.violacoes}'
    )
    violacao = alvos[0]
    assert violacao['limiar'] == 4.5
    assert violacao['contraste'] < 4.5
    # O achado precisa dizer *quanto*, e entre quais cores: sem isso ninguém
    # consegue agir sobre a falha sem reproduzir o teste à mão.
    assert violacao['corTexto'].startswith('rgb(')
    assert violacao['corFundo'].startswith('rgb(')
    assert 'span#alvo' in violacao['seletor']


def test_a_varredura_aprova_o_mesmo_par_quando_o_contraste_e_suficiente(
    pagina_medivel,
):
    """Contraprova do controle positivo: não é o seletor que reprova, é a cor."""
    _injetar(
        pagina_medivel,
        '<div style="background: oklch(0.968 0.007 247.896)">'
        '<span id="alvo" style="color: oklch(0.28 0.03 250)">legível</span>'
        '</div>',
    )

    medicao = medir_contraste(pagina_medivel)

    assert [v for v in medicao.violacoes if v['texto'] == 'legível'] == []


def test_a_varredura_ignora_texto_que_ninguem_ve(pagina_medivel):
    """`display:none` e `sr-only` não têm contraste a medir.

    Sem esta prova, um guarda "seguro demais" que reprovasse tudo passaria pelo
    controle positivo acima e encheria as onze telas de falso positivo.
    """
    _injetar(
        pagina_medivel,
        '<p style="display: none; background: #fff; color: #eee">oculto</p>'
        '<p style="position: absolute; width: 1px; height: 1px; overflow: hidden;'
        ' background: #fff; color: #eee">so para leitor de tela</p>',
    )

    medicao = medir_contraste(pagina_medivel)

    textos = {v['texto'] for v in medicao.violacoes}
    assert 'oculto' not in textos
    assert 'so para leitor de tela' not in textos


def test_a_varredura_acusa_cor_legitima_identica_a_uma_sentinela(pagina_medivel):
    """`fillStyle` inválido não lança — só retém o valor anterior.

    A detecção de recusa usa duas sentinelas justamente para não confundir
    "cor recusada" com "a cor é exatamente a sentinela". Este caso guarda isso.
    """
    _injetar(
        pagina_medivel,
        '<p style="background: rgb(1, 2, 3); color: rgb(20, 22, 24)">sentinela um</p>'
        '<p style="background: #fefdfc; color: #fefdfc">sentinela dois</p>',
    )

    medicao = medir_contraste(pagina_medivel)

    assert medicao.nao_convertidas == []
    textos = {v['texto'] for v in medicao.violacoes}
    assert {'sentinela um', 'sentinela dois'} <= textos


_EFEITOS_NAO_SUPORTADOS = [
    (
        'background-image',
        '<div style="background-image: linear-gradient(#fff, #000)">'
        '<span>sobre gradiente</span></div>',
    ),
    (
        'mix-blend-mode',
        '<p style="mix-blend-mode: multiply; background: #fff; color: #333">'
        'misturado</p>',
    ),
    (
        'opacity de ancestral',
        '<div style="opacity: 0.5"><span style="color: #333">desbotado</span></div>',
    ),
    (
        'texto em ::after',
        '<style>#com-pseudo::after { content: "Passo 1"; }</style>'
        '<p id="com-pseudo">rotulado por pseudo-elemento</p>',
    ),
]


@pytest.mark.parametrize(
    ('motivo', 'html'),
    _EFEITOS_NAO_SUPORTADOS,
    ids=[e[0] for e in _EFEITOS_NAO_SUPORTADOS],
)
def test_a_varredura_acusa_o_efeito_de_css_que_nao_sabe_medir(
    pagina_medivel, motivo, html
):
    """Cegueira declarada é cegueira mesmo assim — tem que falhar, não constar.

    Estes quatro efeitos não existem no produto hoje. O risco não é o presente,
    é o dia em que alguém introduzir um deles: sem detecção, o guarda continuaria
    verde medindo a cor errada, ou medindo nada, sem dizer nada.
    """
    _injetar(pagina_medivel, html)

    medicao = medir_contraste(pagina_medivel)

    motivos = {n['motivo'] for n in medicao.nao_suportados}
    assert motivo in motivos, (
        f'{motivo} passou despercebido — a varredura ficou cega em silêncio. '
        f'Não suportados vistos: {medicao.nao_suportados}'
    )


@pytest.mark.parametrize(
    ('motivo', 'html'),
    _EFEITOS_NAO_SUPORTADOS,
    ids=[e[0] for e in _EFEITOS_NAO_SUPORTADOS],
)
def test_data_contraste_ignorar_e_a_saida_explicita_para_o_efeito_nao_suportado(
    pagina_medivel, motivo, html
):
    """A exceção existe, mas é visível no template — não herdada em silêncio."""
    _injetar(pagina_medivel, f'<div data-contraste-ignorar>{html}</div>')

    medicao = medir_contraste(pagina_medivel)

    assert medicao.nao_suportados == []
    assert medicao.violacoes == []
