"""Context processors de notificações."""

from apps.notificacoes.models import Notificacao


def notificacoes_ctx(request):
    """Injeta contagem de não-lidas em todo request de usuário autenticado."""
    usuario = getattr(request, 'user', None)
    if usuario is None or not usuario.is_authenticated:
        return {'notificacoes_nao_lidas': 0}
    try:
        count = Notificacao.objects.filter(destinatario=usuario, lida=False).count()
    except Exception:
        count = 0
    return {'notificacoes_nao_lidas': count}
