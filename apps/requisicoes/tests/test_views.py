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
    assert 'Buscar por código ou nome…' in conteudo
    assert 'x-show="itensVisiveis >= 2"' in conteudo
    assert 'mostrarProximo(1)' in conteudo


@pytest.mark.django_db
def test_get_nova_requisicao_solicitante_puro_comeca_como_beneficiario(
    client,
    user_obras,
    user_administrativo,
    material_papel,
):
    client.force_login(user_obras)

    resposta = client.get(reverse('requisicoes:nova'))
    form = resposta.context['form']
    conteudo = resposta.content.decode()

    assert form.beneficiario_padrao == user_obras
    assert 'Toda nova requisição começa para você.' in conteudo
    assert user_obras.nome in conteudo
    assert 'Criar para outra pessoa' not in conteudo
    assert user_administrativo.nome not in resposta.content.decode()


@pytest.mark.django_db
def test_get_nova_requisicao_auxiliar_abre_beneficiarios_do_setor(
    client,
    auxiliar_obras,
    auxiliar_almoxarifado,
    user_obras,
    material_papel,
):
    client.force_login(auxiliar_obras)

    resposta = client.get(reverse('requisicoes:nova'))
    form = resposta.context['form']
    beneficiarios = set(form.fields['beneficiario'].queryset)
    conteudo = resposta.content.decode()

    assert user_obras in beneficiarios
    assert auxiliar_obras not in beneficiarios
    assert auxiliar_almoxarifado not in beneficiarios
    assert form.beneficiario_padrao == auxiliar_obras
    assert 'Criar para outra pessoa' in conteudo
    assert 'x-show="criarParaTerceiro"' in conteudo


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
            'material_1': material_papel.id,
            'quantidade_solicitada_1': '2.000',
            'observacao_geral': 'Uso administrativo.',
        },
    )

    requisicao = Requisicao.objects.get()
    assert resposta.status_code == 302
    assert resposta['Location'] == reverse('requisicoes:detalhe', args=[requisicao.id])
    assert requisicao.beneficiario == user_obras


@pytest.mark.django_db
def test_post_nova_requisicao_auxiliar_cria_para_terceiro_quando_explicitado(
    client,
    auxiliar_obras,
    user_obras,
    material_papel,
):
    client.force_login(auxiliar_obras)

    resposta = client.post(
        reverse('requisicoes:nova'),
        {
            'criar_para_terceiro': 'on',
            'beneficiario': user_obras.id,
            'material_1': material_papel.id,
            'quantidade_solicitada_1': '2.000',
        },
    )

    requisicao = Requisicao.objects.get()
    assert resposta.status_code == 302
    assert requisicao.criador == auxiliar_obras
    assert requisicao.beneficiario == user_obras


@pytest.mark.django_db
def test_post_nova_requisicao_cria_multiplos_itens(
    client,
    user_obras,
    material_papel,
    material_caneta,
):
    client.force_login(user_obras)

    resposta = client.post(
        reverse('requisicoes:nova'),
        {
            'material_1': material_papel.id,
            'quantidade_solicitada_1': '2.000',
            'material_2': material_caneta.id,
            'quantidade_solicitada_2': '4.000',
        },
    )

    requisicao = Requisicao.objects.get()
    assert resposta.status_code == 302
    assert requisicao.itens.count() == 2
    assert set(requisicao.itens.values_list('material_id', flat=True)) == {
        material_papel.id,
        material_caneta.id,
    }


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
            'criar_para_terceiro': 'on',
            'beneficiario': user_administrativo.id,
            'material_1': material_papel.id,
            'quantidade_solicitada_1': '1.000',
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
            'material_1': material_papel.id,
            'quantidade_solicitada_1': Decimal('0.000'),
        },
    )
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'A quantidade solicitada deve ser maior que zero.' in conteudo
    assert Requisicao.objects.count() == 0
