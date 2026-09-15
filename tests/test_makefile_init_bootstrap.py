"""Testes do bootstrap `make init` desacoplado do banco (#225).

`make init` dependia de `veryclean` -> `clean` -> `resetpostgres`. Num clone
novo, sem `.env`, o alvo falhava por falta de `DATABASE_URL`; e qualquer
tentativa de materializar o `.env` antes da limpeza faria `resetpostgres`
rodar contra a `DATABASE_URL` de exemplo. O contrato agora é: `init` só
recria o ambiente Python e materializa o `.env`, sem tocar em banco nenhum.

Método de execução: mesmo da guarda do `resetpostgres` (#218) — `make` de
verdade num `tmp_path` isolado, com cópia do `Makefile` e do `.env.example`
reais, `psql` e `uv` falsos passados como argumento do make (`PSQL=`/`UV=`),
e ambiente mínimo (só PATH/HOME herdados).
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent

PSQL_FALSO = """#!/bin/sh
touch "$(dirname "$0")/psql_chamado.marker"
exit 0
"""

# Registra os argumentos e se `.venv` ainda existia no momento do `uv sync`,
# para provar que a remoção do ambiente antigo acontece antes da instalação.
UV_FALSO = """#!/bin/sh
marcador="$(dirname "$0")/uv_chamado.marker"
printf '%s\\n' "$*" > "$marcador"
if [ -e .venv ]; then echo venv-existia >> "$marcador"; else echo venv-ausente >> "$marcador"; fi
exit 0
"""

pytestmark = pytest.mark.skipif(
    shutil.which('make') is None or shutil.which('bash') is None,
    reason='make/bash indisponíveis neste ambiente',
)


def _executavel(caminho: Path, conteudo: str) -> Path:
    caminho.write_text(conteudo)
    modo = caminho.stat().st_mode
    caminho.chmod(modo | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


def _preparar_clone(tmp_path: Path) -> None:
    """Simula um clone novo: `Makefile` + `.env.example`, sem `.env`."""
    shutil.copy(REPO_ROOT / 'Makefile', tmp_path / 'Makefile')
    shutil.copy(REPO_ROOT / '.env.example', tmp_path / '.env.example')
    _executavel(tmp_path / 'psql_falso.sh', PSQL_FALSO)
    _executavel(tmp_path / 'uv_falso.sh', UV_FALSO)


def _criar_venv_antigo(tmp_path: Path) -> Path:
    venv = tmp_path / '.venv'
    venv.mkdir()
    (venv / 'pyvenv.cfg').write_text('home = /nada\n')
    return venv


def _rodar_make(tmp_path: Path, *argumentos: str) -> subprocess.CompletedProcess:
    """Roda `make` sem herdar `DATABASE_URL`/`DJANGO_SETTINGS_MODULE` de quem testa."""
    ambiente = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': os.environ.get('HOME', ''),
    }
    return subprocess.run(
        [
            'make',
            *argumentos,
            f'PSQL={tmp_path / "psql_falso.sh"}',
            f'UV={tmp_path / "uv_falso.sh"}',
        ],
        cwd=tmp_path,
        env=ambiente,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _saida(resultado: subprocess.CompletedProcess) -> str:
    return resultado.stdout + resultado.stderr


def test_init_em_clone_sem_env_remove_venv_e_roda_uv_sync_sem_tocar_no_banco(
    tmp_path,
):
    _preparar_clone(tmp_path)
    venv = _criar_venv_antigo(tmp_path)

    resultado = _rodar_make(tmp_path, 'init')

    assert resultado.returncode == 0, _saida(resultado)
    assert not (tmp_path / 'psql_chamado.marker').exists()
    assert (tmp_path / '.env').read_text() == (tmp_path / '.env.example').read_text()
    assert (tmp_path / 'uv_chamado.marker').read_text().splitlines() == [
        'sync',
        'venv-ausente',
    ]
    assert not venv.exists()


def test_init_preserva_env_existente_e_nao_consulta_a_guarda(tmp_path):
    """Com `.env` do piloto, `init` não é recusado nem apaga banco: não há banco na cadeia."""
    _preparar_clone(tmp_path)
    env_piloto = (
        'DJANGO_SETTINGS_MODULE=config.settings.piloto\n'
        'DATABASE_URL=postgres://x:y@127.0.0.1:5999/nada\n'
    )
    (tmp_path / '.env').write_text(env_piloto)

    resultado = _rodar_make(tmp_path, 'init')

    assert resultado.returncode == 0, _saida(resultado)
    assert 'lista permitida' not in _saida(resultado)
    assert not (tmp_path / 'psql_chamado.marker').exists()
    assert (tmp_path / '.env').read_text() == env_piloto


def test_init_nao_tem_resetpostgres_na_cadeia_de_dependencias(tmp_path):
    """Prova estrutural: em dry-run, nenhuma receita de `resetpostgres` aparece."""
    _preparar_clone(tmp_path)

    resultado = _rodar_make(tmp_path, '-n', 'init')
    saida = _saida(resultado)

    assert resultado.returncode == 0, saida
    assert 'DROP SCHEMA' not in saida
    assert 'lista permitida' not in saida


def test_veryclean_segue_recriando_o_schema_em_dev(tmp_path):
    """Contrato de `veryclean` preservado: limpa banco e `.venv`."""
    _preparar_clone(tmp_path)
    (tmp_path / '.env').write_text(
        'DJANGO_SETTINGS_MODULE=config.settings.dev\n'
        'DATABASE_URL=postgres://x:y@127.0.0.1:5999/nada\n'
    )
    venv = _criar_venv_antigo(tmp_path)

    resultado = _rodar_make(tmp_path, 'veryclean')

    assert resultado.returncode == 0, _saida(resultado)
    assert (tmp_path / 'psql_chamado.marker').exists()
    assert not venv.exists()


def test_veryclean_com_settings_do_piloto_aborta_sem_apagar_venv(tmp_path):
    _preparar_clone(tmp_path)
    (tmp_path / '.env').write_text(
        'DJANGO_SETTINGS_MODULE=config.settings.piloto\n'
        'DATABASE_URL=postgres://x:y@127.0.0.1:5999/nada\n'
    )
    venv = _criar_venv_antigo(tmp_path)

    resultado = _rodar_make(tmp_path, 'veryclean')

    assert resultado.returncode != 0
    assert not (tmp_path / 'psql_chamado.marker').exists()
    assert venv.exists()
