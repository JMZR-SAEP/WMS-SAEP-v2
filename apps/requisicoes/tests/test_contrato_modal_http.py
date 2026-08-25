"""Contrato HTTP das rotas de `action_url` de modal deste app (issue #130).

A parametrização vem de `REGISTRO_CONTRATO_MODAL`, não de uma lista local: uma
rota registrada sem construtora falha aqui, e uma rota usada num modal sem estar
registrada falha em `core/tests/test_contrato_modal.py`. Juntas, as duas pontas
fazem com que um modal novo não consiga nascer fora do contrato.

A carga de cada cenário busca o **ramo de erro** da rota — é onde as violações
desta issue viviam —, e todas as nove chegam lá. Quatro terminam em 422; as
outras cinco em 204 para o detalhe, com a transição recusada e mensagem. Como
essas cinco respondem o mesmo que o caminho feliz responderia, `muta=False` no
cenário faz o eixo HTMX conferir que nada foi gravado: sem isso elas seriam
tautológicas.

Nenhum cenário usa `RASCUNHO` para `autorizar`/`separar_retirada`, e não é
descuido: rascunho de terceiro não é visível ao selector desses atores, então a
resposta seria 404 — que não exercita o corpo do modal.

Uma resposta **2xx** que não seja o 204 do PRG é trocada dentro de
`[data-modal-body]` pelo `hx-swap="outerHTML"` do componente, e produz a imagem
que a issue descreve: sucesso e falha indistinguíveis, com a pessoa sem resposta
para se gravou ou não. O 422 também é trocado, mas por opt-in explícito do
`modal.js` (`htmx:beforeSwap`), e é por isso que ele serve de superfície de
erro. Já 403/404/5xx **não** são trocados por padrão no htmx 2 — viram no-op
silencioso, que é outro defeito e está registrado como tal em
`apps/core/tests/contrato_modal.py`.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.tests.contrato_modal import (
    REGISTRO_CONTRATO_MODAL,
    CenarioModal,
    assert_contrato_modal,
    assert_copy_nao_diverge,
    assert_fallback_sem_htmx,
    snapshot,
)
from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao


ROTAS = sorted(
    rota for rota, app in REGISTRO_CONTRATO_MODAL.items() if app == 'requisicoes'
)


def _requisicao(request, estado: str, *, com_item: bool = True) -> Requisicao:
    """Requisição no estado pedido, criada por ORM direto.

    Estado é `CharField`: montar por ORM em vez de percorrer a máquina de
    transições mantém o cenário mínimo, que é o que a ADR-0010 pede de teste de
    view. As transições em si são assunto de `test_services.py`.
    """
    solicitante = request.getfixturevalue('solicitante')
    setor_obras = request.getfixturevalue('setor_obras')
    requisicao = Requisicao.objects.create(
        estado=estado,
        numero_publico=(
            '' if estado == EstadoRequisicao.RASCUNHO else f'REQ-2026-{estado[:4]}'
        ),
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    if com_item:
        material = request.getfixturevalue('material_disponivel')
        ItemRequisicao.objects.create(
            requisicao=requisicao,
            material=material,
            quantidade_solicitada=Decimal('5'),
        )
    return requisicao


def _le_requisicao(pk: int):
    """Snapshot da requisição — `None` quando o registro deixou de existir.

    `filter(...).first()` e não `get(...)`: é forma defensiva exigida pelo
    contrato de `ler_estado`, porque o descarte de rascunho sem número público
    apaga a linha (`services/cancelamento.py`) e um `get` estouraria
    `DoesNotExist` em vez de comparar. Nenhum cenário deste arquivo percorre
    esse caminho hoje — `cancelar` usa ATENDIDA, e `_requisicao` grava
    `numero_publico=''`, enquanto o descarte exige `None`. A forma vale pelo
    contrato, não pelo cenário atual.
    """
    from apps.estoque.models import SaldoEstoque

    return (
        snapshot(Requisicao.objects, pk, 'estado', 'numero_publico'),
        sorted(
            SaldoEstoque.objects.values_list('pk', 'saldo_fisico', 'saldo_reservado')
        ),
    )


def _detalhe(pk: int) -> str:
    return reverse('requisicoes:detalhe', args=[pk])


def _cenario_estado_recusado(
    request,
    rota: str,
    estado: str,
    ator: str,
    modal_id: str,
    payload: dict | None = None,
    muta: bool = False,
) -> CenarioModal:
    """Rota chamada num estado dado, com o destino de 204 já declarado.

    Serve tanto às que erram por transição recusada quanto às duas que acabam no
    caminho feliz: nos dois casos a view responde 204 para o detalhe, e é o
    destino que o cenário declara.
    """
    requisicao = _requisicao(request, estado)
    return CenarioModal(
        url=reverse(rota, args=[requisicao.pk]),
        payload=payload or {},
        destino_esperado=_detalhe(requisicao.pk),
        ler_estado=lambda: _le_requisicao(requisicao.pk),
        ator=request.getfixturevalue(ator),
        modal_id=modal_id,
        muta=muta,
    )


def _cenario_autorizar(request) -> CenarioModal:
    """Requisição já atendida: a transição é recusada, nada muda.

    A policy de autorizar (`policies.py`, via `pode_recusar_requisicao`) só olha
    `setor_chefiado_ativo_id` e não lê o estado, então o estado errado chega ao
    service e vira erro de transição — não 403. Só `RASCUNHO` daria 404, por
    não ser visível ao chefe.
    """
    return _cenario_estado_recusado(
        request,
        'requisicoes:autorizar',
        EstadoRequisicao.ATENDIDA,
        'chefe_obras',
        modal_id='confirmar-autorizar',
    )


def _cenario_retornar_rascunho(request) -> CenarioModal:
    # Rascunho já é rascunho: a transição é recusada. O ator é o criador porque
    # a policy exige criador ou beneficiário — com outro ator a resposta seria
    # 403, que não diz nada sobre o contrato do corpo do modal.
    return _cenario_estado_recusado(
        request,
        'requisicoes:retornar_rascunho',
        EstadoRequisicao.RASCUNHO,
        'solicitante',
        modal_id='confirmar-retornar',
    )


def _cenario_separar_retirada(request) -> CenarioModal:
    # Mesmo raciocínio de `autorizar`: `pode_separar_para_retirada` só checa
    # papel, então o estado errado vira erro de transição no service. Rascunho
    # daria 404 (invisível ao almoxarifado), e por isso não serve de cenário.
    return _cenario_estado_recusado(
        request,
        'requisicoes:separar_retirada',
        EstadoRequisicao.ATENDIDA,
        'aux_almoxarifado',
        modal_id='confirmar-separar',
    )


def _cenario_enviar_rascunho(request) -> CenarioModal:
    # Rascunho sem item nenhum. Não é recusa de transição: a transição é
    # válida, e `enviar_para_autorizacao` levanta `DadosInvalidos(sem_itens)`
    # depois dela.
    requisicao = _requisicao(request, EstadoRequisicao.RASCUNHO, com_item=False)
    return CenarioModal(
        url=reverse('requisicoes:enviar_rascunho', args=[requisicao.pk]),
        payload={},
        destino_esperado=_detalhe(requisicao.pk),
        ler_estado=lambda: _le_requisicao(requisicao.pk),
        ator=request.getfixturevalue('solicitante'),
        modal_id='confirmar-enviar',
    )


def _cenario_cancelar(request) -> CenarioModal:
    # Requisição já encerrada não é cancelável.
    return _cenario_estado_recusado(
        request,
        'requisicoes:cancelar',
        EstadoRequisicao.ATENDIDA,
        'solicitante',
        modal_id='confirmar-cancelar',
        payload={'justificativa': 'Motivo.'},
    )


def _cenario_recusar(request) -> CenarioModal:
    """Motivo vazio numa requisição recusável: `DadosInvalidos` → 422."""
    requisicao = _requisicao(request, EstadoRequisicao.AGUARDANDO_AUTORIZACAO)
    return CenarioModal(
        url=reverse('requisicoes:recusar', args=[requisicao.pk]),
        payload={'motivo': ''},
        destino_esperado=None,
        ler_estado=lambda: _le_requisicao(requisicao.pk),
        ator=request.getfixturevalue('chefe_obras'),
        modal_id='confirmar-recusar',
        url_render_inicial=_detalhe(requisicao.pk),
    )


def _cenario_estornar(request) -> CenarioModal:
    """Justificativa vazia: Form inválido → 422 com o texto vindo do Form."""
    requisicao = _requisicao(request, EstadoRequisicao.ATENDIDA)
    return CenarioModal(
        url=reverse('requisicoes:estornar', args=[requisicao.pk]),
        payload={'justificativa': ''},
        destino_esperado=None,
        ler_estado=lambda: _le_requisicao(requisicao.pk),
        ator=request.getfixturevalue('chefe_almoxarifado'),
        modal_id='estornar-modal',
        url_render_inicial=_detalhe(requisicao.pk),
    )


def _cenario_registrar_devolucao(request) -> CenarioModal:
    """Quantidade vazia: Form inválido → 422.

    Sem `url_render_inicial`: a requisição desta fábrica não tem entregue
    líquida registrada, então o item não entra em `itens_devolviveis` e o
    modal não aparece no detalhe — comparar seria falso positivo de
    divergência. A cobertura de copy deste modal fica em
    `test_registrar_devolucao_copy_do_422_nao_diverge_do_render_inicial`
    (`test_views.py`), que usa `req_atendida_view`.
    """
    requisicao = _requisicao(request, EstadoRequisicao.ATENDIDA)
    item = requisicao.itens.first()
    return CenarioModal(
        url=reverse(
            'requisicoes:registrar_devolucao',
            kwargs={'pk': requisicao.pk, 'item_pk': item.pk},
        ),
        payload={'quantidade': ''},
        destino_esperado=None,
        ler_estado=lambda: _le_requisicao(requisicao.pk),
        ator=request.getfixturevalue('aux_almoxarifado'),
        modal_id=f'devolver-{item.pk}',
    )


def _cenario_confirmar_importacao_scpi(request) -> CenarioModal:
    """Sem pré-visualização na sessão — o pior caso descrito na issue.

    A sessão está vazia desde o início; o caminho realista que produz isso é a
    segunda tentativa, depois de a primeira ter consumido o preview. O
    encadeamento das duas está em `estoque/tests/test_views.py`
    (`test_htmx_hash_duplicado_devolve_422`).
    """
    from apps.estoque.models import ImportacaoSCPI

    request.getfixturevalue('estoque_principal')
    return CenarioModal(
        url=reverse('requisicoes:confirmar_importacao_scpi'),
        payload={},
        destino_esperado=None,
        ler_estado=lambda: ImportacaoSCPI.objects.count(),
        ator=request.getfixturevalue('superuser'),
        modal_id='confirmar-importacao-scpi',
    )


CONSTRUTORAS = {
    'requisicoes:autorizar': _cenario_autorizar,
    'requisicoes:cancelar': _cenario_cancelar,
    'requisicoes:confirmar_importacao_scpi': _cenario_confirmar_importacao_scpi,
    'requisicoes:enviar_rascunho': _cenario_enviar_rascunho,
    'requisicoes:estornar': _cenario_estornar,
    'requisicoes:recusar': _cenario_recusar,
    'requisicoes:registrar_devolucao': _cenario_registrar_devolucao,
    'requisicoes:retornar_rascunho': _cenario_retornar_rascunho,
    'requisicoes:separar_retirada': _cenario_separar_retirada,
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
    if resposta.status_code == 422 and cenario.url_render_inicial:
        inicial = client.get(cenario.url_render_inicial)
        assert_copy_nao_diverge(
            resposta,
            html_inicial=inicial.content.decode('utf-8'),
            modal_id=cenario.modal_id,
        )
    if not cenario.muta:
        # `cancelar` em ATENDIDA, `retornar_rascunho` em RASCUNHO e
        # `enviar_rascunho` sem item respondem 204 para o detalhe — igual ao
        # caminho feliz. Sem esta linha, os três seguiriam verdes se a
        # transição que deviam recusar passasse a acontecer.
        assert cenario.ler_estado() == antes, (
            f'{rota}: cenário declarado como sem mutação, mas o estado mudou.'
        )


@pytest.mark.parametrize('rota', ROTAS)
def test_anonimo_vai_para_o_login_sem_mutar_nada(db, request, client, rota):
    cenario = _cenario(request, rota)
    antes = cenario.ler_estado()

    resposta = client.post(cenario.url, cenario.payload)

    assert resposta.status_code == 302
    assert resposta['Location'] == f'{reverse("accounts:login")}?next={cenario.url}'
    # 302 para o login com a mutação já gravada seria o pior resultado possível,
    # e é a metade do contrato que o status não cobre.
    assert cenario.ler_estado() == antes


@pytest.mark.parametrize('rota', ROTAS)
def test_resposta_sem_htmx_nao_e_204_nem_hx_redirect(db, request, client, rota):
    cenario = _cenario(request, rota)
    client.force_login(cenario.ator)
    resposta = client.post(cenario.url, cenario.payload)
    assert_fallback_sem_htmx(resposta)
