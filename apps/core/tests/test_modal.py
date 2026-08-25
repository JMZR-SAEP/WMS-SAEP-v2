"""Testes diretos de components/modal.html (sem DB, sem view)."""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Template

from apps.core.tests.marcacao import atributo, elementos, pares


def _render_modal(**ctx):
    """Renderiza o componente. Valor não-string vai pelo contexto, não literal.

    `{% include ... with x="True" %}` entrega a **string** "True", que é
    verdadeira para qualquer `{% if %}` — inclusive quando o teste quis dizer
    `False`. Bool e None viram variável de contexto para que o template receba
    o mesmo tipo que uma view lhe entregaria.
    """
    ctx.setdefault('id', 'meu-modal')
    ctx.setdefault('titulo', 'Título')
    contexto, literais = {}, []
    for chave, valor in ctx.items():
        if isinstance(valor, str):
            literais.append(f'{chave}="{valor}"')
        else:
            contexto[chave] = valor
            literais.append(f'{chave}={chave}')
    template = Template(
        '{% include "components/modal.html" with ' + ' '.join(literais) + ' %}'
    )
    return template.render(Context(contexto))


def _dialogo(html):
    """Atributos do `<dialog>`, lidos com parser e não por índice."""
    for _, atributos, _ in elementos(html, 'dialog'):
        return atributos
    raise AssertionError('modal renderizado sem <dialog>')


def test_action_url_sozinho_renderiza_form_com_action():
    html = _render_modal(action_url='/confirmar/')
    assert 'action="/confirmar/"' in html
    assert '<form' in html


def test_submit_form_id_e_action_url_juntos_falha_validacao():
    with pytest.raises(ImproperlyConfigured):
        _render_modal(action_url='/confirmar/', submit_form_id='form-externo')


def test_nenhum_dos_dois_falha_validacao():
    with pytest.raises(ImproperlyConfigured):
        _render_modal()


def test_submit_form_id_sozinho_nao_renderiza_form_interno():
    html = _render_modal(submit_form_id='form-externo')
    assert 'form-externo' in html
    assert '<form' not in html


def test_form_htmx_bloqueia_duplo_envio_no_proprio_htmx():
    """O bloqueio de duplo envio deste form tem que estar no HTMX, não só no JS.

    `form-submit.js` escuta `submit` em `document`, depois do listener que o
    HTMX instala no próprio `<form>`, e o HTMX não consulta `defaultPrevented`
    antes de emitir o XHR — o `preventDefault()` de lá chega tarde. Sem
    `hx-sync`, um clique duplo no rodapé grava duas vezes uma ação que o modal
    apresenta como irreversível.
    """
    html = _render_modal(action_url='/confirmar/')
    assert 'hx-sync="this:drop"' in html


def _corpo(html):
    """Atributos do `<div data-modal-body>`, lidos com parser e não por índice."""
    for _, atributos, _ in elementos(html, 'div'):
        if atributo(atributos, 'data-modal-body'):
            return atributos
    raise AssertionError('modal renderizado sem [data-modal-body]')


def _tem(atributos: str, nome: str) -> bool:
    """Presença de atributo sem valor (`data-modal-confirm`, `disabled`)."""
    return any(chave.lower() == nome for chave, _ in pares(atributos))


def _botoes(html):
    """Atributos de cada `<button>` do modal, em ordem de DOM."""
    return [atributos for _, atributos, _ in elementos(html, 'button')]


def test_corpo_do_modal_e_focavel_por_programa():
    """O corpo tem que ser focável por programa (#132).

    `tabindex="-1"` faz dele o primeiro focável do diálogo, que é onde os passos
    nativos de `showModal()` põem o foco antes de `modal.js` decidir — e é a
    única perna que sobra num modal sem botão de dispensa. Sem o atributo, essa
    janela entrega o foco a um botão do rodapé.
    """
    corpo = _corpo(_render_modal(action_url='/confirmar/'))
    assert atributo(corpo, 'data-modal-body') == 'meu-modal'
    assert atributo(corpo, 'tabindex') == '-1'


def test_rodape_marca_a_dispensa_e_a_confirmacao_com_ganchos_distintos():
    """`data-modal-dismiss` é o par de `data-modal-confirm` (#132).

    `modal.js` precisa distinguir "o botão que só fecha" de "o botão que
    executa" para levar o foco de abertura ao primeiro. Um rodapé com os dois
    ganchos no mesmo botão, ou sem o de dispensa, devolve o foco ao caminho
    perigoso sem quebrar nada visível.
    """
    botoes = _botoes(_render_modal(action_url='/confirmar/'))
    dispensa = [i for i, a in enumerate(botoes) if _tem(a, 'data-modal-dismiss')]
    confirmacao = [i for i, a in enumerate(botoes) if _tem(a, 'data-modal-confirm')]

    assert len(dispensa) == 1
    assert len(confirmacao) == 1
    assert dispensa != confirmacao, 'Os dois ganchos caíram no mesmo botão.'
    # Dispensa antes da confirmação na ordem do DOM: é ela que o `querySelector`
    # de `focarPrimeiroCampo` encontra, e é ela que vem primeiro na tabulação a
    # partir do corpo.
    assert dispensa[0] < confirmacao[0]


def test_botao_de_dispensa_nao_e_o_que_submete():
    """O gancho de dispensa nunca pode cair num `<button type="submit">`.

    Seria o pior dos dois mundos: o foco de abertura iria para um botão que
    executa a ação, com o nome de quem não executa.
    """
    for atributos in _botoes(_render_modal(action_url='/confirmar/')):
        if _tem(atributos, 'data-modal-dismiss'):
            assert atributo(atributos, 'type') == 'button'


def test_form_do_modal_barra_submissao_implicita():
    """Enter num campo de linha única não pode confirmar a ação (#132).

    O modal de devolução abre com o foco num `<input type="number">`. A
    submissão implícita do HTML levaria o POST direto, pulando o rodapé — que é
    onde a frase que descreve a consequência está.
    """
    formularios = [
        atributos
        for _, atributos, _ in elementos(
            _render_modal(action_url='/confirmar/'), 'form'
        )
    ]
    assert formularios, 'modo action_url renderizado sem <form>'
    assert (
        atributo(formularios[0], '@keydown.enter') == 'bloquearSubmitImplicito($event)'
    )


def test_modo_submit_form_id_tambem_barra_submissao_implicita():
    """Sem `<form>` próprio a trava continua necessária (#132).

    Neste modo o `<dialog>` costuma ficar **dentro** do formulário que confirma
    — `requisicoes/atender_retirada.html` abre o `<form>` antes do diálogo —, e
    um campo no corpo do modal pertenceria a esse form externo. Hoje nenhum
    consumidor do modo tem campo no corpo; a trava é o que impede que o primeiro
    a ter reabra o buraco em silêncio.
    """
    html = _render_modal(submit_form_id='form-externo')
    assert '<form' not in html
    envolvente = next(
        atributos
        for _, atributos, _ in elementos(html, 'div')
        if atributo(atributos, '@keydown.enter')
    )
    assert atributo(envolvente, '@keydown.enter') == 'bloquearSubmitImplicito($event)'


def test_modo_submit_form_id_mantem_o_contrato_de_foco():
    """O corpo focável e o gancho de dispensa valem nos dois modos do modal."""
    html = _render_modal(submit_form_id='form-externo')
    assert atributo(_corpo(html), 'tabindex') == '-1'
    assert any(_tem(a, 'data-modal-dismiss') for a in _botoes(html))


def _corpos_dos_moldes(html):
    """Conteúdo de cada `<template data-modal-erro-transporte>`, sem a tag."""
    corpos = []
    for pedaco in html.split('<template data-modal-erro-transporte=')[1:]:
        corpos.append(pedaco.split('</template>')[0])
    assert corpos, 'modal renderizado sem molde de falha de transporte'
    return corpos


def _moldes_de_transporte(html):
    """Atributos de cada `<template data-modal-erro-transporte>`, em ordem."""
    return {
        atributo(atributos, 'data-modal-erro-transporte'): atributos
        for _, atributos, _ in elementos(html, 'template')
        if atributo(atributos, 'data-modal-erro-transporte')
    }


def test_modal_traz_o_slot_e_os_dois_moldes_de_falha_de_transporte():
    """5xx e queda de conexão têm superfície pronta no HTML (#133).

    O JS não renderiza a caixa: ele clona o que o servidor deixou no
    `<template>`. Sem o slot ou sem os moldes, `mostrarFalhaDeTransporte` vira
    no-op e a falha volta a ser silenciosa — que é exatamente o defeito.
    """
    html = _render_modal(action_url='/confirmar/')

    assert 'data-modal-erro-transporte-slot' in html
    assert set(_moldes_de_transporte(html)) == {'conexao', 'servidor'}


def test_moldes_de_transporte_valem_tambem_no_modo_submit_form_id():
    """O corpo é fonte única: os moldes vêm nos dois modos.

    Hoje eles não são alcançáveis neste modo — o `<dialog>` fica **dentro** do
    formulário que confirma, e evento de htmx sobe a partir de quem emitiu, logo
    nunca chega aos listeners do diálogo; e o único consumidor do modo
    (`requisicoes/atender_retirada.html`) nem usa htmx. O que este teste guarda é
    que `_modal_body.html` continua sendo uma grafia só: um `{% if %}` que
    poupasse os moldes aqui é como o modo vira um componente paralelo, e é ele
    que teria de ser desfeito no dia em que o modo ganhar `hx-post`.
    """
    html = _render_modal(submit_form_id='form-externo')

    assert 'data-modal-erro-transporte-slot' in html
    assert set(_moldes_de_transporte(html)) == {'conexao', 'servidor'}


def test_falha_de_transporte_usa_a_caixa_canonica_de_erro():
    """A caixa é a de `{% erros_do_formulario %}`, não uma terceira grafia.

    `data-error-summary` e `role="alert"` são o que `error_summary.html` emite —
    se a caixa passar a ser montada em `modal.js`, o mesmo erro volta a parecer
    coisa diferente conforme a tela, e o anúncio depende de quem escreveu o JS.
    """
    html = _render_modal(action_url='/confirmar/', acao_erro='estornar a saída')

    assert html.count('data-error-summary') == 2
    assert html.count('role="alert"') == 2
    # O verbo da tela chega à frase-líder das duas caixas.
    assert html.count('Não foi possível estornar a saída:') == 2


def test_texto_da_falha_de_transporte_e_copy_de_produto_em_pt_br():
    """Nem status code cru, nem jargão de rede (#133).

    A pessoa que vê isto acabou de confirmar uma operação irreversível: o texto
    tem que dizer o que fazer para descobrir se ela foi registrada.
    """
    html = _render_modal(action_url='/confirmar/')

    assert 'A conexão com o servidor caiu durante o envio.' in html
    assert 'O servidor não concluiu esta ação.' in html
    # A varredura é dos dois moldes, e não do modal inteiro: no dia em que um
    # consumidor tiver um campo "Status" ou uma `action_url` com esquema, um
    # teste de escopo aberto acusaria a tela errada.
    for corpo in _corpos_dos_moldes(html):
        for proibido in ('500', 'Internal Server Error', 'HTTP', 'XHR', 'status'):
            assert proibido not in corpo, f'{proibido!r} vazou para a copy.'


def test_moldes_de_transporte_nao_repetem_id_entre_si():
    """Dois `<template>` no mesmo diálogo não podem carregar o mesmo id.

    A caixa entra no documento por clone; ids iguais nos moldes viram ids
    duplicados na página assim que os dois desfechos ocorrerem na mesma sessão,
    e é por id que `aria-describedby` e as âncoras do sumário resolvem.
    """
    html = _render_modal(action_url='/confirmar/')

    assert 'id="meu-modal-erro-conexao"' in html
    assert 'id="meu-modal-erro-servidor"' in html


def test_backdrop_ancora_o_fechamento_no_mousedown():
    """Fechar por backdrop exige o par `mousedown` + `click` (#133).

    Só com `@click`, uma seleção de texto que começa dentro da caixa e termina
    fora chega com `target` no `<dialog>` e descarta a justificativa inteira.
    """
    dialogo = next(
        atributos
        for _, atributos, _ in elementos(
            _render_modal(action_url='/confirmar/'), 'dialog'
        )
    )

    assert atributo(dialogo, '@mousedown') == 'backdropMouseDown($event)'
    assert atributo(dialogo, '@click') == 'backdropClick($event)'


def test_form_do_modal_carrega_o_hx_post_de_que_a_trava_em_voo_depende():
    """`fechar()` só trava em `form[data-submitting="1"][hx-post]` (#133).

    O recorte por `hx-post` existe para não trancar o diálogo num POST clássico,
    cuja marca de envio só é liberada pela navegação — mas ele também significa
    que este `<form>` perder o `hx-post` mataria a trava em silêncio, e a
    resposta voltaria a ser engolida por um `Esc` no meio do caminho.
    """
    formularios = [
        atributos
        for _, atributos, _ in elementos(
            _render_modal(action_url='/confirmar/'), 'form'
        )
    ]
    assert atributo(formularios[0], 'hx-post') == '/confirmar/'
    assert _tem(formularios[0], 'data-prevent-double-submit')


def test_abrir_ao_carregar_emite_open_no_dialog():
    """A abertura ao carregar é do servidor, não só do Alpine (#134).

    Antes, `abrir_ao_carregar` só existia como opção do `modalController`: o
    template documentava o parâmetro como server-side e não emitia nada. Com o
    JS fora do ar, o re-render com erro devolvia a tela aparentemente intacta e
    a caixa de erro ficava dentro de um `<dialog>` invisível — a ação
    irreversível tinha sido recusada e ninguém era avisado.
    """
    dialogo = _dialogo(_render_modal(action_url='/confirmar/', abrir_ao_carregar=True))
    assert _tem(dialogo, 'open')


def test_modal_comum_nao_emite_open():
    """O caso normal continua fechado — `open` é a exceção, não o default."""
    for html in (
        _render_modal(action_url='/confirmar/'),
        _render_modal(action_url='/confirmar/', abrir_ao_carregar=False),
        _render_modal(action_url='/confirmar/', abrir_ao_carregar=''),
    ):
        assert not _tem(_dialogo(html), 'open')


@pytest.mark.parametrize('literal', ['true', 'false', 'True', 'False'])
def test_abrir_ao_carregar_com_yesno_falha_no_render(literal):
    """`|yesno` em `abrir_ao_carregar` abriria todo modal, em silêncio (#134).

    O idioma anterior era `erro|yesno:"true,false"`, porque o destino era uma
    expressão JavaScript. O mesmo filtro apontado ao parâmetro de hoje entrega
    a string "false" a um `{% if %}`, que a considera verdadeira. O erro é mudo
    por natureza — o modal abre e nada quebra —, então o render é o único lugar
    onde ele pode gritar.
    """
    with pytest.raises(ImproperlyConfigured):
        _render_modal(action_url='/confirmar/', abrir_ao_carregar=literal)


def test_dialogo_nao_declara_contencao_de_rolagem_que_nao_governa():
    """`overscroll-contain` não pertence ao `<dialog>` (#134).

    O diálogo tem `max-h` e nunca ganha barra de rolagem própria; a contenção
    ali não tinha nada que conter, e a rolagem que chegava ao fim do corpo
    continuava passando para a tela atrás.
    """
    assert 'overscroll-contain' not in atributo(
        _dialogo(_render_modal(action_url='/confirmar/', erro='falhou')), 'class'
    )


def test_corpo_rolavel_contem_a_propria_rolagem():
    """Quem rola é a caixa do corpo, e é ela que declara a contenção (#134)."""
    html = _render_modal(action_url='/confirmar/', erro='falhou')
    rolaveis = [
        atributo(atributos, 'class')
        for _, atributos, _ in elementos(html, 'div')
        if 'overflow-y-auto' in (atributo(atributos, 'class') or '')
    ]
    assert rolaveis, 'modal com corpo renderizado sem região rolável'
    for classes in rolaveis:
        assert 'overscroll-contain' in classes


def test_modal_nao_declara_x_trap():
    """`x-trap` saiu do componente inteiro (#134).

    Os três efeitos eram nulos ou redundantes: a expressão nunca reavaliava, e
    trap de foco e `.inert` repetem por JS o que `showModal()` já faz pelo top
    layer. O que faltava — a trava de rolagem — é explícito em `modal.js`.
    """
    for html in (
        _render_modal(action_url='/confirmar/'),
        _render_modal(submit_form_id='form-externo'),
    ):
        assert 'x-trap' not in html


def test_dialogo_entregue_aberto_nao_se_anuncia_como_modal():
    """`aria-modal` acompanha o que o diálogo é, não o que ele vai virar (#134).

    Aberto pelo atributo `open`, o `<dialog>` é não-modal: o resto da página
    continua operável e o "Voltar" do rodapé — que é `@click="fechar()"` — está
    morto sem Alpine. Anunciar "modal" ali prende o leitor de tela num diálogo
    sem saída. Quem sobe o valor para "true" é `modal.js`, no mesmo passo do
    `showModal()`.

    Medido (#137): a exposição implícita de `<dialog>` não se reflete no
    atributo HTML — `getAttribute('aria-modal')` continua `null` mesmo depois
    de `showModal()` —, então escrever o valor à mão não é redundante.
    """
    aberto = _render_modal(action_url='/confirmar/', abrir_ao_carregar=True)
    fechado = _render_modal(action_url='/confirmar/')

    assert atributo(_dialogo(aberto), 'aria-modal') == 'false'
    assert atributo(_dialogo(fechado), 'aria-modal') == 'true'


def test_role_default_e_dialog():
    """Sem `role` explícito, o diálogo continua `role="dialog"` (#137)."""
    assert (
        atributo(_dialogo(_render_modal(action_url='/confirmar/')), 'role') == 'dialog'
    )


def test_role_e_parametrizavel_para_alertdialog():
    """Modal de confirmação de operação irreversível pede `alertdialog` (#137).

    É o que faz o leitor de tela anunciar o corpo como alerta na abertura, e
    não só o título — o APG prescreve `alertdialog` para diálogos que exigem
    resposta imediata a algo importante, que é a família de todo modal deste
    sistema com corpo de confirmação pura.
    """
    html = _render_modal(action_url='/confirmar/', role='alertdialog')
    assert atributo(_dialogo(html), 'role') == 'alertdialog'


def test_rodape_respeita_a_area_segura_do_home_indicator():
    """O botão de confirmar não pode ficar sob a barra do sistema (#137).

    Mesma grafia de `atender_retirada.html:218` e da `.app-bar`:
    `pb-[calc(<base>+env(safe-area-inset-bottom))]`. Sem isso, um modal na
    altura máxima (estorno com justificativa, teclado aberto) deixa o botão de
    confirmar embaixo do home indicator do iPhone.
    """
    html = _render_modal(action_url='/confirmar/')
    rodapes = [atributos for _, atributos, _ in elementos(html, 'footer')]
    assert rodapes, 'modal renderizado sem <footer>'
    classe_rodape = atributo(rodapes[0], 'class') or ''
    assert 'env(safe-area-inset-bottom)' in classe_rodape


def _botao_de_confirmacao(html):
    """Atributos do botão que carrega `data-modal-confirm`."""
    for atributos in _botoes(html):
        if _tem(atributos, 'data-modal-confirm'):
            return atributos
    raise AssertionError('modal renderizado sem botão de confirmação')


def test_loading_label_chega_ao_botao_de_confirmar_no_modo_action_url():
    """O único mecanismo de feedback de submit do design system chega ao rodapé (#137).

    `loading_label` + `form-submit.js` é como o sistema inteiro mostra que um
    POST está em andamento. Sem repassar o parâmetro a `components/button.html`,
    o feedback visível de uma ação irreversível era um botão que só escurecia.
    """
    html = _render_modal(action_url='/confirmar/', loading_label='Confirmando…')
    confirmar = _botao_de_confirmacao(html)
    assert atributo(confirmar, 'data-submit-loading-label') == 'Confirmando…'


def test_loading_label_chega_ao_botao_de_confirmar_no_modo_submit_form_id():
    """A mesma troca de rótulo vale no modo sem `<form>` próprio (#137)."""
    html = _render_modal(submit_form_id='form-externo', loading_label='Confirmando…')
    confirmar = _botao_de_confirmacao(html)
    assert atributo(confirmar, 'data-submit-loading-label') == 'Confirmando…'


def test_corpo_rolavel_e_focavel_por_teclado_e_tem_nome_acessivel():
    """WCAG 2.1.1: uma região que rola tem que ser alcançável pelo teclado (#137).

    `confirmar-importacao-scpi` não tem nenhum campo no corpo — em viewport
    curta (celular com teclado aberto, landscape) o recap da importação ficava
    inalcançável pelas setas. `aria-labelledby` reaproveita o `<h2>` que o
    diálogo já tem, em vez de duplicar texto num `aria-label` novo.
    """
    html = _render_modal(action_url='/confirmar/', erro='falhou')
    rolaveis = [
        atributos
        for _, atributos, _ in elementos(html, 'div')
        if 'overflow-y-auto' in (atributo(atributos, 'class') or '')
    ]
    assert rolaveis, 'modal com corpo renderizado sem região rolável'
    for atributos in rolaveis:
        assert atributo(atributos, 'tabindex') == '0'
        assert atributo(atributos, 'aria-labelledby') == 'meu-modal-titulo'


def test_expressao_de_submit_externo_vira_metodo_do_controller():
    """O `console.error` só pode disparar quando o form realmente não existe (#137).

    `getElementById(...)?.requestSubmit() ?? console.error(...)` disparava
    sempre: `requestSubmit()` devolve `undefined`, e `undefined ?? X` avalia
    `X`. A expressão sai do template — que não tem como distinguir os dois
    casos — e vira método do `modalController`, como `validarFormId` já é.
    """
    html = _render_modal(submit_form_id='form-externo')
    confirmar = _botao_de_confirmacao(html)
    assert (
        atributo(confirmar, '@click') == "submeterFormExterno('form-externo', $event)"
    )
    assert '?? console.error' not in html


def test_nome_antigo_do_parametro_de_abertura_falha_no_render():
    """`abrir_ao_carregar_expr` morreu na #134 e não pode voltar em silêncio.

    Um chamador que ressuscite o nome antigo não abre modal nenhum — que é
    exatamente o defeito que a issue fechou, de volta e mudo.
    """
    with pytest.raises(ImproperlyConfigured):
        _render_modal(action_url='/confirmar/', abrir_ao_carregar_expr='true')
