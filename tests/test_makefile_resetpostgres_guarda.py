"""Testes da guarda de `DJANGO_SETTINGS_MODULE` no alvo `resetpostgres` (#218).

O alvo `resetpostgres` roda `DROP SCHEMA IF EXISTS public CASCADE` contra
`DATABASE_URL`. Ele é pré-requisito de `clean`/`veryclean`/`setup`/`resetdb`
(`init` saiu da cadeia em #225). Sem guarda, um `.env` do piloto (`DJANGO_SETTINGS_MODULE=
config.settings.piloto`) faz qualquer um desses comandos apagar os dados do
piloto.

Método de execução: cada teste roda `make` de verdade dentro de um `tmp_path`
isolado — cópia do `Makefile` real, um `.env` falso apontando para uma porta
sem PostgreSQL (127.0.0.1:5999) e um `psql` falso (só grava um
arquivo-marcador e sai 0) passado via `PSQL=`. Assim o comportamento real da
guarda é provado sem tocar em nenhum banco, mesmo que a guarda tenha um bug e
deixe passar.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE_ORIGINAL = REPO_ROOT / 'Makefile'

PSQL_FALSO = """#!/bin/sh
touch "$(dirname "$0")/psql_chamado.marker"
exit 0
"""

pytestmark = pytest.mark.skipif(
    shutil.which('make') is None or shutil.which('bash') is None,
    reason='make/bash indisponíveis neste ambiente',
)


def _preparar_projeto(
    tmp_path: Path,
    django_settings_module: str,
    *,
    database_url: str | None = 'postgres://x:y@127.0.0.1:5999/nada',
) -> Path:
    """Copia o `Makefile` real e monta `.env` falso + `psql` falso em tmp_path.

    Com `database_url=None`, o `.env` falso sai sem `DATABASE_URL`.

    Retorna o caminho do `psql` falso, pronto para ser passado como `PSQL=`.
    """
    shutil.copy(MAKEFILE_ORIGINAL, tmp_path / 'Makefile')

    linhas = [f'DJANGO_SETTINGS_MODULE={django_settings_module}\n']
    if database_url is not None:
        linhas.insert(0, f'DATABASE_URL={database_url}\n')
    (tmp_path / '.env').write_text(''.join(linhas))

    psql_falso = tmp_path / 'psql_falso.sh'
    psql_falso.write_text(PSQL_FALSO)
    modo = psql_falso.stat().st_mode
    psql_falso.chmod(modo | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return psql_falso


def _marcador(tmp_path: Path) -> Path:
    return tmp_path / 'psql_chamado.marker'


def _rodar_make(
    tmp_path: Path, *alvos: str, psql_falso: Path
) -> subprocess.CompletedProcess:
    """Roda `make` em `tmp_path` com ambiente mínimo (só PATH/HOME herdados).

    Nunca `os.environ.copy()`: o ambiente de quem roda o teste pode ter
    `DATABASE_URL`/`DJANGO_SETTINGS_MODULE` reais, e herdá-los mascararia
    exatamente o cenário que este teste existe para provar. Tudo o mais vem
    só do `.env` falso em `tmp_path`, via `include .env` do próprio Makefile.
    """
    ambiente = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': os.environ.get('HOME', ''),
    }
    return subprocess.run(
        ['make', *alvos, f'PSQL={psql_falso}'],
        cwd=tmp_path,
        env=ambiente,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _saida(resultado: subprocess.CompletedProcess) -> str:
    return resultado.stdout + resultado.stderr


@pytest.mark.parametrize('modulo', ['config.settings.dev', 'config.settings.test'])
def test_resetpostgres_com_settings_permitido_chama_psql(tmp_path, modulo):
    """A guarda deixa passar dev/test; o `psql` falso impede qualquer efeito real."""
    psql_falso = _preparar_projeto(tmp_path, modulo)

    resultado = _rodar_make(tmp_path, 'resetpostgres', psql_falso=psql_falso)

    assert resultado.returncode == 0, _saida(resultado)
    assert _marcador(tmp_path).exists()


def test_resetpostgres_com_settings_do_piloto_aborta_sem_chamar_psql(tmp_path):
    psql_falso = _preparar_projeto(tmp_path, 'config.settings.piloto')

    resultado = _rodar_make(tmp_path, 'resetpostgres', psql_falso=psql_falso)
    saida = _saida(resultado)

    assert resultado.returncode != 0
    assert 'config.settings.piloto' in saida
    assert 'config.settings.dev' in saida
    assert 'config.settings.test' in saida
    assert not _marcador(tmp_path).exists()


def test_resetpostgres_com_settings_do_piloto_sem_database_url_recusa_pela_guarda(
    tmp_path,
):
    """A guarda vem antes da checagem de `DATABASE_URL`.

    Sem `DATABASE_URL` o alvo abortaria de qualquer jeito na checagem seguinte;
    o que este teste trava é a ordem: a recusa tem de vir da guarda, não da
    falta de `DATABASE_URL`.
    """
    psql_falso = _preparar_projeto(
        tmp_path, 'config.settings.piloto', database_url=None
    )

    resultado = _rodar_make(tmp_path, 'resetpostgres', psql_falso=psql_falso)
    saida = _saida(resultado)

    assert resultado.returncode != 0
    assert 'não está na lista permitida' in saida
    assert 'DATABASE_URL não definido' not in saida
    assert not _marcador(tmp_path).exists()


def test_resetpostgres_com_settings_vazio_aborta_sem_chamar_psql(tmp_path):
    """Lista permitida, não lista proibida: um settings novo nasce protegido."""
    psql_falso = _preparar_projeto(tmp_path, '')

    resultado = _rodar_make(tmp_path, 'resetpostgres', psql_falso=psql_falso)

    assert resultado.returncode != 0
    assert not _marcador(tmp_path).exists()


def test_resetpostgres_com_settings_desconhecido_aborta_sem_chamar_psql(tmp_path):
    psql_falso = _preparar_projeto(tmp_path, 'config.settings.producao_nova')

    resultado = _rodar_make(tmp_path, 'resetpostgres', psql_falso=psql_falso)
    saida = _saida(resultado)

    assert resultado.returncode != 0
    assert 'config.settings.producao_nova' in saida
    assert not _marcador(tmp_path).exists()


def test_clean_com_settings_do_piloto_aborta_antes_de_apagar_migration(tmp_path):
    """`clean` depende de `resetpostgres`: a guarda protege a cadeia inteira."""
    psql_falso = _preparar_projeto(tmp_path, 'config.settings.piloto')

    migrations_dir = tmp_path / 'apps' / 'fake' / 'migrations'
    migrations_dir.mkdir(parents=True)
    migracao = migrations_dir / '0001_x.py'
    migracao.write_text('# migration de teste, não deve ser apagada\n')

    resultado = _rodar_make(tmp_path, 'clean', psql_falso=psql_falso)

    assert resultado.returncode != 0
    assert not _marcador(tmp_path).exists()
    assert migracao.exists()


def test_setup_com_settings_do_piloto_aborta_sem_chamar_psql(tmp_path):
    """`setup` depende de `clean` -> `resetpostgres`: a guarda também o protege."""
    psql_falso = _preparar_projeto(tmp_path, 'config.settings.piloto')

    resultado = _rodar_make(tmp_path, 'setup', psql_falso=psql_falso)

    assert resultado.returncode != 0
    assert not _marcador(tmp_path).exists()


def test_setup_com_settings_dev_continua_avancando_ate_a_guarda_deixar_passar(
    tmp_path,
):
    """`make setup` com `config.settings.dev` não pode regredir por causa da guarda.

    O teste não roda `setup` inteiro (dependeria de `uv`/Django/DB de verdade);
    prova só que a guarda do `resetpostgres` -- o pré-requisito comum -- deixa
    dev passar e chega a chamar o `psql` falso, isto é, não é a guarda que
    bloquearia `make setup` em dev.
    """
    psql_falso = _preparar_projeto(tmp_path, 'config.settings.dev')

    resultado = _rodar_make(tmp_path, 'resetpostgres', psql_falso=psql_falso)

    assert resultado.returncode == 0, _saida(resultado)
    assert _marcador(tmp_path).exists()
