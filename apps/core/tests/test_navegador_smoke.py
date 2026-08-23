"""Primeiro caso da camada Navegador (ADR-0019).

Prova duas coisas de uma vez.

**Que a lane funciona**: `live_server` sobe o Django com `StaticFilesHandler`,
o Chromium carrega a página autenticada, e Alpine/htmx inicializam de verdade.
Se este arquivo quebrar, o problema é a infraestrutura da camada, não o produto.

**Uma invariante que a ADR-0019 usa como premissa**: `x-trap.inert.noscroll`
ligado a um dado Alpine reativo **realmente** trava a rolagem do fundo. O menu
da barra de aplicação (`base_auth.html`) liga a `menuOpen`, que é dado Alpine, e
funciona. `components/modal.html` liga a `$refs.dialog.open`, que é propriedade
DOM nativa e não é rastreável pelo `effect` — por isso o modal não trava nada
(issue #134).

Este teste guarda o lado que funciona. Sem ele, alguém "consertaria" o modal
copiando a forma quebrada, ou concluiria que `noscroll` nunca funcionou neste
projeto. O lado quebrado ganha teste quando a #134 for consertada.

Critério de admissão atendido: depende de layout real (`documentElement.style
.overflow` só existe depois que o browser aplica o efeito) — nenhuma asserção
sobre HTML renderizado alcança isso.
"""

import pytest
from django.test import Client

pytestmark = pytest.mark.navegador


@pytest.fixture
def pagina_logada(live_server, context, page, chefe_comum):
    """Devolve uma `page` já autenticada como `chefe_comum`, na home.

    O login é feito pelo `Client` do Django e transplantado para o browser como
    cookie de sessão. Preencher o formulário de login em cada teste gastaria um
    round-trip e acoplaria toda a camada à marcação da tela de login — que tem
    testes próprios, na camada certa.
    """
    cliente = Client()
    cliente.force_login(chefe_comum)
    context.add_cookies(
        [
            {
                'name': 'sessionid',
                'value': cliente.cookies['sessionid'].value,
                'url': live_server.url,
            }
        ]
    )
    page.goto(f'{live_server.url}/')
    return page


def test_lane_de_navegador_carrega_pagina_autenticada_com_alpine_e_htmx(pagina_logada):
    """Fumaça da infraestrutura: sem isso, nenhum outro teste da camada vale."""
    assert pagina_logada.evaluate('Boolean(window.Alpine)'), (
        'Alpine não inicializou — a camada não consegue observar comportamento.'
    )
    assert pagina_logada.evaluate('Boolean(window.htmx)'), (
        'htmx não carregou — o ciclo de 422 do modal não seria observável.'
    )
    assert pagina_logada.locator('header.app-bar').count() == 1


def test_x_trap_com_dado_alpine_trava_a_rolagem_do_fundo(pagina_logada):
    """`x-trap.noscroll="menuOpen"` grava `overflow: hidden` no `<html>`.

    Viewport abaixo de `lg` (64rem) porque o hamburger é `lg:hidden` — acima
    disso a navegação é a sidebar fixa e não há popover para prender foco.
    """
    pagina_logada.set_viewport_size({'width': 390, 'height': 844})
    pagina_logada.reload()

    overflow = 'document.documentElement.style.overflow'
    assert pagina_logada.evaluate(overflow) == ''

    abrir = pagina_logada.get_by_role('button', name='Abrir menu')
    abrir.click()
    pagina_logada.wait_for_function(f"{overflow} === 'hidden'")

    # Fecha por `Escape` e não por segundo clique no toggle: o `Escape` é
    # determinístico (`@keydown.escape.window` no `<header>`) e não depende da
    # transição de opacidade do overlay ter assentado. O caminho do clique
    # também funciona, mas expirou uma vez durante a construção deste teste — e
    # o primeiro caso de uma camada nova não é lugar de instabilidade.
    pagina_logada.keyboard.press('Escape')
    pagina_logada.wait_for_function(f"{overflow} !== 'hidden'")
