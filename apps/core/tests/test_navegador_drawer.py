"""Camada Navegador (ADR-0019) — affordance de rolagem do drawer (issue #186).

Fatia (c) da #173. O clip do "Sair" foi corrigido em `df20393f` (`max-height`
ancorada em `100dvh` + `overflow-y: auto`); faltava a pista visual de que o
painel rola quando o conteúdo excede a altura — com a navegação completa a
375px, o bloco Conta e o botão "Sair" caem abaixo da dobra do drawer.

Critério de admissão: o caso mede `scrollHeight`/`clientHeight` reais do painel
depois que o navegador executou o layout com a viewport estreita e o menu
aberto por Alpine. O HTML do servidor não diz se o conteúdo transbordou.
"""

import pytest

from apps.core.tests.navegador import autenticar

pytestmark = pytest.mark.navegador


@pytest.fixture
def drawer_aberto(live_server, context, page, superusuario):
    """Superusuário (navegação completa) a 375×667, com o drawer aberto."""
    autenticar(live_server, context, superusuario)
    page.set_viewport_size({'width': 375, 'height': 667})
    page.goto(f'{live_server.url}/')
    page.click('.app-bar__nav-toggle')
    page.wait_for_selector('.app-bar__menu', state='visible')
    return page


def _metricas_do_menu(page) -> dict:
    return page.evaluate(
        """() => {
            const el = document.querySelector('.app-bar__menu');
            const cs = getComputedStyle(el);
            return {
                transbordo: el.scrollHeight - el.clientHeight,
                backgroundImage: cs.backgroundImage,
                backgroundAttachment: cs.backgroundAttachment,
            };
        }"""
    )


def test_o_drawer_de_fato_rola_com_a_navegacao_completa(drawer_aberto):
    """Sem transbordo, a affordance não teria o que sinalizar — este é o
    pré-requisito do caso abaixo."""
    assert _metricas_do_menu(drawer_aberto)['transbordo'] > 0


def test_o_drawer_sinaliza_a_rolagem_com_sombras_de_scroll(drawer_aberto):
    """Mesmo mecanismo do `.scroll-shadow-x` das tabelas, na vertical: quatro
    camadas de gradiente (duas de cobertura `local`, duas de sombra `scroll`).
    A cobertura acompanha o conteúdo e esconde a sombra na ponta.
    """
    metricas = _metricas_do_menu(drawer_aberto)
    assert metricas['backgroundImage'].count('gradient') >= 4, (
        f'drawer sem as camadas de sombra de scroll: {metricas["backgroundImage"]}'
    )
    assert 'local' in metricas['backgroundAttachment'], (
        'as camadas de cobertura precisam de `background-attachment: local` '
        f'para se ancorarem no conteúdo: {metricas["backgroundAttachment"]}'
    )
