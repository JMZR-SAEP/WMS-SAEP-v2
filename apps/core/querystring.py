"""Forma canônica de querystring para telas de listagem filtrável.

Infraestrutura de apresentação pura (ADR-0011): não conhece domínio. A URL é a
fonte de verdade do recorte (issue #152), e "mesmo recorte lógico → mesma
querystring" só vale se a serialização for determinística. `canonicalizar`
aplica, nesta ordem:

1. remove chaves de valor vazio;
2. ordem fixa de chaves (`ordem_chaves`);
3. ordem fixa dentro de cada multi-valor.

Idempotência é contrato, não intenção: ``canonicalizar(canonicalizar(x)) ==
canonicalizar(x)``. Sem isso, o 302 do caminho nativo entra em loop de redirect.
"""

from __future__ import annotations

from collections.abc import Sequence

from django.http import HttpRequest
from django.http.request import QueryDict
from django.utils.http import urlencode


def canonicalizar(params: QueryDict, *, ordem_chaves: Sequence[str]) -> str:
    """Querystring canônica (sem o `?`) a partir de um QueryDict.

    `ordem_chaves` fixa a posição das chaves conhecidas; chaves fora da lista
    vêm depois, em ordem alfabética, para que o resultado siga determinístico
    mesmo se a tela ganhar um parâmetro que ninguém registrou aqui.
    """
    posicao = {chave: indice for indice, chave in enumerate(ordem_chaves)}

    def prioridade(chave: str) -> tuple[int, object]:
        return (0, posicao[chave]) if chave in posicao else (1, chave)

    itens: list[tuple[str, str]] = []
    for chave in sorted(params.keys(), key=prioridade):
        for valor in sorted(v for v in params.getlist(chave) if v != ''):
            itens.append((chave, valor))
    return urlencode(itens)


def caminho_canonico(request: HttpRequest, *, ordem_chaves: Sequence[str]) -> str:
    """`request.path` + querystring canônica (com `?` só quando há query)."""
    query = canonicalizar(request.GET, ordem_chaves=ordem_chaves)
    return f'{request.path}?{query}' if query else request.path


def querystring_ja_canonica(
    request: HttpRequest, *, ordem_chaves: Sequence[str]
) -> bool:
    """A query crua já está na forma canônica? (decide o 302 do caminho nativo)."""
    crua = request.META.get('QUERY_STRING', '')
    return crua == canonicalizar(request.GET, ordem_chaves=ordem_chaves)
