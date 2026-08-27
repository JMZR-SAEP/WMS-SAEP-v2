"""Testes diretos de components/field_error.html (sem DB, sem view)."""

from pathlib import Path

from django.template.loader import render_to_string

from apps.core.tests.marcacao import atributo, classes, elementos


def _render(**ctx):
    ctx.setdefault('id', 'id_campo-erro')
    ctx.setdefault('erros', ['Este campo é obrigatório.'])
    return render_to_string('components/field_error.html', ctx)


def test_id_permite_ancorar_o_aria_describedby_do_campo():
    assert 'id="id_campo-erro"' in _render()


def test_erro_e_anunciado():
    assert 'role="alert"' in _render()


def test_varios_erros_viram_uma_frase_so():
    """`role="alert"` lê o nó inteiro de uma vez.

    Quebrar em vários parágrafos não muda o que é anunciado, só o que ocupa a
    tela — era o que o login fazia, com um `<p>` por erro.
    """
    html = _render(erros=['Obrigatório.', 'Mínimo 1.'])
    assert 'Obrigatório., Mínimo 1.' in html
    assert html.count('<p') == 1


def test_class_passthrough_nao_substitui_a_tipografia_do_erro():
    html = _render(**{'class': 'mb-3'})
    assert 'mb-3' in html
    assert 'text-xs' in html
    assert 'text-danger-text' in html


def test_nenhum_template_escreve_erro_de_campo_a_mao():
    """Erro de campo tem uma voz só.

    O markup vivia copiado em sete lugares e três grafias — `mt-1 text-xs` no
    componente e nas linhas de item, `mb-3` numa variante do rascunho, e um
    `<div class="mt-2 text-sm">` com um `<p>` por erro no login. Três tamanhos
    de texto para dizer a mesma coisa não é decisão de tela.

    `data-erro-busca` e `data-erro-gate` são as únicas saídas, e não são
    brechas: a primeira marca falha da requisição de busca do autocomplete; a
    segunda, o gate de submit no cliente (#151) — texto digitado sem item
    vinculado. Nenhuma das duas é erro de campo: não vêm do `clean()`, não
    sobrevivem ao POST e somem na tecla seguinte. Erro de campo vem do Form,
    sobrevive ao POST e é ancorado pelo sumário de erros. Unificar tudo na
    mesma voz seria dizer que a rede caiu, ou que a pessoa esqueceu de
    escolher da lista, do mesmo jeito que se diz que o campo é obrigatório.
    """
    raiz = Path(__file__).resolve().parents[3]
    infratores: list[str] = []
    for caminho in (raiz / 'apps').rglob('*.html'):
        if caminho.name == 'field_error.html':
            continue
        texto = caminho.read_text()
        for _, atributos, numero in elementos(texto, 'p'):
            # Atributo sem valor: `atributo()` devolve None tanto para ausente
            # quanto para vazio, então quem decide aqui é a presença no texto.
            if 'data-erro-busca' in atributos or 'data-erro-gate' in atributos:
                continue
            if atributo(atributos, 'role') == 'alert' and 'text-danger-text' in classes(
                atributos
            ):
                infratores.append(f'{caminho.relative_to(raiz)}:{numero}')

    assert not infratores, (
        f'Erro de campo escrito à mão; use components/field_error.html: {infratores}'
    )
