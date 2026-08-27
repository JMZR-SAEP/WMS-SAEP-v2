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


def test_esc_fecha_o_dropdown(pagina_rascunho):
    """`@keydown.escape="fecharDropdown()"` precisa ser exercido por Esc real.

    `test_seta_para_baixo_com_popup_fechado_reabre_em_opcao_visivel`, logo
    abaixo, passou a fechar o dropdown chamando `fecharDropdown()` direto via
    `Alpine.$data(...)` — necessário porque o Esc nativo do Chrome em
    `type="search"` também limpa o campo, o que não serve pra reproduzir
    aquele caso. Mas isso deixou o binding `@keydown.escape` em si sem
    nenhum teste que realmente aperta a tecla. Este caso cobre só isso: Esc
    fecha o popup (o efeito colateral de limpar o campo, próprio do
    `type="search"`, é esperado e não é o que está sob teste aqui).
    """
    campo = _buscar(pagina_rascunho, 'MAT')
    assert campo.get_attribute('aria-expanded') == 'true'

    campo.press('Escape')
    pagina_rascunho.wait_for_timeout(200)

    assert campo.get_attribute('aria-expanded') == 'false'


def test_seta_para_baixo_com_popup_fechado_reabre_em_opcao_visivel(
    live_server, context, page, aux_obras, outro_usuario_obras
):
    """`aria-activedescendant` apontava para uma opção em `display:none`.

    O dropdown fecha mas `resultados` continua em memória: a seta movia o
    descendente ativo dentro de um listbox fechado. Para quem enxerga, nada
    acontecia; para o leitor de tela, o foco virtual ia parar numa opção
    invisível de um listbox anunciado como fechado.

    Fecha via `fecharDropdown()` chamado direto no componente Alpine, não via
    Esc: os dois combobox (material e beneficiário) são `type="search"`, e o
    Esc nativo do Chrome nesse tipo de campo limpa o valor e dispara `input`
    — o que reabre a busca 300ms depois com outro conjunto de resultados
    (ou nenhum, se `minChars` não for atingido) e não reproduz o estado sob
    teste. `fecharDropdown()` só zera `aberto`/`ativo`; `query` e
    `resultados` ficam como estavam, que é justamente a combinação que
    quebrava — dropdown fechado, resultados antigos ainda em memória, campo
    com foco.
    """
    autenticar(live_server, context, aux_obras)
    page.goto(f'{live_server.url}/requisicoes/nova/')
    page.wait_for_function('Boolean(window.Alpine)')
    page.locator('input[name="modo_criacao"][value="outro"]').check()

    campo = page.locator('#id_beneficiario_id')
    campo.click()
    page.wait_for_timeout(900)
    assert page.locator('#id_beneficiario_id').get_attribute('aria-expanded') == 'true'

    page.evaluate(
        "() => Alpine.$data(document.querySelector('#id_beneficiario_id')).fecharDropdown()"
    )
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


# ── #151: estado "vinculado" vs "digitado e vinculado a nada" ──────────────────

HIDDEN_MATERIAL = '#id_itens-0-material_id'


def _selecionar_primeiro(page, termo, campo_sel=COMBO_MATERIAL):
    """Busca e clica na primeira opção do dropdown — deixa a linha vinculada."""
    campo = page.locator(campo_sel)
    campo.fill(termo)
    page.wait_for_timeout(900)
    page.locator('li[role="option"]').first.click()
    page.wait_for_timeout(150)
    return campo


def _apagar_um_caractere(page, campo):
    """Foco explícito + Backspace. `Locator.press` logo após o blur da seleção
    não estava editando o campo; um clique antes resolve."""
    campo.click()
    page.keyboard.press('End')
    page.keyboard.press('Backspace')


def test_selecionar_material_mostra_marca_de_vinculado(pagina_rascunho):
    """Selecionar da lista => borda de vínculo + ✓, e o hidden tem valor."""
    campo = _selecionar_primeiro(pagina_rascunho, 'MAT')

    assert pagina_rascunho.locator(HIDDEN_MATERIAL).input_value() != ''
    assert 'campo--vinculado' in (campo.get_attribute('class') or '')
    marca = pagina_rascunho.locator('span[x-show="vinculado && !buscando"]').first
    assert marca.is_visible(), 'marca de vinculado invisível após seleção'


def test_apagar_caractere_remove_a_marca_no_mesmo_gesto(pagina_rascunho):
    """A marca some na primeira tecla, antes do debounce de 300ms — pelo
    caminho de `onInvalidate()` que já zerava o hidden."""
    campo = _selecionar_primeiro(pagina_rascunho, 'MAT')
    assert 'campo--vinculado' in (campo.get_attribute('class') or '')

    _apagar_um_caractere(pagina_rascunho, campo)
    pagina_rascunho.wait_for_timeout(50)  # bem abaixo dos 300ms do debounce

    assert 'campo--vinculado' not in (campo.get_attribute('class') or '')
    assert pagina_rascunho.locator(HIDDEN_MATERIAL).input_value() == ''


def test_mudanca_de_vinculo_e_anunciada_na_regiao_live(pagina_rascunho):
    """vinculado -> desvinculado passa pela região `role="status"` existente."""
    campo = _selecionar_primeiro(pagina_rascunho, 'MAT')

    _apagar_um_caractere(pagina_rascunho, campo)
    pagina_rascunho.wait_for_timeout(100)  # antes de o callback limpar o texto

    regiao = pagina_rascunho.locator('span.sr-only[role="status"]').first
    assert 'Seleção desfeita' in regiao.inner_text()


def test_submit_com_texto_sem_vinculo_e_bloqueado_no_cliente(pagina_rascunho):
    """Texto digitado sem seleção => envio barrado antes do servidor, foco no
    campo culpado e mensagem visível."""
    _buscar(pagina_rascunho, 'Parafuso')
    campo = pagina_rascunho.locator(COMBO_MATERIAL)
    # Blur (não Esc: em type="search" o Esc nativo do Chrome limpa o campo, e
    # o gate só dispara com texto presente).
    campo.evaluate('el => el.blur()')
    pagina_rascunho.locator('#id_itens-0-quantidade_solicitada').fill('3')

    pagina_rascunho.get_by_role('button', name='Salvar rascunho').click()
    pagina_rascunho.wait_for_timeout(300)

    assert pagina_rascunho.url.endswith('/requisicoes/nova/'), 'o envio não foi barrado'
    gate = pagina_rascunho.locator('p[data-erro-gate]').first
    assert gate.is_visible()
    assert (
        pagina_rascunho.evaluate('document.activeElement.id')
        == 'id_itens-0-material_label'
    )
    # A mensagem do gate fica amarrada ao combobox por aria-describedby.
    descrito_por = campo.get_attribute('aria-describedby') or ''
    assert gate.get_attribute('id') in descrito_por.split()


def test_gate_aponta_a_linha_culpada_no_formset(pagina_rascunho):
    """Formset com várias linhas: o gate põe o foco na linha errada, não na
    primeira."""
    _selecionar_primeiro(pagina_rascunho, 'MAT')
    pagina_rascunho.locator('#id_itens-0-quantidade_solicitada').fill('2')

    pagina_rascunho.get_by_role('button', name='Adicionar material').click()
    pagina_rascunho.wait_for_selector('#id_itens-1-material_label')

    linha1 = pagina_rascunho.locator('#id_itens-1-material_label')
    linha1.fill('texto que não casa com nada')
    linha1.evaluate('el => el.blur()')
    pagina_rascunho.locator('#id_itens-1-quantidade_solicitada').fill('1')

    pagina_rascunho.get_by_role('button', name='Salvar rascunho').click()
    pagina_rascunho.wait_for_timeout(300)

    assert pagina_rascunho.url.endswith('/requisicoes/nova/')
    assert (
        pagina_rascunho.evaluate('document.activeElement.id')
        == 'id_itens-1-material_label'
    )
