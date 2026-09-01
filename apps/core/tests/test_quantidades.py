"""Política de precisão de quantidade — exibição, `step` e valor de campo."""

from decimal import Decimal

import pytest

from apps.core.quantidades import casas_decimais, formatar, normalizar, step


@pytest.mark.parametrize(
    ('unidade', 'esperado'),
    [('un', 0), ('kg', 1), ('l', 1), ('m', 1), ('cx', 3), ('', 3)],
)
def test_casas_por_unidade(unidade, esperado):
    assert casas_decimais(unidade) == esperado


@pytest.mark.parametrize(
    ('unidade', 'esperado'),
    [('un', '1'), ('kg', '0.1'), ('cx', '0.001')],
)
def test_step_acompanha_as_casas_da_unidade(unidade, esperado):
    assert step(unidade) == esperado


@pytest.mark.parametrize(
    ('entrada', 'esperado'),
    [
        ('1.000', '1'),
        ('2.000', '2'),
        ('5.500', '5.5'),
        ('0.250', '0.25'),
        ('0.001', '0.001'),
        ('0.000', '0'),
    ],
)
def test_normalizar_tira_zeros_a_direita(entrada, esperado):
    """`1.000` num campo numérico é lido como mil em pt-BR."""
    assert str(normalizar(Decimal(entrada))) == esperado


def test_normalizar_nao_devolve_notacao_cientifica():
    """`Decimal.normalize()` devolve `1E+2` para 100 — o navegador recusa."""
    assert str(normalizar(Decimal('100.000'))) == '100'
    assert 'E' not in str(normalizar(Decimal('1000.000')))


def test_normalizar_nunca_arredonda():
    """Campo que reescreve o número recebido faz confirmar o que não foi autorizado.

    Se o banco guarda 5,5 de um material medido em unidade, o campo mostra 5,5 e
    deixa o `step` reclamar. Arredondar para 6 daria baixa de 6 com a pessoa
    achando que confirmou o autorizado.
    """
    assert str(normalizar(Decimal('5.500'))) == '5.5'
    assert str(normalizar(Decimal('0.7'))) == '0.7'


@pytest.mark.parametrize('vazio', [None, ''])
def test_normalizar_sem_valor(vazio):
    assert normalizar(vazio) is None


def test_normalizar_ignora_lixo():
    assert normalizar('abc') is None


@pytest.mark.parametrize(
    ('qtd', 'unidade', 'esperado'),
    [
        (Decimal('1.000'), 'un', '1'),
        (Decimal('12.000'), 'un', '12'),
        (Decimal('1.000'), 'kg', '1,0'),
        (Decimal('1.250'), 'kg', '1,2'),
        (Decimal('2.500'), 'cx', '2,5'),
        (Decimal('3.000'), 'cx', '3'),
        (None, 'un', '—'),
    ],
)
def test_formatar_para_exibicao(qtd, unidade, esperado):
    """Unidade fracionária guarda a casa mesmo inteira: ali ela comunica precisão."""
    assert formatar(qtd, unidade) == esperado


@pytest.mark.parametrize(
    ('qtd', 'unidade', 'esperado'),
    [
        (Decimal('1250.500'), 'm', '1250,5'),
        (Decimal('820.000'), 'un', '820'),
        (Decimal('18.750'), 'm2', '18,75'),
        (Decimal('0.250'), 'cx', '0,25'),
    ],
)
def test_formatar_usa_virgula_e_nao_agrupa_milhar(qtd, unidade, esperado):
    """Este módulo existe para matar o `1.000` que em pt-BR se lê *mil*, e emitia
    `1.0`. Agrupar milhar traria o ponto de volta como separador na mesma tela em
    que ele já foi lido como decimal — e daria um caractere de largura variável à
    coluna `font-mono` do livro-razão."""
    assert formatar(qtd, unidade) == esperado
    assert '.' not in formatar(qtd, unidade)


def test_normalizar_segue_com_ponto_porque_e_valor_de_input():
    """`normalizar` alimenta `value` de `<input type=\"number\">`, que o HTML
    define em notação de máquina. Vírgula ali faz o navegador recusar o valor."""
    assert str(normalizar(Decimal('5.500'))) == '5.5'
    assert ',' not in str(normalizar(Decimal('1250.500')))
