"""Configuração de sessão do pytest válida para a suíte inteira.

Fixtures não moram aqui — elas ficam em `apps/<app>/tests/conftest.py`, como a
ADR-0010 define. Este arquivo existe só para o que precisa acontecer antes de
qualquer fixture, inclusive antes da criação do banco de teste.
"""

import os


def pytest_configure(config):
    """Libera o ORM sob o event loop do Playwright, e só quando ele vai rodar.

    A API síncrona do Playwright mantém um event loop na própria thread. O
    Django detecta esse loop e recusa acesso ao banco com
    `SynchronousOnlyOperation` — proteção pensada para código assíncrono de
    produção, onde uma query bloquearia o loop. Na camada Navegador (ADR-0019) o
    acesso é síncrono de verdade: quem está no meio é um greenlet, não uma
    corrotina.

    A liberação precisa valer antes da criação do banco de teste, que acontece
    antes de qualquer fixture — daí um hook de `pytest_configure` e não uma
    fixture autouse, que roda tarde demais.

    O ajuste é condicionado à seleção do marcador para que a suíte padrão
    (`-m "not navegador"`) mantenha a proteção do Django ligada. Expressão de
    marcador fora dessas duas formas não é reconhecida: nesse caso, exporte
    `DJANGO_ALLOW_ASYNC_UNSAFE=true` na invocação.
    """
    expressao = config.getoption('-m') or ''
    if 'navegador' in expressao and 'not navegador' not in expressao:
        os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
