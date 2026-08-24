"""Testes diretos de components/modal.html (sem DB, sem view)."""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Template


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


def test_corpo_do_modal_e_focavel_por_programa():
    """O corpo é o alvo de último recurso do foco de abertura (#132).

    Sem `tabindex="-1"` o `focarDispensa` de `modal.js` não teria para onde
    mandar o foco num modal sem campo e sem botão de dispensa, e a única coisa
    focável restante seria o botão que executa a ação.
    """
    html = _render_modal(action_url='/confirmar/')
    assert 'data-modal-body="meu-modal" tabindex="-1"' in html


def test_rodape_marca_a_dispensa_e_a_confirmacao_com_ganchos_distintos():
    """`data-modal-dismiss` é o par de `data-modal-confirm` (#132).

    `modal.js` precisa distinguir "o botão que só fecha" de "o botão que
    executa" para levar o foco de abertura ao primeiro. Um rodapé com os dois
    ganchos no mesmo botão, ou sem o de dispensa, devolve o foco ao caminho
    perigoso sem quebrar nada visível.
    """
    html = _render_modal(action_url='/confirmar/')
    assert html.count('data-modal-dismiss') == 1
    assert html.count('data-modal-confirm') == 1
    # Dispensa antes da confirmação, na ordem do DOM: é ela que o
    # `querySelector` de `focarDispensa` encontra, e é ela que vem primeiro na
    # tabulação a partir do corpo.
    assert html.index('data-modal-dismiss') < html.index('data-modal-confirm')


def test_botao_de_dispensa_nao_e_o_que_submete():
    """O gancho de dispensa nunca pode cair num `<button type="submit">`."""
    html = _render_modal(action_url='/confirmar/')
    trecho = html[: html.index('data-modal-dismiss')]
    abertura = trecho.rindex('<button')
    assert 'type="submit"' not in html[abertura : html.index('data-modal-dismiss')]


def test_form_do_modal_barra_submissao_implicita():
    """Enter num campo de linha única não pode confirmar a ação (#132).

    O modal de devolução abre com o foco num `<input type="number">`. A
    submissão implícita do HTML levaria o POST direto, pulando o rodapé — que é
    onde a frase que descreve a consequência está.
    """
    html = _render_modal(action_url='/confirmar/')
    assert '@keydown.enter="bloquearSubmitImplicito($event)"' in html


def test_modo_submit_form_id_nao_tem_form_para_barrar():
    """Sem `<form>` interno não há submissão implícita — nem handler pendurado."""
    html = _render_modal(submit_form_id='form-externo')
    assert 'bloquearSubmitImplicito' not in html
    assert 'tabindex="-1"' in html
    assert 'data-modal-dismiss' in html
