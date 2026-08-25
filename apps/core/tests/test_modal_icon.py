"""Testes de components/_modal_icon.html — vocabulário de severidade (#136).

Cada variante conhecida tem que emitir exatamente um glifo do registry
`{% icon %}` (nunca SVG inline), decorativo. A variante desconhecida cai na
Decisão A-1: fundo cheio de grito, `role="alert"` e o valor cru em
`data-modal-icon-variant`.
"""

import pytest
from django.template.loader import render_to_string

PARTIAL = 'components/_modal_icon.html'
VARIANTES = ('info', 'warning', 'danger', 'descarte', 'return')


def _render(**ctx) -> str:
    return render_to_string(PARTIAL, ctx)


@pytest.mark.parametrize('variant', VARIANTES)
def test_toda_variante_conhecida_emite_um_glifo_do_registry(variant):
    html = _render(variant=variant)

    assert html.count('<svg') == 1
    assert '<path' in html


@pytest.mark.parametrize('variant', VARIANTES)
def test_toda_variante_conhecida_e_decorativa(variant):
    """O nível é anunciado pelo título do modal, não pelo ícone."""
    html = _render(variant=variant)

    assert 'aria-hidden="true"' in html
    assert 'aria-label' not in html
    assert 'role="alert"' not in html


def test_lixeira_e_exclusiva_do_descarte():
    """A lixeira não pode voltar a ser o glifo de `danger` inteiro (#136).

    Cancelar, recusar e estornar não apagam nada — a trilha é append-only.
    O nome do ícone nunca aparece como texto no HTML — só o `<path>` do
    glifo escolhido, então a distinção é pelo desenho, não pela palavra.
    """
    trecho_lixeira = 'M8.5 3.5a1.5'  # abertura do <path> de lixeira.svg

    assert trecho_lixeira not in _render(variant='danger')
    assert trecho_lixeira in _render(variant='descarte')


def test_danger_e_descarte_sao_glifos_diferentes():
    danger = _render(variant='danger')
    descarte = _render(variant='descarte')

    assert danger != descarte


@pytest.mark.parametrize('variant', ['dangre', 'estado-que-nao-existe', ''])
def test_variante_desconhecida_grita_pela_decisao_a1(variant):
    html = _render(variant=variant)

    assert 'role="alert"' in html
    assert f'data-modal-icon-variant="{variant}"' in html
    # Fundo cheio de grito (`bg-danger`), não a lavagem `-muted` das variantes
    # conhecidas — senão a variante desconhecida vira uma cor plausível.
    assert 'bg-danger ' in html or html.rstrip().endswith('bg-danger')
    assert 'bg-danger-muted' not in html


@pytest.mark.parametrize('variant', ['dangre', 'estado-que-nao-existe', ''])
def test_variante_desconhecida_ainda_tem_glifo_decorativo(variant):
    """A caixa que grita ainda precisa do sinal não-cromático."""
    html = _render(variant=variant)

    assert html.count('<svg') == 1
    assert 'aria-hidden="true"' in html


def test_variante_desconhecida_tem_texto_acessivel():
    """`role="alert"` sem conteúdo perceptível por AT não anuncia nada."""
    html = _render(variant='dangre')

    assert 'sr-only' in html


def test_modal_icon_nao_desenha_svg_inline():
    """Guarda contra o desenho voltar a ser inline — dois mecanismos no mesmo
    arquivo foi como `warning`/`info` divergiram do registry usado por `danger`."""
    import pathlib

    partial = (
        pathlib.Path(__file__).resolve().parents[3]
        / 'apps/core/templates/components/_modal_icon.html'
    )
    conteudo = partial.read_text(encoding='utf-8')

    assert '<svg' not in conteudo
    assert '{% icon "' in conteudo
