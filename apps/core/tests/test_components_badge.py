"""Testes diretos de components/badge.html (sem DB, sem view)."""

import pathlib
import re
import xml.etree.ElementTree as ET

import pytest
from django.template.loader import render_to_string

BASE_DIR = pathlib.Path(__file__).resolve().parents[3]
BADGE_TEMPLATE = BASE_DIR / 'apps' / 'core' / 'templates' / 'components' / 'badge.html'

VARIANTE_DESCONHECIDA = 'estado-que-nao-existe'

# Famílias de paleta crua que o design system declara como exceção viva para
# este arquivo (`docs/design-system.md`, regra "Token, nunca shade"): as quatro
# variantes de catálogo que ainda não têm token semântico. Qualquer outra
# família crua aqui é regressão.
FAMILIAS_DE_CATALOGO_PERMITIDAS = {'orange', 'indigo', 'violet', 'yellow'}

CLASSE_DE_PALETA_RE = re.compile(r'(?:bg|text|border|ring|divide)-([a-z]+)-\d')


def _render(**ctx):
    ctx.setdefault('variant', 'slate')
    ctx.setdefault('label', 'Rótulo')
    return render_to_string('components/badge.html', ctx)


def _arvore(**ctx):
    """Renderiza e devolve o <span> raiz como árvore.

    O componente é um único elemento bem-formado, então `ElementTree` basta e
    não traz dependência nova. Asserção por árvore, e não por substring, é o
    que distingue "o texto está no HTML" de "o texto está no lugar certo, no
    elemento certo, na ordem certa" — a diferença que este arquivo precisa
    provar depois que o ramo de fallback passou a carregar `sr-only`.
    """
    return ET.fromstring(_render(**ctx).strip())


def _classes(elemento):
    return set((elemento.get('class') or '').split())


def _e_sr_only(elemento):
    return 'sr-only' in _classes(elemento)


def _tokens(raiz):
    """Pedaços de texto do badge em ordem de documento, marcados por visibilidade.

    Devolve `[(visivel, texto), ...]`. Serve para afirmar **ordem** entre o
    sinal visível e o texto só-leitor-de-tela sem depender de o sinal estar
    solto na raiz ou dentro de um `<span>` interno.
    """
    tokens = [(True, raiz.text or '')]
    for filho in raiz:
        tokens.append((not _e_sr_only(filho), ''.join(filho.itertext())))
        tokens.append((True, filho.tail or ''))
    return tokens


def _texto_visivel(raiz):
    """Texto que sobra na tela depois de descontar todo `sr-only`."""
    return ''.join(texto for visivel, texto in _tokens(raiz) if visivel)


@pytest.mark.parametrize(
    'variant,classes_esperadas',
    [
        ('slate', ['bg-bg-subtle', 'text-text-primary', 'ring-border']),
        (
            'blue',
            ['bg-primary-muted', 'text-primary-text-strong', 'ring-primary-border'],
        ),
        (
            'blue-strong',
            [
                'bg-primary-muted-strong',
                'text-primary-text-strong',
                'ring-primary-border-strong',
            ],
        ),
        (
            'amber',
            ['bg-warning-muted', 'text-warning-text-strong', 'ring-warning-border'],
        ),
        (
            'amber-strong',
            [
                'bg-warning-muted-strong',
                'text-warning-text-strong',
                'ring-warning-border-strong',
            ],
        ),
        (
            'green',
            ['bg-success-muted', 'text-success-text-strong', 'ring-success-border'],
        ),
        ('red', ['bg-danger-muted', 'text-danger-text-strong', 'ring-danger-border']),
        (
            'red-strong',
            [
                'bg-danger-muted-strong',
                'text-danger-text-strong',
                'ring-danger-border-strong',
            ],
        ),
        ('teal', ['bg-return-muted', 'text-return-text-strong', 'ring-return-border']),
        # Fora do mapeamento da issue #86 — permanecem cru de propósito.
        ('orange', ['bg-orange-100', 'text-orange-900', 'ring-orange-200']),
        ('indigo', ['bg-indigo-100', 'text-indigo-900', 'ring-indigo-200']),
        ('violet', ['bg-violet-100', 'text-violet-900', 'ring-violet-200']),
        ('yellow', ['bg-yellow-100', 'text-yellow-900', 'ring-yellow-200']),
    ],
)
def test_variant_produz_classes_de_cor_esperadas(variant, classes_esperadas):
    html = _render(variant=variant)
    for classe in classes_esperadas:
        assert classe in html


def test_label_e_renderizado():
    html = _render(label='Autorizada')
    assert 'Autorizada' in html


def test_variant_desconhecida_cai_no_fallback_indisponivel():
    html = _render(variant='estado-que-nao-existe')
    assert 'bg-danger' in html
    assert 'ring-danger-hover' in html
    assert 'Indisponível' in html


def test_role_e_propagado_literalmente():
    html = _render(variant='blue', role='status')
    assert 'role="status"' in html


def test_role_ausente_por_padrao():
    html = _render()
    assert 'role=' not in html


def test_aria_label_e_propagado_literalmente():
    html = _render(variant='red', aria_label='Estado: Recusada')
    assert 'aria-label="Estado: Recusada"' in html


def test_aria_label_ausente_por_padrao():
    html = _render()
    assert 'aria-label=' not in html


def test_todas_as_variantes_de_marca_mantem_rounded_full_pill():
    for variant in ['slate', 'blue', 'amber', 'green', 'red', 'teal']:
        html = _render(variant=variant)
        assert 'rounded-full' in html


# ─── Ramo de fallback: preserva o que hoje descarta (issue #121) ──────────


def test_fallback_emite_prefixo_sr_dentro_de_sr_only():
    raiz = _arvore(variant=VARIANTE_DESCONHECIDA, prefixo_sr='Estado: ')
    primeiro = list(raiz)[0]
    assert _e_sr_only(primeiro), (
        'o prefixo do leitor de tela precisa ser o primeiro filho do badge'
    )
    assert primeiro.text == 'Estado: '


def test_fallback_mantem_indisponivel_como_texto_visivel():
    raiz = _arvore(variant=VARIANTE_DESCONHECIDA, label='Aguardando autorização')
    assert 'Indisponível' in _texto_visivel(raiz)


def test_fallback_preserva_label_em_sr_only_depois_do_sinal():
    tokens = _tokens(
        _arvore(variant=VARIANTE_DESCONHECIDA, label='Aguardando autorização')
    )

    posicao_sinal = [
        i
        for i, (visivel, texto) in enumerate(tokens)
        if visivel and 'Indisponível' in texto
    ]
    posicao_label = [
        i
        for i, (visivel, texto) in enumerate(tokens)
        if not visivel and '(Aguardando autorização)' in texto
    ]

    assert posicao_sinal, 'o sinal "Indisponível" sumiu do texto visível'
    assert posicao_label, (
        'o label recebido não foi preservado em sr-only entre parênteses'
    )
    assert min(posicao_label) > max(posicao_sinal), (
        'o label precisa vir depois do sinal, não no lugar dele'
    )


def test_fallback_preserva_role_e_aria_label():
    raiz = _arvore(
        variant=VARIANTE_DESCONHECIDA,
        role='status',
        aria_label='Estado: Indisponível',
    )
    assert raiz.get('role') == 'status'
    assert raiz.get('aria-label') == 'Estado: Indisponível'


def test_fallback_expoe_variant_crua_para_depuracao():
    raiz = _arvore(variant=VARIANTE_DESCONHECIDA)
    assert raiz.get('data-badge-variant') == VARIANTE_DESCONHECIDA


def test_fallback_sem_label_nao_emite_parenteses_vazios():
    raiz = _arvore(variant=VARIANTE_DESCONHECIDA, label='')
    assert '()' not in ''.join(raiz.itertext())


def test_fallback_sem_prefixo_sr_tem_um_unico_sr_only_o_do_label():
    raiz = _arvore(variant=VARIANTE_DESCONHECIDA, label='Autorizada')
    sr_only = [filho for filho in raiz if _e_sr_only(filho)]
    assert len(sr_only) == 1
    assert 'Autorizada' in ''.join(sr_only[0].itertext())


# ─── Token no lugar da última cor crua (issue #121) ───────────────────────


def test_fallback_usa_token_semantico_e_nao_text_white():
    raiz = _arvore(variant=VARIANTE_DESCONHECIDA)
    classes = _classes(raiz)
    assert 'text-text-on-primary' in classes
    assert 'text-white' not in classes


def test_badge_nao_tem_cor_crua_fora_das_quatro_variantes_de_catalogo():
    conteudo = BADGE_TEMPLATE.read_text(encoding='utf-8')
    familias = set(CLASSE_DE_PALETA_RE.findall(conteudo))
    assert familias == FAMILIAS_DE_CATALOGO_PERMITIDAS, (
        'famílias de paleta crua fora da exceção declarada: '
        f'{sorted(familias - FAMILIAS_DE_CATALOGO_PERMITIDAS)}; '
        f'exceção que sumiu do arquivo: '
        f'{sorted(FAMILIAS_DE_CATALOGO_PERMITIDAS - familias)}'
    )


def test_badge_nao_usa_cor_crua_sem_shade():
    """`text-white` não tem dígito e escapa do regex de família — cobre à parte."""
    conteudo = BADGE_TEMPLATE.read_text(encoding='utf-8')
    assert 'text-white' not in conteudo
    assert 'bg-white' not in conteudo
