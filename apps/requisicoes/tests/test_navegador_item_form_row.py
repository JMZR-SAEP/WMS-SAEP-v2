"""Camada Navegador (ADR-0019) — botão "Remover" do formset de itens (issue #198),
painel de saldo reativo da linha (issue #174, PR #214) e borda de alerta
reativa da linha (mesma issue/PR, achado posterior).

Critério de admissão: a regra é mínimo 1 item, mas o servidor sempre renderiza
o botão de cada linha — quem decide se ele aparece é `totalVisiveis`, contado
em tempo de execução por `itensFormset` (`item_form_row.js`) conforme linhas
são adicionadas ou removidas. Nenhuma asserção sobre o HTML do primeiro
request alcança esse número. O mesmo vale para o painel de saldo
(`saldoLinha`, apps/estoque/static/estoque/js/saldo_linha.js): se
`registrarMaterial()` parar de atualizar `saldoTexto`/`motivo` ao trocar de
material, só um teste que seleciona outro material no autocomplete de
verdade — não uma asserção sobre o JSON inicial de `x-data` — pega a
regressão.
"""

from decimal import Decimal

import pytest

from apps.core.tests.navegador import autenticar
from apps.requisicoes.services import criar_requisicao

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
    # O botão que recebia o foco (issue #198) desaparece no mesmo instante em
    # que a linha 0 fica sozinha — sem o desvio pro combobox, o foco caía em
    # <body>.
    assert (
        pagina_rascunho.evaluate('document.activeElement.id')
        == 'id_itens-0-material_label'
    )


# ── PR #214 (achado do João): o painel de saldo reativo precisa de prova de
# comportamento, não só de estrutura ──────────────────────────────────────
#
# test_components_item_form_row.py cobre a camada unitária (o JSON inicial de
# x-data está certo, o markup é x-text/x-show e não texto fixo), mas nunca
# inicializa Alpine nem dispara `registrarMaterial()` — continuaria verde
# mesmo se a atualização de `saldoTexto`/`motivo` quebrasse de novo. Só um
# teste que seleciona outro material no autocomplete de verdade prova que o
# painel (e o aviso "Acima do saldo", que lê o mesmo escopo) acompanham a
# troca.


@pytest.fixture
def rascunho_com_item_inelegivel(db, solicitante, material_disponivel):
    """Rascunho com um item que fica sem saldo DEPOIS de já estar vinculado —
    `criar_requisicao` valida elegibilidade na criação (não dá pra criar já
    com `material_sem_saldo`), mas nada revalida depois: é assim que um item
    de rascunho vira inelegível na vida real, e é exatamente o cenário que
    `saldo_item.motivo`/`linha_alpine_config` existem para sinalizar.
    """
    from apps.estoque.models import SaldoEstoque

    requisicao = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('1'),
            }
        ],
    )
    SaldoEstoque.objects.filter(material=material_disponivel).update(
        saldo_reservado=100
    )
    return requisicao


@pytest.fixture
def pagina_editar_rascunho(
    live_server, context, page, solicitante, rascunho_com_item_inelegivel
):
    autenticar(live_server, context, solicitante)
    page.goto(
        f'{live_server.url}/requisicoes/{rascunho_com_item_inelegivel.pk}/editar/'
    )
    page.wait_for_function('Boolean(window.Alpine)')
    return page


def test_painel_de_saldo_acompanha_troca_de_material_no_autocomplete(
    pagina_editar_rascunho, material_disponivel_2
):
    linha = pagina_editar_rascunho.locator('.item-form-row').first

    # A linha já vem vinculada (server-side) a um material sem saldo — o
    # painel mostra o motivo de inelegibilidade desde a carga da página.
    assert linha.get_by_text('Sem saldo disponível').is_visible()

    campo = pagina_editar_rascunho.locator('#id_itens-0-material_label')
    campo.fill('Fita')
    pagina_editar_rascunho.wait_for_timeout(900)
    pagina_editar_rascunho.locator('li[role="option"]').first.click()
    pagina_editar_rascunho.wait_for_timeout(150)

    # O motivo do material anterior some — não fica preso ao que veio do
    # servidor — e o painel passa a mostrar o saldo do material novo.
    assert not linha.get_by_text('Sem saldo disponível').is_visible()
    assert linha.get_by_text(
        f'Saldo disponível: 30 {material_disponivel_2.unidade}'
    ).is_visible()

    # O aviso "Acima do saldo" lê o mesmo escopo Alpine (`saldoValor`) que o
    # painel — reage ao mesmo evento de seleção, sem um segundo estado que
    # possa divergir dele.
    campo_quantidade = pagina_editar_rascunho.locator(
        '#id_itens-0-quantidade_solicitada'
    )
    campo_quantidade.fill('999')
    pagina_editar_rascunho.wait_for_timeout(200)
    assert linha.get_by_text('Acima do saldo').is_visible()


def test_borda_de_alerta_acompanha_troca_de_material_no_autocomplete(
    pagina_editar_rascunho, material_disponivel_2
):
    """Mesma classe de bug do painel de saldo (achado do CodeRabbit, PR #214),
    só que na borda da linha em vez do texto: `borda_alerta` era calculado
    uma vez no render do servidor (`saldo_item|saldo_insuficiente`) e não
    acompanhava a troca de material na mesma linha, sem reload. A borda passou
    a acompanhar `alerta`, reativo — mesmo `motivo` que já dirige o painel.
    """
    linha = pagina_editar_rascunho.locator('.item-form-row').first

    # A linha já vem vinculada a um material sem saldo — a borda âmbar acende
    # desde a carga da página.
    assert 'border-warning-border-strong' in linha.get_attribute('class')

    campo = pagina_editar_rascunho.locator('#id_itens-0-material_label')
    campo.fill('Fita')
    pagina_editar_rascunho.wait_for_timeout(900)
    pagina_editar_rascunho.locator('li[role="option"]').first.click()
    pagina_editar_rascunho.wait_for_timeout(150)

    # O material novo é elegível — a borda não pode ficar presa ao material
    # anterior, o mesmo `motivo` que já limpa o painel de saldo.
    classe = linha.get_attribute('class')
    assert 'border-warning-border-strong' not in classe
    assert 'border-border' in classe
