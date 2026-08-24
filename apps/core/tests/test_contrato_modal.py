"""Guarda estática do contrato de `action_url` de modal (issue #130).

Sem DB e sem view: aqui só se pergunta *quais* rotas estão na posição de
`action_url`. Se a resposta de cada uma cabe na caixa do modal é pergunta dos
`test_contrato_modal_http.py` de cada app, onde as fixtures existem.
"""

import pytest

from apps.core.tests.contrato_modal import (
    REGISTRO_CONTRATO_MODAL,
    rotas_de_modal,
    rotas_do_texto,
)


def test_toda_action_url_de_modal_esta_registrada():
    """Modal novo apontando para rota não registrada quebra aqui.

    É a primeira das duas pontas do critério 6 da issue: registrar a rota
    obriga a escrever o cenário HTTP (o teste do app falha sem ele), e não
    registrar a rota falha neste teste. Um modal só nasce dentro do contrato.
    """
    varridas = rotas_de_modal()
    registradas = set(REGISTRO_CONTRATO_MODAL)

    novas = varridas - registradas
    assert not novas, (
        f'Rotas usadas como action_url de modal e não registradas: {sorted(novas)}. '
        'Acrescente cada uma a REGISTRO_CONTRATO_MODAL e escreva o cenário no '
        'test_contrato_modal_http.py do app dono — sem isso, nada garante que a '
        'resposta dela caiba dentro da caixa do modal.'
    )

    sumidas = registradas - varridas
    assert not sumidas, (
        f'Rotas registradas que não são mais action_url de nenhum modal: '
        f'{sorted(sumidas)}. Remova do registro e apague o cenário órfão.'
    )


def test_registro_cobre_apenas_apps_existentes():
    """O app dono precisa ser um app real — é onde o teste HTTP vai morar."""
    assert set(REGISTRO_CONTRATO_MODAL.values()) <= {'requisicoes', 'estoque'}


def test_varredura_encontra_alguma_coisa():
    """Protege contra o pior modo de falha de um guarda de varredura.

    Um glob que deixa de casar devolve conjunto vazio, e o teste de cima passaria
    comparando nada com nada — o guarda viraria decoração silenciosa.
    """
    assert len(rotas_de_modal()) >= 10


def test_action_url_literal_e_recusada():
    """URL literal é o que tornaria a varredura cega — tem que doer, não passar."""
    texto = (
        '{% include "components/modal.html" with id="x" titulo="T" '
        'action_url="/requisicoes/1/cancelar/" %}'
    )
    with pytest.raises(AssertionError, match='não vem de um'):
        rotas_do_texto(texto, origem='sintetico.html')


def test_submit_form_id_fica_fora_do_contrato():
    """No modo de form externo o <dialog> não emite `hx-post` nenhum."""
    texto = (
        '{% include "components/modal.html" with id="x" titulo="T" '
        'submit_form_id="form-externo" %}'
    )
    assert rotas_do_texto(texto, origem='sintetico.html') == set()


def test_exemplo_em_comment_nao_conta_como_ponto_de_chamada():
    """A bula do componente documenta o uso com um include de exemplo."""
    texto = (
        '{% comment %}'
        '{% include "components/modal.html" with action_url=inventado %}'
        '{% endcomment %}'
    )
    assert rotas_do_texto(texto, origem='sintetico.html') == set()


def test_action_url_via_url_como_e_resolvida():
    texto = (
        "{% url 'requisicoes:cancelar' requisicao.pk as cancelar_url %}"
        '{% include "components/modal.html" with id="x" titulo="T" '
        'action_url=cancelar_url %}'
    )
    assert rotas_do_texto(texto, origem='sintetico.html') == {'requisicoes:cancelar'}
