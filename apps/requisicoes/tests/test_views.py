from decimal import Decimal

import pytest
from django.urls import reverse

from apps.requisicoes.models import Requisicao


@pytest.mark.django_db
def test_get_nova_requisicao_exige_login(client):
    resposta = client.get(reverse('requisicoes:nova'))

    assert resposta.status_code == 302
    assert resposta['Location'].startswith('/login/')


@pytest.mark.django_db
def test_get_nova_requisicao_renderiza_formulario(
    client,
    user_obras,
    material_papel,
):
    client.force_login(user_obras)

    resposta = client.get(reverse('requisicoes:nova'))
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'requisicoes/nova.html' in {t.name for t in resposta.templates}
    assert 'Nova requisição' in conteudo
    assert 'Beneficiário' in conteudo
    assert 'Material' in conteudo
    assert material_papel.nome in conteudo
    assert 'bg-slate-50' in conteudo
    assert 'rounded-lg border border-slate-200 bg-white' in conteudo


@pytest.mark.django_db
def test_post_nova_requisicao_cria_rascunho_e_redireciona_para_detalhe(
    client,
    user_obras,
    material_papel,
):
    client.force_login(user_obras)

    resposta = client.post(
        reverse('requisicoes:nova'),
        {
            'beneficiario': user_obras.id,
            'material': material_papel.id,
            'quantidade_solicitada': '2.000',
            'observacao_geral': 'Uso administrativo.',
        },
    )

    requisicao = Requisicao.objects.get()
    assert resposta.status_code == 302
    assert resposta['Location'] == reverse('requisicoes:detalhe', args=[requisicao.id])
    assert requisicao.beneficiario == user_obras


@pytest.mark.django_db
def test_post_nova_requisicao_sem_permissao_retorna_403(
    client,
    user_obras,
    user_administrativo,
    material_papel,
):
    client.force_login(user_obras)

    resposta = client.post(
        reverse('requisicoes:nova'),
        {
            'beneficiario': user_administrativo.id,
            'material': material_papel.id,
            'quantidade_solicitada': '1.000',
        },
    )

    assert resposta.status_code == 403
    assert Requisicao.objects.count() == 0


@pytest.mark.django_db
def test_post_nova_requisicao_com_quantidade_invalida_reexibe_formulario(
    client,
    user_obras,
    material_papel,
):
    client.force_login(user_obras)

    resposta = client.post(
        reverse('requisicoes:nova'),
        {
            'beneficiario': user_obras.id,
            'material': material_papel.id,
            'quantidade_solicitada': Decimal('0.000'),
        },
    )
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'A quantidade solicitada deve ser maior que zero.' in conteudo
    assert Requisicao.objects.count() == 0
