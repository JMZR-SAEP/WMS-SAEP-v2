"""Copy de apresentação dos modais de requisições — fonte única (#135).

Título, descrição e rótulos de cada modal vivem aqui uma vez só. O template
(`{% cancelamento_copy %}` / `{% modal_copy %}`, em `templatetags/requisicoes_tags.py`)
e a view — no re-render 422 via `apps.core.modal.render_modal_erro` — lêem o
mesmo dicionário, para que o modal reaberto com erro não possa dizer algo
diferente do que disse ao abrir.

Strings de UI puras, sem regra de domínio (ADR-0011). `cancelamento_copy` só
projeta a classificação que `apps.requisicoes.transitions.cancelamento_info`
já fez — não reimplementa nem reconsulta a regra. `registro_requisicao` idem:
projeta campos já persistidos em texto de tela, sem decidir nada.
"""

from __future__ import annotations

from apps.requisicoes.models import CancelamentoVariant, EstadoRequisicao, Requisicao
from apps.requisicoes.transitions import CancelamentoInfo


def registro_requisicao(requisicao: Requisicao) -> dict[str, str]:
    """Linha de identidade da requisição no cabeçalho do modal (#138).

    Fonte única dos seis modais da tela de detalhe mais o de atender retirada:
    seis `{% include %}` escrevendo cada um a sua versão de "qual requisição é
    esta" é a mesma divergência que a #135 fechou para título e descrição.

    `identificador` é o número público, e o fallback do rascunho é o literal
    "Rascunho" — **não** `str(requisicao)`, que cairia no `__str__` do model e
    devolveria `Rascunho #<pk>`. A regra é `docs/CONVENTIONS.md`
    §Identificadores na interface: PK interno não vaza para UI.
    O `__str__` continua servindo admin e log, que é para onde ele foi escrito.

    O rascunho tem modal (descartar, cancelar, enviar) e não tem número —
    quem responde "qual documento?" ali é o `contexto`, e a linha diz
    explicitamente que número ainda não há em vez de inventar um.

    `contexto` é beneficiário e setor, não estado. Estado é redundante com o
    título do modal (que nomeia a transição) e com o próprio `identificador` no
    caso do rascunho; quem desempata dois documentos abertos em sequência num
    bloco de decisão é de quem é a requisição e de que setor ela veio.

    Ambas as relações vêm no `select_related` de `requisicoes_visiveis_para`,
    então a linha não custa consulta nova.
    """
    return {
        'rotulo': 'Requisição',
        'identificador': requisicao.numero_publico or 'Rascunho',
        'contexto': (
            f'{requisicao.beneficiario.nome} · {requisicao.setor_beneficiario.nome}'
        ),
    }


_CANCELAMENTO_COPY = {
    (CancelamentoVariant.DESCARTE, EstadoRequisicao.RASCUNHO): {
        'titulo': 'Descartar rascunho',
        'descricao': (
            'Este rascunho ainda não foi enviado. O descarte remove o registro '
            'definitivamente e não consome número público nem reserva de estoque.'
        ),
        'trigger': 'Descartar rascunho',
        'confirmar': 'Descartar',
        # 'descarte', não 'danger' (#136): é a única operação do vocabulário de
        # modal que remove um registro sem rastro. Cancelamento, logo abaixo,
        # encerra sem apagar — a distinção é o próprio ponto da issue.
        'icon_variant': 'descarte',
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
            'estoque e encerra a requisição.'
        ),
        # Separada da `descricao` (#138): no cabeçalho ela saía em
        # `text-text-secondary`, mais apagada que os dados que qualifica. O
        # corpo do modal a renderiza com ênfase — ver `consequencia` em
        # `components/_modal_body.html`. Continua dita uma vez só.
        'consequencia': 'Esta operação é irreversível.',
        # Só do painel de decisão: não é a consequência do estorno (essa é
        # `descricao`, dita uma vez só — #135), é um fato à parte sobre a
        # justificativa que só fazia sentido *antes* de abrir o modal.
        'painel_extra': 'A justificativa é obrigatória e fica registrada na timeline.',
        'confirm_label': 'Confirmar estorno',
        # 'return', não 'danger': o estorno é reversão operacional, e a Regra da
        # Reversão Não é Erro reserva o vermelho para negação, falha e
        # divergência. O estado resultante já era carimbado em `teal-strong`
        # pelo `_estado_badge.html`, então a ação e o seu efeito diziam coisas
        # opostas. Mesmo caminho que a devolução fez na #136.
        'icon_variant': 'return',
    },
    'devolucao': {
        'titulo': 'Registrar devolução',
        'descricao': 'Informe a quantidade a devolver ao estoque.',
        'confirm_label': 'Registrar devolução',
        # 'return', não 'info' (#136): fecha o fio teal que a issue nomeia —
        # o trigger já é 'return-outline' (Regra da Reversão Não é Erro), e o
        # modal não pode confirmar essa mesma ação em azul.
        'icon_variant': 'return',
    },
}
