"""Contrato HTTP das rotas de `action_url` de modal deste app (issue #130).

A parametrização vem de `REGISTRO_CONTRATO_MODAL`, não de uma lista local: uma
rota registrada sem construtora falha aqui, e uma rota usada num modal sem estar
registrada falha em `core/tests/test_contrato_modal.py`. Juntas, as duas pontas
fazem com que um modal novo não consiga nascer fora do contrato.
"""

import pytest
from django.urls import reverse

from apps.core.tests.contrato_modal import (
    REGISTRO_CONTRATO_MODAL,
    CenarioModal,
    assert_contrato_modal,
    assert_fallback_sem_htmx,
    snapshot,
)


ROTAS = sorted(
    rota for rota, app in REGISTRO_CONTRATO_MODAL.items() if app == 'estoque'
)


def _cenario_estornar_saida(request) -> CenarioModal:
    """Justificativa vazia: o service recusa, e o modal tem de continuar de pé.

    A carga exercita o ramo de erro de propósito — é o ramo onde as violações
    desta issue viviam. O caminho feliz tem teste próprio em `test_views.py`.
    """
    from apps.estoque.models import SaidaExcepcional, SaldoEstoque

    chefe = request.getfixturevalue('chefe_almoxarifado')
    saida = request.getfixturevalue('saida_registrada')

    def ler_estado():
        return (
            snapshot(SaidaExcepcional.objects, saida.pk, 'estado', 'estornado_em'),
            sorted(SaldoEstoque.objects.values_list('pk', 'saldo_fisico')),
        )

    return CenarioModal(
        url=reverse('estoque:estornar_saida_excepcional', args=[saida.pk]),
        payload={'justificativa': ''},
        destino_esperado=None,
        ler_estado=ler_estado,
        ator=chefe,
        modal_id='estornar-saida',
        muta=False,
    )


CONSTRUTORAS = {
    'estoque:estornar_saida_excepcional': _cenario_estornar_saida,
}


def _cenario(request, rota: str) -> CenarioModal:
    construtora = CONSTRUTORAS.get(rota)
    if construtora is None:
        pytest.fail(
            f'{rota} está em REGISTRO_CONTRATO_MODAL como rota deste app, mas não '
            'tem construtora de cenário aqui. Registrar a rota sem escrever o '
            'cenário deixaria o contrato dela sem prova nenhuma.'
        )
    return construtora(request)


@pytest.mark.parametrize('rota', ROTAS)
def test_resposta_htmx_cabe_na_caixa_do_modal(db, request, client, rota):
    cenario = _cenario(request, rota)
    client.force_login(cenario.ator)
    antes = cenario.ler_estado()
    resposta = client.post(cenario.url, cenario.payload, HTTP_HX_REQUEST='true')
    assert_contrato_modal(
        resposta,
        destino_esperado=cenario.destino_esperado,
        modal_id=cenario.modal_id,
    )
    if not cenario.muta:
        # Sem isto, um cenário de erro e um de caminho feliz asseveram a mesma
        # resposta e nada distingue os dois.
        assert cenario.ler_estado() == antes, (
            f'{rota}: cenário declarado como sem mutação, mas o estado mudou.'
        )


@pytest.mark.parametrize('rota', ROTAS)
def test_anonimo_vai_para_o_login_sem_mutar_nada(db, request, client, rota):
    cenario = _cenario(request, rota)
    antes = cenario.ler_estado()

    resposta = client.post(cenario.url, cenario.payload)

    assert resposta.status_code == 302
    assert resposta['Location'] == (f'{reverse("accounts:login")}?next={cenario.url}')
    # 302 para o login com a mutação já gravada seria o pior resultado possível,
    # e é a metade do contrato que o status não cobre.
    assert cenario.ler_estado() == antes


@pytest.mark.parametrize('rota', ROTAS)
def test_resposta_sem_htmx_nao_e_204_nem_hx_redirect(db, request, client, rota):
    cenario = _cenario(request, rota)
    client.force_login(cenario.ator)
    resposta = client.post(cenario.url, cenario.payload)
    assert_fallback_sem_htmx(resposta)
