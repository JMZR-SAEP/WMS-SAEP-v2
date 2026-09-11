"""Camada Navegador (ADR-0019) — travessia por teclado na fila (#194).

Critério de admissão: depende de foco real (`document.activeElement`) e de
evento de teclado real (`page.keyboard.press`) — não provável por atributo
estático no HTML renderizado.
"""

import pytest
from django.urls import reverse

from apps.core.tests.navegador import autenticar
from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

pytestmark = pytest.mark.navegador


@pytest.fixture
def abrir_pagina(live_server, context, page):
    def _abrir(usuario, caminho):
        autenticar(live_server, context, usuario)
        page.goto(f'{live_server.url}{caminho}')
        return page

    return _abrir


@pytest.fixture
def duas_requisicoes_na_fila(db, solicitante, setor_obras, material_disponivel):
    reqs = []
    for numero in ('REQ-2026-8401', 'REQ-2026-8402'):
        req = Requisicao.objects.create(
            estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico=numero,
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_obras,
        )
        ItemRequisicao.objects.create(
            requisicao=req,
            material=material_disponivel,
            quantidade_solicitada=1,
        )
        reqs.append(req)
    return reqs


def test_seta_para_baixo_move_o_foco_para_o_proximo_cartao(
    abrir_pagina, chefe_obras, duas_requisicoes_na_fila
):
    page = abrir_pagina(chefe_obras, reverse('requisicoes:autorizacoes'))
    page.wait_for_selector('[data-cartao-link]')

    links = page.locator('[data-cartao-link]')
    links.first.focus()
    primeiro_texto = page.evaluate('document.activeElement.textContent.trim()')

    page.keyboard.press('ArrowDown')
    segundo_texto = page.evaluate('document.activeElement.textContent.trim()')

    assert primeiro_texto != segundo_texto
    assert segundo_texto == links.nth(1).text_content().strip()


def test_seta_para_cima_no_primeiro_cartao_volta_para_o_ultimo(
    abrir_pagina, chefe_obras, duas_requisicoes_na_fila
):
    page = abrir_pagina(chefe_obras, reverse('requisicoes:autorizacoes'))
    page.wait_for_selector('[data-cartao-link]')

    links = page.locator('[data-cartao-link]')
    links.first.focus()

    page.keyboard.press('ArrowUp')
    texto_atual = page.evaluate('document.activeElement.textContent.trim()')

    assert texto_atual == links.last.text_content().strip()


def test_seta_para_baixo_fora_do_container_nao_move_foco(
    abrir_pagina, chefe_obras, duas_requisicoes_na_fila
):
    """O listener é escopado ao container — o campo de busca não é afetado."""
    page = abrir_pagina(chefe_obras, reverse('requisicoes:autorizacoes'))
    page.wait_for_selector('#busca-autorizacoes')

    page.locator('#busca-autorizacoes').focus()
    page.keyboard.press('ArrowDown')
    id_do_ativo = page.evaluate('document.activeElement.id')

    assert id_do_ativo == 'busca-autorizacoes'
