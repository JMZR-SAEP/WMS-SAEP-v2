"""Context processors do app de requisições.

Expõem flags de capacidade do usuário autenticado para uso no chrome
compartilhado (topbar), evitando duplicação de policy em templates.
"""

from apps.requisicoes.policies import (
    pode_ver_fila_atendimento,
    pode_ver_fila_autorizacao,
)


def flags_de_papel(request):
    """Adiciona `pode_ver_fila_*` ao contexto para o chrome global."""
    usuario = getattr(request, 'user', None)
    if usuario is None or not usuario.is_authenticated:
        return {
            'pode_ver_fila_autorizacao': False,
            'pode_ver_fila_atendimento': False,
        }
    return {
        'pode_ver_fila_autorizacao': pode_ver_fila_autorizacao(usuario),
        'pode_ver_fila_atendimento': pode_ver_fila_atendimento(usuario),
    }
