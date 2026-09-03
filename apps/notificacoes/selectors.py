"""Seletores de leitura para notificações."""

from django.apps import apps

from apps.notificacoes.models import Notificacao


def notificacoes_com_numero_publico(destinatario_id: int) -> list[Notificacao]:
    """Notificações do destinatário, decoradas para exibição.

    Resolve ``requisicao_id -> numero_publico`` em lote (sem N+1) e anota duas
    coisas em cada instância, sem persistir:

    - ``numero_publico_exibicao``: o número, ou ``"Rascunho"`` para requisição
      que existe e ainda não tem número.
    - ``requisicao_existe``: se há para onde ir.

    Os dois são necessários porque ``requisicao_id`` é um ``IntegerField``
    solto, sem FK e sem integridade referencial (ver
    ``numeros_publicos_por_requisicao``): um id órfão é indistinguível de um
    rascunho pelo valor do campo. Colapsar os dois em ``"Rascunho"`` fazia o
    cartão prometer um link cujo detalhe devolve 404.
    """
    notificacoes = list(
        Notificacao.objects.filter(destinatario_id=destinatario_id).order_by(
            '-criado_em'
        )
    )
    requisicao_ids = [n.requisicao_id for n in notificacoes if n.requisicao_id]
    numeros_publicos = numeros_publicos_por_requisicao(requisicao_ids)
    for notificacao in notificacoes:
        if notificacao.requisicao_id is None:
            notificacao.requisicao_existe = False  # type: ignore[attr-defined]
            continue
        existe = notificacao.requisicao_id in numeros_publicos
        notificacao.requisicao_existe = existe  # type: ignore[attr-defined]
        numero = numeros_publicos.get(notificacao.requisicao_id)
        notificacao.numero_publico_exibicao = numero or 'Rascunho'  # type: ignore[attr-defined]
    return notificacoes


def numeros_publicos_por_requisicao(requisicao_ids: list[int]) -> dict[int, str | None]:
    """Resolve requisicao_id -> numero_publico em uma única query, sem N+1.

    ``Notificacao.requisicao_id`` é um ``IntegerField`` solto (não FK) para
    evitar dependência reversa de ``notificacoes`` -> ``requisicoes``; a
    resolução usa o registro de apps do Django para não acoplar em tempo de
    import.
    """
    if not requisicao_ids:
        return {}
    requisicao_model = apps.get_model('requisicoes', 'Requisicao')
    return dict(
        requisicao_model.objects.filter(pk__in=requisicao_ids).values_list(
            'pk', 'numero_publico'
        )
    )
