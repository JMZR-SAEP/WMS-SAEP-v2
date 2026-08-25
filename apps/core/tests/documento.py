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


class _ColetorDeIds(HTMLParser):
    """Todos os `id` do documento, na ordem em que aparecem."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for nome, valor in attrs:
            if nome == 'id' and valor:
                self.ids.append(valor)


def ids_do_documento(html: str) -> list[str]:
    """Os `id` do documento, na ordem de emissão e com as repetições."""
    coletor = _ColetorDeIds()
    coletor.feed(html)
    return coletor.ids


class _NomesDeDialogo(HTMLParser):
    """Para cada `<dialog>`, o `aria-labelledby` e os ids dos `<h2>` internos."""

    def __init__(self) -> None:
        super().__init__()
        self.dialogos: list[NomeDeDialogo] = []
        self._dentro = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        atributos = dict(attrs)
        if tag == 'dialog':
            self.dialogos.append(NomeDeDialogo(atributos.get('aria-labelledby'), []))
            self._dentro = True
        elif self._dentro and tag == 'h2' and atributos.get('id'):
            self.dialogos[-1].ids_de_titulo.append(atributos['id'])

    def handle_endtag(self, tag: str) -> None:
        if tag == 'dialog':
            self._dentro = False


def dialogos(html: str) -> list[NomeDeDialogo]:
    """Um `NomeDeDialogo` por `<dialog>` do documento, na ordem de emissão."""
    parser = _NomesDeDialogo()
    parser.feed(html)
    return parser.dialogos


def ids_duplicados(html: str) -> list[str]:
    """Os `id` que aparecem mais de uma vez, na ordem da primeira ocorrência."""
    return [id_ for id_, vezes in Counter(ids_do_documento(html)).items() if vezes > 1]


def assert_sem_id_duplicado(html: str) -> None:
    """Nenhum `id` aparece duas vezes: id repetido é HTML inválido e torna
    qualquer `getElementById` — logo, qualquer `aria-labelledby` — imprevisível.
    """
    duplicados = ids_duplicados(html)
    assert duplicados == [], f'ids repetidos no documento: {duplicados}'


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
