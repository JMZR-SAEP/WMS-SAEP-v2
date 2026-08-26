"""Leitura do documento renderizado pelos testes-guarda de front-end.

Irmão de `marcacao.py`: lá a varredura é sobre o **template**, texto com tag
Django dentro; aqui é sobre o **HTML já renderizado por uma view**, onde os
atributos são finais e o aninhamento é real.

O que mora aqui é a leitura de identidade do documento — os `id` emitidos e o
nome acessível de cada `<dialog>` —, porque `components/modal.html` deriva o
alvo do `aria-labelledby` do `<h2>` do corpo (`{{ id }}-titulo`) e esse contrato
é o mesmo em toda tela que inclui o componente. A leitura é por `HTMLParser` e
não por fatia de string: prova que o alvo do `aria-labelledby` está *dentro* do
diálogo, em vez de existir em algum lugar do documento.

Nasceu privado de `apps/requisicoes/tests/test_views.py` na #131, onde o `<h3>`
do painel de decisão derivava o mesmo `{{ modal_id }}-titulo` do `<h2>` do modal
que ele abre: o `<dialog>` era anunciado pelo heading do cartão que ficava
atrás. Subiu para cá na #139 para que as telas de modal de `estoque` herdassem
a guarda sem reescrever a leitura.

Não é coletado como teste (nome sem prefixo `test_`), como `marcacao.py`.
"""

from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from typing import NamedTuple


class NomeDeDialogo(NamedTuple):
    """O nome acessível declarado por um `<dialog>` e os candidatos internos.

    `rotulado_por` é o valor cru do `aria-labelledby` (`None` se ausente);
    `ids_de_titulo` são os `id` dos `<h2>` que estão dentro daquele diálogo.
    """

    rotulado_por: str | None
    ids_de_titulo: list[str]


def _primeiro(attrs: list[tuple[str, str | None]], nome: str) -> str | None:
    """Primeiro valor do atributo, que é o que o navegador resolve.

    Atributo repetido no mesmo elemento vale pela primeira ocorrência; um
    `dict(attrs)` devolveria a última. É também o que `marcacao.atributo`, o
    irmão que lê template, já faz — os dois módulos respondem igual.
    """
    for chave, valor in attrs:
        if chave == nome:
            return valor
    return None


class _ColetorDeIds(HTMLParser):
    """Todos os `id` do documento, na ordem em que aparecem."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        valor = _primeiro(attrs, 'id')
        if valor:
            self.ids.append(valor)


def ids_do_documento(html: str) -> list[str]:
    """Os `id` do documento, na ordem de emissão e com as repetições.

    Inclui o que está dentro de `<template>` — os moldes que `modal.js` clona,
    por exemplo. Um id ali vive num `DocumentFragment` e não colide com o
    documento real, então esta leitura é mais estrita que o navegador. Hoje não
    dá falso positivo, porque nenhum molde repete um id de elemento vivo; no dia
    em que der, o recorte é aqui.
    """
    coletor = _ColetorDeIds()
    coletor.feed(html)
    return coletor.ids


class _NomesDeDialogo(HTMLParser):
    """Para cada `<dialog>`, o `aria-labelledby` e os ids dos `<h2>` internos.

    A pilha de diálogos abertos é contada, e não uma bandeira booleana: com
    `<dialog>` aninhado — HTML válido —, uma bandeira devolveria os `<h2>` do
    resto do documento como se fossem do diálogo, depois que o interno fechasse.
    O `<h2>` do interno conta para o externo também, porque está dentro dele.
    """

    def __init__(self) -> None:
        super().__init__()
        self.dialogos: list[tuple[str | None, list[str]]] = []
        self._abertos: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == 'dialog':
            self.dialogos.append((_primeiro(attrs, 'aria-labelledby'), []))
            self._abertos.append(len(self.dialogos) - 1)
            return
        if tag != 'h2' or not self._abertos:
            return
        valor = _primeiro(attrs, 'id')
        if valor:
            for indice in self._abertos:
                self.dialogos[indice][1].append(valor)

    def handle_endtag(self, tag: str) -> None:
        if tag == 'dialog' and self._abertos:
            self._abertos.pop()


def dialogos(html: str) -> list[NomeDeDialogo]:
    """Um `NomeDeDialogo` por `<dialog>` do documento, na ordem de emissão."""
    parser = _NomesDeDialogo()
    parser.feed(html)
    return [NomeDeDialogo(*dialogo) for dialogo in parser.dialogos]


def ids_duplicados(html: str) -> list[str]:
    """Os `id` que aparecem mais de uma vez, na ordem da primeira ocorrência."""
    return [id_ for id_, vezes in Counter(ids_do_documento(html)).items() if vezes > 1]


def assert_sem_id_duplicado(html: str) -> None:
    """Nenhum `id` aparece duas vezes: id repetido é HTML inválido e torna
    qualquer `getElementById` — logo, qualquer `aria-labelledby` — imprevisível.
    """
    duplicados = ids_duplicados(html)
    assert duplicados == [], f'ids repetidos no documento: {duplicados}'


_TAGS_VAZIAS = {
    'area',
    'base',
    'br',
    'col',
    'embed',
    'hr',
    'img',
    'input',
    'link',
    'meta',
    'param',
    'source',
    'track',
    'wbr',
}
"""Todo elemento vazio da lista void do HTML5, e não só os que os templates
emitem hoje: um `_PilhaDeTags` que só conhece o recorte atual reprovaria um
fragmento válido (`<source>`, `<track>` etc.) que um template futuro venha a
emitir, e a asserção de balanceamento existe para pegar HTML errado, não
para restringir o vocabulário de tags permitidas.
"""


class _PilhaDeTags(HTMLParser):
    """Valida aninhamento/fechamento de tags num fragmento HTML (issue #88)."""

    def __init__(self) -> None:
        super().__init__()
        self.pilha: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _TAGS_VAZIAS:
            self.pilha.append(tag)

    def handle_endtag(self, tag: str) -> None:
        assert self.pilha and self.pilha[-1] == tag, (
            f'fechamento inesperado de </{tag}>: pilha atual {self.pilha}'
        )
        self.pilha.pop()


def assert_html_balanceado(fragmento: str) -> None:
    """Toda tag aberta no fragmento fecha, na ordem certa, antes do fim dele."""
    parser = _PilhaDeTags()
    parser.feed(fragmento)
    assert parser.pilha == [], f'tags não fechadas: {parser.pilha}'


def assert_dialogo_nomeado_pelo_proprio_titulo(html: str) -> None:
    """O nome acessível de cada `<dialog>` é um `<h2>` de dentro dele, e único.

    As duas asserções andam juntas, e a de unicidade é a que pega a regressão da
    #131: com o id duplicado, o `<h2>` do modal continua carregando o id e a
    checagem estrutural passa — quem resolve para o elemento errado, o heading
    do cartão que ficou atrás, é o navegador.
    """
    ids = ids_do_documento(html)
    encontrados = dialogos(html)

    assert encontrados, 'nenhum <dialog> no documento'
    for rotulado_por, ids_de_titulo in encontrados:
        assert rotulado_por, f'<dialog> sem aria-labelledby: {encontrados}'
        assert rotulado_por in ids_de_titulo, (
            f'aria-labelledby="{rotulado_por}" não resolve para um <h2> de dentro '
            f'do próprio diálogo (internos: {ids_de_titulo})'
        )
        assert ids.count(rotulado_por) == 1, (
            f'id "{rotulado_por}" aparece {ids.count(rotulado_por)} vezes no '
            f'documento: o nome acessível do diálogo é imprevisível'
        )
