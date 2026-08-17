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
    """Devolve (tag, atributos, linha) de cada tag de abertura pedida."""
    padrao = re.compile(r'<(' + '|'.join(tags) + r')\b', re.I)
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


def atributo(atributos: str, nome: str) -> str | None:
    """Valor literal do atributo, com aspas simples ou duplas. `None` se ausente."""
    encontro = re.search(
        rf'\b{re.escape(nome)}\s*=\s*(["\'])(?P<valor>.*?)\1', atributos, re.S
    )
    return encontro.group('valor') if encontro else None


def classes(atributos: str) -> set[str]:
    """Classes literais do elemento, sem o que vem de tag Django.

    As tags viram espaço em vez de serem removidas: `border{% if x %}...`
    concatenado sem separador criaria uma classe que ninguém escreveu.
    """
    valor = atributo(atributos, 'class')
    if valor is None:
        return set()
    return set(TAGS_DJANGO.sub(' ', valor).split())
