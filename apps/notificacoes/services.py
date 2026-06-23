"""Services de notificações in-app."""

from django.db import transaction

from apps.notificacoes.models import Notificacao


def criar_notificacoes_para(
    *,
    criador_id: int,
    beneficiario_id: int,
    requisicao_id: int,
    tipo: str,
) -> None:
    """Cria notificações para criador e beneficiário, deduplicando se iguais."""
    destinatarios = list(dict.fromkeys(uid for uid in [criador_id, beneficiario_id]))
    Notificacao.objects.bulk_create(
        [
            Notificacao(
                destinatario_id=uid,
                tipo=tipo,
                requisicao_id=requisicao_id,
            )
            for uid in destinatarios
        ]
    )


@transaction.atomic
def marcar_notificacao_lida(*, ator_id: int, notificacao_id: int) -> None:
    """Marca notificação individual como lida, ignorando se já lida."""
    Notificacao.objects.filter(
        pk=notificacao_id,
        destinatario_id=ator_id,
        lida=False,
    ).update(lida=True)


@transaction.atomic
def marcar_todas_notificacoes_lidas(*, ator_id: int) -> None:
    """Marca todas as notificações não lidas do ator como lidas."""
    Notificacao.objects.filter(destinatario_id=ator_id, lida=False).update(lida=True)
