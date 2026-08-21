"""Testes de components/_icone_nivel.html — o glifo de nível compartilhado (#127).

O desenho vivia inline no `alert.html` e era reescrito por quem precisasse do
mesmo sinal. Extraído, ele tem um dono só — e um teste que cobra a propriedade
que a #124 comprou: a cor vem de `currentColor`, nunca de classe da variante.
"""

import pathlib

import pytest
from django.template.loader import render_to_string

BASE_DIR = pathlib.Path(__file__).resolve().parents[3]
PARTIAL = 'components/_icone_nivel.html'
VARIANTES = ('info', 'success', 'warning', 'danger')


def _render(**ctx) -> str:
    return render_to_string(PARTIAL, ctx)


@pytest.mark.parametrize('variant', VARIANTES)
def test_toda_variante_conhecida_emite_um_svg(variant):
    html = _render(variant=variant)

    assert html.count('<svg') == 1
    assert '<path' in html


@pytest.mark.parametrize('variant', [*VARIANTES, 'estado-que-nao-existe', ''])
def test_o_glifo_e_sempre_decorativo(variant):
    """O nível é anunciado pelo `role` da caixa, não pelo ícone.

    Ícone com nome acessível duplicaria o anúncio em toda faixa e todo painel.
    """
    html = _render(variant=variant)

    assert 'aria-hidden="true"' in html
    assert 'aria-label' not in html
    assert '<title' not in html


@pytest.mark.parametrize('variant', [*VARIANTES, 'estado-que-nao-existe'])
def test_a_cor_do_glifo_e_sempre_herdada(variant):
    """1.4.11: com cor fixa da variante o ícone de `warning` dava 2.07:1 sobre o
    próprio fundo `-subtle`. Herdando o token de texto da caixa, vai a 6.88:1."""
    import re

    html = _render(variant=variant)

    assert 'fill="currentColor"' in html
    assert not re.search(r'\btext-(?:primary|success|warning|danger)-', html)
    assert 'fill="#' not in html


@pytest.mark.parametrize('variant', [*VARIANTES, 'estado-que-nao-existe'])
def test_a_classe_do_chamador_chega_ao_svg(variant):
    html = _render(variant=variant, **{'class': 'mt-0.5 h-4 w-4 shrink-0'})

    assert 'mt-0.5 h-4 w-4 shrink-0' in html


def test_variante_desconhecida_nao_fica_sem_glifo():
    """A caixa que grita ainda precisa do sinal não-cromático."""
    html = _render(variant='estado-que-nao-existe')

    assert html.count('<svg') == 1


def test_alert_html_consome_o_partial_em_vez_de_desenhar_o_glifo():
    """Guarda contra o desenho voltar a ser inline — foi assim que ele virou
    quatro cópias."""
    alert = (BASE_DIR / 'apps/core/templates/components/alert.html').read_text(
        encoding='utf-8'
    )

    assert PARTIAL in alert
    assert '<svg' not in alert
