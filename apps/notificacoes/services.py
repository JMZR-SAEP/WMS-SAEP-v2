"""Services de notificações in-app."""

from apps.notificacoes.models import Notificacao, TipoNotificacao


def criar_notificacoes_para(
    *,
    criador_id: int,
    beneficiario_id: int,
    requisicao_id: int,
    tipo: str,
) -> None:
    """Cria notificações para criador e beneficiário, deduplicando se iguais."""
    destinatarios = list(
        dict.fromkeys(uid for uid in [criador_id, beneficiario_id])
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
