"""Testes da varredura que sustenta os testes-guarda (sem DB, sem template)."""

from apps.core.tests.marcacao import atributo, classes, elementos


def test_nome_de_tag_termina_no_delimitador_e_nao_no_hifen():
    assert list(elementos('<button-group class="x">', 'button')) == []
    assert [tag for tag, _, _ in elementos('<button class="x">', 'button')] == [
        'button'
    ]


def test_tag_sem_atributo_e_reconhecida():
    assert [linha for _, _, linha in elementos('\n<p>erro</p>', 'p')] == [2]


def test_atributo_atravessa_valor_com_maior_que():
    marcacao = '<input @keydown.enter="if (ativo > 0) sair()" class="campo">'
    _, atributos, _ = next(elementos(marcacao, 'input'))
    assert atributo(atributos, 'class') == 'campo'


def test_nome_que_so_termina_igual_nao_e_o_atributo():
    assert atributo(' data-class="falso"', 'class') is None


def test_ocorrencia_dentro_de_outro_valor_nao_e_o_atributo():
    assert atributo(' x-bind=\'class="falso"\'', 'class') is None


def test_atributo_sem_valor_nao_vira_valor_do_seguinte():
    assert atributo(' disabled class="campo"', 'disabled') is None
    assert atributo(' disabled class="campo"', 'class') == 'campo'


def test_tag_django_separa_classes_em_vez_de_colar_uma_nova():
    """A classe dentro do ramo é literal e conta; a tag em si vira separador.

    Remover a tag em vez de trocá-la por espaço colaria `border` e
    `border-danger` numa terceira classe que ninguém escreveu.
    """
    atributos = ' class="border{% if erro %}border-danger{% endif %}px-3"'
    assert classes(atributos) == {'border', 'border-danger', 'px-3'}
