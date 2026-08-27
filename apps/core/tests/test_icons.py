"""Testes diretos da tag {% icon %} e do catálogo vendorizado (sem DB, sem view)."""

import re

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Template

from apps.core.templatetags.core_tags import ICONES_CATALOGO


def _render(tag_call: str, **ctx) -> str:
    template = Template('{% load core_tags %}' + tag_call)
    return template.render(Context(ctx))


@pytest.mark.parametrize('name', sorted(ICONES_CATALOGO))
def test_icon_todo_catalogo_mantem_aria_hidden(name):
    html = _render(f'{{% icon "{name}" %}}')
    assert 'aria-hidden="true"' in html


def test_icon_adicionar_renderiza_path_e_viewbox_originais():
    html = _render('{% icon "adicionar" %}')
    assert (
        'd="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"'
        in html
    )
    assert 'viewBox="0 0 20 20"' in html
    assert 'aria-hidden="true"' in html


def test_icon_repassa_class_verbatim():
    html = _render('{% icon "adicionar" class="h-4 w-4 text-blue-600" %}')
    assert 'class="h-4 w-4 text-blue-600"' in html


def test_icon_nome_fora_do_catalogo_levanta_improperly_configured():
    with pytest.raises(ImproperlyConfigured, match='nao-existe'):
        _render('{% icon "nao-existe" %}')


def test_icon_nome_com_separador_de_caminho_levanta_improperly_configured():
    with pytest.raises(ImproperlyConfigured):
        _render('{% icon "../../etc/passwd" %}')


def test_icon_nome_nao_string_levanta_improperly_configured_em_vez_de_typeerror():
    with pytest.raises(ImproperlyConfigured):
        _render('{% icon nome %}', nome=['adicionar'])


def test_icon_voltar_usa_size_para_width_height_mas_viewbox_fixo_em_24():
    html_default = _render('{% icon "voltar" %}')
    assert 'width="20"' in html_default
    assert 'height="20"' in html_default
    assert 'viewBox="0 0 24 24"' in html_default
    assert (
        'd="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"'
        in html_default
    )

    html_24 = _render('{% icon "voltar" size=24 %}')
    assert 'width="24"' in html_24
    assert 'height="24"' in html_24
    assert 'viewBox="0 0 24 24"' in html_24


def test_icon_voltar_honra_class_como_todo_o_catalogo():
    """`voltar.svg` era o único `.svg` a descartar `class` em silêncio.

    Ele dimensionava só por `size`, então chegar via `icon_template` de
    `button.html` — que passa `class` e não `size` — rendia `width=""` e um
    ícone sem classe nenhuma. O arquivo agora aceita as duas convenções.
    """
    html = _render('{% icon "voltar" class="qualquer-coisa" %}')
    assert 'qualquer-coisa' in html


def test_icon_lixeira_renderiza_path_original_variante_modal_danger():
    html = _render('{% icon "lixeira" class="h-5 w-5" %}')
    assert (
        'd="M8.5 3.5a1.5 1.5 0 0 1 3 0V4H15a1 1 0 1 1 0 2h-1.1l-.5 8.1A2.5 2.5 0 0 1 '
        '10.9 16H9.1a2.5 2.5 0 0 1-2.49-1.9L6.1 6H5a1 1 0 1 1 0-2h3.5v-.5Zm-1.35 8.7.25 '
        '4.05a.5.5 0 0 0 .5.48h2.7a.5.5 0 0 0 .5-.48l.25-4.05H7.15Z"' in html
    )
    assert 'viewBox="0 0 20 20"' in html
    assert 'class="h-5 w-5"' in html
    assert 'aria-hidden="true"' in html


def test_icon_remover_renderiza_path_original_variante_linha_de_item():
    html = _render('{% icon "remover" class="h-4 w-4 shrink-0" %}')
    assert (
        'd="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 '
        '1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 '
        '1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"' in html
    )
    assert 'viewBox="0 0 20 20"' in html
    assert 'class="h-4 w-4 shrink-0"' in html


def test_icon_enviar_e_o_aviao_revendorizado():
    """O path anterior não fechava a silhueta.

    Ampliado, ele emitia um traço solto no canto superior esquerdo, fora do
    corpo do avião, e o corpo saía assimétrico no eixo horizontal. O ícone está
    em duas CTAs primárias ("Enviar para autorização"), então o defeito
    aparecia no caminho mais percorrido do produto.
    """
    html = _render('{% icon "enviar" class="h-4 w-4" %}')
    assert 'M2.87 2.298' in html
    assert '.3-1.4z' not in html
    assert 'viewBox="0 0 20 20"' in html
    assert 'class="h-4 w-4"' in html


def test_icon_spinner_renderiza_circle_e_path_com_class_repassada():
    html = _render(
        '{% icon "spinner" class="h-4 w-4 animate-spin motion-reduce:animate-none" %}'
    )
    assert (
        '<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"'
        in html
    )
    assert 'd="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"' in html
    assert 'viewBox="0 0 24 24"' in html
    assert 'fill="none"' in html
    assert 'class="h-4 w-4 animate-spin motion-reduce:animate-none"' in html


def test_icon_copiar_renderiza_os_dois_paths_originais():
    html = _render('{% icon "copiar" class="h-4 w-4" %}')
    assert (
        'd="M7 9a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V9Z"'
        in html
    )
    assert 'd="M5 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2V5h8a2 2 0 0 0-2-2H5Z"' in html
    assert 'viewBox="0 0 20 20"' in html
    assert 'class="h-4 w-4"' in html


def test_icon_confirmar_renderiza_path_original():
    html = _render('{% icon "confirmar" class="h-4 w-4 shrink-0" %}')
    # Os arcos precisam do separador antes dos flags: sem o espaço depois da
    # rotação (`a1 1 010`), o parser de SVG rejeita o path inteiro e o check
    # some do botão primário.
    assert (
        'd="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 '
        '011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"' in html
    )
    assert 'viewBox="0 0 20 20"' in html
    assert 'class="h-4 w-4 shrink-0"' in html
    assert 'aria-hidden="true"' in html


def test_catalogo_tem_um_unico_check():
    """`confirmar` e `confirmar_check` eram o mesmo glifo, variando a espessura.

    Duas confirmações do domínio ("Registrar saída excepcional" e "Confirmar
    importação") não precisam de dois desenhos, e o nome `confirmar_check` não
    distinguia nada. Sobrou `confirmar`.
    """
    from apps.core.templatetags.core_tags import ICONES_CATALOGO

    assert 'confirmar' in ICONES_CATALOGO
    assert 'confirmar_check' not in ICONES_CATALOGO
    with pytest.raises(ImproperlyConfigured):
        _render('{% icon "confirmar_check" %}')


def test_icon_informacao_renderiza_path_original():
    html = _render('{% icon "informacao" class="h-5 w-5" %}')
    assert (
        'd="M18 10A8 8 0 1 1 2 10a8 8 0 0 1 16 0Zm-8.75-4.25a.75.75 0 0 1 1.5 0v.5a.75.75 '
        '0 0 1-1.5 0v-.5Zm.75 3a.75.75 0 0 0-.75.75v4a.75.75 0 0 0 1.5 0v-4a.75.75 0 0 '
        '0-.75-.75Z"' in html
    )
    assert 'viewBox="0 0 20 20"' in html
    assert 'class="h-5 w-5"' in html


def test_icon_atencao_renderiza_path_original_variante_modal_warning():
    html = _render('{% icon "atencao" class="h-5 w-5" %}')
    assert (
        'd="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 '
        '2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 5a.75.75 '
        '0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 5Zm0 9a1 1 0 1 0 0-2 1 1 '
        '0 0 0 0 2Z"' in html
    )
    assert 'viewBox="0 0 20 20"' in html


def test_icon_alerta_renderiza_path_original_variante_modal_danger():
    """#136: `danger` deixou de ser a lixeira e passou a ser este glifo."""
    html = _render('{% icon "alerta" class="h-5 w-5" %}')
    assert (
        'd="M18 10A8 8 0 1 1 2 10a8 8 0 0 1 16 0Zm-7-4a1 1 0 1 0-2 0v4a1 1 0 1 0 2 0V6Zm-1 '
        '8a1.2 1.2 0 1 1 0-2.4 1.2 1.2 0 0 1 0 2.4Z"' in html
    )
    assert 'viewBox="0 0 20 20"' in html


def test_icon_devolver_usa_size_para_width_height_mas_viewbox_fixo_em_24():
    html = _render('{% icon "devolver" %}')
    assert 'width="20"' in html
    assert 'height="20"' in html
    assert 'viewBox="0 0 24 24"' in html


def test_icon_estornar_e_reversao_nao_lixeira():
    """Estorno não apaga: preserva número público, timeline e movimentação.

    O glifo era uma lata de lixo — o mesmo desenho de `lixeira` e `remover` —
    e ensinava o contrário do domínio (Princípio 2: auditabilidade acima de
    conveniência). Agora é a seta em U da reversão.
    """
    html = _render('{% icon "estornar" class="h-4 w-4" %}')
    assert 'M7.793 2.232' in html
    assert 'viewBox="0 0 20 20"' in html
    assert 'class="h-4 w-4"' in html

    def caminho(svg: str) -> str:
        return re.search(r'd="([^"]+)"', svg).group(1)

    lixeira = _render('{% icon "lixeira" %}')
    remover = _render('{% icon "remover" %}')
    assert caminho(html) != caminho(lixeira)
    assert caminho(html) != caminho(remover)


def test_nenhum_template_inlina_um_path_que_ja_esta_no_catalogo():
    """O catálogo não tinha exclusividade, e a cópia divergente é que rodava.

    `components/autocomplete.html` inlinava dois SVGs: um era o path de
    `confirmar.svg` byte a byte, o outro era um spinner **diferente** do
    `spinner.svg` — que, por consequência, não tinha nenhum consumidor. Dois
    desenhos para o mesmo estado, com o do catálogo fora de uso.

    A tag `{% icon %}` valida nome e barra traversal, mas nada impedia o
    bypass. Este guard impede.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[3]
    icones = raiz / 'apps/core/templates/components/icons'

    paths_do_catalogo = {}
    for arquivo in icones.glob('*.svg'):
        for d in re.findall(r'\sd="([^"]+)"', arquivo.read_text()):
            paths_do_catalogo[d] = arquivo.name

    reincidencias = []
    for template in (raiz / 'apps').rglob('*.html'):
        if icones in template.parents:
            continue
        conteudo = template.read_text()
        for d in re.findall(r'\sd="([^"]+)"', conteudo):
            if d in paths_do_catalogo:
                relativo = template.relative_to(raiz)
                reincidencias.append(f'{relativo} inlina {paths_do_catalogo[d]}')

    assert not reincidencias, (
        'use {% icon "nome" %} em vez de copiar o path do catálogo: '
        f'{sorted(set(reincidencias))}'
    )
