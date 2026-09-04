"""Views da camada compartilhada de UI. Sem regra de domínio."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

from apps.accounts.papeis import papel_efetivo
from apps.requisicoes.policies import (
    pode_ver_fila_atendimento,
    pode_ver_fila_autorizacao,
)


@login_required
def home(request):
    """Dispatcher pós-login — redireciona por papel efetivo do usuário.

    `is_superuser` é flag técnica do Django, fora do domínio (PRODUCT.md): não
    sequestra a raiz. O superusuário chega ao admin por link explícito e, no
    produto, é roteado pelo papel efetivo como qualquer outro usuário.
    """
    papel = papel_efetivo(request.user)
    if pode_ver_fila_atendimento(papel):
        return redirect(reverse('requisicoes:atendimentos'))
    if pode_ver_fila_autorizacao(papel):
        return redirect(reverse('requisicoes:autorizacoes'))
    return redirect(reverse('requisicoes:minhas'))
