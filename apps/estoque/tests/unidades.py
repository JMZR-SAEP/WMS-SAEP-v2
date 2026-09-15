"""Unidades de medida para testes (ADR-0020).

`Material.unidade` é FK: a unidade precisa existir antes do material que aponta
para ela. Teste não depende do `seed_dev` (ADR-0010), então cria a que usa.
"""

from apps.estoque.models import UNIDADES_CONHECIDAS, UnidadeMedida


def obter_unidade(codigo: str) -> UnidadeMedida:
    """Unidade de `UNIDADES_CONHECIDAS` salva, criada no primeiro uso."""
    nome, casas = UNIDADES_CONHECIDAS[codigo]
    unidade, _ = UnidadeMedida.objects.get_or_create(
        codigo=codigo,
        defaults={'nome': nome, 'casas_decimais': casas},
    )
    return unidade
