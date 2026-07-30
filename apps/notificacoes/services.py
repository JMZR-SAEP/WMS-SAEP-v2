"""Services de notificações in-app."""

from collections.abc import Iterable

from django.db import transaction

from apps.notificacoes.models import Notificacao


@transaction.atomic
def criar_notificacoes_para_destinatarios(
    *,
    destinatarios_ids: Iterable[int | None],
    requisicao_id: int,
    tipo: str,
) -> None:
    """Cria notificações para os destinatários informados, deduplicando.

    Ignora ``None`` e ids repetidos. É o primitivo de roteamento;
    ``criar_notificacoes_para`` é o atalho para o par criador/beneficiário.
    """
    destinatarios = list(
        dict.fromkeys(uid for uid in destinatarios_ids if uid is not None)
    )
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


def criar_notificacoes_para(
    *,
    criador_id: int,
    beneficiario_id: int,
    requisicao_id: int,
    tipo: str,
) -> None:
    """Cria notificações para criador e beneficiário, deduplicando se iguais."""
    criar_notificacoes_para_destinatarios(
        destinatarios_ids=[criador_id, beneficiario_id],
        requisicao_id=requisicao_id,
        tipo=tipo,
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
