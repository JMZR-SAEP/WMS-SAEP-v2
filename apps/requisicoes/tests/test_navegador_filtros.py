"""Camada Navegador (ADR-0019) — comportamento da barra de filtros.

Critério de admissão: os três casos dependem de estado que só existe depois
que o navegador executa layout e eventos. Onde está `document.activeElement`
depois de um swap HTMX, se um `<details>` fechado volta a expor o formulário
ao cruzar o breakpoint, e se o `aria-busy` aparece durante a requisição — nada
disso é observável no HTML que o servidor devolve.

Regressões de achados da Etapa 4 do `docs/plans/audit-frontend-restante.md`.
"""

import pytest

from apps.core.tests.navegador import autenticar

pytestmark = pytest.mark.navegador

SUBMIT_FILTRO = 'form[data-prevent-double-submit] button[type="submit"]'


@pytest.fixture
def pagina_historico(live_server, context, page, chefe_almoxarifado):
    autenticar(live_server, context, chefe_almoxarifado)
    page.set_viewport_size({'width': 1280, 'height': 800})
    page.goto(f'{live_server.url}/requisicoes/historico/')
    page.wait_for_function('Boolean(window.htmx)')
    return page


def test_aplicar_filtro_mantem_o_foco_no_botao(pagina_historico):
    """O foco caía no `<body>` a cada aplicação de filtro.

    Duas causas somadas: o swap out-of-band reemitia a linha inteira de ações,
    destruindo o próprio submit que disparou a requisição; e desabilitar o
    botão focado durante o envio joga o foco no `<body>`. Quem navega por
    teclado perdia o lugar e o Tab seguinte recomeçava do "Pular para o
    conteúdo".
    """
    botao = pagina_historico.locator(SUBMIT_FILTRO)
    pagina_historico.locator('#filtro-texto').fill('Aux')
    botao.focus()

    botao.click()
    pagina_historico.wait_for_timeout(600)

    focado = pagina_historico.evaluate(
        'document.activeElement && document.activeElement.textContent.trim()'
    )
    assert focado == 'Aplicar filtros', f'foco foi parar em: {focado!r}'


def test_envio_do_filtro_sinaliza_e_se_recupera(pagina_historico):
    """Aplicar filtro não devolvia sinal nenhum até o swap chegar.

    Em rede de galpão, a leitura honesta de silêncio é "não registrou, clica
    de novo".
    """
    botao = pagina_historico.locator(SUBMIT_FILTRO)
    estados = pagina_historico.evaluate(
        """() => new Promise(resolve => {
            const b = document.querySelector('%s');
            const visto = {};
            document.body.addEventListener('htmx:beforeRequest', () => {
                setTimeout(() => {
                    visto.emVoo = b.getAttribute('aria-busy') + '/' + b.disabled;
                }, 5);
            }, { once: true });
            document.body.addEventListener('htmx:afterSettle', () => {
                setTimeout(() => {
                    visto.depois = b.getAttribute('aria-busy') + '/' + b.disabled;
                    resolve(visto);
                }, 150);
            }, { once: true });
            b.click();
        })"""
        % SUBMIT_FILTRO
    )

    assert estados['emVoo'] == 'true/true', estados
    assert estados['depois'] == 'null/false', estados
    assert botao.is_enabled()


def test_filtros_fechados_no_mobile_voltam_a_ser_alcancaveis_no_desktop(
    pagina_historico,
):
    """O `<summary>` é `sm:hidden`: fechar no celular e alargar a janela
    escondia o formulário E o único controle capaz de reabri-lo.

    `sm:block!` não resolve — um `<details>` fechado esconde pelo slot do
    próprio elemento, não por `display` no filho.
    """
    pagina_historico.set_viewport_size({'width': 375, 'height': 812})
    pagina_historico.wait_for_timeout(200)
    pagina_historico.locator('details summary').click()
    pagina_historico.wait_for_timeout(200)

    visiveis = 'els => els.filter(e => e.checkVisibility()).length'
    controles = 'details input, details select, details button'
    assert pagina_historico.locator(controles).evaluate_all(visiveis) == 0, (
        'o disclosure precisa mesmo fechar no mobile'
    )

    pagina_historico.set_viewport_size({'width': 1280, 'height': 800})
    pagina_historico.wait_for_timeout(300)

    total = pagina_historico.locator(controles).count()
    assert pagina_historico.locator(controles).evaluate_all(visiveis) == total, (
        'ao voltar ao desktop, nenhum controle de filtro pode ficar inalcançável'
    )
