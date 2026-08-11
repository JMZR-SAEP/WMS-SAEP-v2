#!/usr/bin/env python3
"""Hook PostToolUse: aplica ruff no arquivo Python recém-editado.

Os jobs `ruff format` e `ruff check` do CI são gate para mypy, migrations e
pytest (.github/workflows/ci.yml): formatação errada derruba o pipeline antes
de qualquer teste rodar. `quote-style = "single"` é não-default, então o erro
é fácil de cometer.

Entrada: JSON do hook via stdin.
Efeito: roda `ruff format` e `ruff check --fix` no arquivo.
Saída: JSON com `additionalContext` quando sobram erros não corrigíveis.
Nunca bloqueia — o modelo recebe o diagnóstico e decide.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TIMEOUT_SEGUNDOS = 30


def caminho_do_evento(evento: dict) -> str | None:
    resposta = evento.get('tool_response') or {}
    entrada = evento.get('tool_input') or {}
    caminho = resposta.get('filePath') or entrada.get('file_path')
    return caminho if isinstance(caminho, str) and caminho else None


def comando_ruff(raiz: Path) -> list[str]:
    binario = raiz / '.venv' / 'bin' / 'ruff'
    if binario.exists():
        return [str(binario)]
    return ['uv', 'run', 'ruff']


def executar(argumentos: list[str], raiz: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argumentos,
        cwd=raiz,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SEGUNDOS,
    )


def main() -> int:
    try:
        evento = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    caminho = caminho_do_evento(evento)
    if caminho is None or not caminho.endswith('.py'):
        return 0

    raiz = Path(
        evento.get('cwd') or os.environ.get('CLAUDE_PROJECT_DIR') or Path.cwd()
    ).resolve()

    arquivo = Path(caminho)
    if not arquivo.is_absolute():
        arquivo = raiz / arquivo
    arquivo = arquivo.resolve()

    if not arquivo.exists():
        return 0
    try:
        arquivo.relative_to(raiz)
    except ValueError:
        return 0

    ruff = comando_ruff(raiz)
    try:
        executar([*ruff, 'format', str(arquivo)], raiz)
        verificacao = executar([*ruff, 'check', '--fix', str(arquivo)], raiz)
    except (OSError, subprocess.SubprocessError):
        return 0

    if verificacao.returncode == 0:
        return 0

    diagnostico = (verificacao.stdout or verificacao.stderr or '').strip()
    if not diagnostico:
        return 0

    resposta = {
        'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'additionalContext': (
                'ruff check deixou erros não corrigíveis automaticamente em '
                f'{arquivo.relative_to(raiz).as_posix()} '
                '(o job `ruff check` do CI vai falhar):\n\n'
                f'{diagnostico}'
            ),
        }
    }
    json.dump(resposta, sys.stdout)
    return 0


if __name__ == '__main__':
    sys.exit(main())
