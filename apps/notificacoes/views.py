"""Views de notificações in-app."""

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.core.exceptions import PermissaoNegada
from apps.core.http import htmx_redirect
from apps.notificacoes.selectors import notificacoes_para_exibicao
from apps.notificacoes.services import (
    marcar_notificacao_lida,
    marcar_todas_notificacoes_lidas,
)


@login_required
@require_GET
def lista_notificacoes_view(request):
    from apps.notificacoes.presentation import titulo_da_notificacao

    notificacoes = notificacoes_para_exibicao(request.user.pk)
    # O título do cartão é o evento (no passado, que é o que a notificação
    # registra) mais o estado ATUAL da requisição, que o selector foi consultar
    # no domínio. Projeção de dado já resolvido, não decisão: quem respondeu
    # "ainda pede ação?" foi `acoes_disponiveis`, via selector. Tipo fora do
    # catálogo cai no rótulo do próprio model, para nenhum aviso ficar sem
    # título.
    for notificacao in notificacoes:
        requisicao = notificacao.requisicao_referida
        notificacao.titulo = titulo_da_notificacao(  # type: ignore[attr-defined]
            tipo=notificacao.tipo,
            rotulo_do_tipo=notificacao.get_tipo_display(),
            pede_acao=notificacao.pede_acao,
            estado_label=requisicao.get_estado_display() if requisicao else '',
        )
    return render(
        request,
        'notificacoes/lista.html',
        {'notificacoes': notificacoes},
    )


@login_required
@require_POST
def marcar_lida_view(request, pk: int):
    """Marca uma notificação como lida.

    Toda a autorização vive no service (#181, ADR-0011): ele carrega ator e
    notificação, resolve o ``PapelEfetivo`` uma vez e aplica
    ``exigir_pode_ver_notificacao``. A view só traduz a ``PermissaoNegada``
    resultante para 404 — e não 403 — porque notificação de terceiro é objeto
    **fora do escopo de visibilidade**, e a ADR-0010 reserva o 403 para ação
    proibida em objeto visível: um 403 aqui confirmaria a existência da
    notificação ``pk`` a qualquer usuário autenticado, abrindo enumeração — o
    mesmo argumento que ``requisicoes/views.py`` já aplica. É substituição
    explícita do mapeamento canônico da ADR-0011 (``PermissaoNegada`` → 403),
    que a própria emenda autoriza "por requisito de contrato do endpoint...
    nunca acidente".
    """
    try:
        marcar_notificacao_lida(ator_id=request.user.pk, notificacao_id=pk)
    except PermissaoNegada as exc:
        raise Http404(str(exc)) from exc
    return htmx_redirect(request, reverse('notificacoes:lista'))


@login_required
@require_POST
def marcar_todas_lidas_view(request):
    marcar_todas_notificacoes_lidas(ator_id=request.user.pk)
    return htmx_redirect(request, reverse('notificacoes:lista'))
