"""Testes diretos de components/alert.html (sem DB, sem view).

Contrato de uma frase (#127): caixa de aviso estático de página ou formulário,
com glifo de nível e `role` derivado da variante. O `layout="row"` — que era
cartão de decisão de workflow — saiu para
`requisicoes/partials/_painel_decisao.html`, e com ele saíram `action_template`,
`heading_id`, `bg_class`, `icone` e `aria_live`.
"""

import copy
import pathlib
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.test import override_settings

FIXTURES_DIR = Path(__file__).resolve().parent / 'fixtures'
BASE_DIR = pathlib.Path(__file__).resolve().parents[3]

VARIANTE_DESCONHECIDA = 'estado-que-nao-existe'
VARIANTES_CONHECIDAS = {'info', 'success', 'warning', 'danger'}


def _templates_com_fixtures():
    templates = copy.deepcopy(settings.TEMPLATES)
    templates[0]['DIRS'] = [FIXTURES_DIR, *templates[0].get('DIRS', [])]
    return templates


com_fixture_body_template = override_settings(TEMPLATES=_templates_com_fixtures())


def _render(**ctx):
    ctx.setdefault('message', 'Mensagem de teste')
    return render_to_string('components/alert.html', ctx)


def test_variant_padrao_info_usa_role_status():
    html = _render()
    assert 'role="status"' in html
    assert 'border-primary-border' in html
    assert 'bg-primary-subtle' in html
    assert 'text-primary-text-emphasis' in html


@pytest.mark.parametrize(
    'variant,role_esperado,classes_esperadas',
    [
        (
            'success',
            'status',
            [
                'border-success-border',
                'bg-success-subtle',
                'text-success-text-emphasis',
            ],
        ),
        (
            'warning',
            'alert',
            ['border-warning-border', 'bg-warning-subtle', 'text-warning-text'],
        ),
        (
            'danger',
            'alert',
            ['border-danger-border', 'bg-danger-subtle', 'text-danger-text-emphasis'],
        ),
    ],
)
def test_variante_define_role_e_cor(variant, role_esperado, classes_esperadas):
    html = _render(variant=variant)
    assert f'role="{role_esperado}"' in html
    for classe in classes_esperadas:
        assert classe in html


def test_role_override_sobrescreve_padrao_da_variante():
    html = _render(variant='warning', role='note')
    assert 'role="note"' in html
    assert 'role="alert"' not in html


def test_o_glifo_de_nivel_e_sempre_emitido():
    """`icone=False` morreu (#127). 100% de quem o passava era `warning` ou
    `danger` — os dois níveis em que o glifo é o único sinal não-cromático, e
    justamente onde a distinção precisa sobreviver ao daltonismo e ao brilho do
    galpão."""
    for variant in ('info', 'success', 'warning', 'danger', VARIANTE_DESCONHECIDA):
        assert _render(variant=variant).count('<svg') == 1


def test_icone_do_chamador_nao_desliga_mais_o_glifo():
    assert '<svg' in _render(icone=False)
    assert '<svg' in _render(icone='False')


def test_message_e_autoescapado():
    html = _render(message='<script>alert(1)</script>')
    assert '<script>' not in html
    assert '&lt;script&gt;' in html


# ─── Hardening: entradas extremas (issue #122, /impeccable harden) ────────


def test_message_extremamente_longa_renderiza_integralmente():
    mensagem_longa = 'A requisição foi bloqueada pela política de estoque. ' * 20
    html = _render(message=mensagem_longa)
    assert mensagem_longa in html


def test_message_com_emoji_e_acentuacao_renderiza_integralmente():
    mensagem = 'Ação necessária ⚠️ — saldo insuficiente no pátio nº 3 (São João)'
    html = _render(message=mensagem)
    assert mensagem in html


def test_fallback_data_alert_variant_e_escapado_no_atributo():
    html = _render(variant='desconhecida:"><img src=x>')
    assert '<img src=x>' not in html
    assert 'data-alert-variant="desconhecida:&quot;&gt;&lt;img src=x&gt;"' in html


@com_fixture_body_template
def test_body_template_inclui_conteudo_e_herda_contexto():
    html = render_to_string(
        'components/alert.html',
        {
            'variant': 'danger',
            'body_template': '_fixture_teste_body_template.html',
            'valor_herdado': 'valor-vindo-do-contexto-do-chamador',
        },
    )
    assert 'data-fixture-heranca-contexto' in html
    assert 'valor-vindo-do-contexto-do-chamador' in html


@com_fixture_body_template
def test_body_template_sem_message_nao_exige_message():
    html = render_to_string(
        'components/alert.html',
        {
            'variant': 'warning',
            'body_template': '_fixture_teste_body_template.html',
            'valor_herdado': 'valor-sem-message',
        },
    )
    assert 'data-fixture-heranca-contexto' in html
    assert 'valor-sem-message' in html


@com_fixture_body_template
def test_body_template_tem_precedencia_sobre_message():
    html = render_to_string(
        'components/alert.html',
        {
            'message': 'mensagem que nao deveria aparecer',
            'body_template': '_fixture_teste_body_template.html',
            'valor_herdado': 'valor-do-body-template',
        },
    )
    assert 'mensagem que nao deveria aparecer' not in html
    assert 'valor-do-body-template' in html


def test_class_passthrough_e_mesclado_nao_substitui_invariantes():
    html = _render(**{'class': 'meu-ajuste-customizado'})
    assert 'meu-ajuste-customizado' in html
    assert 'rounded-lg' in html
    assert 'px-4 py-3' in html


@pytest.mark.parametrize('variant', ['info', 'success', 'warning', 'danger'])
def test_aria_live_nao_existe_mais_no_contrato(variant):
    """Contradição impossível por construção, não barrada por guarda (#127).

    `role` e `aria_live` eram passthrough independentes, e nada impedia
    `role="alert"` com `aria-live="polite"`. O `role` já carrega a
    assertividade: `alert` é assertivo, `status` é polido.
    """
    assert 'aria-live' not in _render(variant=variant, aria_live='polite')
    assert 'aria-live' not in _render(variant=variant, aria_live='assertive')


def test_id_ausente_por_padrao():
    html = _render()
    assert ' id=' not in html


def test_id_explicito_renderiza_atributo():
    html = _render(id='aviso-duplicidade')
    assert 'id="aviso-duplicidade"' in html


def test_message_vazia_sem_body_template_renderiza_casca_valida():
    html = render_to_string(
        'components/alert.html',
        {
            'variant': 'danger',
            'id': 'aviso-duplicidade',
            'message': '',
            'class': 'hidden',
        },
    )
    assert 'id="aviso-duplicidade"' in html
    assert 'hidden' in html
    assert 'role="alert"' in html


def test_casca_com_id_declara_o_slot_de_hidratacao():
    """O JS do chamador escrevia `textContent` no nó raiz, apagando o wrapper
    interno — funcionava por acidente de layout, porque as classes de flex da
    raiz continuavam aplicando sobre o text node. O slot dá um alvo declarado."""
    html = _render(id='aviso-duplicidade', message='')

    assert 'id="aviso-duplicidade-conteudo"' in html


def test_sem_id_nao_ha_slot_a_declarar():
    assert '-conteudo"' not in _render()


# ─── Variante "" explícita normaliza para info (issue #122) ───────────────


def test_variant_vazia_explicita_normaliza_para_info():
    html = _render(variant='')
    assert 'role="status"' in html
    assert 'bg-primary-subtle' in html


# ─── Ramo de fallback: variante desconhecida grita (issue #122) ───────────


def test_fallback_stack_usa_cor_preenchida_de_grito():
    html = _render(variant=VARIANTE_DESCONHECIDA)
    assert 'bg-danger' in html
    assert 'text-text-on-primary' in html


def test_fallback_emite_sinal_visivel_aviso_indisponivel():
    html = _render(variant=VARIANTE_DESCONHECIDA)
    assert 'Aviso indisponível' in html


def test_fallback_preserva_message():
    html = _render(variant=VARIANTE_DESCONHECIDA, message='Mensagem original')
    assert 'Mensagem original' in html


@com_fixture_body_template
def test_fallback_preserva_body_template():
    html = render_to_string(
        'components/alert.html',
        {
            'variant': VARIANTE_DESCONHECIDA,
            'body_template': '_fixture_teste_body_template.html',
            'valor_herdado': 'valor-do-fallback',
        },
    )
    assert 'data-fixture-heranca-contexto' in html
    assert 'valor-do-fallback' in html


def test_fallback_emite_data_alert_variant_com_valor_cru():
    html = _render(variant=VARIANTE_DESCONHECIDA)
    assert f'data-alert-variant="{VARIANTE_DESCONHECIDA}"' in html


def test_fallback_stack_recebe_role_alert():
    html = _render(variant=VARIANTE_DESCONHECIDA)
    assert 'role="alert"' in html


def test_fallback_ignora_role_explicito():
    html = _render(variant=VARIANTE_DESCONHECIDA, role='note')
    assert 'role="alert"' in html
    assert 'role="note"' not in html


PARAMETROS_MORTOS = ('layout', 'action_template', 'heading_id', 'bg_class')


@pytest.mark.parametrize('morto', PARAMETROS_MORTOS)
def test_parametro_do_painel_de_decisao_nao_tem_mais_efeito(morto):
    """O componente fazia três trabalhos incompatíveis. Sobrou um."""
    html = _render(variant='danger', **{morto: 'bg-return-subtle'})

    assert 'bg-return-subtle' not in html
    assert 'bg-danger-subtle' in html
    assert '<section' not in html


@pytest.mark.parametrize('morto', [*PARAMETROS_MORTOS, 'icone', 'aria_live'])
def test_nenhum_chamador_passa_parametro_morto_ao_alert(morto):
    """Falha na presença, não na contagem: parâmetro morto que continua sendo
    passado não quebra a tela — ele silenciosamente não faz nada."""
    padrao = re.compile(
        r'\{%\s*include\s+["\']components/alert\\.html["\'].*?%\}', re.S
    )
    for arquivo in sorted((BASE_DIR / 'apps').rglob('*.html')):
        for include in padrao.findall(arquivo.read_text(encoding='utf-8')):
            assert f'{morto}=' not in include, arquivo.relative_to(BASE_DIR)


def test_nenhum_chamador_de_alert_passa_variante_fora_das_quatro_conhecidas():
    padrao_include = re.compile(
        r'include\s+"components/alert\.html"[^%]*?(?:with[^%]*?variant(?:_token)?=([^\s%]+))?'
    )
    ofensores = []
    for arquivo in sorted((BASE_DIR / 'apps').rglob('*.html')):
        conteudo = arquivo.read_text(encoding='utf-8')
        for m in padrao_include.finditer(conteudo):
            valor = m.group(1)
            if valor is None:
                continue
            if valor.startswith('"') and valor.endswith('"'):
                literal = valor.strip('"')
                if literal not in VARIANTES_CONHECIDAS:
                    ofensores.append(
                        f'{arquivo.relative_to(BASE_DIR)}: variant={valor}'
                    )
    assert ofensores == [], f'chamador(es) fora do catálogo: {ofensores}'
