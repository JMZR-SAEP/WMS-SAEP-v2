"""Testes diretos de partials de badge de estoque (sem DB, sem view).

Mesma correção de `_estado_badge.html` (issue #122) para os três partials de
estoque que anulavam o fallback vermelho de `components/badge.html`: valor
não mapeado passa a gritar sob o prefixo `desconhecida:`, em vez de virar
uma cor plausível. Os dois que hoje passam `aria_label` (que o fallback do
badge.html propagaria literalmente, calando o grito para leitor de tela)
trocam para `prefixo_sr` só no ramo do grito.
"""

from types import SimpleNamespace

import pytest
from django.template.loader import render_to_string

TIPOS_CANONICOS = {
    'reserva': 'blue',
    'liberacao': 'slate',
    'consumo': 'indigo',
    'saida_excepcional': 'red',
    'estorno_saida': 'amber',
    'devolucao': 'teal',
    'estorno_requisicao': 'violet',
}


def _movimentacao(tipo, rotulo='Rótulo do tipo'):
    return SimpleNamespace(tipo=tipo, rotulo=rotulo)


def _render_tipo_movimentacao(tipo, rotulo='Rótulo do tipo'):
    mov = _movimentacao(tipo, rotulo)
    return render_to_string(
        'estoque/partials/_badge_tipo_movimentacao.html',
        {'tipo': mov.tipo, 'rotulo': mov.rotulo},
    )


def _saida(estado, label='Rótulo do estado'):
    return SimpleNamespace(estado=estado, get_estado_display=lambda: label)


def _render_saida(estado, label='Rótulo do estado'):
    return render_to_string(
        'estoque/partials/_estado_saida_badge.html',
        {'saida': _saida(estado, label)},
    )


# ─── _badge_tipo_movimentacao.html ─────────────────────────────────────────


def test_tipo_inexistente_renderiza_indisponivel_visivel():
    html = _render_tipo_movimentacao('tipo-que-nao-existe')
    assert 'Indisponível' in html


def test_tipo_inexistente_emite_data_badge_variant_prefixado():
    html = _render_tipo_movimentacao('tipo-que-nao-existe')
    assert 'data-badge-variant="desconhecida:tipo-que-nao-existe"' in html


def test_tipo_orange_colide_mas_gruda_no_fallback():
    html = _render_tipo_movimentacao('orange')
    assert 'Indisponível' in html
    assert 'bg-orange-100' not in html


def test_tipo_inexistente_preserva_rotulo_real():
    html = _render_tipo_movimentacao('tipo-que-nao-existe', rotulo='Reserva de saída')
    assert 'Reserva de saída' in html


def test_tipo_inexistente_nao_emite_aria_label():
    html = _render_tipo_movimentacao('tipo-que-nao-existe')
    assert 'aria-label=' not in html


def test_tipo_inexistente_nome_acessivel_contem_indisponivel_e_rotulo():
    html = _render_tipo_movimentacao('tipo-que-nao-existe', rotulo='Reserva de saída')
    assert 'Tipo de movimentação: ' in html
    assert 'Indisponível' in html
    assert 'Reserva de saída' in html


@pytest.mark.parametrize('tipo,variant_esperada', sorted(TIPOS_CANONICOS.items()))
def test_tipo_canonico_mantem_variante_de_hoje(tipo, variant_esperada):
    html = _render_tipo_movimentacao(tipo)
    marcadores = {
        'blue': 'bg-primary-muted ',
        'slate': 'bg-bg-subtle',
        'indigo': 'bg-indigo-100',
        'red': 'bg-danger-muted ',
        'amber': 'bg-warning-muted ',
        'teal': 'bg-return-muted',
        'violet': 'bg-violet-100',
    }[variant_esperada]
    assert marcadores in html
    assert 'aria-label="Tipo de movimentação: '.encode().decode() in html


# ─── _estado_saida_badge.html ──────────────────────────────────────────────


def test_saida_inexistente_renderiza_indisponivel_visivel():
    html = _render_saida('estado-que-nao-existe')
    assert 'Indisponível' in html


def test_saida_inexistente_emite_data_badge_variant_prefixado():
    html = _render_saida('estado-que-nao-existe')
    assert 'data-badge-variant="desconhecida:estado-que-nao-existe"' in html


def test_saida_orange_colide_mas_gruda_no_fallback():
    html = _render_saida('orange')
    assert 'Indisponível' in html
    assert 'bg-orange-100' not in html


def test_saida_inexistente_nao_emite_aria_label():
    html = _render_saida('estado-que-nao-existe')
    assert 'aria-label=' not in html


def test_saida_inexistente_nome_acessivel_contem_indisponivel_e_rotulo():
    html = _render_saida('estado-que-nao-existe', label='Registrada')
    assert 'Estado: ' in html
    assert 'Indisponível' in html
    assert 'Registrada' in html


def test_saida_registrada_mantem_blue_strong():
    html = _render_saida('registrada')
    assert 'bg-primary-muted-strong' in html


def test_saida_estornada_continua_teal():
    """`estornada` passava pelo `{% else %}` antigo — precisa de ramo explícito
    novo com o `teal` de hoje, senão o grito pintaria todo estorno de vermelho.
    """
    html = _render_saida('estornada')
    assert 'bg-return-muted' in html
    assert 'Indisponível' not in html
