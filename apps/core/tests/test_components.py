"""Testes diretos de components/button.html (sem DB, sem view)."""

import re

import pytest
from django.template.loader import render_to_string


def _render(**ctx):
    ctx.setdefault('label', 'Rótulo')
    return render_to_string('components/button.html', ctx)


def test_sem_href_renderiza_button():
    html = _render()
    assert '<button' in html
    assert '<a ' not in html and '<a\n' not in html


def test_com_href_renderiza_link():
    html = _render(href='/destino/')
    assert html.lstrip().startswith('<a')
    assert 'href="/destino/"' in html
    assert '<button' not in html


def test_type_default_button():
    html = _render()
    assert 'type="button"' in html


def test_type_submit():
    html = _render(type='submit')
    assert 'type="submit"' in html


def test_name_e_value_renderizam_atributos_no_button():
    html = _render(name='acao', value='enviar')
    assert 'name="acao"' in html
    assert 'value="enviar"' in html


def test_name_e_value_ausentes_por_padrao():
    html = _render()
    assert 'name=' not in html
    assert 'value=' not in html


def test_value_inteiro_zero_nao_e_tratado_como_ausente():
    html = _render(value=0)
    assert 'value="0"' in html


def test_label_bind_tem_precedencia_sobre_loading_label_e_label_mobile():
    html = _render(
        label='Confirmar',
        label_bind="x ? 'A' : 'B'",
        loading_label='Carregando…',
        label_mobile='Curto',
    )
    assert 'x-text' in html
    assert 'data-submit-text' not in html
    assert 'data-submit-loading-label="Carregando…"' in html


def test_disabled_aplica_atributo_boolean_na_tag():
    html = _render(disabled=True)
    abertura = html[: html.index('>') + 1]
    assert re.search(r'\bdisabled\b(?!:)', abertura)
    assert 'disabled:cursor-not-allowed' in html
    assert 'disabled:opacity-60' in html


def test_disabled_false_nao_aplica_atributo_na_tag():
    html = _render(disabled=False)
    abertura = html[: html.index('>') + 1]
    assert not re.search(r'\bdisabled\b(?!:)', abertura)


@pytest.mark.parametrize(
    'variant,classes_esperadas',
    [
        (
            'primary',
            ['bg-primary', 'hover:bg-primary-hover', 'active:bg-primary-active'],
        ),
        (
            'secondary',
            [
                'bg-surface',
                # border-control (slate-500), não border-strong (slate-300): num
                # botão secundário a borda é a única pista de que há um controle
                # ali, e slate-300 entregava 1.48:1 contra o papel branco.
                'border-border-control',
                'hover:bg-bg-page',
                'text-text-secondary',
            ],
        ),
        (
            'neutral',
            ['bg-text-secondary', 'text-text-on-primary', 'hover:bg-text-primary'],
        ),
        ('danger', ['bg-danger', 'hover:bg-danger-hover', 'active:bg-danger-active']),
        (
            'danger-outline',
            [
                'border-danger-border-strong',
                'text-danger-text',
                'hover:bg-danger-subtle',
            ],
        ),
        ('ghost', ['bg-transparent', 'hover:bg-bg-subtle', 'text-text-secondary']),
        ('link', ['bg-transparent', 'text-primary-text', 'hover:underline']),
    ],
)
def test_variant_produz_classes_de_cor_esperadas(variant, classes_esperadas):
    html = _render(variant=variant)
    for classe in classes_esperadas:
        assert classe in html


@pytest.mark.parametrize(
    'size,classes_esperadas',
    [
        ('sm', ['px-3 py-2 text-xs']),
        ('md', ['px-3 py-2 text-sm']),
    ],
)
def test_size_produz_padding_tipografia_esperados(size, classes_esperadas):
    html = _render(size=size)
    for classe in classes_esperadas:
        assert classe in html


def test_full_width_mobile_aplica_classes():
    html = _render(full_width_mobile=True)
    assert 'w-full sm:w-auto' in html


def test_full_width_mobile_ausente_nao_aplica_classes():
    html = _render()
    assert 'w-full sm:w-auto' not in html


def test_aria_label_sobrescreve_texto_acessivel_mantendo_label_visivel():
    html = _render(label='Ver', aria_label='Ver detalhes da requisição REQ-2026-001')
    assert 'aria-label="Ver detalhes da requisição REQ-2026-001"' in html
    assert '>Ver</' in html or '>Ver<' in html


def test_hx_get_renderiza_atributo_hifenizado():
    html = _render(hx_get='/parcial/')
    assert 'hx-get="/parcial/"' in html
    assert 'hx_get' not in html


def test_hx_post_renderiza_atributo_hifenizado():
    html = _render(hx_post='/acao/')
    assert 'hx-post="/acao/"' in html


def test_hx_target_e_hx_swap_renderizam_atributos_hifenizados():
    html = _render(hx_target='#alvo', hx_swap='outerHTML')
    assert 'hx-target="#alvo"' in html
    assert 'hx-swap="outerHTML"' in html


def test_hx_atributos_ausentes_por_padrao():
    html = _render()
    assert 'hx-get' not in html
    assert 'hx-post' not in html
    assert 'hx-target' not in html
    assert 'hx-swap' not in html


def test_class_passthrough_e_mesclado_nao_substitui_invariantes():
    html = _render(**{'class': 'meu-ajuste-customizado'})
    assert 'meu-ajuste-customizado' in html
    assert 'min-h-11' in html
    assert 'inline-flex' in html


def test_data_modal_trigger_renderiza_atributo():
    html = _render(data_modal_trigger='meu-modal')
    assert 'data-modal-trigger="meu-modal"' in html


def test_data_modal_trigger_renderiza_click_abrir_conforme_contrato_do_modal():
    html = _render(data_modal_trigger='meu-modal')
    assert '@click="abrir($event)"' in html


def test_data_modal_trigger_ausente_por_padrao():
    html = _render()
    assert 'data-modal-trigger' not in html
    assert '@click' not in html


def test_icon_template_incluido_antes_do_label():
    html = render_to_string(
        'components/button.html',
        {'label': 'Confirmar', 'icon_template': 'components/icons/_check.html'},
    )
    icon_idx = html.index('aria-hidden="true"')
    label_idx = html.index('Confirmar')
    assert icon_idx < label_idx


def test_icon_template_ausente_por_padrao_nao_renderiza_span_icone():
    html = _render()
    assert 'aria-hidden="true"' not in html


def test_botao_somente_icone_usa_aria_label_como_nome_acessivel():
    html = render_to_string(
        'components/button.html',
        {
            'label': '',
            'aria_label': 'Fechar',
            'icon_template': 'components/icons/_check.html',
        },
    )
    assert 'aria-label="Fechar"' in html
    assert 'aria-hidden="true"' in html


def test_label_e_aria_label_ausentes_nao_mascara_com_texto_generico():
    html = render_to_string('components/button.html', {})
    assert 'Botão' not in html
    assert 'aria-label' not in html
    assert 'button' in html.lower()


@pytest.mark.parametrize(
    'variant', ['primary', 'secondary', 'danger', 'danger-outline', 'ghost']
)
def test_invariantes_comuns_presentes_exceto_link(variant):
    html = _render(variant=variant)
    for classe in [
        'inline-flex',
        'items-center',
        'justify-center',
        'min-h-11',
        'rounded-md',
        'focus-visible:outline-none',
        'focus-visible:ring-2',
        'focus-visible:ring-offset-1',
    ]:
        assert classe in html


def test_link_nao_forca_min_h_11_nem_justify_center():
    html = _render(variant='link')
    assert 'min-h-11' not in html
    assert 'justify-center' not in html


def test_icon_class_chega_ao_icone_sem_vazar_class_do_botao():
    html = render_to_string(
        'components/button.html',
        {
            'label': 'Registrar',
            'icon_template': 'components/icons/confirmar.svg',
            'icon_class': 'h-5 w-5',
            'class': 'mt-4',
        },
    )
    assert 'class="h-5 w-5"' in html
    icon_svg = html[html.index('<svg') : html.index('</svg>') + len('</svg>')]
    assert 'mt-4' not in icon_svg


def test_icon_class_default_h4_w4_quando_nao_informado():
    html = render_to_string(
        'components/button.html',
        {'label': 'Registrar', 'icon_template': 'components/icons/confirmar.svg'},
    )
    assert 'class="h-4 w-4"' in html


def test_loading_label_gera_atributo_e_span_com_valor_exato():
    html = _render(loading_label='Enviando...')
    assert 'data-submit-loading-label="Enviando..."' in html
    assert '<span data-submit-text>Rótulo</span>' in html


def test_loading_label_ausente_por_padrao():
    html = _render()
    assert 'data-submit-loading-label' not in html
    assert 'data-submit-text' not in html


def test_label_mobile_junto_de_loading_label_gera_dois_spans_responsivos():
    html = _render(
        label='Criar e enviar para autorização',
        label_mobile='Enviar',
        loading_label='Enviando...',
    )
    assert 'data-submit-loading-label="Enviando..."' in html
    assert (
        '<span data-submit-text class="hidden sm:inline">Criar e enviar para autorização</span>'
        in html
    )
    assert '<span data-submit-text class="sm:hidden">Enviar</span>' in html
    assert '<span data-submit-text>Criar e enviar para autorização</span>' not in html


def test_label_mobile_sozinho_sem_loading_label_nao_ativa_spans_responsivos():
    html = _render(label='Criar e enviar para autorização', label_mobile='Enviar')
    assert 'data-submit-text' not in html
    assert 'hidden sm:inline' not in html


def test_x_disabled_emite_binding_alpine_sem_atributo_disabled_estatico():
    html = _render(x_disabled='enviando')
    assert ':disabled="enviando"' in html
    abertura = html[: html.index('>') + 1]
    assert not re.search(r'\bdisabled\b(?!:)(?!=)', abertura.replace(':disabled', ''))


def test_x_disabled_ausente_por_padrao():
    html = _render()
    assert ':disabled' not in html


def test_disabled_e_x_disabled_simultaneos_so_emite_bind_dinamico():
    html = _render(disabled=True, x_disabled='enviando')
    assert ':disabled="enviando"' in html
    abertura = html[: html.index('>') + 1]
    assert not re.search(r'(?<!:)\bdisabled\b(?!:)(?!=)', abertura)


def test_x_aria_busy_emite_binding_alpine():
    html = _render(x_aria_busy='enviando')
    assert ':aria-busy="enviando"' in html


def test_x_aria_busy_ausente_por_padrao():
    html = _render()
    assert ':aria-busy' not in html


def test_label_bind_envolve_label_em_span_x_text_com_fallback_estatico():
    html = _render(label='Entrar', label_bind="submitting ? 'Entrando…' : 'Entrar'")
    assert 'x-text="submitting ? &#x27;Entrando…&#x27; : &#x27;Entrar&#x27;"' in html
    assert '>Entrar</span>' in html


def test_label_bind_ausente_por_padrao():
    html = _render()
    assert 'x-text' not in html


def test_spinner_show_renderiza_spinner_com_x_show_antes_do_label():
    html = _render(spinner_show='enviando')
    assert 'x-show="enviando"' in html
    spinner_idx = html.index('x-show="enviando"')
    label_idx = html.index('Rótulo')
    assert spinner_idx < label_idx


def test_spinner_show_esconde_icon_template_com_x_show_negado():
    html = render_to_string(
        'components/button.html',
        {
            'label': 'Confirmar importação',
            'icon_template': 'components/icons/confirmar_check.svg',
            'spinner_show': 'confirmando',
        },
    )
    assert 'x-show="!(confirmando)"' in html


def test_spinner_show_ausente_por_padrao_nao_renderiza_spinner():
    html = _render()
    assert 'x-show' not in html


def test_href_setado_nao_renderiza_nenhum_param_dinamico_de_button():
    html = _render(
        href='/destino/',
        loading_label='Enviando...',
        label_mobile='Enviar',
        x_disabled='enviando',
        x_aria_busy='enviando',
        spinner_show='enviando',
        label_bind="'x'",
    )
    for trecho in (
        'data-submit-loading-label',
        'data-submit-text',
        ':disabled',
        ':aria-busy',
        'x-show',
        'x-text',
    ):
        assert trecho not in html


def test_nenhum_template_usa_comentario_de_linha_em_varias_linhas():
    """`{# #}` é comentário de UMA linha; multi-linha vaza como texto na tela.

    Django não fecha `{# ... #}` que atravessa quebra de linha — o conteúdo é
    renderizado como conteúdo, visível para o usuário, e nenhum teste de
    presença de marcação pega isso porque o HTML continua válido. Comentário de
    mais de uma linha usa `{% comment %}`.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[3]
    infratores: list[str] = []
    for caminho in (raiz / 'apps').rglob('*.html'):
        dentro = False
        for numero, linha in enumerate(caminho.read_text().splitlines(), 1):
            if dentro:
                if '#}' in linha:
                    dentro = False
                continue
            inicio = linha.find('{#')
            if inicio != -1 and '#}' not in linha[inicio:]:
                infratores.append(f'{caminho.relative_to(raiz)}:{numero}')
                dentro = True

    assert not infratores, (
        'Comentário {# #} atravessando linhas (vaza como texto renderizado); '
        f'use {{% comment %}}: {infratores}'
    )


def test_nenhum_template_escreve_campo_na_mao():
    """Campo tem uma definição só: `.campo`, em input.css.

    A string do campo já viveu copiada 19 vezes nos forms.py dos apps e nos
    componentes de filtro, e divergiu em silêncio — dois campos ficaram sem o
    piso de 44px e três com raio de controle em vez de raio de campo. Nada
    quebrava quando isso acontecia, que é exatamente por que aconteceu.

    O que trava aqui é a assinatura da borda de campo escrita à mão. Regra sem
    mecanismo vira sugestão.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[3]
    assinaturas = (
        'border border-border-strong px-3 py-2',
        'border border-border-control px-3 py-2',
    )
    infratores: list[str] = []
    for caminho in (raiz / 'apps').rglob('*.html'):
        for numero, linha in enumerate(caminho.read_text().splitlines(), 1):
            if any(assinatura in linha for assinatura in assinaturas):
                infratores.append(f'{caminho.relative_to(raiz)}:{numero}')

    assert not infratores, (
        'Campo escrito à mão; use class="campo" (definido em '
        f'apps/core/static/core/css/input.css): {infratores}'
    )


def test_nenhum_controle_abaixo_do_piso_de_44px():
    """`min-h-9`/`min-h-10` em controle clicável.

    Não são omissões: são alguém escolhendo conscientemente um número menor que
    o piso de `--size-touch-target`. A mesma tela é operada com o dedo, em pé no
    galpão, e com teclado no escritório.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[3]
    infratores: list[str] = []
    for caminho in (raiz / 'apps').rglob('*.html'):
        for numero, linha in enumerate(caminho.read_text().splitlines(), 1):
            if 'min-h-9' in linha or 'min-h-10' in linha:
                infratores.append(f'{caminho.relative_to(raiz)}:{numero}')

    assert not infratores, (
        f'Controle abaixo do piso de 44px; use min-h-11: {infratores}'
    )


class TestPaginationHref:
    """A paginação já navegou para lugar nenhum sem quebrar um teste.

    `add` é numérico primeiro: `add('?page=', 2)` tenta `int('?page=')`, falha,
    tenta `str + int`, falha de novo, e devolve string vazia em silêncio. Com
    href vazio, `button.html` cai no ramo <button> e os controles de página
    param de navegar — sem erro, sem log, sem teste vermelho.
    """

    def _render(self, numero_pagina, **ctx):
        from django.core.paginator import Paginator
        from django.template.loader import render_to_string

        paginator = Paginator(list(range(30)), 10)
        return render_to_string(
            'components/pagination.html',
            {
                'page_obj': paginator.page(numero_pagina),
                'rotulo_itens': 'itens',
                **ctx,
            },
        )

    def _hrefs(self, html):
        return re.findall(r'href="([^"]*)"', html)

    def test_href_carrega_o_numero_da_pagina(self):
        hrefs = self._hrefs(self._render(2))
        assert hrefs == ['?page=1', '?page=3']

    def test_href_preserva_filtros_ativos(self):
        html = self._render(2, querystring_filtros='texto=a+b&setor=1')
        hrefs = self._hrefs(html)
        assert len(hrefs) == 2
        for href in hrefs:
            assert 'texto=a+b' in href
            assert 'setor=1' in href

    def test_ampersand_dos_filtros_nao_e_escapado_duas_vezes(self):
        """`&amp;amp;` faz o navegador ler um parâmetro chamado `amp;setor`.

        Ou seja: paginar perderia exatamente os filtros que o param existe para
        preservar. O escape duplo não quebra nada visível — o link continua
        clicável e a página continua carregando, só que sem filtro.
        """
        import html as html_lib
        from urllib.parse import parse_qs, urlparse

        html = self._render(2, querystring_filtros='texto=a+b&setor=1')
        assert '&amp;amp;' not in html

        for href in self._hrefs(html):
            params = parse_qs(urlparse(html_lib.unescape(href)).query)
            assert set(params) == {'texto', 'setor', 'page'}
            assert params['texto'] == ['a b']
            assert params['setor'] == ['1']

    def test_sem_filtros_nao_deixa_e_comercial_solto(self):
        assert self._hrefs(self._render(2)) == ['?page=1', '?page=3']

    def test_extremos_desabilitam_em_vez_de_gerar_href_vazio(self):
        primeira = self._render(1)
        ultima = self._render(3)
        assert self._hrefs(primeira) == ['?page=2']
        assert self._hrefs(ultima) == ['?page=2']
        assert 'href=""' not in primeira
        assert 'href=""' not in ultima


def test_todo_icon_template_de_button_honra_a_classe():
    """`button.html` dimensiona o ícone por `class`, a tag {% icon %} por `size`.

    O catálogo tem as duas convenções convivendo: 10 dos 11 `.svg` usam
    `class="{{ class }}"`, e `voltar.svg` usa `width="{{ size }}"`. Passar um
    ícone de `size` para `icon_template` renderiza `width=""` — o ícone estoura
    o botão, e nada quebra: sem erro, sem log, sem teste vermelho.
    """
    import re
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[3]
    usados = set()
    for caminho in (raiz / 'apps').rglob('*.html'):
        usados.update(re.findall(r'icon_template="([^"]+)"', caminho.read_text()))

    incompativeis = []
    for relativo in sorted(usados):
        arquivo = raiz / 'apps/core/templates' / relativo
        if not arquivo.exists():
            incompativeis.append(f'{relativo} (arquivo não existe)')
        elif '{{ class' not in arquivo.read_text():
            incompativeis.append(f'{relativo} (não usa {{{{ class }}}})')

    assert not incompativeis, (
        f'icon_template precisa de um SVG que dimensione por class: {incompativeis}'
    )
