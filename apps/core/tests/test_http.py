"""Testes unitários dos helpers HTTP/HTMX de apps/core/http.py."""

from datetime import date

import pytest
from django.http import QueryDict
from django.test import RequestFactory

from apps.core.http import htmx_redirect, parse_data_iso, querystring_sem_page

pytestmark = pytest.mark.django_db


def _htmx_request(factory, method='post', path='/qualquer/'):
    request = getattr(factory, method)(path, HTTP_HX_REQUEST='true')
    return request


def _requisicao_normal(factory, method='post', path='/qualquer/'):
    return getattr(factory, method)(path)


class TestHtmxRedirect:
    def test_requisicao_htmx_retorna_204_com_header_hx_redirect(self):
        factory = RequestFactory()
        request = _htmx_request(factory)
        request.htmx = True

        resposta = htmx_redirect(request, '/destino/')

        assert resposta.status_code == 204
        assert resposta['HX-Redirect'] == '/destino/'

    def test_requisicao_normal_retorna_302_com_location(self):
        factory = RequestFactory()
        request = _requisicao_normal(factory)
        request.htmx = False

        resposta = htmx_redirect(request, '/destino/')

        assert resposta.status_code == 302
        assert resposta['Location'] == '/destino/'


class TestParseDataIso:
    def test_string_iso_valida_retorna_date(self):
        assert parse_data_iso('2026-07-08') == date(2026, 7, 8)

    def test_none_retorna_none(self):
        assert parse_data_iso(None) is None

    def test_string_vazia_retorna_none(self):
        assert parse_data_iso('') is None

    def test_string_invalida_retorna_none(self):
        assert parse_data_iso('não-é-data') is None


class TestQuerystringSemPage:
    def test_remove_page_preservando_outros_params(self):
        params = QueryDict('page=2&material=parafuso&ordem=asc')

        resultado = querystring_sem_page(params)

        assert 'page' not in resultado
        assert 'material=parafuso' in resultado
        assert 'ordem=asc' in resultado

    def test_sem_page_e_idempotente(self):
        params = QueryDict('material=parafuso')

        resultado = querystring_sem_page(params)

        assert resultado == 'material=parafuso'
