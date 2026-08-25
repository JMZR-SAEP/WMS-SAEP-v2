"""Testes de apps.core.modal.render_modal_erro — o helper do fragment 422.

Este helper renderiza `_modal_body.html` direto, sem passar por
`components/modal.html` — logo sem passar por `validar_contrato_modal`. A
obrigatoriedade de `icon_variant` (#136) precisa da própria checagem aqui, ou
um consumidor novo do 422 esquece o parâmetro e recebe em silêncio o fallback
de variante desconhecida.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory

from apps.core.modal import render_modal_erro

_REQUEST = RequestFactory().post('/')


def test_icon_variant_ausente_falha_no_render():
    with pytest.raises(ImproperlyConfigured):
        render_modal_erro(
            _REQUEST,
            modal_id='meu-modal',
            titulo='Título',
            erro='Falhou.',
        )


def test_icon_variant_none_falha_no_render():
    with pytest.raises(ImproperlyConfigured):
        render_modal_erro(
            _REQUEST,
            modal_id='meu-modal',
            titulo='Título',
            erro='Falhou.',
            icon_variant=None,
        )


def test_icon_variant_vazia_falha_no_render():
    with pytest.raises(ImproperlyConfigured):
        render_modal_erro(
            _REQUEST,
            modal_id='meu-modal',
            titulo='Título',
            erro='Falhou.',
            icon_variant='',
        )


@pytest.mark.parametrize('variant', ['info', 'warning', 'danger', 'descarte', 'return'])
def test_icon_variant_presente_renderiza_422(variant):
    response = render_modal_erro(
        _REQUEST,
        modal_id='meu-modal',
        titulo='Título',
        erro='Falhou.',
        icon_variant=variant,
    )
    assert response.status_code == 422
    assert 'data-modal-body="meu-modal"' in response.content.decode()
