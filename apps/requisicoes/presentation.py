"""Copy de apresentação dos modais de requisições — fonte única (#135).

Título, descrição e rótulos de cada modal vivem aqui uma vez só. O template
(`{% cancelamento_copy %}` / `{% modal_copy %}`, em `templatetags/requisicoes_tags.py`)
e a view — no re-render 422 via `apps.core.modal.render_modal_erro` — lêem o
mesmo dicionário, para que o modal reaberto com erro não possa dizer algo
diferente do que disse ao abrir.

Strings de UI puras, sem regra de domínio (ADR-0011). `cancelamento_copy` só
projeta a classificação que `apps.requisicoes.transitions.cancelamento_info`
já fez — não reimplementa nem reconsulta a regra.
"""

from __future__ import annotations

from apps.requisicoes.models import CancelamentoVariant, EstadoRequisicao
from apps.requisicoes.transitions import CancelamentoInfo

_CANCELAMENTO_COPY = {
    (CancelamentoVariant.DESCARTE, EstadoRequisicao.RASCUNHO): {
        'titulo': 'Descartar rascunho',
        'descricao': (
            'Este rascunho ainda não foi enviado. O descarte remove o registro '
            'definitivamente e não consome número público nem reserva de estoque.'
        ),
        'trigger': 'Descartar rascunho',
        'confirmar': 'Descartar',
        'icon_variant': 'danger',
    },
    (CancelamentoVariant.CANCELAMENTO, EstadoRequisicao.RASCUNHO): {
        'titulo': 'Cancelar rascunho',
        'descricao': (
            'Este rascunho já foi enviado alguma vez. O cancelamento encerra '
            'a requisição sem nova reserva e preserva o número público.'
        ),
        'trigger': 'Cancelar rascunho',
        'confirmar': 'Confirmar cancelamento',
        'icon_variant': 'danger',
    },
    (CancelamentoVariant.CANCELAMENTO, EstadoRequisicao.AGUARDANDO_AUTORIZACAO): {
        'titulo': 'Cancelar requisição',
        'descricao': (
            'A requisição será encerrada antes da autorização. Não há reserva '
            'de estoque a liberar e a justificativa é opcional.'
        ),
        'trigger': 'Cancelar requisição',
        'confirmar': 'Confirmar cancelamento',
        'icon_variant': 'danger',
    },
    (CancelamentoVariant.CANCELAMENTO, EstadoRequisicao.AUTORIZADA): {
        'titulo': 'Cancelar requisição',
        'descricao': (
            'A requisição será encerrada e as reservas voltam ao saldo '
            'disponível. O saldo físico permanece inalterado.'
        ),
        'trigger': 'Cancelar requisição',
        'confirmar': 'Confirmar cancelamento',
        'icon_variant': 'danger',
    },
}
_CANCELAMENTO_COPY[
    (CancelamentoVariant.CANCELAMENTO, EstadoRequisicao.PRONTA_PARA_RETIRADA)
] = _CANCELAMENTO_COPY[(CancelamentoVariant.CANCELAMENTO, EstadoRequisicao.AUTORIZADA)]


def cancelamento_copy(
    info: CancelamentoInfo | None, estado: EstadoRequisicao
) -> dict[str, str]:
    """Copy do modal de cancelamento por (variante, estado).

    `info` é `CancelamentoInfo | None` (`None` quando a operação não está
    disponível); `estado` é `requisicao.estado`.
    """
    if info is None:
        return {}
    return _CANCELAMENTO_COPY[(info.variante, estado)]


MODAL_COPY: dict[str, dict[str, str]] = {
    'recusar': {
        'titulo': 'Recusar requisição?',
        'descricao': 'A recusa encerra a requisição sem reservar ou baixar estoque.',
        'confirm_label': 'Confirmar recusa',
        'icon_variant': 'danger',
    },
    'estornar': {
        'titulo': 'Estornar requisição',
        'descricao': (
            'O estorno reverte toda a entregue líquida ao saldo físico do '
            'estoque e encerra definitivamente a requisição. Esta operação é '
            'irreversível.'
        ),
        # Só do painel de decisão: não é a consequência do estorno (essa é
        # `descricao`, dita uma vez só — #135), é um fato à parte sobre a
        # justificativa que só fazia sentido *antes* de abrir o modal.
        'painel_extra': 'A justificativa é obrigatória e fica registrada na timeline.',
        'confirm_label': 'Confirmar estorno',
    },
    'devolucao': {
        'titulo': 'Registrar devolução',
        'descricao': 'Informe a quantidade a devolver ao estoque.',
        'confirm_label': 'Registrar devolução',
    },
}
