"""Testes diretos de partials de badge de estoque (sem DB, sem view).

Mesma correção de `_estado_badge.html` (issue #122) para os três partials de
estoque que anulavam o fallback vermelho de `components/badge.html`: valor
não mapeado passa a gritar sob o prefixo `desconhecida:`, em vez de virar
uma cor plausível. Os dois que hoje passam `aria_label` (que o fallback do
badge.html propagaria literalmente, calando o grito para leitor de tela)
trocam para `prefixo_sr` só no ramo do grito.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.template.loader import render_to_string

TIPOS_CANONICOS = {
    'reserva': 'blue',
    'liberacao': 'slate',
    'consumo': 'indigo',
    'saida_excepcional': 'red',
    'estorno_saida': 'amber',
    'devolucao': 'teal',
    'estorno_requisicao': 'violet',
}


def _movimentacao(tipo, rotulo='Rótulo do tipo'):
    return SimpleNamespace(tipo=tipo, rotulo=rotulo)


def _render_tipo_movimentacao(tipo, rotulo='Rótulo do tipo'):
    mov = _movimentacao(tipo, rotulo)
    return render_to_string(
        'estoque/partials/_badge_tipo_movimentacao.html',
        {'tipo': mov.tipo, 'rotulo': mov.rotulo},
    )


def _saida(estado, label='Rótulo do estado'):
    return SimpleNamespace(estado=estado, get_estado_display=lambda: label)


def _render_saida(estado, label='Rótulo do estado'):
    return render_to_string(
        'estoque/partials/_estado_saida_badge.html',
        {'saida': _saida(estado, label)},
    )


# ─── _badge_tipo_movimentacao.html ─────────────────────────────────────────


def test_tipo_inexistente_renderiza_indisponivel_visivel():
    html = _render_tipo_movimentacao('tipo-que-nao-existe')
    assert 'Indisponível' in html


def test_tipo_inexistente_emite_data_badge_variant_prefixado():
    html = _render_tipo_movimentacao('tipo-que-nao-existe')
    assert 'data-badge-variant="desconhecida:tipo-que-nao-existe"' in html


def test_tipo_orange_colide_mas_gruda_no_fallback():
    html = _render_tipo_movimentacao('orange')
    assert 'Indisponível' in html
    assert 'bg-orange-100' not in html


def test_tipo_inexistente_preserva_rotulo_real():
    html = _render_tipo_movimentacao('tipo-que-nao-existe', rotulo='Reserva de saída')
    assert 'Reserva de saída' in html


def test_tipo_inexistente_nao_emite_aria_label():
    html = _render_tipo_movimentacao('tipo-que-nao-existe')
    assert 'aria-label=' not in html


def test_tipo_inexistente_nome_acessivel_contem_indisponivel_e_rotulo():
    html = _render_tipo_movimentacao('tipo-que-nao-existe', rotulo='Reserva de saída')
    assert 'Tipo de movimentação: ' in html
    assert 'Indisponível' in html
    assert 'Reserva de saída' in html


@pytest.mark.parametrize('tipo,variant_esperada', sorted(TIPOS_CANONICOS.items()))
def test_tipo_canonico_mantem_variante_de_hoje(tipo, variant_esperada):
    html = _render_tipo_movimentacao(tipo)
    marcadores = {
        'blue': 'bg-primary-muted ',
        'slate': 'bg-bg-subtle',
        'indigo': 'bg-indigo-100',
        'red': 'bg-danger-muted ',
        'amber': 'bg-warning-muted ',
        'teal': 'bg-return-muted',
        'violet': 'bg-violet-100',
    }[variant_esperada]
    assert marcadores in html
    # `prefixo_sr` e não `aria-label`+`role="status"`: badge de dado estático não
    # é live region (contrato escrito em components/badge.html), e no ledger eram
    # 25 delas por página. Texto `sr-only` é sempre exposto; `aria-label` num
    # <span> sem role, não — a spec ARIA não garante.
    assert '<span class="sr-only">Tipo de movimentação: </span>' in html
    assert 'role="status"' not in html
    assert 'aria-label=' not in html


# ─── _estado_saida_badge.html ──────────────────────────────────────────────


def test_saida_inexistente_renderiza_indisponivel_visivel():
    html = _render_saida('estado-que-nao-existe')
    assert 'Indisponível' in html


def test_saida_inexistente_emite_data_badge_variant_prefixado():
    html = _render_saida('estado-que-nao-existe')
    assert 'data-badge-variant="desconhecida:estado-que-nao-existe"' in html


def test_saida_orange_colide_mas_gruda_no_fallback():
    html = _render_saida('orange')
    assert 'Indisponível' in html
    assert 'bg-orange-100' not in html


def test_saida_inexistente_nao_emite_aria_label():
    html = _render_saida('estado-que-nao-existe')
    assert 'aria-label=' not in html


def test_saida_inexistente_nome_acessivel_contem_indisponivel_e_rotulo():
    html = _render_saida('estado-que-nao-existe', label='Registrada')
    assert 'Estado: ' in html
    assert 'Indisponível' in html
    assert 'Registrada' in html


def test_saida_registrada_mantem_blue_strong():
    html = _render_saida('registrada')
    assert 'bg-primary-muted-strong' in html


def test_saida_estornada_usa_teal_forte():
    """`estornada` tem ramo explícito próprio (senão o grito pintaria todo
    estorno de vermelho). Desde a issue #157 sobe para `teal-strong` — fundo
    shade 200 — para não empatar no varrimento com o verde de "Atendida".
    """
    html = _render_saida('estornada')
    assert 'bg-return-muted-strong' in html
    assert 'ring-return-border-strong' in html
    assert 'Indisponível' not in html


# ─── _alert_divergencias_corpo.html ────────────────────────────────────────


def _render_divergencias(divergencias=3):
    return render_to_string(
        'estoque/partials/_alert_divergencias_corpo.html',
        {'divergencias': divergencias},
    )


def test_alerta_de_divergencia_nomeia_quem_decide_e_a_proxima_acao():
    """Um âmbar mudo parece erro do sistema para quem confia no papel.

    O `DESIGN.md` define âmbar como "a decisão está com alguém"; a decisão do
    dono do produto (issue #123) diz que esse alguém é o chefe de almoxarifado,
    e que a ação é ajustar no SCPI. A copy antiga informava só o efeito técnico.
    """
    html = _render_divergencias()
    assert 'chefe de almoxarifado' in html
    assert 'ajustar no SCPI' in html


def test_alerta_de_divergencia_enquadra_a_divergencia_como_esperada():
    """`PRODUCT.md`: divergência entre WMS e SCPI é estado normal, não erro.

    O fluxo é reexecutado por gente que confia mais no papel do que no
    software. Sem dizer que é esperado, o âmbar lê como falha da importação.
    """
    html = _render_divergencias()
    assert 'estado esperado da coexistência com o SCPI' in html
    assert 'não é falha da importação' in html


def test_alerta_de_divergencia_nomeia_os_dois_lados_sem_jargao():
    """O WMS é a fonte do saldo; o SCPI informa uma quantidade em arquivo.

    "registradas como alerta" descreve o que o sistema fez consigo mesmo, não o
    que o usuário está vendo. `CONTEXT.md` define divergência como a diferença
    entre a quantidade do arquivo SCPI e o saldo do WMS — é esse par que a copy
    precisa nomear, preservando a garantia de que o saldo do WMS não muda.
    """
    html = _render_divergencias()
    assert 'saldo do WMS' in html
    assert 'quantidade informada no arquivo do SCPI' in html
    assert 'saldo do WMS não será alterado' in html
    assert 'registrada' not in html


# ─── _alert_novos_materiais_corpo.html ─────────────────────────────────────


def _render_novos(novos=2):
    return render_to_string(
        'estoque/partials/_alert_novos_materiais_corpo.html',
        {'novos': novos},
    )


def test_alerta_de_materiais_novos_diz_quem_confere_o_catalogo():
    """O material novo entra no catálogo com uma unidade que ninguém escolheu.

    `confirmar_importacao_scpi` cria o material com `unidade=UNIDADE` fixa,
    porque o CSV do SCPI não informa unidade, e com o nome vindo da denominação
    do arquivo. Existe conferência humana pendente de fato — e ela é do mesmo
    dono que decide sobre a divergência.
    """
    html = _render_novos()
    assert 'unidade' in html
    assert 'chefe de almoxarifado' in html
    assert 'conferir' in html


# ─── Regra dos 14px nos dois corpos ────────────────────────────────────────


@pytest.mark.parametrize('render', [_render_divergencias, _render_novos])
def test_corpo_de_alerta_do_preview_usa_14px(render):
    """`DESIGN.md` reserva 12px a rótulo estrutural em caixa alta.

    Aqui é conteúdo numérico que sustenta a decisão do chefe de almoxarifado,
    renderizado no tamanho de metadado. "Se um texto precisa de mais presença,
    mude o peso ou o tom, não o tamanho" vale nos dois sentidos.
    """
    html = render()
    assert 'text-sm' in html
    assert 'text-xs' not in html


@pytest.mark.parametrize(
    'render,quantidade,esperado,proibido',
    [
        (_render_divergencias, 1, 'divergência', 'divergências'),
        (_render_divergencias, 2, 'divergências', None),
        (_render_novos, 1, 'material novo será criado', 'serão criados'),
        (_render_novos, 2, 'materiais novos serão criados', 'será criado'),
    ],
)
def test_corpo_de_alerta_flexiona_singular_e_plural(
    render, quantidade, esperado, proibido
):
    """A reescrita da copy não pode levar junto a flexão que já funcionava."""
    html = render(quantidade)
    assert esperado in html
    if proibido is not None:
        assert proibido not in html


# ─── _delta_movimentacao.html — precisão por unidade ───────────────────────


def _render_delta(valor, unidade='un'):
    return render_to_string(
        'estoque/partials/_delta_movimentacao.html',
        {'valor': Decimal(valor), 'unidade': unidade},
    )


@pytest.mark.parametrize(
    'valor,unidade,esperado',
    [
        ('1.000', 'un', '+1'),
        ('-3.000', 'un', '-3'),
        ('15.000', 'un', '+15'),
        ('2.500', 'kg', '+2.5'),
        ('-2.500', 'kg', '-2.5'),
        ('1.000', 'kg', '+1.0'),
    ],
)
def test_delta_usa_a_precisao_da_unidade(valor, unidade, esperado):
    """O Decimal do banco carrega três casas; a unidade decide quantas valem.

    Sem o filtro, um delta de 1 saía `+1,000` — em pt-BR isso se lê *mil*, e é
    exatamente o erro que `apps/core/quantidades.py` foi criado para matar em
    `atender_retirada`. Aqui o número é lido em pé, no galpão, ao lado do
    material físico.
    """
    assert esperado in _render_delta(valor, unidade)


@pytest.mark.parametrize('valor', ['1.000', '-3.000', '47.000'])
def test_delta_nunca_imprime_as_tres_casas_cruas(valor):
    """Guarda de regressão: o `,000` é o defeito, não o formato.

    Vale a grafia com ponto também — se alguém trocar o filtro por um
    `floatformat` fixo, o zero à direita volta por outra porta.
    """
    html = _render_delta(valor)
    assert ',000' not in html
    assert '.000' not in html


def test_delta_zero_nao_ganha_casa_decimal_da_unidade():
    """Zero é ausência de movimento, não quantidade medida.

    Em `kg` o filtro devolveria `0.0`; o literal `0` mantém a coluna curta e
    diz a coisa certa.
    """
    html = _render_delta('0.000', 'kg')
    assert '>0<' in html.replace(' ', '')
    assert '0.0' not in html


def test_delta_sem_unidade_ainda_degrada_para_o_numero_certo():
    """Chamador que esquecer a unidade não pode reintroduzir o `1,000`."""
    html = render_to_string(
        'estoque/partials/_delta_movimentacao.html', {'valor': Decimal('1.000')}
    )
    assert '+1<' in html.replace(' ', '')
    assert ',000' not in html
