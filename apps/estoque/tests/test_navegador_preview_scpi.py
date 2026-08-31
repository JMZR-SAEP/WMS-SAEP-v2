"""Camada Navegador (ADR-0019) — recorte e âncoras do preview SCPI (issue #162).

Critério de admissão: os casos medem estado que só existe depois que o
navegador executa layout — altura da página com 300 linhas, se a barra de ação
está dentro da viewport sem rolagem, se a barra de resumo continua visível na
segunda tela e se o recorte por chip (HTMX) encurta a página. Nada disso é
observável no HTML que o servidor devolve, que é onde a camada de contrato
(`test_views.py::TestRecorteEAncoraDoPreviewScpi`) para.
"""

from decimal import Decimal

import pytest

from apps.core.tests.navegador import autenticar

pytestmark = pytest.mark.navegador

TOTAL_DE_LINHAS = 300
LINHAS_DIVERGENTES = 2
LINHAS_NOVAS = 10
LINHAS_OK = TOTAL_DE_LINHAS - LINHAS_DIVERGENTES - LINHAS_NOVAS


def _codigo(indice: int) -> str:
    return f'{indice // 1000:03d}.{indice % 1000:03d}.000'


@pytest.fixture
def arquivo_de_300_linhas(db, estoque_principal, tmp_path):
    """CSV do tamanho do achado: 300 linhas, quase todas sem nada a pedir."""
    from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida

    conhecidos = LINHAS_OK + LINHAS_DIVERGENTES
    materiais = Material.objects.bulk_create(
        Material(
            codigo=_codigo(indice),
            nome=f'Material {indice}',
            unidade=UnidadeMedida.UNIDADE,
            ativo=True,
        )
        for indice in range(conhecidos)
    )
    SaldoEstoque.objects.bulk_create(
        SaldoEstoque(
            estoque=estoque_principal,
            material=material,
            saldo_fisico=Decimal('10'),
            saldo_reservado=Decimal('0'),
        )
        for material in materiais
    )

    linhas = ['CADPRO;DENOMINACAO;QUAN3']
    for indice in range(LINHAS_OK):
        linhas.append(f'{_codigo(indice)};Material {indice};10.000')
    for indice in range(LINHAS_OK, conhecidos):
        linhas.append(f'{_codigo(indice)};Material {indice};77.000')
    for indice in range(LINHAS_NOVAS):
        linhas.append(f'900.{indice:03d}.000;Material Novo {indice};5.000')

    caminho = tmp_path / 'scpi_300.csv'
    caminho.write_text('\n'.join(linhas) + '\n', encoding='utf-8')
    return caminho


@pytest.fixture
def pagina_preview(live_server, context, page, superuser, arquivo_de_300_linhas):
    autenticar(live_server, context, superuser)
    page.set_viewport_size({'width': 1280, 'height': 720})
    page.goto(f'{live_server.url}/estoque/importacao-scpi/pre-visualizacao/')
    page.set_input_files('#arquivo', str(arquivo_de_300_linhas))
    page.click('form[data-prevent-double-submit] button[type="submit"]')
    page.wait_for_selector('#resultados-preview-scpi article')
    page.wait_for_function('Boolean(window.htmx)')
    return page


def _rolagem_horizontal(page) -> int:
    return page.evaluate(
        'document.documentElement.scrollWidth - document.documentElement.clientWidth'
    )


def _retangulo(page, seletor: str) -> dict:
    return page.evaluate(
        'seletor => {'
        '  const el = document.querySelector(seletor);'
        '  const r = el.getBoundingClientRect();'
        '  return {top: r.top, bottom: r.bottom, altura: window.innerHeight};'
        '}',
        seletor,
    )


def test_recorte_torna_um_arquivo_de_300_linhas_navegavel(pagina_preview):
    """61 telas de rolagem para achar 12 linhas que pedem decisão.

    O chip é a única coisa entre a conferência e rolar o arquivo inteiro: com
    "Só divergências" a página precisa encolher para uma fração do que era.
    """
    assert pagina_preview.locator('#resultados-preview-scpi article').count() == (
        TOTAL_DE_LINHAS
    )
    altura_inteira = pagina_preview.evaluate('document.body.scrollHeight')

    pagina_preview.click('#filter-chips a:has-text("Só divergências")')
    pagina_preview.wait_for_function(
        'document.querySelectorAll("#resultados-preview-scpi article").length === %d'
        % LINHAS_DIVERGENTES
    )

    assert 'status=divergente' in pagina_preview.url
    altura_recortada = pagina_preview.evaluate('document.body.scrollHeight')
    assert altura_recortada < altura_inteira / 10, (
        f'recorte não encurtou a página: {altura_inteira}px → {altura_recortada}px'
    )


def test_chip_reemitido_no_swap_mantem_a_alternancia(pagina_preview):
    """Sem o reemite OOB o chip fica preso na primeira renderização (#143)."""
    pagina_preview.click('#filter-chips a:has-text("Só divergências")')
    pagina_preview.wait_for_function(
        'document.querySelectorAll("#resultados-preview-scpi article").length === %d'
        % LINHAS_DIVERGENTES
    )

    chip = pagina_preview.locator('#filter-chips a:has-text("Só divergências")')
    assert chip.get_attribute('aria-current') == 'true'

    chip.click()
    pagina_preview.wait_for_function(
        'document.querySelectorAll("#resultados-preview-scpi article").length === %d'
        % TOTAL_DE_LINHAS
    )
    assert 'status=' not in pagina_preview.url


def test_barra_de_acao_e_de_resumo_ficam_na_tela_a_1280(pagina_preview):
    """As duas âncoras da conferência, medidas na largura em que ela acontece.

    O `sm:static` deixava justamente o desktop sem barra de ação, e a barra de
    resumo sumia na segunda tela — as três contagens só reapareciam dentro do
    modal, dezenas de rolagens depois.
    """
    barra_acao = '[x-data^="modalController"]'
    resumo = '[aria-label^="Resumo:"]'

    assert _rolagem_horizontal(pagina_preview) == 0

    inicial = _retangulo(pagina_preview, barra_acao)
    assert inicial['bottom'] <= inicial['altura'] + 1, (
        'barra de ação nasce fora da viewport a 1280'
    )

    pagina_preview.evaluate('window.scrollTo(0, 4000)')
    pagina_preview.wait_for_timeout(150)

    depois_acao = _retangulo(pagina_preview, barra_acao)
    depois_resumo = _retangulo(pagina_preview, resumo)
    assert depois_acao['bottom'] <= depois_acao['altura'] + 1
    assert 0 <= depois_resumo['top'] < depois_resumo['altura'], (
        'barra de resumo saiu da tela na segunda tela de rolagem'
    )
    assert _rolagem_horizontal(pagina_preview) == 0


def test_sem_rolagem_horizontal_nova_a_375(pagina_preview):
    """A barra fixa do mobile é a de antes; o que não pode é vazar largura."""
    pagina_preview.set_viewport_size({'width': 375, 'height': 812})
    pagina_preview.wait_for_timeout(150)

    assert _rolagem_horizontal(pagina_preview) == 0

    barra = _retangulo(pagina_preview, '[x-data^="modalController"]')
    assert barra['bottom'] <= barra['altura'] + 1
