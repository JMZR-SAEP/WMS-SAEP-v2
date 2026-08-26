"""Testes da leitura do documento renderizado (sem DB, sem template)."""

import pytest

from apps.core.tests.documento import (
    assert_dialogo_nomeado_pelo_proprio_titulo,
    assert_html_balanceado,
    assert_sem_id_duplicado,
    dialogos,
    ids_do_documento,
    ids_duplicados,
)


def test_ids_saem_na_ordem_e_com_as_repeticoes():
    html = '<div id="a"><h3 id="b"></h3><h2 id="a"></h2></div>'
    assert ids_do_documento(html) == ['a', 'b', 'a']
    assert ids_duplicados(html) == ['a']


def test_id_vazio_nao_conta_como_id():
    assert ids_do_documento('<div id=""></div><div id=""></div>') == []


def test_h2_de_fora_do_dialogo_nao_entra_nos_candidatos():
    """O `<h2>` que vem depois do `</dialog>` é de outra parte da página.

    Se ele entrasse, um `aria-labelledby` apontando para fora do diálogo
    passaria pela checagem estrutural.
    """
    html = '<dialog aria-labelledby="m-titulo"></dialog><h2 id="m-titulo"></h2>'
    assert dialogos(html) == [('m-titulo', [])]


def test_dialogo_aninhado_nao_captura_h2_do_resto_do_documento():
    """Uma bandeira booleana atribuiria ao diálogo tudo o que vem depois.

    Fechado o interno, o externo segue aberto; fechado o externo, nenhum `<h2>`
    do documento entra. E o `<h2>` do interno conta para os dois, porque está
    dentro dos dois.
    """
    html = (
        '<dialog aria-labelledby="externo-titulo">'
        '<h2 id="externo-titulo"></h2>'
        '<dialog aria-labelledby="interno-titulo"><h2 id="interno-titulo"></h2></dialog>'
        '</dialog>'
        '<h2 id="de-fora"></h2>'
    )
    assert dialogos(html) == [
        ('externo-titulo', ['externo-titulo', 'interno-titulo']),
        ('interno-titulo', ['interno-titulo']),
    ]


def test_atributo_repetido_vale_pela_primeira_ocorrencia():
    """É como o navegador resolve; `dict(attrs)` devolveria a última."""
    assert ids_do_documento('<div id="primeiro" id="segundo"></div>') == ['primeiro']
    assert dialogos('<dialog aria-labelledby="a" aria-labelledby="b"></dialog>') == [
        ('a', [])
    ]


def test_dialogo_sem_aria_labelledby_vem_com_none():
    assert dialogos('<dialog><h2 id="m-titulo"></h2></dialog>') == [
        (None, ['m-titulo'])
    ]


def test_documento_conforme_passa_pelas_duas_guardas():
    html = (
        '<button data-modal-trigger="m"></button>'
        '<dialog id="m" aria-labelledby="m-titulo"><h2 id="m-titulo"></h2></dialog>'
    )
    assert_sem_id_duplicado(html)
    assert_dialogo_nomeado_pelo_proprio_titulo(html)


def test_id_duplicado_reprova_as_duas_guardas():
    """A regressão da #131 em miniatura: o heading de fora carrega o mesmo id.

    A estrutural também reprova aqui, mas só por causa da contagem — o `<h2>`
    de dentro do diálogo continua carregando o id.
    """
    html = (
        '<h3 id="m-titulo"></h3>'
        '<dialog id="m" aria-labelledby="m-titulo"><h2 id="m-titulo"></h2></dialog>'
    )
    with pytest.raises(AssertionError):
        assert_sem_id_duplicado(html)
    with pytest.raises(AssertionError):
        assert_dialogo_nomeado_pelo_proprio_titulo(html)


def test_documento_sem_dialogo_reprova_em_vez_de_passar_vazio():
    """Guarda que não encontra `<dialog>` não provou nada: o estado renderizado
    não emitiu o modal, e o `for` sobre lista vazia passaria em silêncio."""
    with pytest.raises(AssertionError):
        assert_dialogo_nomeado_pelo_proprio_titulo('<h2 id="m-titulo"></h2>')


def test_nome_acessivel_apontando_para_fora_do_dialogo_reprova():
    html = '<dialog aria-labelledby="m-titulo"></dialog><h2 id="m-titulo"></h2>'
    with pytest.raises(AssertionError):
        assert_dialogo_nomeado_pelo_proprio_titulo(html)


def test_fragmento_balanceado_passa():
    assert_html_balanceado('<div><span>texto</span><img src="x"></div>')


def test_fechamento_fora_de_ordem_reprova():
    with pytest.raises(AssertionError):
        assert_html_balanceado('<div><span></div></span>')


def test_tag_nao_fechada_reprova():
    with pytest.raises(AssertionError):
        assert_html_balanceado('<div><span>texto</div>')
