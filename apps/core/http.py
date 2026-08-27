"""Helpers HTTP/HTMX de infraestrutura, compartilhados entre apps.

Não importa models/services de domínio (ADR-0011): esta é uma camada de
infraestrutura HTTP pura.
"""

from __future__ import annotations

from datetime import date

from django.http import HttpRequest, HttpResponse
from django.http.request import QueryDict
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django_htmx.middleware import HtmxDetails


class HtmxHttpRequest(HttpRequest):
    """HttpRequest com `.htmx` tipado (populado em runtime por `HtmxMiddleware`)."""

    htmx: HtmxDetails


def htmx_redirect(request: HtmxHttpRequest, url: str) -> HttpResponse:
    """PRG para HTMX: 204 + `HX-Redirect` em requisições HTMX; `redirect()` normal caso contrário.

    Não delega em `django_htmx.http.HttpResponseClientRedirect`: esse helper
    responde com status 200, o que quebraria o contrato 204 já documentado
    para o fluxo PRG deste projeto.
    """
    if request.htmx:
        response = HttpResponse(status=204)
        response['HX-Redirect'] = url
        return response
    return redirect(url)


def parse_data_iso(valor: str | None) -> date | None:
    """Converte 'YYYY-MM-DD' em date; entrada inválida/vazia → None (no-op)."""
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def voltar_url_seguro(request: HttpRequest, *, default: str) -> str:
    """Destino de 'Voltar': o `next` recebido (POST tem prioridade sobre GET) se
    for uma URL local segura; caso contrário, `default`.

    Mesma checagem de open redirect que o `LoginView` do Django faz — o `next`
    vem da querystring do link de origem e não pode ser confiado às cegas.
    """
    candidato = request.POST.get('next') or request.GET.get('next', '')
    if candidato and url_has_allowed_host_and_scheme(
        candidato,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidato
    return default


def querystring_sem_page(get_params: QueryDict) -> str:
    """Querystring atual sem o parâmetro `page`, para preservar filtros na
    paginação (links e swap HTMX)."""
    params = get_params.copy()
    params.pop('page', None)
    return params.urlencode()
