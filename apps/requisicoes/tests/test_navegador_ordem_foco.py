"""Camada Navegador (ADR-0019) — ordem de foco das pilhas de ação (issue #186).

Guarda **A Regra da Pilha que Segue o DOM** (`DESIGN.md` §Layout): abaixo de
640px uma pilha de ações desce na tela na ordem do DOM, que é a mesma ordem em
que o Tab a visita. `flex-col-reverse` quebrava isso — o olho lia
`[Enviar, Editar, Descartar]` e o Tab visitava `[Descartar, Editar, Enviar]`,
falha de WCAG 2.4.3.

Critério de admissão: o caso compara a posição vertical renderizada (`top` do
`getBoundingClientRect`) com a ordem de tabulação real (`Tab` + `activeElement`)
num viewport de 375px. Nenhuma asserção sobre o HTML do servidor observa
geometria de layout nem foco.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.tests.navegador import autenticar
from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

pytestmark = pytest.mark.navegador

MOBILE = {'width': 375, 'height': 812}


def _controles_visiveis(page, seletor_container):
    """`[{texto, top}]` de cada <a>/<button> visível dentro do container, na
    ordem do DOM. Filtra filhos de `<dialog>` fechado (rect vazio)."""
    return page.evaluate(
        """(seletor) => {
            const container = document.querySelector(seletor);
            const nós = container.querySelectorAll('a[href], button');
            return [...nós]
                .filter((el) => el.getClientRects().length > 0)
                .map((el) => ({
                    texto: el.textContent.replace(/\\s+/g, ' ').trim(),
                    top: el.getBoundingClientRect().top,
                }));
        }""",
        seletor_container,
    )


def _ordem_de_tabulacao(page, seletor_container, quantos):
    """Foca o primeiro controle do container e devolve o texto de cada
    `activeElement` a cada `Tab`, incluindo o de partida."""
    page.evaluate(
        """(seletor) => {
            const container = document.querySelector(seletor);
            const primeiro = [...container.querySelectorAll('a[href], button')]
                .find((el) => el.getClientRects().length > 0);
            primeiro.focus();
        }""",
        seletor_container,
    )
    visitados = [
        page.evaluate('document.activeElement.textContent.replace(/\\s+/g, " ").trim()')
    ]
    for _ in range(quantos - 1):
        page.keyboard.press('Tab')
        visitados.append(
            page.evaluate(
                'document.activeElement.textContent.replace(/\\s+/g, " ").trim()'
            )
        )
    return visitados


@pytest.fixture
def abrir_pagina(live_server, context, page):
    def _abrir(usuario, caminho):
        autenticar(live_server, context, usuario)
        page.set_viewport_size(MOBILE)
        page.goto(f'{live_server.url}{caminho}')
        return page

    return _abrir


@pytest.fixture
def rascunho_do_solicitante(db, solicitante, setor_obras, material_disponivel):
    """Rascunho do próprio criador — a seção "Pronto para enviar?" traz as três
    ações: Descartar (destrutiva), Editar (secundária), Enviar (primária)."""
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
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
def recusada_do_solicitante(db, solicitante, setor_obras, material_disponivel):
    """Requisição recusada do próprio criador — habilita a tela de cópia, cuja
    pilha de ações é Cancelar (secundária) + Criar rascunho (primária)."""
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.RECUSADA,
        numero_publico='REQ-2026-0001',
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


def test_detalhe_a_ordem_visual_da_pilha_bate_com_a_de_foco_a_375(
    abrir_pagina, solicitante, rascunho_do_solicitante
):
    """`requisicoes/detalhe.html` — o item mais sério da fatia (c) da #173."""
    page = abrir_pagina(solicitante, f'/requisicoes/{rascunho_do_solicitante.pk}/')
    container = 'section[aria-labelledby="acoes-titulo"]'
    page.wait_for_selector(container)

    controles = _controles_visiveis(page, container)
    textos = [c['texto'] for c in controles]
    assert textos == [
        'Descartar rascunho',
        'Editar rascunho',
        'Enviar para autorização',
    ], f'a pilha de ações não traz os três controles esperados: {controles}'
    tops = [c['top'] for c in controles]
    assert all(anterior < seguinte for anterior, seguinte in zip(tops, tops[1:])), (
        f'a pilha não desce estritamente na vertical a 375px (regressão de '
        f'`flex-row`?): {controles}'
    )

    tabulacao = _ordem_de_tabulacao(page, container, len(controles))
    assert tabulacao == textos, f'Tab visita a pilha fora da ordem visual: {tabulacao}'


@pytest.fixture
def aguardando_autorizacao(db, solicitante, setor_obras, material_disponivel):
    """Requisição aguardando autorização — a tela do chefe do setor traz o
    modal `confirmar-autorizar`, sem campo, cujo rodapé é
    Voltar (dispensa) + Confirmar autorização (primária)."""
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-0190',
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


# O foco de abertura assenta num alvo dentro do diálogo que não é o próprio
# `<dialog>` nem o `[data-modal-body]` (`tabindex="-1"`) — os dois pousos
# nativos intermediários antes de `modal.js` decidir. Mesmo predicado de
# `test_navegador_modal_foco.py`.
_FOCO_ASSENTOU = """
  (id) => {
    const ativo = document.activeElement;
    if (!ativo || !ativo.closest(`dialog#${id}`)) { return false; }
    return ativo.tagName !== 'DIALOG' && !ativo.hasAttribute('data-modal-body');
  }
"""


def _abrir_modal(page, modal_id):
    """Aciona o trigger e espera o foco parar de se mexer dentro do diálogo."""
    page.locator(f'[data-modal-trigger="{modal_id}"]').first.click()
    page.wait_for_function(f"document.getElementById('{modal_id}').open")
    page.wait_for_function(_FOCO_ASSENTOU, arg=modal_id)


def test_modal_footer_a_ordem_visual_bate_com_a_de_foco_a_375(
    abrir_pagina, chefe_obras, aguardando_autorizacao
):
    """`components/_modal_body.html` — o rodapé de todo modal (ponto global da
    #190). A 375px o `<footer>` desce em `flex-col` na ordem do DOM e o Tab
    visita a pilha na mesma ordem (WCAG 2.4.3)."""
    page = abrir_pagina(
        chefe_obras,
        reverse('requisicoes:detalhe', kwargs={'pk': aguardando_autorizacao.pk}),
    )
    _abrir_modal(page, 'confirmar-autorizar')
    container = 'dialog#confirmar-autorizar footer'
    page.wait_for_selector(container)

    controles = _controles_visiveis(page, container)
    textos = [c['texto'] for c in controles]
    assert textos == ['Voltar', 'Confirmar autorização'], (
        f'o rodapé do modal não traz os dois controles esperados: {controles}'
    )
    tops = [c['top'] for c in controles]
    assert all(anterior < seguinte for anterior, seguinte in zip(tops, tops[1:])), (
        f'o rodapé não desce estritamente na vertical a 375px '
        f'(regressão de `flex-col-reverse`?): {controles}'
    )

    tabulacao = _ordem_de_tabulacao(page, container, len(controles))
    assert tabulacao == textos, (
        f'Tab visita o rodapé do modal fora da ordem visual: {tabulacao}'
    )


def test_copiar_confirmacao_a_ordem_visual_bate_com_a_de_foco_a_375(
    abrir_pagina, solicitante, recusada_do_solicitante
):
    """Mesmo defeito, `requisicoes/copiar_confirmacao.html`."""
    page = abrir_pagina(
        solicitante, f'/requisicoes/{recusada_do_solicitante.pk}/copiar/'
    )
    container = 'form[action*="/copiar/"] > div'
    page.wait_for_selector(container)

    controles = _controles_visiveis(page, container)
    textos = [c['texto'] for c in controles]
    assert textos == ['Cancelar', 'Criar rascunho'], (
        f'a pilha de ações não traz os dois controles esperados: {controles}'
    )
    tops = [c['top'] for c in controles]
    assert all(anterior < seguinte for anterior, seguinte in zip(tops, tops[1:])), (
        f'a pilha não desce estritamente na vertical a 375px (regressão de '
        f'`flex-row`?): {controles}'
    )

    tabulacao = _ordem_de_tabulacao(page, container, len(controles))
    assert tabulacao == textos, f'Tab visita a pilha fora da ordem visual: {tabulacao}'
