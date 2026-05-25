"""Views da camada compartilhada de UI. Sem regra de domínio."""

from django.shortcuts import render

from apps.requisicoes.policies import pode_ser_beneficiario


def home(request):
    pode_visualizar_requisicoes = request.user.is_authenticated
    pode_criar_requisicao = False
    if request.user.is_authenticated:
        pode_criar_requisicao = pode_ser_beneficiario(request.user)

    return render(
        request,
        'core/home.html',
        {
            'pode_visualizar_requisicoes': pode_visualizar_requisicoes,
            'pode_criar_requisicao': pode_criar_requisicao,
        },
    )
