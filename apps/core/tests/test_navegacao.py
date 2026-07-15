"""Testes da tag core_tags.secoes_navegacao (sem DB, sem view)."""

import pytest
from django.urls import NoReverseMatch, reverse

from apps.core.templatetags.core_tags import ICONES, NAVEGACAO, secoes_navegacao


def _todas_as_flags():
    return {
        item['flag']: True
        for secao in NAVEGACAO
        for item in secao['itens']
        if item.get('flag')
    }


def test_sem_flags_mostra_apenas_itens_sempre_visiveis():
    secoes = secoes_navegacao({})
    assert len(secoes) == 1
    (requisicoes,) = secoes
    assert requisicoes['titulo'] == 'Requisições'
    rotulos = [item['rotulo'] for item in requisicoes['itens']]
    assert rotulos == ['Nova requisição', 'Minhas requisições']


def test_flag_ligada_individualmente_mostra_item_correspondente():
    secoes = secoes_navegacao({'pode_ver_fila_autorizacao': True})
    (requisicoes,) = secoes
    rotulos = [item['rotulo'] for item in requisicoes['itens']]
    assert 'Fila de autorizações' in rotulos


def test_flag_ausente_esconde_item_e_secao_almoxarifado_some_sem_nenhuma_flag():
    secoes = secoes_navegacao({})
    titulos = [secao['titulo'] for secao in secoes]
    assert 'Almoxarifado' not in titulos


def test_uma_flag_de_almoxarifado_liga_a_secao_inteira():
    secoes = secoes_navegacao({'pode_ver_fila_atendimento': True})
    titulos = [secao['titulo'] for secao in secoes]
    assert 'Almoxarifado' in titulos
    (almoxarifado,) = [s for s in secoes if s['titulo'] == 'Almoxarifado']
    assert [item['rotulo'] for item in almoxarifado['itens']] == ['Atendimento']


def test_todas_as_flags_mostram_todos_os_itens_na_ordem_original():
    secoes = secoes_navegacao(_todas_as_flags())
    todos_rotulos = [item['rotulo'] for secao in secoes for item in secao['itens']]
    assert todos_rotulos == [
        'Nova requisição',
        'Minhas requisições',
        'Fila de autorizações',
        'Histórico de requisições',
        'Atendimento',
        'Saídas excepcionais',
        'Catálogo de materiais',
        'Movimentações',
        'Importar SCPI',
        'Histórico de importações SCPI',
    ]


def test_item_scpi_expõe_trio_de_url_names_ativos():
    secoes = secoes_navegacao({'pode_visualizar_preview_scpi': True})
    (almoxarifado,) = [s for s in secoes if s['titulo'] == 'Almoxarifado']
    (item_scpi,) = [
        item for item in almoxarifado['itens'] if item['rotulo'] == 'Importar SCPI'
    ]
    assert item_scpi['url_names_ativos'] == [
        'estoque:preview_importacao_scpi',
        'requisicoes:confirmar_importacao_scpi',
        'estoque:sucesso_importacao_scpi',
    ]


def test_item_sem_url_names_ativos_customizado_usa_apenas_o_proprio_url_name():
    secoes = secoes_navegacao({})
    (requisicoes,) = secoes
    (item,) = [i for i in requisicoes['itens'] if i['rotulo'] == 'Nova requisição']
    assert item['url_names_ativos'] == ['requisicoes:nova_requisicao']


@pytest.mark.parametrize(
    'secao_idx,item_idx',
    [
        (s_idx, i_idx)
        for s_idx, secao in enumerate(NAVEGACAO)
        for i_idx in range(len(secao['itens']))
    ],
)
def test_toda_chave_icone_existe_em_icones_com_path_nao_vazio(secao_idx, item_idx):
    item = NAVEGACAO[secao_idx]['itens'][item_idx]
    assert item['icone'] in ICONES
    assert isinstance(ICONES[item['icone']], str)
    assert ICONES[item['icone']]


def _url_name_existe(nome):
    """True se `nome` resolve sem args ou apenas exige um `pk` numérico."""
    for kwargs in ({}, {'pk': 1}):
        try:
            reverse(nome, kwargs=kwargs)
            return True
        except NoReverseMatch:
            continue
    return False


@pytest.mark.django_db
def test_todo_url_name_e_url_names_ativos_sao_resolviveis():
    secoes = secoes_navegacao(_todas_as_flags())
    for secao in secoes:
        for item in secao['itens']:
            assert _url_name_existe(item['url_name']), item['url_name']
            for nome_ativo in item['url_names_ativos']:
                assert _url_name_existe(nome_ativo), nome_ativo


def test_duas_chamadas_consecutivas_nao_compartilham_containers_mutaveis():
    primeira = secoes_navegacao({'pode_ver_fila_autorizacao': True})
    segunda = secoes_navegacao({})

    assert primeira is not segunda
    (requisicoes_primeira,) = primeira
    assert 'Fila de autorizações' in [
        item['rotulo'] for item in requisicoes_primeira['itens']
    ]

    for secao in NAVEGACAO:
        assert secao is not requisicoes_primeira
    for item_original in NAVEGACAO[0]['itens']:
        for item_retornado in requisicoes_primeira['itens']:
            assert item_retornado is not item_original
            if 'url_names_ativos' in item_original:
                assert (
                    item_retornado['url_names_ativos']
                    is not item_original['url_names_ativos']
                )
