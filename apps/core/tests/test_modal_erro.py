"""Testes de apps.core.modal.render_modal_erro — o helper do fragment 422.

Este helper renderiza `_modal_body.html` direto, sem passar por
`components/modal.html` — logo sem passar por `validar_contrato_modal`. A
obrigatoriedade de `icon_variant` (#136) e a de `registro` (#138) precisam da
própria checagem aqui, ou um consumidor novo do 422 esquece o parâmetro e
recebe em silêncio o fallback de variante desconhecida — ou devolve um modal
anônimo no lugar do modal nomeado que a tela abriu.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory

from apps.core.modal import render_modal_erro

_REQUEST = RequestFactory().post('/')

# Registro válido para os testes que **não** são sobre a identidade. Sem ele
# `validar_registro_modal` estoura primeiro, e os testes de `icon_variant`
# passariam por engano — pelo motivo errado, e continuariam verdes se a
# checagem de ícone fosse apagada.
_REGISTRO = {
    'rotulo': 'Requisição',
    'identificador': 'REQ-2026-000123',
    'contexto': 'Maria Silva · Obras',
}


def test_icon_variant_ausente_falha_no_render():
    with pytest.raises(ImproperlyConfigured):
        render_modal_erro(
            _REQUEST,
            modal_id='meu-modal',
            titulo='Título',
            erro='Falhou.',
            registro=_REGISTRO,
        )


def test_icon_variant_none_falha_no_render():
    with pytest.raises(ImproperlyConfigured):
        render_modal_erro(
            _REQUEST,
            modal_id='meu-modal',
            titulo='Título',
            erro='Falhou.',
            registro=_REGISTRO,
            icon_variant=None,
        )


def test_icon_variant_vazia_falha_no_render():
    with pytest.raises(ImproperlyConfigured):
        render_modal_erro(
            _REQUEST,
            modal_id='meu-modal',
            titulo='Título',
            erro='Falhou.',
            registro=_REGISTRO,
            icon_variant='',
        )


@pytest.mark.parametrize('variant', ['info', 'warning', 'danger', 'descarte', 'return'])
def test_icon_variant_presente_renderiza_422(variant):
    response = render_modal_erro(
        _REQUEST,
        modal_id='meu-modal',
        titulo='Título',
        erro='Falhou.',
        registro=_REGISTRO,
        icon_variant=variant,
    )
    assert response.status_code == 422
    assert 'data-modal-body="meu-modal"' in response.content.decode()


def test_registro_ausente_falha_no_render():
    """O 422 reconstrói o cabeçalho inteiro, e a identidade é parte dele (#138).

    Sem esta checagem, um consumidor novo do 422 devolveria um modal anônimo no
    lugar do modal nomeado que a tela abriu — e é justamente no re-render com
    erro, depois de a pessoa já ter confirmado uma vez, que saber qual documento
    está na frente importa mais.
    """
    with pytest.raises(ImproperlyConfigured):
        render_modal_erro(
            _REQUEST,
            modal_id='meu-modal',
            titulo='Título',
            erro='Falhou.',
            icon_variant='danger',
        )


def test_registro_sem_identificador_falha_no_render():
    """Dict incompleto é recusado, não renderizado vazio.

    `{{ registro.identificador }}` resolve chave ausente como string vazia: sem
    esta regra, a linha de identidade sairia com rótulo e sem identidade —
    exatamente o defeito da #138, agora com moldura.
    """
    with pytest.raises(ImproperlyConfigured):
        render_modal_erro(
            _REQUEST,
            modal_id='meu-modal',
            titulo='Título',
            erro='Falhou.',
            registro={'rotulo': 'Requisição'},
            icon_variant='danger',
        )


def test_registro_chega_ao_cabecalho_do_fragment():
    response = render_modal_erro(
        _REQUEST,
        modal_id='meu-modal',
        titulo='Título',
        erro='Falhou.',
        registro=_REGISTRO,
        icon_variant='danger',
    )
    html = response.content.decode()
    assert 'data-modal-registro' in html
    assert 'REQ-2026-000123' in html
    assert 'Maria Silva · Obras' in html


def test_consequencia_chega_ao_corpo_do_fragment():
    """A frase de irreversibilidade sobrevive ao 422 (#138).

    O swap troca o corpo inteiro; se `consequencia` não fosse repassada, o modal
    reaberto com erro perderia justamente o aviso de que a ação não tem volta —
    na tentativa em que a pessoa já está com o dedo no botão pela segunda vez.
    """
    response = render_modal_erro(
        _REQUEST,
        modal_id='meu-modal',
        titulo='Título',
        erro='Falhou.',
        registro=_REGISTRO,
        consequencia='Esta operação é irreversível.',
        icon_variant='danger',
    )
    html = response.content.decode()
    assert 'data-modal-consequencia' in html
    assert 'Esta operação é irreversível.' in html
