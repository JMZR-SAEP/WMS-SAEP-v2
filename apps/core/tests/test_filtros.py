"""Atalhos de recorte sobre a querystring canônica (issue #153)."""

from datetime import timedelta

from django.test import RequestFactory
from django.utils import timezone

from apps.core.filtros import montar_chip, montar_presets_periodo

_ORDEM = ('texto', 'estados', 'data_ini', 'data_fim', 'setor', 'ordem', 'page')
_MULTIVALOR = ('estados', 'tipos')


def _req(qs: str = ''):
    return RequestFactory().get(f'/historico/?{qs}' if qs else '/historico/')


def _chip(qs: str, valores):
    return montar_chip(
        _req(qs),
        id='x',
        rotulo='X',
        chave='estados',
        valores=valores,
        ordem_chaves=_ORDEM,
        chaves_multivalor=_MULTIVALOR,
    )


class TestMontarChip:
    def test_inativo_quando_valores_ausentes(self):
        chip = _chip('', ['estornada', 'recusada'])
        assert chip.ativo is False
        assert chip.url == '/historico/?estados=estornada&estados=recusada'

    def test_ativo_quando_todos_os_valores_presentes(self):
        chip = _chip('estados=estornada&estados=recusada', ['estornada', 'recusada'])
        assert chip.ativo is True

    def test_ativo_por_subconjunto_e_desliga_removendo_so_os_seus(self):
        chip = _chip(
            'estados=estornada&estados=recusada&estados=atendida',
            ['estornada', 'recusada'],
        )
        assert chip.ativo is True
        assert chip.url == '/historico/?estados=atendida'

    def test_ligar_preserva_selecao_alheia(self):
        chip = _chip('estados=atendida', ['estornada', 'recusada'])
        assert chip.ativo is False
        assert (
            chip.url
            == '/historico/?estados=atendida&estados=estornada&estados=recusada'
        )

    def test_url_e_canonica_e_dropa_page(self):
        chip = _chip('setor=3&page=2&texto=Obras', ['estornada'])
        assert chip.url == '/historico/?texto=Obras&estados=estornada&setor=3'


class TestMontarPresetsPeriodo:
    def _presets(self, qs: str = ''):
        return montar_presets_periodo(
            _req(qs), ordem_chaves=_ORDEM, chaves_multivalor=_MULTIVALOR
        )

    def test_tres_presets_com_datas_absolutas_terminando_hoje(self):
        hoje = timezone.localdate()
        presets = self._presets()
        assert [p.rotulo for p in presets] == [
            'Últimos 7 dias',
            'Últimos 30 dias',
            'Este mês',
        ]
        esperado = {
            '7d': hoje - timedelta(days=6),
            '30d': hoje - timedelta(days=29),
            'mes': hoje.replace(day=1),
        }
        for preset in presets:
            ini = esperado[preset.id].isoformat()
            assert preset.url == (
                f'/historico/?data_ini={ini}&data_fim={hoje.isoformat()}'
            )

    def test_nenhum_estado_novo_alem_de_data_ini_data_fim(self):
        query = self._presets('texto=Obras&estados=atendida')[0].url.split('?')[1]
        chaves = {p.split('=')[0] for p in query.split('&')}
        assert 'periodo' not in chaves
        assert chaves == {'texto', 'estados', 'data_ini', 'data_fim'}

    def test_ativo_quando_a_url_ja_mostra_a_janela(self):
        hoje = timezone.localdate()
        ini = (hoje - timedelta(days=29)).isoformat()
        presets = self._presets(f'data_ini={ini}&data_fim={hoje.isoformat()}')
        assert presets[1].ativo is True
        assert presets[0].ativo is False
