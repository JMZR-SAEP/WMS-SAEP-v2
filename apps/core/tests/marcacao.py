"""Varredura de marcação compartilhada pelos testes-guarda de front-end.

Os guardas varrem templates procurando markup escrito à mão que já tem
componente ou classe própria. O que eles não podem fazer é depender da grafia:
um regex que exige `role="alert"` logo depois de `class` deixa passar o mesmo
elemento com os atributos em outra ordem, com aspas simples ou quebrado em
várias linhas — e o guarda vira decoração.

Daí este módulo: extrai o elemento respeitando aspas (um atributo pode conter
`>`, como o `@keydown.enter="if (ativo >= 0)"` de autocomplete.html) e devolve
os atributos já em forma consultável.
"""

import re

TAGS_DJANGO = re.compile(r'\{%.*?%\}|\{\{.*?\}\}', re.S)


def elementos(texto: str, *tags: str):
    """Devolve (tag, atributos, linha) de cada tag de abertura pedida.

    O nome da tag termina em espaço, `/` ou `>` — e não num `\\b`, que aceita
    `-` como limite e faria `<button-group>` passar por `<button>`.
    """
    nomes = '|'.join(re.escape(tag) for tag in tags)
    padrao = re.compile(r'<(' + nomes + r')(?=[\s/>])', re.I)
    for encontro in padrao.finditer(texto):
        i, aspas = encontro.end(), None
        while i < len(texto):
            caractere = texto[i]
            if aspas:
                if caractere == aspas:
                    aspas = None
            elif caractere in '"\'':
                aspas = caractere
            elif caractere == '>':
                break
            i += 1
        linha = texto.count('\n', 0, encontro.start()) + 1
        yield encontro.group(1).lower(), texto[encontro.end() : i], linha


def pares(atributos: str):
    """Devolve (nome, valor) de cada atributo, da esquerda para a direita.

    A varredura é sequencial e guarda o estado das aspas, porque uma busca
    plana confunde duas coisas diferentes com o atributo procurado: um nome
    que só termina igual (`data-class` casaria com `class`) e um trecho que
    mora *dentro* do valor de outro atributo (`x-bind="class=…"`).

    Atributo sem valor (`disabled`, `novalidate`) vem com valor `None`.
    """
    i, n = 0, len(atributos)
    while i < n:
        if atributos[i].isspace():
            i += 1
            continue

        inicio = i
        while i < n and not atributos[i].isspace() and atributos[i] != '=':
            i += 1
        nome = atributos[inicio:i]
        if not nome:
            i += 1
            continue

        j = i
        while j < n and atributos[j].isspace():
            j += 1
        if j >= n or atributos[j] != '=':
            yield nome, None
            continue

        j += 1
        while j < n and atributos[j].isspace():
            j += 1
        if j < n and atributos[j] in '"\'':
            fim = atributos.find(atributos[j], j + 1)
            fim = n if fim == -1 else fim
            yield nome, atributos[j + 1 : fim]
            i = fim + 1
        else:
            fim = j
            while fim < n and not atributos[fim].isspace():
                fim += 1
            yield nome, atributos[j:fim]
            i = fim


def atributo(atributos: str, nome: str) -> str | None:
    """Valor do atributo. `None` se ausente ou se ele não tiver valor."""
    procurado = nome.lower()
    for chave, valor in pares(atributos):
        if chave.lower() == procurado:
            return valor
    return None


def classes(atributos: str) -> set[str]:
    """Classes literais do elemento, sem o que vem de tag Django.

    As tags viram espaço em vez de serem removidas: `border{% if x %}...`
    concatenado sem separador criaria uma classe que ninguém escreveu.
    """
    valor = atributo(atributos, 'class')
    if valor is None:
        return set()
    return set(TAGS_DJANGO.sub(' ', valor).split())
