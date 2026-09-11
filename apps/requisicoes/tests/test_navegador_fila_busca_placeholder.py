"""Camada Navegador (ADR-0019) — geometria do placeholder de busca (#194).

`test_*_placeholder_de_busca_cabe_a_375` (test_views.py) só verifica a
string renderizada — não prova que o texto cabe visualmente no campo a
375px, que foi o defeito original (a string-fonte já estava correta; o
corte era do input, não do texto). `placeholder` não é nó de texto real do
DOM (não altera `scrollWidth`), então a única forma confiável de provar
"cabe" é medir o texto com a fonte computada do próprio input via canvas e
comparar contra a largura útil (`clientWidth` menos padding).
"""

import pytest
from django.urls import reverse

from apps.core.tests.navegador import autenticar

pytestmark = pytest.mark.navegador

MOBILE = {'width': 375, 'height': 812}

_PLACEHOLDER_CABE = """
(seletor) => {
    const input = document.querySelector(seletor);
    const estilo = getComputedStyle(input);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.font = `${estilo.fontStyle} ${estilo.fontWeight} ${estilo.fontSize} ${estilo.fontFamily}`;
    const larguraTexto = ctx.measureText(input.placeholder).width;
    const padding = parseFloat(estilo.paddingLeft) + parseFloat(estilo.paddingRight);
    const larguraUtil = input.clientWidth - padding;
    return larguraTexto <= larguraUtil;
}
"""


@pytest.fixture
def abrir_pagina(live_server, context, page):
    def _abrir(usuario, caminho):
        autenticar(live_server, context, usuario)
        page.set_viewport_size(MOBILE)
        page.goto(f'{live_server.url}{caminho}')
        return page

    return _abrir


def test_fila_autorizacao_placeholder_nao_corta_a_375(abrir_pagina, chefe_obras):
    page = abrir_pagina(chefe_obras, reverse('requisicoes:autorizacoes'))
    page.wait_for_selector('#busca-autorizacoes')

    assert page.evaluate(_PLACEHOLDER_CABE, '#busca-autorizacoes')


def test_fila_atendimento_placeholder_nao_corta_a_375(abrir_pagina, aux_almoxarifado):
    page = abrir_pagina(aux_almoxarifado, reverse('requisicoes:atendimentos'))
    page.wait_for_selector('#busca-atendimentos')

    assert page.evaluate(_PLACEHOLDER_CABE, '#busca-atendimentos')


def test_minhas_placeholder_nao_corta_a_375(abrir_pagina, solicitante):
    page = abrir_pagina(solicitante, reverse('requisicoes:minhas'))
    page.wait_for_selector('#busca-minhas')

    assert page.evaluate(_PLACEHOLDER_CABE, '#busca-minhas')
