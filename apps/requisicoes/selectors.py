"""Seletores de leitura para requisições.

Concentram queries não-triviais: autocomplete de materiais elegíveis.
Leituras triviais podem usar o ORM direto na view.
"""

from django.db.models import F, Q, QuerySet

from apps.estoque.models import Material


def materiais_para_requisicao(q: str = '', limite: int = 20) -> QuerySet:
    """Retorna materiais elegíveis para inclusão em nova requisição.

    Elegível = ativo, com ao menos um SaldoEstoque com saldo_disponivel > 0
    (saldo_fisico > saldo_reservado implica ausência de divergência crítica).
    Busca por código ou nome (case-insensitive, substring).
    """
    qs = (
        Material.objects.filter(ativo=True)
        .filter(saldos__saldo_fisico__gt=F('saldos__saldo_reservado'))
        .exclude(saldos__saldo_fisico__lt=F('saldos__saldo_reservado'))
        .distinct()
    )
    if q:
        qs = qs.filter(Q(codigo__icontains=q) | Q(nome__icontains=q))
    return qs.order_by('nome')[:limite]


def material_eh_elegivel(material: Material) -> bool:
    """True se o material pode entrar em nova requisição agora.

    Revalida no submit: ativo, sem divergência e saldo disponível > 0.
    """
    if not material.ativo:
        return False
    if material.saldos.filter(saldo_fisico__lt=F('saldo_reservado')).exists():
        return False
    return material.saldos.filter(saldo_fisico__gt=F('saldo_reservado')).exists()
