"""Testes diretos de components/filter_chips.html e filter_presets_periodo.html.

Assimetria que esta suíte fecha: `badge.html` tem teste de classes por variante
em `test_components_badge.py`; o chip de filtro e o preset de período não tinham
nenhum. Os dois são `<a>` com `hx-get` + `hx-push-url` que alternam um recorte de
query — controles, não marcadores —, e por isso usam **raio de controle**
(`rounded-md`), não pílula (`rounded-full`). Ver DESIGN.md §Shapes, "Chip de
filtro não é badge de estado" (fatia b da #173).
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from django.template.loader import render_to_string

from apps.core.filtros import ChipFiltro, PresetPeriodo

_COMPONENTES = Path(__file__).resolve().parents[2] / 'core' / 'templates' / 'components'
_COMENTARIO_DJANGO = re.compile(r'\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}', re.S)

# Bloco de classes que o anel de foco exige nos dois estados do controle.
FOCO = {
    'focus-visible:outline-none',
    'focus-visible:ring-2',
    'focus-visible:ring-border-focus',
    'focus-visible:ring-offset-1',
}

SUPERFICIE_ATIVA = {
    'border-primary-border-strong',
    'bg-primary-muted',
    'text-primary-text-strong',
}

SUPERFICIE_NEUTRA = {
    'border-border',
    'bg-surface',
    'text-text-secondary',
    'hover:bg-bg-page',
}


def _chip(*, ativo, glifo='', rotulo='Só divergências'):
    return ChipFiltro(
        id='divergencias',
        rotulo=rotulo,
        glifo=glifo,
        ativo=ativo,
        url='/preview/?status=divergencia',
    )


def _preset(*, ativo, rotulo='30 dias'):
    return PresetPeriodo(
        id='30d',
        rotulo=rotulo,
        ativo=ativo,
        url='/historico/?data_ini=2026-08-10&data_fim=2026-09-09',
    )


def _render_chips(chips):
    return render_to_string(
        'components/filter_chips.html',
        {'chips': chips, 'target_id': 'resultados'},
    )


def _render_presets(presets):
    return render_to_string(
        'components/filter_presets_periodo.html',
        {'presets': presets, 'target_id': 'resultados'},
    )


def _ancora(html):
    """O primeiro `<a>` do bloco renderizado, como árvore."""
    raiz = ET.fromstring(html.strip())
    return next(el for el in raiz.iter() if el.tag == 'a')


def _classes(elemento):
    return set((elemento.get('class') or '').split())


# ─── Chip de filtro ──────────────────────────────────────────────────────


def test_chip_ativo_usa_raio_de_controle_e_nao_pilula():
    classes = _classes(_ancora(_render_chips([_chip(ativo=True)])))
    assert 'rounded-md' in classes
    assert 'rounded-full' not in classes


def test_chip_inativo_usa_raio_de_controle_e_nao_pilula():
    classes = _classes(_ancora(_render_chips([_chip(ativo=False)])))
    assert 'rounded-md' in classes
    assert 'rounded-full' not in classes


def test_chip_mantem_piso_de_alvo_de_toque_nos_dois_estados():
    for ativo in (True, False):
        classes = _classes(_ancora(_render_chips([_chip(ativo=ativo)])))
        assert 'min-h-11' in classes, f'chip ativo={ativo} perdeu o piso de 44px'


def test_chip_mantem_anel_de_foco_nos_dois_estados():
    for ativo in (True, False):
        classes = _classes(_ancora(_render_chips([_chip(ativo=ativo)])))
        assert FOCO <= classes, f'chip ativo={ativo} sem o bloco de foco completo'


def test_chip_ativo_tem_aria_current_e_glifo_de_desligar():
    html = _render_chips([_chip(ativo=True)])
    assert 'aria-current="true"' in html
    assert '✕' in html


def test_chip_inativo_nao_tem_aria_current_nem_glifo_de_desligar():
    html = _render_chips([_chip(ativo=False)])
    assert 'aria-current' not in html
    assert '✕' not in html


def test_chip_ativo_tem_superficie_primaria():
    classes = _classes(_ancora(_render_chips([_chip(ativo=True)])))
    assert SUPERFICIE_ATIVA <= classes


def test_chip_inativo_tem_superficie_neutra():
    classes = _classes(_ancora(_render_chips([_chip(ativo=False)])))
    assert SUPERFICIE_NEUTRA <= classes


def test_chip_renderiza_glifo_opcional():
    html = _render_chips([_chip(ativo=False, glifo='●')])
    assert '●' in html


def test_sem_chips_nao_renderiza_nada():
    assert _render_chips([]).strip() == ''


def _markup_sem_comentario(nome):
    texto = (_COMPONENTES / nome).read_text(encoding='utf-8')
    return _COMENTARIO_DJANGO.sub('', texto)


def test_markup_do_chip_nao_volta_para_rounded_full():
    """O chip saiu da pílula na fatia b da #173 — `rounded-full` não volta a
    um ramo de classe. A prosa do cabeçalho pode citar o token; o markup não.
    """
    assert 'rounded-full' not in _markup_sem_comentario('filter_chips.html')


# ─── Preset de período (mesmo contrato de forma que o chip) ───────────────


def test_preset_usa_raio_de_controle_e_nao_pilula_nos_dois_estados():
    for ativo in (True, False):
        classes = _classes(_ancora(_render_presets([_preset(ativo=ativo)])))
        assert 'rounded-md' in classes
        assert 'rounded-full' not in classes


def test_preset_mantem_piso_de_toque_e_anel_de_foco():
    for ativo in (True, False):
        classes = _classes(_ancora(_render_presets([_preset(ativo=ativo)])))
        assert 'min-h-11' in classes
        assert FOCO <= classes


def test_sem_presets_nao_renderiza_nada():
    assert _render_presets([]).strip() == ''


def test_markup_do_preset_nao_volta_para_rounded_full():
    assert 'rounded-full' not in _markup_sem_comentario('filter_presets_periodo.html')
