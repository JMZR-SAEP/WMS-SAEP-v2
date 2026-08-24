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
