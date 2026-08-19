"""Testes diretos de components/button.html (sem DB, sem view)."""

import re
from collections.abc import Mapping
from pathlib import Path

import pytest
from django.template.loader import render_to_string

from apps.core.templatetags.core_tags import _VARIANTES_BOTAO
from apps.core.tests.marcacao import TAGS_DJANGO, atributo, classes, elementos


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


def test_href_setado_nao_renderiza_nenhum_param_dinamico_de_button():
    html = _render(
        href='/destino/',
        loading_label='Enviando...',
        label_mobile='Enviar',
    )
    for trecho in (
        'data-submit-loading-label',
        'data-submit-text',
    ):
        assert trecho not in html


def test_nenhum_template_usa_comentario_de_linha_em_varias_linhas():
    """`{# #}` é comentário de UMA linha; multi-linha vaza como texto na tela.

    Django não fecha `{# ... #}` que atravessa quebra de linha — o conteúdo é
    renderizado como conteúdo, visível para o usuário, e nenhum teste de
    presença de marcação pega isso porque o HTML continua válido. Comentário de
    mais de uma linha usa `{% comment %}`.
    """

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


# Bordas que *identificam* um controle. `border-border` fica de fora: é borda
# estrutural de papel, e o dropdown de autocomplete a usa legitimamente.
_BORDAS_DE_CONTROLE = (
    'border-border-strong',
    'border-border-control',
    'border-danger-border-input',
)

# `.campo` é a definição de campo de texto. Checkbox e radio seguem `size-5`
# dentro de uma label de 44px, e upload é outro controle — nenhum dos três
# passa por `.campo`, então não são infração.
_TIPOS_DE_TEXTO = frozenset(
    {
        '',
        'text',
        'search',
        'number',
        'email',
        'password',
        'tel',
        'url',
        'date',
        'datetime-local',
        'month',
        'week',
        'time',
    }
)


def _controles_de_texto(texto: str):
    """Devolve (tag, atributos, linha) de cada input/select/textarea de texto.

    A varredura respeita aspas (ver apps/core/tests/marcacao.py): um atributo
    pode conter `>` — o `@keydown.enter="if (ativo >= 0)"` de autocomplete.html
    contém —, e um `<[^>]*>` ingênuo truncaria o elemento no meio, justamente
    antes do `class`.
    """
    yield from elementos(texto, 'input', 'select', 'textarea')


def test_nenhum_template_escreve_campo_na_mao():
    """Campo tem uma definição só: `.campo`, em input.css.

    A string do campo já viveu copiada 19 vezes nos forms.py dos apps e nos
    componentes de filtro, e divergiu em silêncio — dois campos ficaram sem o
    piso de 44px e três com raio de controle em vez de raio de campo. Nada
    quebrava quando isso acontecia, que é exatamente por que aconteceu.

    A versão anterior deste teste procurava a assinatura contígua
    `border border-border-strong px-3 py-2`, e por isso era cega para o único
    infrator que existia: o input de autocomplete escrevia
    `border {% if com_erro %}...{% else %}border-border-strong{% endif %} px-3`,
    e a tag no meio quebrava a string. A regra tinha mecanismo e o mecanismo não
    alcançava o infrator — que ficou a 1.48:1 de contraste de borda, contra os
    3:1 da WCAG 1.4.11, pelo tempo em que ninguém olhou.

    Agora a varredura é por elemento, com as tags de template removidas antes da
    comparação, para que uma classe condicional não sirva de esconderijo.
    """

    raiz = Path(__file__).resolve().parents[3]
    infratores: list[str] = []
    for caminho in (raiz / 'apps').rglob('*.html'):
        texto = caminho.read_text()
        for tag, atributos, numero in _controles_de_texto(texto):
            limpo = TAGS_DJANGO.sub(' ', atributos)
            if 'class=' not in limpo or 'campo' in limpo:
                continue
            if tag == 'input':
                tipo = re.search(r'type="([^"]*)"', limpo)
                if (
                    tipo.group(1).strip().lower() if tipo else ''
                ) not in _TIPOS_DE_TEXTO:
                    continue
            escreveu_borda = any(b in limpo for b in _BORDAS_DE_CONTROLE)
            if escreveu_borda or 'px-3 py-2' in limpo:
                infratores.append(f'{caminho.relative_to(raiz)}:{numero}')

    assert not infratores, (
        'Campo escrito à mão; use class="campo" (definido em '
        f'apps/core/static/core/css/input.css): {infratores}'
    )


_INPUT_CSS = 'apps/core/static/core/css/input.css'

_COMENTARIO_CSS = re.compile(r'/\*.*?\*/', re.S)
# Os blocos são casados de dentro para fora: `[^{}]*` nunca atravessa uma chave,
# então uma regra dentro de `@media` sai com o at-rule grudado no seletor. Não
# atrapalha — o que se extrai do seletor é nome de classe, e `@media` não tem.
_BLOCO_CSS = re.compile(r'([^{}]*)\{([^{}]*)\}', re.S)
_ALTURA_DE_PISO = re.compile(r'(?<![-\w])(?:min-)?height:\s*var\(--size-touch-target\)')
# Nome de classe começa por letra, `_` ou `-`. Sem essa âncora, o `.5rem` de um
# `padding: 0.5rem` viraria uma classe chamada `5rem`.
_NOME_DE_CLASSE_CSS = re.compile(r'\.(-?[A-Za-z_][\w-]*)')

_COMENTARIO_DJANGO = re.compile(r'\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}', re.S)
_CONDICIONAL_DJANGO = re.compile(r'\{%\s*if\b.*?\{%\s*endif\s*%\}', re.S)
# O projeto escreve `{% include %}` com as duas aspas — `fila_atendimento.html`
# usa simples, `notificacoes/lista.html` usa duplas —, e a mesma liberdade vale
# para o valor de `variant`. Um guarda que só entende aspas duplas seria
# contornável por uma escolha de estilo, que é a definição de guarda decorativo.
# A aspa é capturada e conferida por retrovisor (`\1`), para que `"...'` não
# passe por par.
_INCLUDE_DE_BOTAO = re.compile(
    r'\{%\s*include\s+([\'"])components/button\.html\1(.*?)%\}', re.S
)
_VARIANTE_LINK = re.compile(r'variant=([\'"])link\1')

# Único arquivo em que a classe pode sair de `{% classes_botao %}`: é lá que
# `variant` é variável de runtime. Fora dele, chamar a tag à mão seria uma rota
# de fuga do piso — e o design system já diz que toda ação passa pelo componente.
_TEMPLATE_DE_BOTAO = 'apps/core/templates/components/button.html'

# Piso confirmado por varredura, para que o guarda não possa passar por não ter
# achado nada. Hoje são 30; o número é folgado de propósito, porque o custo de
# um falso vermelho aqui é alto e o de um teto baixo é zero.
_MINIMO_DE_CLICAVEIS_VARRIDOS = 25

# Exceção declarada em docs/design-system.md: a variante `link` de button.html é
# texto inline no meio de prosa, e uma caixa de 44px quebraria a linha (WCAG
# 2.5.8 isenta link em sentença).
#
# Nasce vazia de propósito. Não existe uso inline ainda, e exceção pré-aprovada
# para caso que não existe é a folga que vira esconderijo — foi assim que os dois
# controles de recuperação ficaram sem piso sem quebrar teste nenhum. O primeiro
# link inline de verdade entra aqui junto com a frase que o justifica.
#
# O mecanismo de exceção é exercitado por fixture sintética
# (`test_excecao_de_prosa_inline_isenta_o_ponto_de_chamada`), nunca por uma
# entrada real posta aqui só para ter teste.
EXCECOES_DE_PROSA_INLINE: dict[str, str] = {}


def _classes_com_piso_no_css(raiz: Path) -> frozenset[str]:
    """Classes cujo bloco em input.css declara altura de `--size-touch-target`.

    Derivada do CSS a cada execução, e não escrita à mão, porque uma lista fixa
    só conheceria o que existia no dia em que foi escrita — que é exatamente o
    defeito que este guarda existe para não repetir.
    """
    css = _COMENTARIO_CSS.sub(' ', (raiz / _INPUT_CSS).read_text())
    nomes: set[str] = set()
    for seletor, corpo in _BLOCO_CSS.findall(css):
        if _ALTURA_DE_PISO.search(corpo):
            nomes.update(_NOME_DE_CLASSE_CSS.findall(seletor))
    return frozenset(nomes)


def _classes_garantidas(atributos: str) -> set[str]:
    """Classes que valem em *qualquer* ramo do template.

    Difere de `classes()` de propósito. Aquele helper troca a tag Django por
    espaço e mantém o texto de dentro, porque os guardas dele perguntam "esta
    string aparece em algum ramo?". Aqui a pergunta é o contrário: piso que só
    existe quando a condição é verdadeira não é piso — do outro lado do `{% if %}`
    o alvo volta a ter 21px, e nenhuma varredura por presença notaria.
    """
    valor = atributo(atributos, 'class') or ''
    return set(TAGS_DJANGO.sub(' ', _CONDICIONAL_DJANGO.sub(' ', valor)).split())


def _sem_comentarios(texto: str) -> str:
    """Remove blocos `{% comment %}` preservando a numeração de linha.

    Markup dentro de comentário não é markup: os blocos de documentação de
    button.html, modal.html e pagination.html trazem exemplos de uso com
    `<button ...>` e `<a ...>` que nunca renderizam. Sem removê-los o guarda
    acusaria quatro falsos positivos, e a correção óbvia seria afrouxá-lo.
    """
    return _COMENTARIO_DJANGO.sub(lambda m: '\n' * m.group(0).count('\n'), texto)


def _clicaveis_sem_piso(
    caminho: str,
    texto: str,
    piso_css: frozenset[str],
    excecoes: Mapping[str, str],
) -> tuple[list[str], int]:
    """Infratores e total de clicáveis de um template.

    Um clicável tem piso comprovável de quatro formas:

    1. `min-h-11` literal na própria lista de classes, fora de `{% if %}`;
    2. uma classe cujo bloco em input.css declara `--size-touch-target`;
    3. classe vinda de `{% classes_botao %}` **dentro de components/button.html**
       — é lá que `variant` é variável de runtime e nenhuma varredura de markup
       pode saber o que o chamador vai pedir. A isenção é por arquivo, e não por
       aparecer a tag: escrita à mão em outro template, ela viraria rota de fuga
       do piso;
    4. para quem *inclui* button.html com `variant="link"` (em aspas simples ou
       duplas): `min-h-11` no `class`, salvo ponto de chamada em `excecoes`.

    A forma 3 tira button.html da varredura; não dá quitação a quem o inclui. É
    a segunda metade da regra do design system — "`link` usado como ação isolada
    recebe `class="min-h-11"` explícito" — e apagá-la abriria, no mecanismo
    novo, um buraco do mesmo formato do que ele fecha.
    """
    limpo = _sem_comentarios(texto)
    infratores: list[str] = []
    quantidade = 0

    for _, atributos, numero in elementos(limpo, 'a', 'button'):
        quantidade += 1
        if caminho == _TEMPLATE_DE_BOTAO and 'classes_botao' in (
            atributo(atributos, 'class') or ''
        ):
            continue
        nomes = _classes_garantidas(atributos)
        if 'min-h-11' in nomes or nomes & piso_css:
            continue
        infratores.append(f'{caminho}:{numero} clicável sem piso de 44px')

    for encontro in _INCLUDE_DE_BOTAO.finditer(limpo):
        argumentos = encontro.group(2)
        if not _VARIANTE_LINK.search(argumentos) or 'min-h-11' in argumentos:
            continue
        if caminho in excecoes:
            continue
        numero = limpo.count('\n', 0, encontro.start()) + 1
        infratores.append(
            f'{caminho}:{numero} variant="link" como ação isolada, sem min-h-11'
        )

    return infratores, quantidade


def test_nenhum_controle_abaixo_do_piso_de_44px():
    """Todo clicável de apps/**/*.html tem piso de 44px comprovável.

    A versão anterior deste guarda procurava os literais `min-h-9`/`min-h-10`
    linha a linha. Ela pega quem escolheu conscientemente um número menor que
    `--size-touch-target` e é **cega para quem não escreveu piso nenhum** — que
    era o caso das âncoras de error_summary.html e do CTA secundário de
    empty_state.html, os dois exatamente na superfície de recuperação de erro,
    os dois passando em silêncio.

    As duas varreduras convivem porque cobrem coisas diferentes: a por linha
    alcança o número menor escrito em qualquer elemento, inclusive nos que não
    são `<a>` nem `<button>`; a por elemento alcança a ausência.

    A mesma tela é operada com o dedo, em pé no galpão, e com teclado no
    escritório.
    """
    raiz = Path(__file__).resolve().parents[3]
    piso_css = _classes_com_piso_no_css(raiz)
    infratores: list[str] = []
    clicaveis = 0

    for caminho in sorted((raiz / 'apps').rglob('*.html')):
        relativo = str(caminho.relative_to(raiz))
        texto = caminho.read_text()
        for numero, linha in enumerate(texto.splitlines(), 1):
            if 'min-h-9' in linha or 'min-h-10' in linha:
                infratores.append(f'{relativo}:{numero} número menor que o piso')
        achados, quantidade = _clicaveis_sem_piso(
            relativo, texto, piso_css, EXCECOES_DE_PROSA_INLINE
        )
        infratores.extend(achados)
        clicaveis += quantidade

    assert clicaveis >= _MINIMO_DE_CLICAVEIS_VARRIDOS, (
        f'A varredura achou só {clicaveis} clicáveis em apps/**/*.html — o '
        'guarda está passando por não enxergar, não por estar tudo certo'
    )
    assert not infratores, (
        f'Controle abaixo do piso de 44px; use min-h-11: {infratores}'
    )


class TestMecanismoDoPisoDe44px:
    """O guarda precisa provar que *detecta*, não que hoje não há infrator.

    Um guarda exercitado só pela árvore real é indistinguível de um guarda
    quebrado enquanto a árvore estiver limpa — e foi assim que a versão anterior
    passou verde por cima de dois controles sem piso. Cada forma de prova e cada
    cegueira conhecida tem aqui um caso sintético que deve falhar (ou passar) por
    conta própria.
    """

    PISO_CSS = frozenset({'skip-link'})

    def _infratores(self, texto, excecoes=None, caminho='sintetico.html'):
        achados, _ = _clicaveis_sem_piso(caminho, texto, self.PISO_CSS, excecoes or {})
        return achados

    def _quantidade(self, texto):
        _, quantidade = _clicaveis_sem_piso('sintetico.html', texto, self.PISO_CSS, {})
        return quantidade

    def test_ausencia_de_piso_e_detectada(self):
        """O caso que a versão anterior não via: nenhum piso escrito."""
        assert self._infratores('<a href="#x" class="underline">Erro</a>')

    def test_min_h_11_literal_passa(self):
        assert not self._infratores('<a href="#x" class="min-h-11">Erro</a>')

    def test_a_seguido_de_newline_e_detectado(self):
        """`<(a|button)[ >]` não casaria — e os dois infratores eram assim.

        As âncoras de error_summary.html e o CTA de empty_state.html quebram
        linha logo depois do nome da tag. Um guarda cego para essa grafia
        nasceria sem enxergar exatamente o que veio corrigir.
        """
        texto = '<a\n  href="#x"\n  class="underline"\n>Erro</a>'
        assert self._infratores(texto)

    def test_classe_condicional_nao_serve_de_esconderijo(self):
        """`min-h-11` dentro de `{% if %}` não conta como piso escrito."""
        texto = '<a href="#x" class="{% if x %}min-h-11{% endif %}">Erro</a>'
        assert self._infratores(texto)

    def test_piso_vindo_do_css_dispensa_min_h_11(self):
        assert not self._infratores('<a href="#x" class="skip-link">Pular</a>')

    def test_markup_dentro_de_comment_nao_e_markup(self):
        texto = '{% comment %}\n<a href="#x" class="underline">Exemplo</a>\n{% endcomment %}'
        assert not self._infratores(texto)
        assert self._quantidade(texto) == 0

    def test_comment_removido_preserva_a_numeracao_de_linha(self):
        texto = '{% comment %}\nexemplo\n{% endcomment %}\n<a href="#x" class="u">E</a>'
        assert self._infratores(texto) == ['sintetico.html:4 clicável sem piso de 44px']

    def test_classes_botao_delega_o_piso_ao_componente(self):
        """Em button.html `variant` é runtime; nenhuma varredura o resolve."""
        texto = '<a href="#x" class="{% classes_botao variant=variant %}">Ir</a>'
        assert not self._infratores(texto, caminho=_TEMPLATE_DE_BOTAO)

    def test_classes_botao_fora_de_button_html_nao_delega_nada(self):
        """A isenção é do arquivo, não da tag.

        Chamar `{% classes_botao %}` à mão numa tela seria rota de fuga do piso
        — e o design system já manda toda ação passar pelo componente.
        """
        texto = '<a href="#x" class="{% classes_botao variant=variant %}">Ir</a>'
        assert self._infratores(texto, caminho='requisicoes/tela.html')

    def test_include_de_variant_link_sem_min_h_11_e_detectado(self):
        """Delegar a classe ao componente não quita o chamador.

        `_FORMA_LINK` é a única forma sem piso, e o design system a isenta só
        para texto inline em prosa. Ação isolada com `variant="link"` carrega
        `class="min-h-11"` explícito.
        """
        texto = '{% include "components/button.html" with variant="link" label="Ir" %}'
        assert self._infratores(texto)

    def test_include_de_variant_link_com_min_h_11_passa(self):
        texto = (
            '{% include "components/button.html" with variant="link" '
            'label="Ir" class="min-h-11" %}'
        )
        assert not self._infratores(texto)

    def test_include_de_variant_link_com_aspas_simples_e_detectado(self):
        """Aspas simples são o estilo majoritário de include neste projeto.

        Um guarda que só entende aspas duplas é contornável por escolha de
        estilo — e um guarda contornável não é mecanismo, é sugestão.
        """
        texto = "{% include 'components/button.html' with variant='link' label='Ir' %}"
        assert self._infratores(texto)

    def test_include_com_aspas_desbalanceadas_nao_casa(self):
        """`"...'` não é par de aspas; o retrovisor `\\1` é o que garante isso."""
        texto = '{% include "components/button.html\' with variant="link" %}'
        assert not self._infratores(texto)

    def test_include_de_outra_variante_nao_exige_min_h_11_do_chamador(self):
        """`primary` já vem com piso de `_FORMA_BOTAO` — cobrar de novo seria ruído."""
        texto = (
            '{% include "components/button.html" with variant="primary" label="Ir" %}'
        )
        assert not self._infratores(texto)

    def test_excecao_de_prosa_inline_isenta_o_ponto_de_chamada(self):
        """Fixture sintética: o mecanismo existe antes de haver caso real.

        A lista real (`EXCECOES_DE_PROSA_INLINE`) continua vazia — ver o teste
        seguinte. Pôr uma entrada nela só para ter teste transformaria a exceção
        num desvio permanente da regra.
        """
        texto = '{% include "components/button.html" with variant="link" label="Ir" %}'
        excecoes = {'sintetico.html': 'link inline no meio de uma frase'}
        assert not self._infratores(texto, excecoes)

    def test_lista_real_de_excecoes_de_prosa_inline_esta_vazia(self):
        """Enquanto não houver link inline de verdade, ela não ganha entrada."""
        assert EXCECOES_DE_PROSA_INLINE == {}

    def test_classes_com_piso_saem_do_css_e_nao_de_lista_escrita_a_mao(self):
        raiz = Path(__file__).resolve().parents[3]
        derivadas = _classes_com_piso_no_css(raiz)

        assert {'campo', 'skip-link', 'app-bar__menu-item'} <= derivadas
        assert not any(nome[0].isdigit() for nome in derivadas), (
            f'`.5rem` de um padding virou nome de classe: {sorted(derivadas)}'
        )


class TestPisoDosControlesDeRecuperacao:
    """error_summary e empty_state: a superfície onde o usuário já falhou uma vez.

    São os dois controles que a issue #120 encontrou sem piso — e os dois estão
    justamente na recuperação de erro e na saída de estado vazio, operados com
    luva, no galpão, depois de a tela já ter dito não.
    """

    def _ancora_de_erro(self):
        html = render_to_string(
            'components/error_summary.html',
            {
                'erros': [
                    {'id': 'id_setor', 'rotulo': 'Setor', 'mensagem': 'Obrigatório.'}
                ]
            },
        )
        ((_, atributos, _),) = elementos(html, 'a')
        return classes(atributos)

    def _cta_secundario(self):
        html = render_to_string(
            'components/empty_state.html',
            {
                'titulo': 'Nenhum material',
                'cta_url': '/estoque/materiais/',
                'cta_label': 'Limpar busca',
                'cta_secundario': True,
            },
        )
        ((_, atributos, _),) = elementos(html, 'a')
        return classes(atributos)

    def test_ancora_de_erro_tem_alvo_de_44px(self):
        """`block` porque `min-height` não tem efeito em elemento inline.

        Num sumário de 4 erros, no celular, um alvo de ~21px leva o solicitante
        ao campo errado — no exato momento em que ele já errou uma vez.
        """
        assert {'block', 'min-h-11', 'py-2.5'} <= self._ancora_de_erro()

    def test_cta_secundario_tem_alvo_de_44px(self):
        """Única saída do estado vazio de busca de material."""
        assert {'inline-flex', 'items-center', 'min-h-11'} <= self._cta_secundario()

    def test_cta_secundario_nao_ganha_folga_horizontal(self):
        """A regra é de altura. `px-*` alargaria o alvo sem que nada peça."""
        assert not {c for c in self._cta_secundario() if c.startswith('px-')}

    @pytest.mark.parametrize(
        'template',
        (
            'components/error_summary.html',
            'components/empty_state.html',
        ),
    )
    def test_nenhum_raio_fora_da_escala(self, template):
        """`rounded` pelado é 0.25rem — degrau abaixo do menor da escala.

        A escala é controle 0.375 → campo 0.5 → papel 0.75 → modal 1rem → pill.
        Um raio intermediário inventado quebra a leitura de hierarquia por
        geometria.
        """
        raiz = Path(__file__).resolve().parents[3]
        texto = (raiz / 'apps/core/templates' / template).read_text()
        for _, atributos, numero in elementos(texto, 'a', 'button', 'div', 'ul', 'li'):
            assert 'rounded' not in classes(atributos), (
                f'{template}:{numero} usa `rounded` pelado; use a escala'
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


def test_disabled_com_motivo_usa_aria_disabled_e_continua_focavel():
    """Botão `disabled` nativo sai da ordem de tabulação — e leva o motivo junto.

    O design system manda a ação de workflow bloqueada permanecer visível com o
    motivo em texto, amarrado por `aria-describedby`. Com `disabled` nativo, quem
    navega por Tab nunca chega ao botão e nunca ouve o motivo: o padrão só
    funcionava para quem lê a tela com os olhos.
    """
    html = _render(label='Estornar', disabled=True, aria_describedby='motivo-bloqueio')
    abertura = html[: html.index('>') + 1]
    assert 'aria-disabled="true"' in abertura
    assert 'aria-describedby="motivo-bloqueio"' in abertura
    assert not re.search(r'(?<![-:])\bdisabled\b(?![:=])', abertura)


def test_disabled_sem_motivo_continua_disabled_nativo():
    """Sem motivo declarado não há o que alcançar pelo foco.

    É o caso da paginação: "Anterior" na primeira página não tem explicação a
    dar, e um controle focável que não faz nada seria só ruído no Tab.
    """
    html = _render(label='Anterior', disabled=True)
    abertura = html[: html.index('>') + 1]
    assert re.search(r'(?<![-:])\bdisabled\b(?![:=])', abertura)
    # Atributo, não substring: as classes `aria-disabled:*` estão sempre no
    # `class`, porque a variante é estática e só o atributo é condicional.
    assert 'aria-disabled="true"' not in abertura


def test_aria_disabled_tem_tratamento_visual_de_desabilitado():
    """`aria-disabled` não herda o estilo de `:disabled` — precisa da variante."""
    html = _render(label='Estornar', disabled=True, aria_describedby='motivo-bloqueio')
    assert 'aria-disabled:opacity-60' in html
    assert 'aria-disabled:cursor-not-allowed' in html


def test_mecanismo_de_campo_enxerga_classe_condicional():
    """Teste do teste: a varredura acima não pode voltar a ser cega.

    O infrator real não era um campo escrito numa string limpa — era um campo
    cuja borda vinha de `{% if %}`. Se alguém trocar a varredura por busca de
    substring contígua de novo, isto quebra antes de o furo voltar a existir.
    """
    marcacao = (
        '<input\n'
        '  type="search"\n'
        '  @keydown.enter="if (ativo >= 0) { confirmar(); }"\n'
        '  class="w-full min-h-11 rounded-lg border '
        '{% if com_erro %}border-danger-border-input'
        '{% else %}border-border-strong{% endif %} px-3 py-2 text-sm"\n'
        '>'
    )
    controles = list(_controles_de_texto(marcacao))
    assert len(controles) == 1, 'o `>` dentro do atributo truncou o elemento'

    _, atributos, _ = controles[0]
    limpo = TAGS_DJANGO.sub(' ', atributos)
    assert 'campo' not in limpo
    assert any(borda in limpo for borda in _BORDAS_DE_CONTROLE)


def test_nenhum_rotulo_de_campo_escrito_a_mao():
    """Rótulo de campo tem uma definição só: `.rotulo-campo`, em input.css.

    Ela carrega também o espaço até o campo — que antes vivia em quatro lugares
    e três valores: `mb-1` na label, `mt-1` no campo (família filter_*), `mt-2`
    na classe do widget em accounts/forms.py, e coisa nenhuma nos quatro
    chamadores de form_field.html que aceitavam o `label_class` padrão, onde o
    rótulo encostava no campo.

    Só `<label>` é varrido: a mesma tipografia é usada legitimamente em `<dt>`
    de lista de dados, que é termo de definição e não rótulo de controle.
    """

    raiz = Path(__file__).resolve().parents[3]
    tipografia_de_rotulo = {'text-xs', 'font-medium', 'uppercase'}
    infratores: list[str] = []
    for caminho in (raiz / 'apps').rglob('*.html'):
        texto = caminho.read_text()
        for _, atributos, numero in elementos(texto, 'label'):
            if tipografia_de_rotulo <= classes(atributos):
                infratores.append(f'{caminho.relative_to(raiz)}:{numero}')

    assert not infratores, (
        'Rótulo de campo escrito à mão; use class="rotulo-campo" (definido em '
        f'apps/core/static/core/css/input.css): {infratores}'
    )


def test_nenhum_widget_carrega_margem_de_rotulo():
    """A régua entre rótulo e campo não pertence ao Python.

    `accounts/forms.py` compensava a falta de margem da label escrevendo
    `campo mt-2` na classe do widget — espaçamento de layout decidido na camada
    que valida, e divergente dos 4px que o resto do sistema usava.
    """

    raiz = Path(__file__).resolve().parents[3]
    # A chave e o valor aceitam qualquer uma das duas aspas, e o valor pode
    # atravessar linhas — a varredura procura o literal, não uma grafia dele.
    padrao = re.compile(r'["\']class["\']\s*:\s*(["\'])(?P<valor>.*?)\1', re.S)
    margem = re.compile(r'\b(mt|mb)-\d')
    infratores: list[str] = []
    for caminho in (raiz / 'apps').rglob('forms.py'):
        texto = caminho.read_text()
        for encontro in padrao.finditer(texto):
            if margem.search(encontro.group('valor')):
                numero = texto.count('\n', 0, encontro.start()) + 1
                infratores.append(f'{caminho.relative_to(raiz)}:{numero}')

    assert not infratores, (
        'Margem vertical na classe do widget; o espaço entre rótulo e campo vem '
        f'de `.rotulo-campo`: {infratores}'
    )


def _classes(**ctx):
    marcacao = _render(**ctx)
    return set(marcacao.split('class="')[1].split('"')[0].split())


def test_ramos_a_e_button_compartilham_a_mesma_classe_de_variante():
    """A expressão de classe vivia duplicada entre os dois ramos, e já divergira.

    `cursor-pointer` e os estados `disabled:` existiam só no ramo `<button>`, e
    nada comparava as duas cópias — variante nova precisava ser escrita em dois
    lugares para não sair torta em um deles. Agora as duas saem de
    `{% classes_botao %}`, e a única diferença legítima é o que um link não tem:
    estado desabilitado e cursor de ponteiro.
    """
    so_do_botao = {
        'cursor-pointer',
        'disabled:cursor-not-allowed',
        'disabled:opacity-60',
        'aria-disabled:cursor-not-allowed',
        'aria-disabled:opacity-60',
    }
    for variante in _VARIANTES_BOTAO:
        link = _classes(variant=variante, href='/x/')
        botao = _classes(variant=variante)
        assert botao - link == so_do_botao, f'variante {variante}: {botao - link}'
        assert not link - botao, (
            f'variante {variante}: link tem classe que o botão não tem'
        )


def test_params_dinamicos_removidos_nao_voltam_por_engano():
    """O vocabulário Alpine de loading foi removido por não ter consumidor.

    Se alguém reintroduzir um deles no corpo do template sem uma tela que
    precise, isto quebra — a alternativa é ele voltar a ser documentado, testado
    e não usado, que foi exatamente como ele viveu até aqui.
    """

    raiz = Path(__file__).resolve().parents[3]
    marcacao = (raiz / 'apps/core/templates/components/button.html').read_text()
    corpo = marcacao[marcacao.index('{% endcomment %}') :]
    for param in ('spinner_show', 'label_bind', 'x_disabled', 'x_aria_busy'):
        assert param not in corpo, f'`{param}` voltou ao corpo de button.html'


class TestMessagesDismiss:
    """O contrato de dismiss de docs/CONVENTIONS.md, §Níveis e ARIA.

    O contrato foi decidido, documentado e nunca implementado — e dois
    documentos passaram a afirmar que existia. Estes testes são o mecanismo que
    faltava: `docs/design-system.md` avisa que regra sem mecanismo vira sugestão,
    e neste conjunto de arquivos isso já aconteceu três vezes.
    """

    NIVEIS = ('error', 'warning', 'success', 'info')

    def _render(self, *niveis, texto=None):
        from django.contrib import messages as django_messages
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        request = RequestFactory().get('/')
        request.session = {}
        request._messages = FallbackStorage(request)
        for indice, nivel in enumerate(niveis):
            getattr(django_messages, nivel)(
                request, texto or f'Mensagem {nivel} {indice}'
            )
        return render_to_string('core/partials/_messages.html', request=request)

    def _itens(self, html):
        """Elementos que carregam `x-data` — um por mensagem renderizada."""
        return [
            (attrs, linha)
            for _, attrs, linha in elementos(html, 'div')
            if atributo(attrs, 'x-data')
        ]

    @pytest.mark.parametrize('nivel', NIVEIS)
    def test_botao_de_fechar_presente_no_nivel(self, nivel):
        html = self._render(nivel)
        rotulos = [
            atributo(attrs, 'aria-label') for _, attrs, _ in elementos(html, 'button')
        ]
        assert rotulos == ['Fechar mensagem']

    @pytest.mark.parametrize('nivel', NIVEIS)
    def test_botao_de_fechar_respeita_o_piso_de_44px(self, nivel):
        html = self._render(nivel)
        (attrs,) = [attrs for _, attrs, _ in elementos(html, 'button')]
        assert {'min-h-11', 'min-w-11'} <= classes(attrs)

    @pytest.mark.parametrize('nivel', NIVEIS)
    def test_dismiss_e_um_button_nativo(self, nivel):
        """`<div @click>` não é focável nem responde a Enter/Espaço.

        O critério "dispensável só pelo teclado" é satisfeito pela escolha do
        elemento, não por handler de teclado — então é o elemento que o teste
        protege.
        """
        html = self._render(nivel)
        (attrs,) = [attrs for _, attrs, _ in elementos(html, 'button')]
        assert atributo(attrs, 'type') == 'button'

    @pytest.mark.parametrize('nivel', NIVEIS)
    def test_botao_fica_fora_do_no_que_carrega_o_role(self, nivel):
        """Botão irmão do texto dentro do nó com role entra no anúncio.

        O leitor de tela leria "Erro tal — Fechar mensagem, botão". O role vive
        num wrapper que contém só o texto.
        """
        html = self._render(nivel)
        for _, attrs, linha in elementos(html, 'div'):
            if atributo(attrs, 'role') not in {'alert', 'status'}:
                continue
            fim = html.index('</div>', html.index(attrs) + len(attrs))
            assert '<button' not in html[html.index(attrs) + len(attrs) : fim], (
                f'botão dentro da live region na linha {linha}'
            )

    def test_contagem_de_role_permanece_uma_por_mensagem(self):
        """Espelha apps/requisicoes/tests/test_views.py:2713, que não muda."""
        html = self._render('error', 'success')
        assert html.count('role="alert"') == 1
        assert html.count('role="status"') == 1
        assert 'aria-live=' not in html

    @pytest.mark.parametrize('nivel', ('success', 'info'))
    def test_success_e_info_pedem_auto_dismiss(self, nivel):
        html = self._render(nivel)
        ((attrs, _),) = self._itens(html)
        assert 'auto: true' in atributo(attrs, 'x-data')

    @pytest.mark.parametrize('nivel', ('warning', 'error'))
    def test_warning_e_error_declaram_auto_false(self, nivel):
        """Asserção positiva, não de ausência.

        Procurar por "não tem auto" passaria vacuamente se o atributo mudasse de
        nome, sumisse, ou o item deixasse de renderizar — o mesmo buraco de
        `test_nenhum_controle_abaixo_do_piso_de_44px`, que procura `min-h-9` e
        `min-h-10` e por isso não enxerga piso nenhum.
        """
        html = self._render(nivel)
        ((attrs, _),) = self._itens(html)
        assert 'auto: false' in atributo(attrs, 'x-data')

    @pytest.mark.parametrize('nivel', ('warning', 'error'))
    def test_warning_e_error_mantem_dismiss_manual(self, nivel):
        """Não ter timer não pode virar não ter saída."""
        html = self._render(nivel)
        assert 'Fechar mensagem' in html

    @pytest.mark.parametrize('nivel', ('success', 'info'))
    def test_timer_pausa_em_hover_e_em_foco(self, nivel):
        html = self._render(nivel)
        ((attrs, _),) = self._itens(html)
        for evento in ('@mouseenter', '@mouseleave', '@focusin', '@focusout'):
            assert atributo(attrs, evento), f'{evento} ausente'

    def test_motivo_da_assimetria_esta_registrado_no_template(self):
        """WCAG 2.2.1 é a razão de warning/error não terem timer.

        Sem o motivo no arquivo, a próxima pessoa "uniformiza" o comportamento.
        """

        raiz = Path(__file__).resolve().parents[3]
        texto = (raiz / 'apps/core/templates/core/partials/_messages.html').read_text()
        assert '2.2.1' in texto

    def test_debug_nao_chega_ao_usuario_final(self):
        html = self._render('debug')
        assert 'Mensagem debug' not in html
        assert self._itens(html) == []

    def test_sem_mensagens_visiveis_nao_sobra_wrapper(self):
        """`{% if messages %}` seria verdadeiro com um storage só de debug."""
        assert self._render('debug').strip() == ''

    def test_um_mecanismo_de_espacamento_so(self):
        """`space-y-2` no wrapper e `mb-2` nos filhos dobravam o respiro."""

        raiz = Path(__file__).resolve().parents[3]
        texto = (raiz / 'apps/core/templates/core/partials/_messages.html').read_text()
        assert not ('space-y-2' in texto and 'mb-2' in texto)

    def test_assertivas_precedem_polidas_no_dom(self):
        html = self._render('success', 'error')
        assert html.index('Mensagem error') < html.index('Mensagem success')


class TestMensagensNasTelasDeAuth:
    """Depois do logout, "Sessão encerrada." precisa ser vista.

    `login.html` incluía `_messages.html` antes do wrapper de 100vh: no celular
    o usuário via só o card e nunca a confirmação. `login_bloqueado.html` não
    incluía o partial, então qualquer mensagem enfileirada antes do 429 do axes
    sumia sem rastro.
    """

    def _render(self, template, nivel='info', texto='Sessão encerrada.', **ctx):
        from datetime import timedelta

        from django.contrib import messages as django_messages
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        # O axes sempre injeta este contexto na tela de bloqueio. Sem ele, o
        # `minutos_totais` estoura antes de o teste chegar ao que interessa.
        ctx.setdefault('cooloff_timedelta', timedelta(minutes=30))
        request = RequestFactory().get('/')
        request.session = {}
        request._messages = FallbackStorage(request)
        getattr(django_messages, nivel)(request, texto)
        return render_to_string(template, ctx, request=request)

    def test_login_renderiza_a_faixa_uma_vez(self):
        html = self._render('accounts/login.html')
        assert html.count('Sessão encerrada.') == 1

    def test_login_renderiza_a_faixa_dentro_do_bloco_centralizado(self):
        """Fora dele, a mensagem fica acima de uma dobra de 100vh."""
        html = self._render('accounts/login.html')
        assert html.index('min-h-screen') < html.index('Sessão encerrada.')

    def test_login_bloqueado_renderiza_a_faixa_uma_vez(self):
        html = self._render('accounts/login_bloqueado.html')
        assert html.count('Sessão encerrada.') == 1

    def test_login_bloqueado_conta_a_faixa_e_nao_o_alerta_fixo(self):
        """O alerta de bloqueio é components/alert.html, não flash message.

        Contá-lo mascararia justamente o caso de a faixa estar ausente.
        """
        html = self._render('accounts/login_bloqueado.html')
        assert 'Tentativas de acesso demais' in html
        assert 'Fechar mensagem' in html

    @pytest.mark.parametrize(
        'template',
        ('base_auth.html', 'accounts/login.html', 'accounts/login_bloqueado.html'),
    )
    def test_ancora_de_foco_existe_nos_tres_layouts(self, template):
        """Destino do foco depois do dismiss por teclado.

        `login_bloqueado.html` não tem nenhum outro elemento focável no card —
        é só texto —, então sem a âncora o foco cairia no body justamente na
        tela que mais precisa dela.
        """
        html = self._render(template)
        (attrs,) = [
            attrs
            for _, attrs, _ in elementos(html, 'main')
            if atributo(attrs, 'id') == 'conteudo'
        ]
        assert atributo(attrs, 'tabindex') == '-1'
