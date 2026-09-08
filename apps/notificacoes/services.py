"""Services de notificações in-app."""

from collections.abc import Iterable

from django.db import transaction

from apps.accounts.models import User
from apps.accounts.papeis import papel_efetivo
from apps.core.exceptions import PermissaoNegada
from apps.notificacoes.models import Notificacao
from apps.notificacoes.policies import exigir_pode_ver_notificacao


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
    """Marca notificação individual como lida, ignorando se já lida.

    A autorização é resolvida aqui, uma única vez (ADR-0011): carrega ator e
    notificação, deriva o ``PapelEfetivo`` e delega a
    ``exigir_pode_ver_notificacao`` — a mesma policy que a view usava. Some o
    filtro ``destinatario_id=ator_id``, que era segunda fonte de verdade da
    regra "só o destinatário vê a notificação" (PER-08/ADR-0004): se a policy
    passasse a liberar um chefe, o ``.update()`` escopado afetaria zero linhas
    em silêncio. Notificação inexistente e notificação de terceiro caem na
    mesma ``PermissaoNegada`` — não revelar existência é deliberado (ADR-0010);
    a view só traduz essa negativa para 404 (#181).
    """
    negada = PermissaoNegada(
        'Você não tem permissão para ver esta notificação.',
        code='permissao_negada',
    )
    try:
        notificacao = Notificacao.objects.select_for_update().get(pk=notificacao_id)
    except Notificacao.DoesNotExist:
        raise negada from None

    try:
        ator = User.objects.get(pk=ator_id)
    except User.DoesNotExist:
        raise negada from None

    exigir_pode_ver_notificacao(papel_efetivo(ator), notificacao)

    if not notificacao.lida:
        notificacao.lida = True
        notificacao.save(update_fields=['lida'])


@transaction.atomic
def marcar_todas_notificacoes_lidas(*, ator_id: int) -> None:
    """Marca todas as notificações não lidas do ator como lidas.

    Não há objeto único a autorizar: o recorte por ``ator_id`` **é** o escopo
    da operação, no mesmo espírito do selector da listagem.
    """
    Notificacao.objects.filter(destinatario_id=ator_id, lida=False).update(lida=True)
