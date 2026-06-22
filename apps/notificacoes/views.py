"""Views de notificações in-app."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.notificacoes.models import Notificacao
from apps.notificacoes.services import (
    marcar_notificacao_lida,
    marcar_todas_notificacoes_lidas,
)


@login_required
@require_GET
def lista_notificacoes_view(request):
    notificacoes = Notificacao.objects.filter(destinatario=request.user).order_by(
        '-criado_em'
    )
    return render(
        request,
        'notificacoes/lista.html',
        {'notificacoes': notificacoes},
    )


@login_required
@require_POST
def marcar_lida_view(request, pk: int):
    get_object_or_404(Notificacao, pk=pk, destinatario=request.user)
    marcar_notificacao_lida(ator_id=request.user.pk, notificacao_id=pk)
    if request.headers.get('HX-Request') == 'true':
        return HttpResponse(status=204)
    return redirect('notificacoes:lista')


@login_required
@require_POST
def marcar_todas_lidas_view(request):
    marcar_todas_notificacoes_lidas(ator_id=request.user.pk)
    if request.headers.get('HX-Request') == 'true':
        return HttpResponse(status=204)
    return redirect('notificacoes:lista')
