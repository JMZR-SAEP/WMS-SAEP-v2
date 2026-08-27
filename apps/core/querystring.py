"""Forma canônica de querystring para telas de listagem filtrável.

Infraestrutura de apresentação pura (ADR-0011): não conhece domínio. A URL é a
fonte de verdade do recorte (issue #152), e "mesmo recorte lógico → mesma
querystring" só vale se a serialização for determinística. `canonicalizar`
aplica, nesta ordem:

1. remove chaves de valor vazio;
2. ordem fixa de chaves (`ordem_chaves`);
3. dentro de uma chave de multi-valor (`chaves_multivalor`), ordena e deduplica
   os valores; nas demais chaves, colapsa para o último valor — que é o que
   `QueryDict.get()` devolve, e portanto o que a view de fato lê. Ordenar os
   valores de uma chave única inverteria a semântica (`texto=z&texto=a` lê `a`,
   mas `a&z` passaria a ler `z` depois do redirect).

Idempotência é contrato, não intenção: ``canonicalizar(canonicalizar(x)) ==
canonicalizar(x)``. Sem isso, o 302 do caminho nativo entra em loop de redirect.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence

from django.http import HttpRequest
from django.http.request import QueryDict
from django.utils.http import urlencode


def canonicalizar(
    params: QueryDict,
    *,
    ordem_chaves: Sequence[str],
    chaves_multivalor: Collection[str] = (),
) -> str:
    """Querystring canônica (sem o `?`) a partir de um QueryDict.

    `ordem_chaves` fixa a posição das chaves conhecidas; chaves fora da lista
    vêm depois, em ordem alfabética, para que o resultado siga determinístico
    mesmo se a tela ganhar um parâmetro que ninguém registrou aqui.

    `chaves_multivalor` são as chaves cuja repetição é intencional (ex.:
    `estados`, `tipos`): seus valores são ordenados e deduplicados. Qualquer
    outra chave é colapsada para o último valor recebido.
    """
    posicao = {chave: indice for indice, chave in enumerate(ordem_chaves)}
    multivalor = set(chaves_multivalor)

    def prioridade(chave: str) -> tuple[int, object]:
        return (0, posicao[chave]) if chave in posicao else (1, chave)

    itens: list[tuple[str, str]] = []
    for chave in sorted(params.keys(), key=prioridade):
        valores = params.getlist(chave)
        if chave in multivalor:
            selecionados: list[str] = sorted({v for v in valores if v != ''})
        else:
            ultimo = valores[-1] if valores else ''
            selecionados = [ultimo] if ultimo != '' else []
        itens.extend((chave, valor) for valor in selecionados)
    return urlencode(itens)


def caminho_canonico(
    request: HttpRequest,
    *,
    ordem_chaves: Sequence[str],
    chaves_multivalor: Collection[str] = (),
) -> str:
    """`request.path` + querystring canônica (com `?` só quando há query)."""
    query = canonicalizar(
        request.GET, ordem_chaves=ordem_chaves, chaves_multivalor=chaves_multivalor
    )
    return f'{request.path}?{query}' if query else request.path


def querystring_ja_canonica(
    request: HttpRequest,
    *,
    ordem_chaves: Sequence[str],
    chaves_multivalor: Collection[str] = (),
) -> bool:
    """A query crua já está na forma canônica? (decide o 302 do caminho nativo)."""
    crua = request.META.get('QUERY_STRING', '')
    return crua == canonicalizar(
        request.GET, ordem_chaves=ordem_chaves, chaves_multivalor=chaves_multivalor
    )
