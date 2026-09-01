"""Política única de precisão de quantidade por unidade de medida.

Uma mesma quantidade aparece de três formas no sistema — o texto que a tela
exibe, o `step` do `<input type="number">` e o valor que preenche esse input —
e as três precisam concordar. Enquanto cada uma vivia por conta própria, elas
divergiram: a tela de atendimento chegava com `1.000` num material medido em
unidade, que o navegador exibe em pt-BR como `1,000` — ou seja, *mil* canetas
num campo que dá baixa em estoque.

Este módulo não conhece Django e não é template tag: é consumido tanto por
`core_tags` (exibição) quanto por views (valor inicial de formulário), e por
isso não pode morar em nenhum dos dois.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

UNIDADE_INTEIRA = 'un'
UNIDADES_UMA_DECIMAL = ('kg', 'l', 'm')
CASAS_PADRAO = 3


def casas_decimais(unidade: str) -> int:
    """Casas significativas que a unidade admite."""
    if unidade == UNIDADE_INTEIRA:
        return 0
    if unidade in UNIDADES_UMA_DECIMAL:
        return 1
    return CASAS_PADRAO


def step(unidade: str) -> str:
    """Valor do atributo `step` de um `<input type="number">` para a unidade."""
    casas = casas_decimais(unidade)
    if casas == 0:
        return '1'
    return format(Decimal(1).scaleb(-casas), 'f')


def normalizar(qtd: object) -> Decimal | None:
    """Quantidade sem os zeros à direita que o DecimalField carrega do banco.

    É o valor que vai para o `value` de um campo numérico: `1.000` vira `1`,
    `5.500` vira `5.5`.

    Deliberadamente **não** arredonda para a precisão da unidade. Um campo de
    digitação que reescreve o número que recebeu é pior que um campo feio: se o
    banco guarda 5,5 de um material medido em unidade, quantizar mostraria 6 e a
    pessoa daria baixa de 6 achando que confirmou o que foi autorizado. Aqui o
    valor aparece como está e é o `step` que reclama — divergência visível em
    vez de silenciosa.

    `normalize()` sozinho não serve: devolve `1E+2` para 100, que o Django
    renderiza literalmente no HTML e o navegador recusa como número.
    """
    if qtd is None or qtd == '':
        return None
    try:
        d = Decimal(str(qtd))
    except (InvalidOperation, TypeError, ValueError):
        return None

    normalizado = d.normalize()
    if normalizado == normalizado.to_integral_value():
        return normalizado.quantize(Decimal(1))
    return normalizado


def formatar(qtd: object, unidade: str) -> str:
    """Texto de exibição da quantidade, em notação pt-BR.

    Difere de `normalizar` em dois pontos de propósito.

    O primeiro: unidade fracionária mantém a casa decimal mesmo quando o valor é
    inteiro (`1,0 kg`), porque ali a casa comunica a precisão da medida. Num
    campo de digitação isso só atrapalharia.

    O segundo: o separador é a **vírgula**. Este módulo existe para matar o bug
    do `1.000` que em pt-BR se lê *mil*, e por muito tempo emitiu `1.0` — ponto
    decimal, no mesmo produto em que `LANGUAGE_CODE = 'pt-br'` e todo `Decimal`
    impresso cru pelo Django sai localizado. O exemplo `1,0 kg` desta docstring
    descrevia a intenção, não o comportamento; agora descreve os dois.

    **Não** há separador de milhar. Agrupar traria de volta o ponto como
    separador de milhar (`1.250,5`) na mesma tela em que ele já foi lido como
    decimal, e a coluna de `font-mono` do livro-razão ganharia um caractere de
    largura variável. Quem precisa de grupo é relatório, não conferência de
    prateleira. `normalizar` segue com ponto: é valor de `<input type="number">`,
    que o HTML define em notação de máquina, não de leitura.
    """
    if qtd is None:
        return '—'
    try:
        d = Decimal(str(qtd))
    except (InvalidOperation, TypeError, ValueError):
        return str(qtd)

    if unidade == UNIDADE_INTEIRA:
        return str(int(d))
    if unidade in UNIDADES_UMA_DECIMAL:
        return _com_virgula(format(d.quantize(Decimal('0.1')), 'f'))

    normalizado = d.normalize()
    if normalizado == normalizado.to_integral_value():
        return str(int(normalizado))
    return _com_virgula(format(normalizado, 'f'))


def _com_virgula(texto: str) -> str:
    """Troca o ponto decimal pela vírgula. Sem agrupamento de milhar."""
    return texto.replace('.', ',')
