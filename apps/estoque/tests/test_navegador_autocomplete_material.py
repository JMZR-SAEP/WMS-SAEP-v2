"""Camada Navegador (ADR-0019) — o rótulo do saldo no autocomplete de material.

Critério de admissão: o texto da opção não existe no HTML do servidor. O
partial `_autocomplete_item_material.html` entrega uma expressão `x-text`, e o
valor só aparece depois que o Alpine avalia o ternário sobre o JSON que o
`fetch` trouxe. Asserção sobre HTML renderizado alcança a expressão, não o
resultado — e é justamente o resultado que estava errado.

O caso: as duas buscas de material compartilham o partial e devolvem grandezas
diferentes. `requisicoes` manda `saldo_disponivel` (físico − reservado);
`estoque` manda `saldo_fisico`, reservado incluído. O rótulo era `disp:` nos
dois, e quem registrava saída excepcional lia "disp: 100" com 10 reservados.

A fixture `material_disponivel` tem `saldo_fisico=100` e `saldo_reservado=10`,
ou seja **90 disponível e 100 físico**. Os dois números serem diferentes é o
que faz estes testes provarem o par: não basta o rótulo certo, o valor ao lado
dele tem de ser o da grandeza que o rótulo nomeia.
"""

import pytest

from apps.core.tests.navegador import autenticar

pytestmark = pytest.mark.navegador

COMBO_MATERIAL = '#id_itens-0-material_label'


def _buscar_primeira_opcao(page, termo='MAT'):
    """Digita no combobox e espera o debounce de 300ms mais a ida à rede."""
    page.wait_for_function('Boolean(window.Alpine)')
    page.locator(COMBO_MATERIAL).fill(termo)
    page.wait_for_timeout(900)
    opcao = page.locator('[role="option"]').first
    opcao.wait_for(state='visible')
    return opcao.inner_text()


def test_busca_de_requisicao_mostra_o_saldo_disponivel(
    live_server, context, page, solicitante, material_disponivel
):
    """Em requisição, o que decide é o que sobra para reservar."""
    autenticar(live_server, context, solicitante)
    page.goto(f'{live_server.url}/requisicoes/nova/')

    texto = _buscar_primeira_opcao(page)

    assert 'disponível: 90 un' in texto
    assert 'físico' not in texto
    # O físico (100) não pode aparecer no lugar do disponível (90).
    assert '100' not in texto


def test_busca_de_saida_excepcional_mostra_o_saldo_fisico(
    live_server, context, page, chefe_almoxarifado, material_disponivel
):
    """Em saída excepcional, a baixa é sobre a prateleira, reservado incluído.

    É o caso que dava o número certo com o nome errado: "disp: 100" enquanto
    10 estavam reservados para requisições já autorizadas.
    """
    autenticar(live_server, context, chefe_almoxarifado)
    page.goto(f'{live_server.url}/estoque/saidas-excepcionais/nova/')

    texto = _buscar_primeira_opcao(page)

    assert 'físico: 100 un' in texto
    assert 'disponível' not in texto
    assert 'disp:' not in texto
