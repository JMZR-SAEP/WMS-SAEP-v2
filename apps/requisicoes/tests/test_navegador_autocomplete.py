"""Camada Navegador (ADR-0019) — comportamento do combobox de autocomplete.

Critério de admissão: cada caso aqui depende de coisa que só existe depois que
o navegador executa Alpine e a rede. `aria-expanded` e `aria-activedescendant`
são escritos em tempo de execução; a visibilidade real do alvo do
`activedescendant` depende de layout; e os estados de erro só aparecem quando
uma resposta HTTP de verdade (ou a falta de uma) atravessa o `fetch`. Nenhuma
asserção sobre HTML renderizado pelo servidor alcança qualquer um deles.

Todos os casos abaixo são regressões de achados da Etapa 4 do
`docs/plans/audit-frontend-restante.md`, reproduzidos no navegador antes da
correção.
"""

import pytest

from apps.core.tests.navegador import autenticar

pytestmark = pytest.mark.navegador

# Seletor do combobox de material da primeira linha do formset de rascunho.
COMBO_MATERIAL = '#id_itens-0-material_label'


@pytest.fixture
def pagina_rascunho(live_server, context, page, solicitante, material_disponivel):
    """Nova requisição, autenticada, com um material buscável no catálogo."""
    autenticar(live_server, context, solicitante)
    page.goto(f'{live_server.url}/requisicoes/nova/')
    page.wait_for_function('Boolean(window.Alpine)')
    return page


def _buscar(page, termo):
    """Digita no combobox e espera o debounce de 300ms mais a ida à rede."""
    campo = page.locator(COMBO_MATERIAL)
    campo.fill(termo)
    page.wait_for_timeout(900)
    return campo


def test_busca_com_resultado_anuncia_a_contagem(pagina_rascunho):
    """Só o caso "nenhum resultado" falava.

    O spinner é `aria-hidden` e abrir o listbox não anuncia nada sozinho, então
    uma busca bem-sucedida era silenciosa para quem usa leitor de tela.
    """
    _buscar(pagina_rascunho, 'MAT')

    regiao = pagina_rascunho.locator('span.sr-only[role="status"]').first
    assert 'resultado' in regiao.inner_text()


def test_seta_para_baixo_com_popup_fechado_reabre_em_opcao_visivel(
    live_server, context, page, aux_obras, outro_usuario_obras
):
    """`aria-activedescendant` apontava para uma opção em `display:none`.

    O dropdown fecha mas `resultados` continua em memória: a seta movia o
    descendente ativo dentro de um listbox fechado. Para quem enxerga, nada
    acontecia; para o leitor de tela, o foco virtual ia parar numa opção
    invisível de um listbox anunciado como fechado.

    O caso roda no combobox de BENEFICIÁRIO, e não no de material, porque só
    ali o estado sob teste é alcançável de verdade: o de material é
    `type="search"`, onde o Esc nativo do Chrome limpa o campo e leva os
    resultados junto. O de beneficiário é `type="text"` — o Esc fecha o
    dropdown e preserva query e resultados, que é exatamente a combinação que
    quebrava.
    """
    autenticar(live_server, context, aux_obras)
    page.goto(f'{live_server.url}/requisicoes/nova/')
    page.wait_for_function('Boolean(window.Alpine)')
    page.locator('input[name="modo_criacao"][value="outro"]').check()

    campo = page.locator('#id_beneficiario_id')
    campo.click()
    page.wait_for_timeout(900)
    assert page.locator('#id_beneficiario_id').get_attribute('aria-expanded') == 'true'

    campo.press('Escape')
    page.wait_for_timeout(200)
    assert campo.get_attribute('aria-expanded') == 'false'
    assert campo.get_attribute('aria-activedescendant') is None

    campo.press('ArrowDown')
    page.wait_for_timeout(200)

    assert campo.get_attribute('aria-expanded') == 'true'
    alvo = campo.get_attribute('aria-activedescendant')
    assert alvo, 'a seta precisa marcar uma opção ao reabrir'
    assert page.locator(f'#{alvo}').is_visible(), (
        'aria-activedescendant não pode apontar para opção invisível'
    )


def test_limpar_o_campo_nao_reabre_o_catalogo_inteiro(pagina_rascunho):
    """O piso de `minChars` vale também para a busca vazia.

    O input é `type="search"`: o Esc nativo do Chrome limpa o campo e emite
    `input`. O gate deixava `q === ''` passar, e 300ms depois o dropdown
    reabria com o catálogo inteiro — exatamente o gesto que a pessoa fez para
    fechá-lo, e uma ida à rede que o piso existe para evitar.
    """
    campo = _buscar(pagina_rascunho, 'MAT')
    assert campo.get_attribute('aria-expanded') == 'true'

    campo.fill('')
    pagina_rascunho.wait_for_timeout(900)

    assert campo.get_attribute('aria-expanded') == 'false'


def test_falha_de_rede_mostra_erro_e_nao_finge_busca_vazia(pagina_rascunho):
    """403/500/queda de rede caíam no texto de "nada encontrado", ou em nada.

    Um 403 devolve JSON sem a chave `resultados` — virava lista vazia e a tela
    dizia que a busca não achou nada, quando o que houve foi falta de
    permissão. Um 500 devolve HTML e estourava no parse: o spinner sumia e o
    componente ficava mudo.
    """
    pagina_rascunho.route('**/materiais/busca/**', lambda rota: rota.abort())

    _buscar(pagina_rascunho, 'MAT')

    erro = pagina_rascunho.locator('p[data-erro-busca]')
    assert erro.is_visible(), 'falha de busca precisa dizer que falhou'
    assert 'Não foi possível buscar' in erro.inner_text()
    vazio = pagina_rascunho.locator('p[role="status"]:not([data-erro-busca])').first
    assert not vazio.is_visible(), (
        'erro de rede não pode se passar por "nenhum resultado"'
    )


def test_busca_boa_depois_do_erro_limpa_o_estado(pagina_rascunho):
    """O erro não pode grudar: a tentativa seguinte é a recuperação."""
    pagina_rascunho.route('**/materiais/busca/**', lambda rota: rota.abort())
    _buscar(pagina_rascunho, 'MAT')
    assert pagina_rascunho.locator('p[data-erro-busca]').is_visible()

    pagina_rascunho.unroute('**/materiais/busca/**')
    _buscar(pagina_rascunho, 'MAT0')

    assert not pagina_rascunho.locator('p[data-erro-busca]').is_visible()
    assert pagina_rascunho.locator('li[role="option"]').count() > 0


def test_opcao_respeita_o_piso_de_toque(pagina_rascunho):
    """A linha tinha 36px — o alvo que o almoxarifado toca em pé, no galpão."""
    pagina_rascunho.set_viewport_size({'width': 1280, 'height': 800})
    _buscar(pagina_rascunho, 'MAT')

    caixa = pagina_rascunho.locator('li[role="option"]').first.bounding_box()
    assert caixa['height'] >= 44, f'opção com {caixa["height"]}px, piso é 44px'


def test_opcao_ativa_tem_indicador_alem_do_fundo(pagina_rascunho):
    """`bg-primary-subtle` sozinho separa a opção ativa do branco por 1.09:1.

    A WCAG 1.4.11 pede 3:1 para identificar estado, e este é o único sinal de
    onde as setas do teclado estão.
    """
    campo = _buscar(pagina_rascunho, 'MAT')
    campo.press('ArrowDown')
    pagina_rascunho.wait_for_timeout(200)

    sombra = pagina_rascunho.locator('li[aria-selected="true"]').first.evaluate(
        'el => getComputedStyle(el).boxShadow'
    )
    assert 'inset' in sombra, f'opção ativa sem anel: {sombra}'
