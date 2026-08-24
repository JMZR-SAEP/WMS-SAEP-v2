"""Utilidades da camada Navegador (ADR-0019), compartilhadas entre apps.

Mesmo lugar e mesmo papel de `marcacao.py` e `contrato_modal.py`: módulo de
teste em `apps/core/tests/` importado pelos testes dos apps de domínio. Não é
`conftest.py` porque `conftest.py` só alcança o próprio diretório, e a camada
tem casos em `core` e em `requisicoes`.
"""


def autenticar(live_server, context, usuario):
    """Transplanta uma sessão logada do `Client` do Django para o navegador.

    Preencher o formulário de login em cada teste gastaria um round-trip e
    acoplaria toda a camada à marcação da tela de login — que tem testes
    próprios, na lane certa.
    """
    from django.test import Client

    cliente = Client()
    cliente.force_login(usuario)
    context.add_cookies(
        [
            {
                'name': 'sessionid',
                'value': cliente.cookies['sessionid'].value,
                'url': live_server.url,
            }
        ]
    )
