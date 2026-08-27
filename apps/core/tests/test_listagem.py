import pytest
from django.http import QueryDict
from django.test import RequestFactory

from apps.accounts.models import VinculoAuxiliar
from apps.core.listagem import paginar_com_filtros
from apps.core.querystring import (
    caminho_canonico,
    canonicalizar,
    querystring_ja_canonica,
)

pytestmark = pytest.mark.django_db

# Ordem canônica de referência (espelha as das views de histórico).
_ORDEM = ('texto', 'estados', 'data_ini', 'data_fim', 'setor', 'ordem', 'page')


def _qd(qs: str) -> QueryDict:
    return QueryDict(qs)


class TestCanonicalizarQuerystring:
    def test_remove_chaves_vazias(self):
        qs = canonicalizar(
            _qd('texto=Obras&data_ini=&data_fim=&setor='), ordem_chaves=_ORDEM
        )
        assert qs == 'texto=Obras'

    def test_ordem_fixa_de_chaves(self):
        qs = canonicalizar(_qd('setor=3&ordem=asc&texto=Obras'), ordem_chaves=_ORDEM)
        assert qs == 'texto=Obras&setor=3&ordem=asc'

    def test_ordem_fixa_dentro_do_multivalor(self):
        a = canonicalizar(_qd('estados=rascunho&estados=atendida'), ordem_chaves=_ORDEM)
        b = canonicalizar(_qd('estados=atendida&estados=rascunho'), ordem_chaves=_ORDEM)
        assert a == b == 'estados=atendida&estados=rascunho'

    def test_chave_desconhecida_vai_para_o_fim_em_ordem_alfabetica(self):
        qs = canonicalizar(_qd('zzz=1&texto=x&aaa=2'), ordem_chaves=_ORDEM)
        assert qs == 'texto=x&aaa=2&zzz=1'

    def test_mesmo_recorte_do_form_e_do_link_produz_a_mesma_querystring(self):
        do_form = canonicalizar(
            _qd('texto=Obras&data_ini=&data_fim=&setor=&estados=rascunho'),
            ordem_chaves=_ORDEM,
        )
        do_link = canonicalizar(
            _qd('estados=rascunho&texto=Obras'), ordem_chaves=_ORDEM
        )
        assert do_form == do_link

    @pytest.mark.parametrize(
        'bruto',
        [
            '',
            'texto=Obras&data_ini=&estados=rascunho&estados=atendida',
            'ordem=asc&page=2&setor=1&texto=a+b',
            'zzz=9&estados=b&estados=a&texto=&x=1',
        ],
    )
    def test_idempotencia(self, bruto):
        """`canonicalizar(canonicalizar(x)) == canonicalizar(x)` — sem loop de 302."""
        uma = canonicalizar(_qd(bruto), ordem_chaves=_ORDEM)
        duas = canonicalizar(_qd(uma), ordem_chaves=_ORDEM)
        assert uma == duas


class TestCaminhoCanonico:
    def test_sem_query_quando_tudo_vazio(self):
        request = RequestFactory().get('/historico/?texto=&setor=')
        assert caminho_canonico(request, ordem_chaves=_ORDEM) == '/historico/'

    def test_querystring_ja_canonica_distingue_forma_suja_da_limpa(self):
        suja = RequestFactory().get('/h/?data_ini=&texto=Obras')
        limpa = RequestFactory().get('/h/?texto=Obras')
        assert not querystring_ja_canonica(suja, ordem_chaves=_ORDEM)
        assert querystring_ja_canonica(limpa, ordem_chaves=_ORDEM)


def _request(factory, params='', htmx=False):
    request = factory.get(f'/qualquer/?{params}')
    request.htmx = htmx
    return request


class TestPaginarComFiltrosOrdenacao:
    def test_ordem_default_desc_quando_ausente(self, setor_comum, solicitante):
        primeiro = VinculoAuxiliar.objects.create(
            usuario=solicitante, setor=setor_comum
        )
        segundo = VinculoAuxiliar.objects.create(
            usuario=solicitante, setor=setor_comum, ativo=False
        )

        request = _request(RequestFactory())
        resultado = paginar_com_filtros(
            request, VinculoAuxiliar.objects.all(), per_page=25
        )

        assert resultado.ordem == 'desc'
        assert list(resultado.page_obj.object_list) == [segundo, primeiro]

    def test_ordem_asc_inverte_cronologia(self, setor_comum, solicitante):
        primeiro = VinculoAuxiliar.objects.create(
            usuario=solicitante, setor=setor_comum
        )
        segundo = VinculoAuxiliar.objects.create(
            usuario=solicitante, setor=setor_comum, ativo=False
        )

        request = _request(RequestFactory(), params='ordem=asc')
        resultado = paginar_com_filtros(
            request, VinculoAuxiliar.objects.all(), per_page=25
        )

        assert resultado.ordem == 'asc'
        assert list(resultado.page_obj.object_list) == [primeiro, segundo]

    def test_ordem_invalida_cai_no_default_desc(self, setor_comum, solicitante):
        primeiro = VinculoAuxiliar.objects.create(
            usuario=solicitante, setor=setor_comum
        )
        segundo = VinculoAuxiliar.objects.create(
            usuario=solicitante, setor=setor_comum, ativo=False
        )

        request = _request(RequestFactory(), params='ordem=lixo')
        resultado = paginar_com_filtros(
            request, VinculoAuxiliar.objects.all(), per_page=25
        )

        assert resultado.ordem == 'desc'
        assert list(resultado.page_obj.object_list) == [segundo, primeiro]


class TestPaginarComFiltrosMetadados:
    def test_url_ordenacao_inverte_ordem_e_preserva_outros_params_removendo_page(
        self, setor_comum, solicitante
    ):
        VinculoAuxiliar.objects.create(usuario=solicitante, setor=setor_comum)

        request = _request(RequestFactory(), params='material=parafuso&page=2')
        resultado = paginar_com_filtros(
            request, VinculoAuxiliar.objects.all(), per_page=25
        )

        assert 'page' not in resultado.url_ordenacao
        assert 'material=parafuso' in resultado.url_ordenacao
        assert 'ordem=asc' in resultado.url_ordenacao

    def test_is_htmx_reflete_request_htmx(self, setor_comum, solicitante):
        VinculoAuxiliar.objects.create(usuario=solicitante, setor=setor_comum)

        request_htmx = _request(RequestFactory(), htmx=True)
        request_normal = _request(RequestFactory(), htmx=False)

        resultado_htmx = paginar_com_filtros(
            request_htmx, VinculoAuxiliar.objects.all(), per_page=25
        )
        resultado_normal = paginar_com_filtros(
            request_normal, VinculoAuxiliar.objects.all(), per_page=25
        )

        assert resultado_htmx.is_htmx is True
        assert resultado_normal.is_htmx is False

    def test_querystring_filtros_remove_page(self, setor_comum, solicitante):
        VinculoAuxiliar.objects.create(usuario=solicitante, setor=setor_comum)

        request = _request(RequestFactory(), params='material=parafuso&page=2')
        resultado = paginar_com_filtros(
            request, VinculoAuxiliar.objects.all(), per_page=25
        )

        assert 'page' not in resultado.querystring_filtros
        assert 'material=parafuso' in resultado.querystring_filtros

    def test_page_obj_pagina_com_per_page_customizado(self, setor_comum, solicitante):
        for _ in range(3):
            VinculoAuxiliar.objects.create(
                usuario=solicitante, setor=setor_comum, ativo=False
            )

        request = _request(RequestFactory())
        resultado = paginar_com_filtros(
            request, VinculoAuxiliar.objects.all(), per_page=2
        )

        assert resultado.page_obj.paginator.count == 3
        assert len(resultado.page_obj.object_list) == 2
        assert resultado.page_obj.has_next() is True
