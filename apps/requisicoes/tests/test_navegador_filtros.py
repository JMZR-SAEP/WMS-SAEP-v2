"""Camada Navegador (ADR-0019) — comportamento da barra de filtros.

Critério de admissão: os casos dependem de estado que só existe depois que o
navegador executa layout e eventos. Onde está `document.activeElement` depois
de um swap HTMX, se um `<details>` fechado volta a expor o formulário ao cruzar
o breakpoint, se o `aria-busy` aparece durante a requisição, e a ordem entre um
callback de `setTimeout` e o ciclo do htmx — nada disso é observável no HTML que
o servidor devolve.

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


def test_liberar_cancela_o_timer_de_disable_quando_afterrequest_vence(pagina_historico):
    """Corrida latente em `form-submit.js` (#149).

    O submit é desabilitado dentro de um `setTimeout(0)`; `liberar()` restaura o
    botão em `htmx:afterRequest`. Se `afterRequest` vence a corrida, `liberar()`
    restaura o botão e descarta o estado de restauração antes de o timer sair da
    fila — e o callback enfileirado então desabilita um botão que ninguém mais
    reabilita. A correção é `liberar()` cancelar o timer antes de restaurar.

    Sobe para a lane Navegador (ADR-0019, critério 3): o defeito é a ordem entre
    um callback de `setTimeout` e o ciclo do htmx, e nenhum atributo do HTML
    renderizado o prova. Um teste de fonte só confirmaria que a chamada de
    `clearTimeout` está escrita, não que ela fecha a corrida.

    Determinismo: um shim de `setTimeout`/`clearTimeout` retém o callback de
    disable (identificado pela fonte) em vez de agendá-lo, e o teste o executa à
    mão depois do `afterRequest` — exatamente o timer que perdeu a corrida.
    """
    resultado = pagina_historico.evaluate(
        """(sel) => new Promise((resolve) => {
            const realSet = window.setTimeout;
            const realClear = window.clearTimeout;
            const presos = new Map();
            let proximoId = 987000;
            let retendo = true;

            window.setTimeout = function (fn, delay) {
                if (retendo && typeof fn === 'function'
                    && /timerDesabilitar/.test(String(fn))) {
                    const id = proximoId++;
                    presos.set(id, { fn, cancelado: false });
                    return id;
                }
                return realSet.apply(window, arguments);
            };
            window.clearTimeout = function (id) {
                if (presos.has(id)) { presos.get(id).cancelado = true; return; }
                return realClear.apply(window, arguments);
            };

            const b = document.querySelector(sel);
            // Registrado depois do listener de form-submit.js (mesmo alvo,
            // `document`), então `liberar()` já rodou quando este dispara.
            document.addEventListener('htmx:afterRequest', () => {
                retendo = false;
                window.setTimeout = realSet;
                window.clearTimeout = realClear;

                const entrada = [...presos.values()][0];
                const saida = {
                    presos: presos.size,
                    canceladoPorLiberar: Boolean(entrada && entrada.cancelado),
                    disabledAposLiberar: b.disabled,
                };
                // Executa o callback retido: é o que o timer faria ao perder a
                // corrida. Sem o cancelamento em `liberar()`, trava o botão.
                if (entrada) { entrada.fn(); }
                saida.disabledSeOCallbackRodasse = b.disabled;
                resolve(saida);
            }, { once: true });

            b.click();
        })""",
        SUBMIT_FILTRO,
    )

    assert resultado['presos'] == 1, resultado
    assert resultado['canceladoPorLiberar'] is True, resultado
    assert resultado['disabledAposLiberar'] is False, resultado
    assert resultado['disabledSeOCallbackRodasse'] is True, resultado
