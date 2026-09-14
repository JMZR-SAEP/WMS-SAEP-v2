"""Camada Navegador (ADR-0019) — botão "Remover" do formset de itens (issue #198).

Critério de admissão: a regra é mínimo 1 item, mas o servidor sempre renderiza
o botão de cada linha — quem decide se ele aparece é `totalVisiveis`, contado
em tempo de execução por `itensFormset` (`item_form_row.js`) conforme linhas
são adicionadas ou removidas. Nenhuma asserção sobre o HTML do primeiro
request alcança esse número.
"""

import pytest

from apps.core.tests.navegador import autenticar

pytestmark = pytest.mark.navegador

BOTAO_REMOVER = 'button[data-remover-item]'


@pytest.fixture
def pagina_rascunho(live_server, context, page, solicitante):
    autenticar(live_server, context, solicitante)
    page.goto(f'{live_server.url}/requisicoes/nova/')
    page.wait_for_function('Boolean(window.Alpine)')
    return page


def test_remover_fica_escondido_com_uma_linha_so(pagina_rascunho):
    assert pagina_rascunho.locator(BOTAO_REMOVER).count() == 1
    assert not pagina_rascunho.locator(BOTAO_REMOVER).first.is_visible()


def test_remover_aparece_ao_adicionar_e_esconde_ao_voltar_pra_uma(pagina_rascunho):
    pagina_rascunho.get_by_role('button', name='Adicionar material').click()
    pagina_rascunho.wait_for_selector('#id_itens-1-material_label')

    botoes = pagina_rascunho.locator(BOTAO_REMOVER)
    assert botoes.count() == 2
    assert botoes.first.is_visible()
    assert botoes.nth(1).is_visible()

    botoes.nth(1).click()
    pagina_rascunho.wait_for_timeout(200)

    assert not pagina_rascunho.locator(BOTAO_REMOVER).first.is_visible()
