"""Testes de fonte de apps/core/static/core/js/form-submit.js.

O projeto não tem runner de JS: o contrato do script é verificado por asserção
sobre a fonte, no mesmo padrão de test_components_item_form_row.py.
"""

from pathlib import Path

import pytest


@pytest.fixture
def fonte_js() -> str:
    raiz = Path(__file__).resolve().parents[3]
    return (raiz / 'apps/core/static/core/js/form-submit.js').read_text()


def test_timer_do_disabled_e_guardado_no_estado_em_voo(fonte_js):
    """O id do `setTimeout(0)` que desabilita os botões tem de ser rastreável.

    Sem guardá-lo, `liberar()` não tem como cancelar o callback enfileirado
    (#149).
    """
    assert 'estado.timerDesabilitar = setTimeout(' in fonte_js


def test_liberar_cancela_o_timer_antes_de_restaurar(fonte_js):
    """Corrida latente (#149): se `htmx:afterRequest` vence o `setTimeout(0)`,
    `liberar()` restaura os botões e apaga o estado em voo; o timer enfileirado,
    ao rodar em seguida, desabilita botões sem estado de restauração — travados
    sem volta. A correção é `clearTimeout` dentro de `liberar()`.
    """
    corpo_liberar = fonte_js[fonte_js.index('function liberar(') :]
    corpo_liberar = corpo_liberar[
        : corpo_liberar.index('\n  document.addEventListener')
    ]
    assert 'clearTimeout(estado.timerDesabilitar)' in corpo_liberar


def test_o_disabled_continua_diferido(fonte_js):
    """Fechar a corrida não pode ter tornado o `disabled` síncrono: o browser
    ainda precisa montar o submit com o `name=valor` do botão antes de ele ser
    desabilitado.
    """
    assert 'setTimeout(' in fonte_js
