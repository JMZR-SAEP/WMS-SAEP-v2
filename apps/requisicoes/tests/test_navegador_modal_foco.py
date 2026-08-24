"""Foco de abertura do modal — camada Navegador (ADR-0019), issue #132.

A regra que estes testes guardam: o foco de abertura de um modal de confirmação
nunca pousa no botão que executa a ação. Modal sem campo visível é exatamente o
que confirma operação irreversível neste sistema, e quem aciona o trigger pelo
teclado chega ao diálogo com o Enter ainda pressionado — o `keydown` repete no
elemento que acabou de receber o foco.

Critério de admissão da ADR-0019 atendido pelas duas vias: `showModal()` põe o
diálogo no top layer e roda os passos nativos de foco antes de `modal.js`
assumir (nenhuma asserção sobre HTML renderizado observa `document.activeElement`),
e o caso do 422 depende da ida e volta real do htmx.

A marcação do contrato — `tabindex="-1"` no corpo, `data-modal-dismiss` no
rodapé, o handler de Enter no `<form>` — fica na lane de baixo, em
`apps/core/tests/test_modal.py`.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.tests.navegador import autenticar
from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

pytestmark = pytest.mark.navegador


@pytest.fixture
def abrir_pagina(live_server, context, page):
    """Fábrica de página autenticada: `abrir_pagina(usuario, caminho)`."""

    def _abrir(usuario, caminho):
        autenticar(live_server, context, usuario)
        page.goto(f'{live_server.url}{caminho}')
        return page

    return _abrir


@pytest.fixture
def req_para_decisao(db, solicitante, setor_obras, material_disponivel):
    """Requisição aguardando autorização — a tela do chefe do setor.

    Dá acesso, numa página só, aos dois lados da regra: `confirmar-autorizar`
    não tem campo nenhum, `confirmar-recusar` abre com textarea obrigatória e
    responde 422 quando o motivo vem vazio.
    """
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-9310',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req,
        material=material_disponivel,
        quantidade_solicitada=Decimal('2'),
    )
    return req


@pytest.fixture
def req_com_devolucao(
    db, solicitante, setor_obras, material_disponivel, aux_almoxarifado
):
    """Requisição atendida com entregue líquida — habilita o modal de devolução.

    É o único modal do sistema cujo primeiro campo é `<input type="number">`,
    ou seja, o único onde a submissão implícita do HTML confirma a operação por
    uma tecla apertada antes da leitura do rodapé.
    """
    from apps.estoque.models import SaldoEstoque
    from apps.requisicoes.services import registrar_atendimento
    from apps.requisicoes.types import LinhaAtendimento

    req = Requisicao.objects.create(
        estado=EstadoRequisicao.PRONTA_PARA_RETIRADA,
        numero_publico='REQ-2026-9311',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    item = ItemRequisicao.objects.create(
        requisicao=req,
        material=material_disponivel,
        quantidade_solicitada=Decimal('5'),
        quantidade_autorizada=Decimal('5'),
    )
    saldo = SaldoEstoque.objects.get(material=material_disponivel)
    saldo.saldo_reservado = (saldo.saldo_reservado or Decimal('0')) + Decimal('5')
    saldo.save(update_fields=['saldo_reservado'])
    registrar_atendimento(
        ator_id=aux_almoxarifado.pk,
        requisicao_id=req.pk,
        itens=[
            LinhaAtendimento(
                item_id=item.pk, quantidade_entregue=Decimal('5'), justificativa=''
            )
        ],
        retirante_nome='Carlos',
    )
    return req


# Espera o foco parar no alvo escolhido por `modal.js`, e não num dos dois
# pousos intermediários do caminho nativo: o próprio `<dialog>` e o
# `[data-modal-body]`, que é `tabindex="-1"` e por isso é o primeiro focável do
# diálogo. Os dois são o estado da janela entre `showModal()` e o `$nextTick` em
# que o controller decide — ler ali mede a ordem de agendamento, não a regra.
# (Modal sem botão de dispensa terminaria legitimamente no corpo; nenhum dos
# casos abaixo é assim, e a lane não é lugar de asserção que espera pelo mesmo
# valor que já é verdade no início.)
_FOCO_ASSENTOU = """
  (id) => {
    const ativo = document.activeElement;
    if (!ativo || !ativo.closest(`dialog#${id}`)) {
      return false;
    }
    return ativo.tagName !== 'DIALOG' && !ativo.hasAttribute('data-modal-body');
  }
"""

_DESCRICAO_DO_FOCO = """
  () => {
    const ativo = document.activeElement;
    return {
      id: ativo.id,
      tag: ativo.tagName,
      dispensa: ativo.hasAttribute('data-modal-dismiss'),
      confirma: ativo.hasAttribute('data-modal-confirm'),
      invalido: ativo.getAttribute('aria-invalid') === 'true',
    };
  }
"""


def _abrir_modal(page, modal_id):
    """Aciona o trigger e espera o foco parar de se mexer dentro do diálogo.

    Esperar só por `dialog.open` não basta: `showModal()` roda os passos
    nativos de foco antes do `$nextTick` em que `modal.js` decide o alvo, e a
    leitura de `document.activeElement` cairia no meio da janela em que o foco
    ainda é o próprio `<dialog>`.
    """
    page.locator(f'[data-modal-trigger="{modal_id}"]').first.click()
    page.wait_for_function(f"document.getElementById('{modal_id}').open")
    page.wait_for_function(_FOCO_ASSENTOU, arg=modal_id)
    return page.evaluate(_DESCRICAO_DO_FOCO)


def test_modal_sem_campo_abre_o_foco_na_dispensa_e_nao_no_confirmar(
    abrir_pagina, chefe_obras, req_para_decisao
):
    """`confirmar-autorizar` não tem campo — o foco vai para "Voltar"."""
    page = abrir_pagina(
        chefe_obras, reverse('requisicoes:detalhe', kwargs={'pk': req_para_decisao.pk})
    )

    foco = _abrir_modal(page, 'confirmar-autorizar')

    assert not foco['confirma'], (
        'O foco de abertura pousou no botão que executa a autorização: '
        f'um Enter reflexo reservaria o saldo. Foco em {foco}.'
    )
    assert foco['dispensa'], f'Foco esperado no botão de dispensa, veio em {foco}.'

    # O alvo novo continua dentro do diálogo certo: é o foco entrando no
    # `<dialog aria-modal="true">` que faz o leitor de tela anunciar o título e a
    # descrição. Mudar para onde o foco vai só é seguro enquanto ele fica aqui
    # dentro, e é só isto que exige navegador — que o `aria-labelledby` aponte
    # para o `<h2>` do próprio modal é fato do HTML renderizado, guardado por
    # `test_dialog_e_nomeado_pelo_titulo_do_proprio_modal` em `test_views.py`.
    assert (
        page.evaluate(
            '() => document.activeElement.closest(\'dialog[aria-modal="true"]\')?.id'
        )
        == 'confirmar-autorizar'
    ), 'O foco saiu do diálogo — sem ele dentro, nada é anunciado na abertura.'


def test_modal_com_campo_abre_o_foco_no_primeiro_campo(
    abrir_pagina, chefe_obras, req_para_decisao
):
    """A perna que já existia continua valendo: campo antes de botão."""
    page = abrir_pagina(
        chefe_obras, reverse('requisicoes:detalhe', kwargs={'pk': req_para_decisao.pk})
    )

    foco = _abrir_modal(page, 'confirmar-recusar')

    assert foco['id'] == 'modal-recusar-motivo', (
        f'Foco esperado na textarea de motivo, veio em {foco}.'
    )


def test_re_render_422_leva_o_foco_ao_campo_invalido(
    abrir_pagina, chefe_obras, req_para_decisao
):
    """Confirmar com motivo vazio devolve 422; o foco vai ao `[aria-invalid]`.

    Depende da ida e volta real do htmx: o swap de `outerHTML` sobre
    `[data-modal-body]` é o que dispara `htmx:afterSwap` e refaz o foco.
    """
    page = abrir_pagina(
        chefe_obras, reverse('requisicoes:detalhe', kwargs={'pk': req_para_decisao.pk})
    )
    _abrir_modal(page, 'confirmar-recusar')

    dialogo = page.locator('dialog#confirmar-recusar')
    dialogo.locator('[data-modal-confirm]').click()
    page.wait_for_selector('dialog#confirmar-recusar [data-modal-erro]')
    page.wait_for_function(
        "() => document.activeElement.getAttribute('aria-invalid') === 'true'"
    )

    foco = page.evaluate(_DESCRICAO_DO_FOCO)
    assert foco['invalido'] and foco['id'] == 'modal-recusar-motivo', (
        f'Depois do 422 o foco tem que voltar ao campo em erro, veio em {foco}.'
    )
    assert dialogo.evaluate('(d) => d.open'), 'O 422 não pode fechar o diálogo.'


def test_enter_no_campo_numerico_nao_confirma_a_devolucao(
    abrir_pagina, aux_almoxarifado, req_com_devolucao
):
    """Submissão implícita do `<form>` está barrada dentro do modal.

    O foco de abertura é o `<input type="number">`; sem a trava, o Enter que a
    pessoa aperta ao terminar de digitar a quantidade grava a devolução sem que
    o rodapé — onde a consequência está escrita — tenha sido lido.
    """
    item = req_com_devolucao.itens.first()
    modal_id = f'devolver-{item.pk}'
    url_devolver = reverse(
        'requisicoes:registrar_devolucao',
        kwargs={'pk': req_com_devolucao.pk, 'item_pk': item.pk},
    )
    page = abrir_pagina(
        aux_almoxarifado,
        reverse('requisicoes:detalhe', kwargs={'pk': req_com_devolucao.pk}),
    )
    enviadas: list[str] = []
    page.on('request', lambda requisicao: enviadas.append(requisicao.url))

    foco = _abrir_modal(page, modal_id)
    assert foco['tag'] == 'INPUT', (
        f'Foco esperado no campo de quantidade, veio em {foco}.'
    )

    page.keyboard.type('2')
    # Asserção negativa não pode ser cronometrada: uma soneca fixa passa num CI
    # lento mesmo se a regressão voltar, e um teste que nunca observa é pior que
    # um instável. A sentinela é uma requisição emitida DEPOIS do Enter — os
    # eventos de rede chegam na ordem em que a página os emitiu, então, quando
    # ela aparece, um POST disparado pelo Enter já estaria na lista.
    with page.expect_request(lambda req: 'sentinela-de-ordem' in req.url):
        page.keyboard.press('Enter')
        page.evaluate("() => { fetch(location.pathname + '?sentinela-de-ordem=1'); }")

    assert not any(url_devolver in url for url in enviadas), (
        'Enter no campo numérico submeteu o form do modal de devolução.'
    )
    assert page.locator(f'dialog#{modal_id}').evaluate('(d) => d.open'), (
        'O diálogo deveria continuar aberto, com a decisão ainda na tela.'
    )
