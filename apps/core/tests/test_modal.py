"""Testes diretos de components/modal.html (sem DB, sem view)."""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Template

from apps.core.tests.marcacao import atributo, elementos, pares


def _render_modal(**ctx):
    ctx.setdefault('id', 'meu-modal')
    ctx.setdefault('titulo', 'Título')
    include_with = ' '.join(f'{chave}="{valor}"' for chave, valor in ctx.items())
    template = Template(
        '{% include "components/modal.html" with ' + include_with + ' %}'
    )
    return template.render(Context({}))


def test_action_url_sozinho_renderiza_form_com_action():
    html = _render_modal(action_url='/confirmar/')
    assert 'action="/confirmar/"' in html
    assert '<form' in html


def test_submit_form_id_e_action_url_juntos_falha_validacao():
    with pytest.raises(ImproperlyConfigured):
        _render_modal(action_url='/confirmar/', submit_form_id='form-externo')


def test_nenhum_dos_dois_falha_validacao():
    with pytest.raises(ImproperlyConfigured):
        _render_modal()


def test_submit_form_id_sozinho_nao_renderiza_form_interno():
    html = _render_modal(submit_form_id='form-externo')
    assert 'form-externo' in html
    assert '<form' not in html


def test_form_htmx_bloqueia_duplo_envio_no_proprio_htmx():
    """O bloqueio de duplo envio deste form tem que estar no HTMX, não só no JS.

    `form-submit.js` escuta `submit` em `document`, depois do listener que o
    HTMX instala no próprio `<form>`, e o HTMX não consulta `defaultPrevented`
    antes de emitir o XHR — o `preventDefault()` de lá chega tarde. Sem
    `hx-sync`, um clique duplo no rodapé grava duas vezes uma ação que o modal
    apresenta como irreversível.
    """
    html = _render_modal(action_url='/confirmar/')
    assert 'hx-sync="this:drop"' in html


def _corpo(html):
    """Atributos do `<div data-modal-body>`, lidos com parser e não por índice."""
    for _, atributos, _ in elementos(html, 'div'):
        if atributo(atributos, 'data-modal-body'):
            return atributos
    raise AssertionError('modal renderizado sem [data-modal-body]')


def _tem(atributos: str, nome: str) -> bool:
    """Presença de atributo sem valor (`data-modal-confirm`, `disabled`)."""
    return any(chave.lower() == nome for chave, _ in pares(atributos))


def _botoes(html):
    """Atributos de cada `<button>` do modal, em ordem de DOM."""
    return [atributos for _, atributos, _ in elementos(html, 'button')]


def test_corpo_do_modal_e_focavel_por_programa():
    """O corpo tem que ser focável por programa (#132).

    `tabindex="-1"` faz dele o primeiro focável do diálogo, que é onde os passos
    nativos de `showModal()` põem o foco antes de `modal.js` decidir — e é a
    única perna que sobra num modal sem botão de dispensa. Sem o atributo, essa
    janela entrega o foco a um botão do rodapé.
    """
    corpo = _corpo(_render_modal(action_url='/confirmar/'))
    assert atributo(corpo, 'data-modal-body') == 'meu-modal'
    assert atributo(corpo, 'tabindex') == '-1'


def test_rodape_marca_a_dispensa_e_a_confirmacao_com_ganchos_distintos():
    """`data-modal-dismiss` é o par de `data-modal-confirm` (#132).

    `modal.js` precisa distinguir "o botão que só fecha" de "o botão que
    executa" para levar o foco de abertura ao primeiro. Um rodapé com os dois
    ganchos no mesmo botão, ou sem o de dispensa, devolve o foco ao caminho
    perigoso sem quebrar nada visível.
    """
    botoes = _botoes(_render_modal(action_url='/confirmar/'))
    dispensa = [i for i, a in enumerate(botoes) if _tem(a, 'data-modal-dismiss')]
    confirmacao = [i for i, a in enumerate(botoes) if _tem(a, 'data-modal-confirm')]

    assert len(dispensa) == 1
    assert len(confirmacao) == 1
    assert dispensa != confirmacao, 'Os dois ganchos caíram no mesmo botão.'
    # Dispensa antes da confirmação na ordem do DOM: é ela que o `querySelector`
    # de `focarPrimeiroCampo` encontra, e é ela que vem primeiro na tabulação a
    # partir do corpo.
    assert dispensa[0] < confirmacao[0]


def test_botao_de_dispensa_nao_e_o_que_submete():
    """O gancho de dispensa nunca pode cair num `<button type="submit">`.

    Seria o pior dos dois mundos: o foco de abertura iria para um botão que
    executa a ação, com o nome de quem não executa.
    """
    for atributos in _botoes(_render_modal(action_url='/confirmar/')):
        if _tem(atributos, 'data-modal-dismiss'):
            assert atributo(atributos, 'type') == 'button'


def test_form_do_modal_barra_submissao_implicita():
    """Enter num campo de linha única não pode confirmar a ação (#132).

    O modal de devolução abre com o foco num `<input type="number">`. A
    submissão implícita do HTML levaria o POST direto, pulando o rodapé — que é
    onde a frase que descreve a consequência está.
    """
    formularios = [
        atributos
        for _, atributos, _ in elementos(
            _render_modal(action_url='/confirmar/'), 'form'
        )
    ]
    assert formularios, 'modo action_url renderizado sem <form>'
    assert (
        atributo(formularios[0], '@keydown.enter') == 'bloquearSubmitImplicito($event)'
    )


def test_modo_submit_form_id_tambem_barra_submissao_implicita():
    """Sem `<form>` próprio a trava continua necessária (#132).

    Neste modo o `<dialog>` costuma ficar **dentro** do formulário que confirma
    — `requisicoes/atender_retirada.html` abre o `<form>` antes do diálogo —, e
    um campo no corpo do modal pertenceria a esse form externo. Hoje nenhum
    consumidor do modo tem campo no corpo; a trava é o que impede que o primeiro
    a ter reabra o buraco em silêncio.
    """
    html = _render_modal(submit_form_id='form-externo')
    assert '<form' not in html
    envolvente = next(
        atributos
        for _, atributos, _ in elementos(html, 'div')
        if atributo(atributos, 'x-trap.inert.noscroll')
    )
    assert atributo(envolvente, '@keydown.enter') == 'bloquearSubmitImplicito($event)'


def test_modo_submit_form_id_mantem_o_contrato_de_foco():
    """O corpo focável e o gancho de dispensa valem nos dois modos do modal."""
    html = _render_modal(submit_form_id='form-externo')
    assert atributo(_corpo(html), 'tabindex') == '-1'
    assert any(_tem(a, 'data-modal-dismiss') for a in _botoes(html))


def _moldes_de_transporte(html):
    """Atributos de cada `<template data-modal-erro-transporte>`, em ordem."""
    return {
        atributo(atributos, 'data-modal-erro-transporte'): atributos
        for _, atributos, _ in elementos(html, 'template')
        if atributo(atributos, 'data-modal-erro-transporte')
    }


def test_modal_traz_o_slot_e_os_dois_moldes_de_falha_de_transporte():
    """5xx e queda de conexão têm superfície pronta no HTML (#133).

    O JS não renderiza a caixa: ele clona o que o servidor deixou no
    `<template>`. Sem o slot ou sem os moldes, `mostrarFalhaDeTransporte` vira
    no-op e a falha volta a ser silenciosa — que é exatamente o defeito.
    """
    html = _render_modal(action_url='/confirmar/')

    assert 'data-modal-erro-transporte-slot' in html
    assert set(_moldes_de_transporte(html)) == {'conexao', 'servidor'}


def test_moldes_de_transporte_valem_tambem_no_modo_submit_form_id():
    """O modo sem `<form>` próprio também pode receber 5xx do form externo."""
    html = _render_modal(submit_form_id='form-externo')

    assert 'data-modal-erro-transporte-slot' in html
    assert set(_moldes_de_transporte(html)) == {'conexao', 'servidor'}


def test_falha_de_transporte_usa_a_caixa_canonica_de_erro():
    """A caixa é a de `{% erros_do_formulario %}`, não uma terceira grafia.

    `data-error-summary` e `role="alert"` são o que `error_summary.html` emite —
    se a caixa passar a ser montada em `modal.js`, o mesmo erro volta a parecer
    coisa diferente conforme a tela, e o anúncio depende de quem escreveu o JS.
    """
    html = _render_modal(action_url='/confirmar/', acao_erro='estornar a saída')

    assert html.count('data-error-summary') == 2
    assert html.count('role="alert"') == 2
    # O verbo da tela chega à frase-líder das duas caixas.
    assert html.count('Não foi possível estornar a saída:') == 2


def test_texto_da_falha_de_transporte_e_copy_de_produto_em_pt_br():
    """Nem status code cru, nem jargão de rede (#133).

    A pessoa que vê isto acabou de confirmar uma operação irreversível: o texto
    tem que dizer o que fazer para descobrir se ela foi registrada.
    """
    html = _render_modal(action_url='/confirmar/')

    assert 'A conexão com o servidor caiu durante o envio.' in html
    assert 'O servidor não concluiu esta ação.' in html
    for proibido in ('500', 'Internal Server Error', 'HTTP', 'XHR', 'status'):
        assert proibido not in html, f'{proibido!r} vazou para a copy do modal.'


def test_moldes_de_transporte_nao_repetem_id_entre_si():
    """Dois `<template>` no mesmo diálogo não podem carregar o mesmo id.

    A caixa entra no documento por clone; ids iguais nos moldes viram ids
    duplicados na página assim que os dois desfechos ocorrerem na mesma sessão,
    e é por id que `aria-describedby` e as âncoras do sumário resolvem.
    """
    html = _render_modal(action_url='/confirmar/')

    assert 'id="meu-modal-erro-conexao"' in html
    assert 'id="meu-modal-erro-servidor"' in html


def test_backdrop_ancora_o_fechamento_no_mousedown():
    """Fechar por backdrop exige o par `mousedown` + `click` (#133).

    Só com `@click`, uma seleção de texto que começa dentro da caixa e termina
    fora chega com `target` no `<dialog>` e descarta a justificativa inteira.
    """
    dialogo = next(
        atributos
        for _, atributos, _ in elementos(_render_modal(action_url='/x/'), 'dialog')
    )

    assert atributo(dialogo, '@mousedown') == 'backdropMouseDown($event)'
    assert atributo(dialogo, '@click') == 'backdropClick($event)'
