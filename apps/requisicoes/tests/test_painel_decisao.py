"""Testes diretos do painel de decisão de workflow (sem DB, sem view) — #127.

O painel — título, descrição e botão que abre o modal de confirmação — vivia
montado em cima de `components/alert.html`, que emprestava só a lavagem de cor
por variante. Dessa carona vinham quatro achados: nível comunicado só por cor,
`role="group"` sem nome acessível, o switch variante→token reescrito nos corpos
de domínio e a descrição de uma decisão irreversível em 12px.

Depois da extração o painel é uma superfície própria, e é ela que estes testes
cobram. A resolução de cor em si é testada isolada, em
`apps/core/tests/test_core_tags.py`.

O painel é renderizado direto, sem o `_confirmacao_acao.html` em volta: o modal
que o partial de composição inclui traz o próprio ícone, e uma asserção de
"exatamente um `<svg>`" feita sobre os dois juntos não estaria medindo o painel.
"""

import pathlib
import re

import pytest
from django.template.loader import render_to_string

from apps.core.tests.marcacao import atributo, elementos

BASE_DIR = pathlib.Path(__file__).resolve().parents[3]
PAINEL = 'requisicoes/partials/_painel_decisao.html'
COMPOSICAO = 'requisicoes/partials/_confirmacao_acao.html'
PARTIAIS_DE_DOMINIO = (
    'apps/requisicoes/templates/requisicoes/partials/_painel_decisao.html',
    'apps/requisicoes/templates/requisicoes/partials/_confirmacao_acao.html',
)
VARIANTES = ('info', 'warning', 'danger')
DESCONHECIDAS = ('', 'primary', 'success', 'nao-existe')


def _render(layout='card', variant_token='info', **extra):
    contexto = {
        'layout': layout,
        'variant_token': variant_token,
        'modal_id': 'confirmar-autorizar',
        'titulo': 'Autorização integral',
        'conteudo': 'Aprove a requisição e reserve o saldo necessário.',
        'botao_label': 'Autorizar',
        'botao_variant': 'primary',
    }
    if layout == 'banner':
        contexto['heading_id'] = 'estornar-titulo'
    contexto.update(extra)
    return render_to_string(PAINEL, contexto)


def _classe_do_paragrafo(html, texto):
    (classe,) = re.findall(rf'<p class="([^"]*)"[^>]*>\s*{re.escape(texto)}', html)
    return classe


# ---------------------------------------------------------------------------
# Nome acessível — nenhum "grupo, grupo, grupo" na navegação estrutural
# ---------------------------------------------------------------------------


def test_card_nomeia_o_grupo_pelo_proprio_titulo():
    html = _render(layout='card')

    (grupo,) = [
        atributos
        for _, atributos, _ in elementos(html, 'div', 'section')
        if atributo(atributos, 'role') == 'group'
    ]
    rotulado_por = atributo(grupo, 'aria-labelledby')

    assert rotulado_por
    assert f'id="{rotulado_por}"' in html


def test_banner_nomeia_a_secao_pelo_heading_id_do_chamador():
    html = _render(layout='banner', heading_id='estornar-titulo')

    (secao,) = [atributos for _, atributos, _ in elementos(html, 'section')]

    assert atributo(secao, 'aria-labelledby') == 'estornar-titulo'
    assert 'id="estornar-titulo"' in html


@pytest.mark.parametrize('layout', ['card', 'banner'])
@pytest.mark.parametrize('variant_token', VARIANTES)
def test_nenhum_grupo_anonimo_em_nenhum_layout(layout, variant_token):
    """`role="group"` sem nome não é agrupamento — é ruído estrutural. Os três
    cards de decisão viravam "grupo, grupo, grupo" apesar de cada um já ter um
    heading pronto para nomeá-lo."""
    html = _render(layout=layout, variant_token=variant_token)

    for _, atributos, _ in elementos(html, 'div', 'section'):
        if atributo(atributos, 'role') == 'group':
            assert atributo(atributos, 'aria-labelledby')


def test_o_id_do_titulo_do_card_deriva_do_modal_id():
    """Derivado, nunca contado: dois painéis na mesma tela não podem colidir."""
    html = _render(layout='card', modal_id='confirmar-recusar')

    assert 'id="confirmar-recusar-titulo"' in html


@pytest.mark.parametrize('layout', ['card', 'banner'])
def test_o_painel_tem_exatamente_um_heading(layout):
    html = _render(layout=layout)

    assert len(re.findall(r'<h[1-6][\s>]', html)) == 1


# ---------------------------------------------------------------------------
# Sinal de nível além da cor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('layout', ['card', 'banner'])
@pytest.mark.parametrize('variant_token', VARIANTES)
def test_o_painel_emite_o_glifo_de_nivel(layout, variant_token):
    """Antes, um banner `danger` e um `warning` só se distinguiam pela lavagem
    `-subtle` (L≈98%) e pela borda — cor como sinal único de estado."""
    html = _render(layout=layout, variant_token=variant_token)

    assert html.count('<svg') == 1
    assert 'fill="currentColor"' in html
    assert 'aria-hidden="true"' in html


@pytest.mark.parametrize('variant_token', [*VARIANTES, 'nao-existe'])
def test_o_glifo_nao_recebe_classe_de_cor_propria(variant_token):
    """1.4.11: cor fixa da variante punha o ícone de `warning` em 2.07:1 sobre
    o próprio fundo. Herdando o token de texto da caixa, vai a 6.88:1."""
    html = _render(variant_token=variant_token)

    (svg,) = [atributos for _, atributos, _ in elementos(html, 'svg')]

    assert not re.search(r'\btext-(?:primary|success|warning|danger)-', svg)


@pytest.mark.parametrize('variant_token', DESCONHECIDAS)
def test_variante_desconhecida_nao_perde_o_sinal_nao_cromatico(variant_token):
    html = _render(variant_token=variant_token)

    assert html.count('<svg') == 1


# ---------------------------------------------------------------------------
# Tipografia — Regra dos 14px
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('layout', ['card', 'banner'])
def test_a_descricao_usa_o_corpo_do_sistema(layout):
    """12px é rótulo estrutural em caixa alta. A prosa que sustenta autorizar,
    recusar ou estornar é conteúdo, lido em bloco pelo chefe de setor."""
    html = _render(layout=layout, conteudo='Descrição da decisão.')

    classe = _classe_do_paragrafo(html, 'Descrição da decisão.')

    assert 'text-sm' in classe
    assert 'text-xs' not in classe


@pytest.mark.parametrize('layout', ['card', 'banner'])
def test_nenhum_texto_do_painel_cai_para_12px(layout):
    html = _render(layout=layout)

    assert 'text-xs' not in html


# ---------------------------------------------------------------------------
# Parâmetros que descreviam conteúdo, não estrutura
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('layout', ['card', 'banner'])
def test_desc_class_do_chamador_nao_tem_mais_efeito(layout):
    """`docs/design-system.md`: parâmetro que descreve conteúdo e não estrutura
    é sinal de abstração errada."""
    html = _render(layout=layout, desc_class='mt-1 text-xs text-return-text')

    assert 'text-return-text' not in html
    assert 'text-xs' not in html


@pytest.mark.parametrize('layout', ['card', 'banner'])
def test_bg_class_do_chamador_nao_tem_mais_efeito(layout):
    html = _render(layout=layout, variant_token='danger', bg_class='bg-return-subtle')

    assert 'bg-return-subtle' not in html
    assert 'bg-danger-subtle' in html


# ---------------------------------------------------------------------------
# Falha alta (Decisão A-1) — o painel é dono do próprio fallback
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('layout', ['card', 'banner'])
@pytest.mark.parametrize('variant_token', DESCONHECIDAS)
def test_variante_desconhecida_grita_em_cor_preenchida(layout, variant_token):
    html = _render(layout=layout, variant_token=variant_token)

    assert 'Aviso indisponível' in html
    assert 'bg-danger ' in html
    assert 'bg-danger-subtle' not in html


@pytest.mark.parametrize('layout', ['card', 'banner'])
def test_variante_desconhecida_emite_role_alert_sem_excecao(layout):
    """O grito não pode ser rebaixado a `group` nem a região anônima."""
    html = _render(layout=layout, variant_token='nao-existe')

    assert 'role="alert"' in html
    assert 'role="group"' not in html


@pytest.mark.parametrize('layout', ['card', 'banner'])
def test_variante_desconhecida_emite_o_valor_cru_para_depuracao(layout):
    html = _render(layout=layout, variant_token='nao-existe')

    assert 'data-painel-variant="nao-existe"' in html


def test_variante_desconhecida_escapa_o_valor_cru_no_atributo():
    html = _render(variant_token='"><script>alert(1)</script>')

    assert '<script>' not in html


@pytest.mark.parametrize('layout', ['card', 'banner'])
def test_variante_desconhecida_preserva_a_decisao(layout):
    """Falha alta não é falha muda: a decisão continua legível e acionável."""
    html = _render(
        layout=layout,
        variant_token='nao-existe',
        titulo='Estornar requisição',
        conteudo='Reverte toda a entregue líquida.',
    )

    assert 'Estornar requisição' in html
    assert 'Reverte toda a entregue líquida.' in html
    assert 'Autorizar' in html


# ---------------------------------------------------------------------------
# Guardas de estrutura
# ---------------------------------------------------------------------------


def test_o_painel_nao_e_mais_montado_em_cima_do_alert():
    """`alert.html` é banner estático. Painel de decisão é papel com ação
    persistente — herdar dele só emprestava a cor.

    A guarda procura o `{% include %}`, não a menção: o docstring do painel
    explica de propósito por que os dois são coisas diferentes, e um `not in`
    sobre o arquivo inteiro proibiria justamente a explicação.
    """
    for caminho in PARTIAIS_DE_DOMINIO:
        fonte = (BASE_DIR / caminho).read_text(encoding='utf-8')

        assert not re.search(
            r'\{%\s*include\s+["\']components/alert\.html["\']', fonte
        ), caminho


def test_nenhum_partial_de_dominio_reimplementa_o_mapa_de_cor():
    """Eram dois switches que precisavam concordar com o do componente, sem
    nada garantindo isso. O mapa vive em `classes_painel_decisao`."""
    for caminho in PARTIAIS_DE_DOMINIO:
        fonte = (BASE_DIR / caminho).read_text(encoding='utf-8')
        corpo = re.sub(
            r'\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}', '', fonte, flags=re.S
        )

        assert not re.search(r'\{%\s*(?:el)?if\s+variant_token\s*==', corpo), caminho


def test_o_painel_usa_raio_de_papel_e_a_razao_esta_no_arquivo():
    """Pela Regra do Raio Crescente, papel é 0.75rem. O painel tem sombra e
    padding de seção — a definição de papel no design system."""
    html = _render(layout='banner')
    fonte = (BASE_DIR / PARTIAIS_DE_DOMINIO[0]).read_text(encoding='utf-8')

    assert 'rounded-xl' in html
    assert 'shadow-sm' in html
    assert 'rounded-lg' not in html
    assert 'Regra do Raio Crescente' in fonte


def test_a_composicao_monta_painel_e_modal_no_mesmo_escopo_alpine():
    """Cada instância é autocontida: o `x-data` que abre o modal envolve o
    botão que o dispara."""
    html = render_to_string(
        COMPOSICAO,
        {
            'layout': 'card',
            'variant_token': 'info',
            'modal_id': 'confirmar-autorizar',
            'titulo': 'Autorização integral',
            'conteudo': 'Aprove a requisição.',
            'botao_label': 'Autorizar',
            'botao_variant': 'primary',
            'modal_titulo': 'Autorizar requisição?',
            'modal_descricao': 'Reserva o saldo.',
            'action_url': '/requisicoes/1/autorizar/',
            'confirm_label': 'Confirmar autorização',
            'confirm_variant': 'primary',
        },
    )

    assert "modalController({ id: 'confirmar-autorizar'" in html
    assert 'data-modal-trigger="confirmar-autorizar"' in html
    assert 'id="confirmar-autorizar"' in html


@pytest.mark.parametrize('morto', ['desc_class', 'bg_class', 'botao_class'])
def test_nenhum_chamador_passa_parametro_morto_ao_painel(morto):
    """Falha na presença, não na contagem.

    `desc_class` e `bg_class` descreviam conteúdo, não estrutura; `botao_class`
    existia só para repassar o `shrink-0` que hoje é do próprio painel. Um
    parâmetro morto que continua sendo passado não quebra a tela — ele
    silenciosamente não faz nada, que é pior.
    """
    for caminho in (BASE_DIR / 'apps').rglob('*.html'):
        fonte = caminho.read_text(encoding='utf-8')
        for include in re.findall(
            r'\{%\s*include\s+["\']requisicoes/partials/_confirmacao_acao\.html["\']'
            r'.*?%\}',
            fonte,
            flags=re.S,
        ):
            assert f'{morto}=' not in include, caminho


@pytest.mark.parametrize('layout', ['card', 'banner'])
def test_o_botao_do_painel_sempre_anuncia_que_abre_um_modal(layout):
    """`aria-haspopup="dialog"` não é opcional: o botão do painel abre um modal
    por definição — é isso que faz dele um painel de decisão.

    Como parâmetro, só o banner de estorno declarava, e os outros quatro
    painéis prometiam menos do que faziam.
    """
    html = _render(layout=layout)

    assert 'aria-haspopup="dialog"' in html


def test_botao_aria_haspopup_deixou_de_ser_parametro():
    for caminho in (BASE_DIR / 'apps').rglob('*.html'):
        assert 'botao_aria_haspopup' not in caminho.read_text(encoding='utf-8'), caminho
