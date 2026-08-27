"""Desfechos do modal depois do clique em confirmar — camada Navegador (#133).

As três formas de o modal falhar em silêncio depois que a pessoa aperta o botão:
fechar com o POST em voo, receber um 5xx que não troca nada, e perder texto
digitado num arrasto de seleção que termina no backdrop.

Critério de admissão da ADR-0019 atendido nas três vias, e nenhuma delas é
observável no HTML renderizado: a primeira depende do estado de uma requisição
real em andamento; a segunda, do ciclo do htmx com uma resposta de erro de
verdade; a terceira, da geometria do `<dialog>` no top layer e da ordem
`mousedown`/`mouseup`/`click` que só o navegador emite.

A marcação do contrato — o slot, os dois `<template>`, o `@mousedown` no
diálogo, a copy PT-BR das duas caixas — fica na lane de baixo, em
`apps/core/tests/test_modal.py`.

## Fora de escopo declarado: o POST clássico do modo `submit_form_id`

A trava de requisição em voo é recortada por `hx-post` justamente para não
trancar `requisicoes/atender_retirada.html`, que é POST clássico e cuja marca de
envio só cai com a navegação. **Esse caso não é dirigível em automação**: com uma
navegação pendente, `evaluate` e `wait_for_function` não retornam — a página não
tem contexto de execução para responder —, então não há como observar o estado
do diálogo no exato instante que interessa. Mesmo tratamento que a ADR-0019 já
dá ao bfcache de `form-submit.js`.

O que sobra guardando o recorte é a lane de baixo: o `hx-post` no `<form>` do
modo `action_url` é cobrado por
`test_form_do_modal_carrega_o_hx_post_de_que_a_trava_em_voo_depende`.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.tests.navegador import autenticar
from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

pytestmark = pytest.mark.navegador


@pytest.fixture
def req_para_decisao(db, solicitante, setor_obras, material_disponivel):
    """Requisição aguardando autorização — a tela do chefe do setor.

    Dá os dois modais de que esta lane precisa na mesma página:
    `confirmar-autorizar` não tem campo nenhum, e `confirmar-recusar` abre com
    uma textarea obrigatória, que é onde há texto a perder.
    """
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-9330',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req,
        material=material_disponivel,
        quantidade_solicitada=Decimal('2'),
    )
    return req


@pytest.fixture
def pagina_de_decisao(live_server, context, page, chefe_obras, req_para_decisao):
    """Página de detalhe autenticada como o chefe que decide."""
    autenticar(live_server, context, chefe_obras)
    page.goto(
        f'{live_server.url}'
        + reverse('requisicoes:detalhe', kwargs={'pk': req_para_decisao.pk})
    )
    return page


def _abrir(page, modal_id):
    """Aciona o trigger e espera o `<dialog>` estar realmente aberto."""
    page.locator(f'[data-modal-trigger="{modal_id}"]').first.click()
    page.wait_for_function(f"document.getElementById('{modal_id}').open")
    return page.locator(f'dialog#{modal_id}')


def _clicar_no_backdrop(page, dialogo):
    """Pressiona e solta acima e à esquerda da caixa — área de backdrop.

    O `<dialog>` ocupa a tela inteira para efeito de eventos, então o alvo é o
    próprio diálogo; o que separa backdrop de caixa é a geometria. O ponto é
    calculado a partir do retângulo real da caixa em vez de fixado, para não
    depender do tamanho da janela do runner.
    """
    caixa = dialogo.bounding_box()
    assert caixa['y'] > 8, 'A caixa encosta no topo — não sobrou backdrop clicável.'
    page.mouse.move(caixa['x'] + caixa['width'] / 2, caixa['y'] / 2)
    page.mouse.down()
    page.mouse.up()


def test_modal_nao_fecha_com_o_post_em_voo_e_o_422_e_visto(
    pagina_de_decisao, req_para_decisao
):
    """Nem `Esc` nem backdrop fecham enquanto a requisição está em andamento.

    Fechar ali engoliria a resposta: o swap do 422 trocaria `[data-modal-body]`
    dentro de um `<dialog>` já fechado, e a recusa nunca seria vista — o
    `role="alert"` seria anunciado num nó que não está renderizado.
    """
    page = pagina_de_decisao
    url_recusar = reverse('requisicoes:recusar', kwargs={'pk': req_para_decisao.pk})

    # Segura a rota em vez de dormir: a resposta só sai quando o teste mandar,
    # então a janela de "em voo" é determinística e não depende da velocidade do
    # CI. Uma soneca fixa passaria num runner lento mesmo com a regressão de
    # volta.
    presas = []
    page.route(f'**{url_recusar}', lambda rota: presas.append(rota))

    dialogo = _abrir(page, 'confirmar-recusar')
    dialogo.locator('[data-modal-confirm]').click()
    page.wait_for_function(
        "() => document.querySelector('dialog#confirmar-recusar form')"
        ".dataset.submitting === '1'"
    )

    page.keyboard.press('Escape')
    assert dialogo.evaluate('(d) => d.open'), (
        '`Esc` fechou o modal com o POST em voo — a resposta seria engolida.'
    )

    # A mesma tecla pela outra rota, e é esta que ocorre de verdade: o
    # `form-submit.js` desabilita o botão recém-clicado, o navegador tira o foco
    # dele, e o `keydown` deixa de ter alvo dentro do `<dialog>` — o
    # `@keydown.escape` de `modal.html` não roda, mas o fechamento nativo sim.
    # O `blur` explícito torna determinístico o que, sem ele, seria uma corrida
    # com o `setTimeout(0)` que desabilita o botão.
    page.evaluate('() => document.activeElement && document.activeElement.blur()')
    page.keyboard.press('Escape')
    assert dialogo.evaluate('(d) => d.open'), (
        '`Esc` com o foco fora do diálogo fechou pelo caminho nativo, '
        'que é justamente o que acontece depois de clicar em confirmar.'
    )

    _clicar_no_backdrop(page, dialogo)
    assert dialogo.evaluate('(d) => d.open'), (
        'Clique no backdrop fechou o modal com o POST em voo.'
    )

    # Motivo vazio: a view responde 422 e o corpo do modal volta com a caixa de
    # erro. É o desfecho que as duas tentativas de fechamento teriam escondido.
    presas[0].continue_()
    page.wait_for_selector('dialog#confirmar-recusar [data-modal-erro]')
    assert dialogo.evaluate('(d) => d.open')

    # E, terminada a requisição, o modal volta a fechar normalmente.
    page.keyboard.press('Escape')
    page.wait_for_function("() => !document.getElementById('confirmar-recusar').open")


def test_erro_de_servidor_dentro_do_modal_vira_mensagem_visivel(
    pagina_de_decisao, req_para_decisao
):
    """Um 500 na autorização não pode devolver o modal ao estado inicial.

    `confirmar-autorizar` não tem campo: sem esta caixa, o 5xx não troca nada, o
    `form-submit.js` reabilita o rodapé no `htmx:afterRequest`, e a tela fica
    indistinguível de "não aconteceu nada" numa ação que o rodapé descreve como
    irreversível.
    """
    page = pagina_de_decisao
    url_autorizar = reverse('requisicoes:autorizar', kwargs={'pk': req_para_decisao.pk})
    page.route(
        f'**{url_autorizar}',
        lambda rota: rota.fulfill(
            status=500, content_type='text/html; charset=utf-8', body='<h1>500</h1>'
        ),
    )

    dialogo = _abrir(page, 'confirmar-autorizar')
    dialogo.locator('[data-modal-confirm]').click()

    caixa = dialogo.locator('[data-modal-erro-transporte-slot] [data-error-summary]')
    caixa.wait_for()
    assert dialogo.evaluate('(d) => d.open'), 'O 5xx não pode fechar o diálogo.'
    assert caixa.get_attribute('role') == 'alert', (
        'Sem `role="alert"` a mensagem aparece sem ser anunciada.'
    )
    assert 'O servidor não concluiu esta ação.' in caixa.inner_text()
    # A página do 500 não pode ter sido trocada para dentro da caixa do modal, e
    # o número do status não é copy de produto.
    assert '500' not in caixa.inner_text()

    # O rodapé volta habilitado: a mensagem manda conferir e tentar de novo, e
    # ela precisa ser executável.
    confirmar = dialogo.locator('[data-modal-confirm]')
    assert not confirmar.is_disabled()


def test_arrasto_de_selecao_que_termina_no_backdrop_nao_fecha_o_modal(
    pagina_de_decisao,
):
    """Selecionar o motivo escrito e soltar fora não pode apagar tudo.

    O `click` de um arrasto assim chega no ancestral comum, que é o próprio
    `<dialog>`: sem a ancoragem no `mousedown`, ele é lido como "clicou fora".
    """
    page = pagina_de_decisao
    dialogo = _abrir(page, 'confirmar-recusar')
    motivo = dialogo.locator('#modal-recusar-motivo')
    motivo.fill('Material já atendido por outra requisição do mesmo setor.')

    caixa_do_campo = motivo.bounding_box()
    page.mouse.move(
        caixa_do_campo['x'] + 10, caixa_do_campo['y'] + caixa_do_campo['height'] / 2
    )
    page.mouse.down()
    page.mouse.move(4, 4, steps=8)
    page.mouse.up()

    assert dialogo.evaluate('(d) => d.open'), (
        'O arrasto de seleção fechou o modal e descartou a justificativa.'
    )
    assert motivo.input_value().startswith('Material já atendido')


def test_backdrop_fica_inerte_com_texto_digitado_mas_esc_e_voltar_continuam(
    pagina_de_decisao,
):
    """Com justificativa escrita, o backdrop não descarta; as saídas deliberadas sim.

    ## Em observação — intermitência sob carga (#149)

    Falhou uma vez numa execução completa da lane Navegador e passou nas 8
    execuções seguintes (5 completas + 3 isoladas do módulo). Descartada a
    hipótese de vir da correção de corrida em `form-submit.js`: a lane roda
    limpa 3x com a versão anterior do arquivo, e o novo `liberar()` só devolve
    foco quando `document.activeElement === document.body`, condição que o
    `x-trap` do modal impede.

    Hipótese corrente: sensibilidade a timing sob carga — `_clicar_no_backdrop`
    depende da ordem `mousedown`/`mouseup`/`click` que o navegador emite e da
    geometria do `<dialog>` no top layer. Nova falha esperada: `d.open` volta
    `False` logo após o clique no backdrop, ou `document.activeElement` não é o
    `[data-modal-dismiss]`. Se reincidir com padrão (mesma asserção, mesma fase
    da lane), abrir issue de investigação e considerar estabilizar o gesto com
    `page.wait_for_*` no lugar do `mouse.down/up` cru.
    """
    page = pagina_de_decisao
    dialogo = _abrir(page, 'confirmar-recusar')
    dialogo.locator('#modal-recusar-motivo').fill('Duplicidade com REQ-2026-9001.')

    _clicar_no_backdrop(page, dialogo)
    assert dialogo.evaluate('(d) => d.open'), (
        'Clique fora apagou texto que a pessoa digitou.'
    )
    # Recusar o gesto em silêncio seria a mesma falha muda que a issue fecha nos
    # outros três lugares. O foco vai para "Voltar": aponta a saída de verdade e
    # é anunciado, sem executar nada.
    assert page.evaluate(
        '() => document.activeElement.hasAttribute("data-modal-dismiss")'
    ), 'O backdrop recusou o fechamento sem dizer por onde sair.'

    dialogo.locator('[data-modal-dismiss]').click()
    page.wait_for_function("() => !document.getElementById('confirmar-recusar').open")


def test_backdrop_continua_fechando_o_modal_sem_texto_digitado(pagina_de_decisao):
    """A trava é sobre perder texto, não sobre desligar o gesto.

    Sem esta perna, a correção do arrasto de seleção poderia ter matado o clique
    de backdrop inteiro sem que nada acusasse.
    """
    page = pagina_de_decisao
    dialogo = _abrir(page, 'confirmar-autorizar')

    _clicar_no_backdrop(page, dialogo)

    page.wait_for_function("() => !document.getElementById('confirmar-autorizar').open")


def test_queda_de_conexao_dentro_do_modal_vira_mensagem_visivel(
    pagina_de_decisao, req_para_decisao
):
    """`htmx:sendError` tem molde próprio, e é outra copy (#133).

    A requisição que nunca chega a ter resposta não passa por
    `htmx:responseError`: só o `sendError` dispara, e sem este caminho a queda
    de conexão continuaria sendo o desfecho mudo que a issue nomeia.
    """
    page = pagina_de_decisao
    url_autorizar = reverse('requisicoes:autorizar', kwargs={'pk': req_para_decisao.pk})
    page.route(f'**{url_autorizar}', lambda rota: rota.abort())

    dialogo = _abrir(page, 'confirmar-autorizar')
    dialogo.locator('[data-modal-confirm]').click()

    caixa = dialogo.locator('[data-modal-erro-transporte-slot] [data-error-summary]')
    caixa.wait_for()
    assert dialogo.evaluate('(d) => d.open')
    assert 'A conexão com o servidor caiu durante o envio.' in caixa.inner_text(), (
        'A queda de conexão recebeu a copy de erro de servidor.'
    )


def test_falha_de_transporte_nao_sobrevive_ao_fechar_e_reabrir(
    pagina_de_decisao, req_para_decisao
):
    """A mensagem descreve a tentativa anterior; reabrir é tentar de novo.

    Sem a limpeza na abertura, o modal reabriria acusando um erro que ainda não
    aconteceu, por cima de um formulário intocado — a mesma classe de defeito
    que a issue fecha: a tela mostrando um estado que não corresponde ao que
    acabou de ocorrer.
    """
    page = pagina_de_decisao
    url_autorizar = reverse('requisicoes:autorizar', kwargs={'pk': req_para_decisao.pk})
    page.route(
        f'**{url_autorizar}',
        lambda rota: rota.fulfill(
            status=500, content_type='text/html; charset=utf-8', body='<h1>500</h1>'
        ),
    )

    dialogo = _abrir(page, 'confirmar-autorizar')
    dialogo.locator('[data-modal-confirm]').click()
    dialogo.locator('[data-modal-erro-transporte-slot] [data-error-summary]').wait_for()

    dialogo.locator('[data-modal-dismiss]').click()
    page.wait_for_function("() => !document.getElementById('confirmar-autorizar').open")
    _abrir(page, 'confirmar-autorizar')

    assert (
        dialogo.locator('[data-modal-erro-transporte-slot]').inner_html().strip() == ''
    ), 'O modal reabriu acusando o erro da tentativa anterior.'
