"""Views de notificações in-app."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.core.http import htmx_redirect
from apps.notificacoes.models import Notificacao
from apps.notificacoes.selectors import notificacoes_com_numero_publico
from apps.notificacoes.services import (
    marcar_notificacao_lida,
    marcar_todas_notificacoes_lidas,
)


@login_required
@require_GET
def lista_notificacoes_view(request):
    from apps.notificacoes.presentation import desfecho_da_notificacao

    notificacoes = notificacoes_com_numero_publico(request.user.pk)
    # O título do cartão passa a ser o DESFECHO, não o tipo do evento.
    # `Autorização` é a categoria do aviso, não a notícia — não diz se foi
    # autorizada. Quem abre esta tela abriu para saber o que aconteceu com o
    # pedido dela. Tipo fora do catálogo cai no rótulo do próprio model, para
    # nenhum aviso ficar sem título.
    for notificacao in notificacoes:
        notificacao.desfecho = (
            desfecho_da_notificacao(  # type: ignore[attr-defined]
                notificacao.tipo
            )
            or notificacao.get_tipo_display()
        )
    return render(
        request,
        'notificacoes/lista.html',
        {'notificacoes': notificacoes},
    )


@login_required
@require_POST
def marcar_lida_view(request, pk: int):
    notificacao = get_object_or_404(Notificacao, pk=pk, destinatario=request.user)
    marcar_notificacao_lida(ator_id=request.user.pk, notificacao_id=notificacao.pk)
    return htmx_redirect(request, reverse('notificacoes:lista'))


@login_required
@require_POST
def marcar_todas_lidas_view(request):
    marcar_todas_notificacoes_lidas(ator_id=request.user.pk)
    return htmx_redirect(request, reverse('notificacoes:lista'))
