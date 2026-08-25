"""`submeterFormExterno` — camada Navegador (ADR-0019), issue #137.

A expressão que vivia em `_modal_body.html` — `getElementById(...)?.
requestSubmit() ?? console.error(...)` — disparava o `console.error` sempre,
porque `requestSubmit()` devolve `undefined` e `undefined ?? X` avalia `X`.
Provar que o `console.error` só dispara quando o `<form>` de verdade não
existe depende de console real do navegador, que nenhuma lane de baixo
observa — daí a camada Navegador.

`confirmar-atender-retirada` é o único consumidor real do modo
`submit_form_id`, e o `<dialog>` fica dentro do `<form>` que ele confirma —
por isso o teste segura uma referência ao controller Alpine antes de remover
o form, em vez de reabrir o modal depois.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.tests.navegador import autenticar
from apps.estoque.models import SaldoEstoque
from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

pytestmark = pytest.mark.navegador


@pytest.fixture
def req_pronta_para_atender(db, solicitante, setor_obras, material_disponivel):
    """Requisição pronta para retirada — a tela de `confirmar-atender-retirada`."""
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.PRONTA_PARA_RETIRADA,
        numero_publico='REQ-2026-9360',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req,
        material=material_disponivel,
        quantidade_solicitada=Decimal('2'),
        quantidade_autorizada=Decimal('2'),
    )
    saldo = SaldoEstoque.objects.get(material=material_disponivel)
    saldo.saldo_reservado = (saldo.saldo_reservado or Decimal('0')) + Decimal('2')
    saldo.save(update_fields=['saldo_reservado'])
    return req


@pytest.fixture
def pagina_de_atendimento(
    live_server, context, page, aux_almoxarifado, req_pronta_para_atender
):
    """Página de atendimento autenticada, com o POST clássico bloqueado.

    O modo `submit_form_id` é POST clássico (`atender_retirada.html` não usa
    htmx) — deixar a navegação acontecer de verdade destruiria o contexto de
    execução antes da segunda parte do teste. Interceptar a rede
    (`route().abort()`) não basta: o navegador navega (e falha) de qualquer
    jeito, o que também destrói o contexto. `requestSubmit()` — ao contrário
    do `.submit()` legado — dispara o evento `submit` e respeita
    `preventDefault()`, e é isso que barra a navegação de verdade.
    """
    autenticar(live_server, context, aux_almoxarifado)
    url = reverse(
        'requisicoes:registrar_atendimento', kwargs={'pk': req_pronta_para_atender.pk}
    )
    page.goto(f'{live_server.url}{url}')
    page.evaluate(
        '() => { window.__submits = 0;'
        " document.getElementById('form-atender-retirada').addEventListener("
        " 'submit', (e) => { e.preventDefault(); window.__submits += 1; }); }"
    )
    return page


def test_submit_form_id_so_loga_console_error_quando_o_form_nao_existe(
    pagina_de_atendimento,
):
    page = pagina_de_atendimento
    mensagens_erro = []
    page.on(
        'console',
        lambda msg: mensagens_erro.append(msg.text) if msg.type == 'error' else None,
    )

    # A referência ao controller é capturada ANTES de remover o form: o
    # `<dialog>` fica dentro dele, e removê-lo tira os dois do documento — mas
    # o objeto reativo do Alpine continua vivo em `window.__ctrl`.
    page.evaluate(
        '() => { window.__ctrl = Alpine.$data('
        "document.getElementById('confirmar-atender-retirada').closest('[x-data]')); }"
    )

    # Form existe: submete (a navegação real morre no `route().abort()`) e
    # não loga nada.
    page.evaluate(
        "() => window.__ctrl.submeterFormExterno('form-atender-retirada', null)"
    )
    assert mensagens_erro == [], (
        f'console.error inesperado com o form presente: {mensagens_erro}'
    )

    # A trava de duplo envio não se desfaz sozinha — em produção não precisa:
    # a chamada real navega e a página é descartada. Aqui, onde a navegação
    # foi barrada de propósito para o teste continuar, resetá-la simula uma
    # segunda tentativa em vez da mesma tentativa repetida.
    page.evaluate('() => { window.__ctrl.submeterFormExternoEmVoo = false; }')

    # Form não existe: loga uma vez, com a mensagem que distingue os dois casos.
    page.evaluate("() => document.getElementById('form-atender-retirada').remove()")
    page.evaluate(
        "() => window.__ctrl.submeterFormExterno('form-atender-retirada', null)"
    )
    assert mensagens_erro == [
        'modal confirmar-atender-retirada: submit_form_id form-atender-retirada nao encontrado'
    ]


def test_submit_form_id_bloqueia_segundo_clique_antes_da_resposta(
    pagina_de_atendimento,
):
    """Bloqueio de duplo envio próprio do modo, não herdado do form externo (#137).

    `form-atender-retirada` tem `data-prevent-double-submit` por acaso — é o
    template quem escreveu o atributo, não um contrato que o componente
    garanta. `submeterFormExterno` trava por conta própria: um segundo clique
    antes do primeiro `requestSubmit()` "terminar" (aqui, antes do teste
    liberar a trava) não pode gerar uma segunda tentativa.
    """
    page = pagina_de_atendimento
    page.evaluate(
        '() => { window.__ctrl = Alpine.$data('
        "document.getElementById('confirmar-atender-retirada').closest('[x-data]')); }"
    )

    submits = page.evaluate(
        "() => { window.__ctrl.submeterFormExterno('form-atender-retirada', null);"
        " window.__ctrl.submeterFormExterno('form-atender-retirada', null);"
        ' return window.__submits; }'
    )

    assert submits == 1, f'Duas tentativas de envio chegaram ao form: {submits}'
