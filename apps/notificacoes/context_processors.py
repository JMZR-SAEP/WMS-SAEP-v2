"""Context processors de notificações."""

from apps.notificacoes.selectors import contagem_de_notificacoes_pendentes


def notificacoes_ctx(request):
    """Injeta a contagem de pendências em todo request de usuário autenticado.

    Pendência, e não "não lidas": o sino contava avisos, e aviso é registro de
    evento passado — o número crescia com o histórico e discordava da fila que
    ele deveria antecipar (issue #175). Passa a contar só o que ainda pede ação
    ao destinatário, resposta que vem do domínio (tabela de transições +
    policies) pelo mesmo caminho que a lista usa. Assim a conta do sino pode ser
    conferida contra a da Fila de autorização sem discordar dela.
    """
    usuario = getattr(request, 'user', None)
    if usuario is None or not usuario.is_authenticated:
        return {'notificacoes_pendentes': 0}
    try:
        count = contagem_de_notificacoes_pendentes(usuario.pk)
    except Exception:
        count = 0
    return {'notificacoes_pendentes': count}
