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
