"""Seletores de leitura para notificações.

A notificação é um registro congelado no instante do evento: guarda o **tipo**
do que aconteceu, nunca o desfecho. Quem responde "e agora, como está?" é a
requisição referenciada — por isso todo seletor daqui decora o aviso com o
estado **atual** dela, e nunca com uma cópia de estado do momento da criação
(issue #175; Princípio 1 do `PRODUCT.md`: o domínio manda na interface).

Os imports de `requisicoes` são todos de função, e não de módulo: o campo
``Notificacao.requisicao_id`` é um ``IntegerField`` solto exatamente para não
haver dependência reversa de ``notificacoes`` -> ``requisicoes`` em tempo de
import. O registro de apps do Django está pronto quando qualquer destes
seletores roda.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.notificacoes.models import Notificacao

if TYPE_CHECKING:
    from apps.requisicoes.models import Operacao, Requisicao


def notificacoes_para_exibicao(destinatario_id: int) -> list[Notificacao]:
    """Notificações do destinatário decoradas com o estado atual da requisição.

    Decorações (não persistidas, uma consulta a mais no total):

    - ``requisicao_referida``: a requisição, ou ``None`` — é ela que o cartão
      passa ao ``_estado_badge.html``, o mesmo partial de domínio das filas.
    - ``requisicao_existe``: se há para onde ir. ``requisicao_id`` é um
      ``IntegerField`` solto, sem FK e sem integridade referencial: um id órfão
      é indistinguível de um rascunho pelo valor do campo, e colapsar os dois
      fazia o cartão prometer um link cujo detalhe devolve 404.
    - ``numero_publico_exibicao``: o número, ou ``"Rascunho"`` para requisição
      que existe e ainda não tem número.
    - ``pede_acao`` / ``resolvida``: ver ``_decorar_com_pendencia``.
    """
    notificacoes = list(
        Notificacao.objects.filter(destinatario_id=destinatario_id).order_by(
            '-criado_em'
        )
    )
    _decorar(notificacoes, destinatario_id=destinatario_id)
    return notificacoes


def contagem_de_notificacoes_pendentes(destinatario_id: int) -> int:
    """Quantos itens de trabalho ainda esperam o destinatário — a conta do sino.

    Conta **requisições**, não avisos. A mesma requisição gera um aviso a cada
    envio, e "retornar ao rascunho e reenviar" é fluxo suportado: somando
    avisos, o sino dizia "2" para uma Fila de autorização de "1". A chave da
    contagem é o par (requisição, operação convocada) — duas notificações que
    convocam a mesma operação sobre a mesma requisição são um item só, e tipos
    que convoquem operações distintas continuam somando separado.

    Quem responde "pode agir agora?" é o domínio, pela mesma regra que a lista
    usa (`acoes_disponiveis`): aqui pela porta em lote e filtrada no banco
    (`requisicoes_com_acao_disponivel`), para o processador de contexto não
    carregar o histórico inteiro a cada request. A decoração completa fica para
    `/notificacoes/`, que é onde ela é exibida.
    """
    from apps.requisicoes.selectors import (
        CHAMADA_DE_ACAO_POR_TIPO_NOTIFICACAO,
        requisicoes_com_acao_disponivel,
    )

    tipos_por_operacao: dict[Operacao, list[str]] = {}
    for tipo, operacao in CHAMADA_DE_ACAO_POR_TIPO_NOTIFICACAO.items():
        tipos_por_operacao.setdefault(operacao, []).append(tipo)

    total = 0
    for operacao, tipos in tipos_por_operacao.items():
        ids_referidos = Notificacao.objects.filter(
            destinatario_id=destinatario_id,
            tipo__in=tipos,
            requisicao_id__isnull=False,
        ).values('requisicao_id')
        total += len(
            requisicoes_com_acao_disponivel(
                ator_id=destinatario_id, operacao=operacao, entre_ids=ids_referidos
            )
        )
    return total


def requisicoes_referidas(requisicao_ids: list[int]) -> dict[int, 'Requisicao']:
    """Resolve ``requisicao_id -> Requisicao`` em uma única query, sem N+1.

    Id sem requisição correspondente simplesmente não aparece no resultado —
    é assim que o chamador distingue órfão de rascunho.
    """
    if not requisicao_ids:
        return {}
    from apps.requisicoes.models import Requisicao

    return {
        requisicao.pk: requisicao
        for requisicao in Requisicao.objects.filter(pk__in=requisicao_ids)
    }


def _decorar(notificacoes: list[Notificacao], *, destinatario_id: int) -> None:
    """Anota identidade e pendência de cada aviso, em lote."""
    from apps.requisicoes.selectors import acoes_disponiveis_em_lote

    requisicoes = requisicoes_referidas(
        [n.requisicao_id for n in notificacoes if n.requisicao_id]
    )
    acoes_por_requisicao = acoes_disponiveis_em_lote(
        ator_id=destinatario_id, requisicoes=requisicoes.values()
    )
    for notificacao in notificacoes:
        requisicao = (
            requisicoes.get(notificacao.requisicao_id)
            if notificacao.requisicao_id is not None
            else None
        )
        notificacao.requisicao_referida = requisicao  # type: ignore[attr-defined]
        notificacao.requisicao_existe = requisicao is not None  # type: ignore[attr-defined]
        notificacao.numero_publico_exibicao = (  # type: ignore[attr-defined]
            (requisicao.numero_publico or 'Rascunho') if requisicao is not None else ''
        )
        _decorar_com_pendencia(
            notificacao,
            requisicao=requisicao,
            acoes=acoes_por_requisicao.get(requisicao.pk, frozenset())
            if requisicao is not None
            else frozenset(),
        )


def _decorar_com_pendencia(
    notificacao: Notificacao,
    *,
    requisicao: 'Requisicao | None',
    acoes: 'frozenset[Operacao]',
) -> None:
    """Responde "este aviso ainda pede ação?" perguntando ao domínio.

    A pergunta não é reconstruída aqui: a resposta é a interseção entre a
    operação que o aviso convoca (``operacao_convocada_por_notificacao``) e as
    que o destinatário pode executar **agora** (``acoes_disponiveis``, que
    deriva da tabela de transições e das policies). Sem essa consulta, o cartão
    afirmava um estado congelado na criação e o sino contava trabalho que já
    tinha sido feito.

    - ``pede_acao``: entra na contagem do sino.
    - ``resolvida``: convocava uma ação que não se aplica mais ao estado
      corrente. Continua visível na lista — ``/notificacoes/`` é o diário do
      que aconteceu com as minhas requisições, não uma caixa de entrada, e o
      `PRODUCT.md` põe auditabilidade acima de conveniência. As duas telas de
      chamada à ação (Fila de autorização e Fila de atendimento) já existem.

    Aviso informativo não é nem uma coisa nem outra: ele narra um desfecho e
    nunca pediu ação a quem o recebeu. Marcar "Resolvida" nele seria inventar
    uma pendência que não houve.
    """
    from apps.requisicoes.selectors import operacao_convocada_por_notificacao

    convocada = operacao_convocada_por_notificacao(notificacao.tipo)
    convoca_alguma_acao = convocada is not None and requisicao is not None
    notificacao.pede_acao = convoca_alguma_acao and convocada in acoes  # type: ignore[attr-defined]
    notificacao.resolvida = convoca_alguma_acao and not notificacao.pede_acao  # type: ignore[attr-defined]
