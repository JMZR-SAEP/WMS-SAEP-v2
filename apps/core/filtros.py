"""Atalhos de recorte sobre a querystring canônica (issue #153).

Infraestrutura de apresentação pura (ADR-0011): não conhece domínio. A view
descreve cada atalho — rótulo, chave multivalor, valores — e este módulo
resolve a URL canônica de ligar/desligar reaproveitando
`apps.core.querystring` (issue #152). Nenhum chip ou preset remonta
querystring à mão: "mesmo recorte lógico → mesma querystring" continua valendo.

Dois usos do mesmo mecanismo (link → querystring canônica → reemite OOB):

- **chips** (`montar_chip`): recorte nomeado sobre uma chave multivalor
  (`estados`, `tipos`). Ligar substitui os valores da chave pelos do chip;
  desligar remove **só** os valores do chip, preservando outros que a pessoa
  já tivesse marcado (regressão #143).
- **presets de período** (`montar_presets_periodo`): atalho de digitação que
  preenche `data_ini`/`data_fim` com datas **absolutas**. Nenhum estado novo
  na querystring — token relativo (`?periodo=30d`) foi descartado (#148/#153).
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from datetime import timedelta

from django.http import HttpRequest
from django.utils import timezone

from apps.core.querystring import canonicalizar


@dataclass(frozen=True)
class ChipFiltro:
    """Chip de recorte já resolvido para a UI (acima dos resultados)."""

    id: str
    rotulo: str
    glifo: str
    ativo: bool
    url: str


@dataclass(frozen=True)
class PresetPeriodo:
    """Preset de período já resolvido para a UI (colado ao par De/Até)."""

    id: str
    rotulo: str
    ativo: bool
    url: str


def _url_canonica(
    request: HttpRequest,
    params,
    *,
    ordem_chaves: Sequence[str],
    chaves_multivalor: Collection[str],
) -> str:
    query = canonicalizar(
        params, ordem_chaves=ordem_chaves, chaves_multivalor=chaves_multivalor
    )
    return f'{request.path}?{query}' if query else request.path


def montar_chip(
    request: HttpRequest,
    *,
    id: str,
    rotulo: str,
    chave: str,
    valores: Iterable[str],
    ordem_chaves: Sequence[str],
    chaves_multivalor: Collection[str],
    glifo: str = '',
) -> ChipFiltro:
    """Chip que liga/desliga um recorte nomeado sobre uma chave multivalor.

    `ativo` quando todos os valores do chip já estão selecionados na chave. A
    URL aponta para o estado oposto e sempre preserva o resto da seleção
    (regressão #143):

    - ativo → desligar: remove **só** os valores do chip;
    - inativo → ligar: acrescenta os valores do chip aos já marcados.
    """
    alvo = sorted({str(v) for v in valores})
    alvo_set = set(alvo)
    selecionados = [v for v in request.GET.getlist(chave) if v]
    sel_set = set(selecionados)
    ativo = bool(alvo_set) and alvo_set.issubset(sel_set)

    params = request.GET.copy()
    params.pop('page', None)
    if ativo:
        params.setlist(chave, [v for v in selecionados if v not in alvo_set])
    else:
        params.setlist(chave, selecionados + [v for v in alvo if v not in sel_set])

    return ChipFiltro(
        id=id,
        rotulo=rotulo,
        glifo=glifo,
        ativo=ativo,
        url=_url_canonica(
            request,
            params,
            ordem_chaves=ordem_chaves,
            chaves_multivalor=chaves_multivalor,
        ),
    )


def montar_presets_periodo(
    request: HttpRequest,
    *,
    ordem_chaves: Sequence[str],
    chaves_multivalor: Collection[str],
) -> list[PresetPeriodo]:
    """Três presets — 7 dias, 30 dias, este mês — sobre `data_ini`/`data_fim`.

    Cada preset resolve para uma janela de datas absolutas terminando hoje e
    preenche os dois campos. `ativo` quando a URL já mostra exatamente essa
    janela.
    """
    hoje = timezone.localdate()
    fim = hoje.isoformat()
    definicoes = (
        ('7d', 'Últimos 7 dias', hoje - timedelta(days=6)),
        ('30d', 'Últimos 30 dias', hoje - timedelta(days=29)),
        ('mes', 'Este mês', hoje.replace(day=1)),
    )

    presets: list[PresetPeriodo] = []
    for id_, rotulo, inicio in definicoes:
        ini = inicio.isoformat()
        params = request.GET.copy()
        params.pop('page', None)
        params['data_ini'] = ini
        params['data_fim'] = fim
        ativo = (
            request.GET.get('data_ini') == ini and request.GET.get('data_fim') == fim
        )
        presets.append(
            PresetPeriodo(
                id=id_,
                rotulo=rotulo,
                ativo=ativo,
                url=_url_canonica(
                    request,
                    params,
                    ordem_chaves=ordem_chaves,
                    chaves_multivalor=chaves_multivalor,
                ),
            )
        )
    return presets
