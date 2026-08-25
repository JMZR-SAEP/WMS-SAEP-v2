"""Trava de rolagem do fundo e abertura server-side — camada Navegador (#134).

Duas regras, e as duas nasceram do mesmo defeito: mecanismo declarado que nunca
executava.

**A rolagem do fundo trava enquanto o modal está aberto.** O componente
declarava `x-trap.inert.noscroll="$refs.dialog.open"` desde sempre, e o
diretivo nunca ativou — `$refs` é `mergeProxies`, não `reactive()`, e `.open` é
propriedade IDL nativa, então o `effect` do Alpine não rastreava nada. A trava é
explícita em `modal.js` agora, presa ao par `showModal()`/evento `close`.

**O `<dialog>` que o servidor entrega aberto vira modal de verdade.** Sem JS ele
fica não-modal, o que é o comportamento certo para quem está sem JS: aparece no
fluxo, com a caixa de erro legível. Com Alpine vivo, o init o promove por
`showModal()` — sem essa promoção o diálogo ficaria na página sem top layer, sem
backdrop e sem nada inerte em volta.

Critério de admissão da ADR-0019 atendido pelas duas vias, e nenhuma é
observável no HTML renderizado: `documentElement.style.overflow` só existe
depois que o navegador aplica o efeito, e a diferença entre `<dialog open>` e
diálogo modal é o top layer, que é estado do navegador e não do documento.

A marcação fica na lane de baixo: o atributo `open` no HTML é cobrado por
`apps/core/tests/test_modal.py` (componente) e por
`test_recusar_sem_motivo_sem_htmx_devolve_o_dialogo_ja_aberto` em
`test_views.py` (a resposta real da view, que é onde a regressão apareceria).
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.tests.navegador import autenticar
from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

pytestmark = pytest.mark.navegador

_OVERFLOW = 'document.documentElement.style.overflow'

# Faz o `<html>` ter mesmo o que travar. Uma página curta demais não rola nem
# com o modal fechado, e o teste passaria medindo a ausência de conteúdo.
_VIEWPORT_CURTA = {'width': 900, 'height': 420}


@pytest.fixture
def req_para_decisao(db, solicitante, setor_obras, material_disponivel):
    """Requisição aguardando autorização — a tela do chefe do setor.

    Dá os dois modais de que esta lane precisa na mesma página:
    `confirmar-autorizar`, que abre por trigger, e `confirmar-recusar`, que é o
    único do sistema que a view devolve aberto pelo servidor.
    """
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-9340',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req,
        material=material_disponivel,
        quantidade_solicitada=Decimal('2'),
    )
    return req


@pytest.fixture
def pagina_de_decisao(live_server, context, page, chefe_obras, req_para_decisao):
    """Página de detalhe autenticada como o chefe que decide, viewport curta."""
    autenticar(live_server, context, chefe_obras)
    page.set_viewport_size(_VIEWPORT_CURTA)
    page.goto(
        f'{live_server.url}'
        + reverse('requisicoes:detalhe', kwargs={'pk': req_para_decisao.pk})
    )
    return page


# Submete o formulário do modal como um navegador sem htmx submeteria: POST
# clássico, navegação de verdade, resposta de página inteira. É esse desfecho —
# e não o 422 do htmx — que produz o `<dialog open>` que este arquivo observa.
#
# O formulário é montado à mão porque o `<dialog>` fechado é `display: none`, e
# um clique no botão do rodapé não é acionável enquanto ele está lá dentro. O
# que importa para o teste é o que o servidor devolve e o que o navegador faz
# com a resposta, e as duas coisas são reais.
_POSTAR_SEM_HTMX = """
  ({ acao, motivo }) => {
    const origem = document.querySelector(`form[action="${acao}"]`);
    const form = document.createElement('form');
    form.method = 'post';
    form.action = acao;
    for (const [nome, valor] of [
      ['csrfmiddlewaretoken', origem.elements.csrfmiddlewaretoken.value],
      ['motivo', motivo],
    ]) {
      const campo = document.createElement('input');
      campo.type = 'hidden';
      campo.name = nome;
      campo.value = valor;
      form.append(campo);
    }
    document.body.append(form);
    form.submit();
  }
"""


def _abrir_por_trigger(page, modal_id):
    page.locator(f'[data-modal-trigger="{modal_id}"]').first.click()
    page.wait_for_function(f"document.getElementById('{modal_id}').open")


def test_modal_aberto_por_trigger_trava_a_rolagem_do_fundo(pagina_de_decisao):
    """Com o modal aberto, a página atrás não rola — e volta a rolar ao fechar.

    Rolar o fundo enquanto o modal pergunta se pode executar uma ação
    irreversível tira da tela justamente o registro sobre o qual a pergunta é
    feita, e a rolagem do gesto é a mesma que a pessoa usa para ler o corpo do
    modal.
    """
    pagina = pagina_de_decisao
    assert pagina.evaluate(
        'document.documentElement.scrollHeight > document.documentElement.clientHeight'
    ), 'A página de fundo não rola nem sem modal — o teste mediria nada.'
    assert pagina.evaluate(_OVERFLOW) == ''

    _abrir_por_trigger(pagina, 'confirmar-autorizar')
    pagina.wait_for_function(f"{_OVERFLOW} === 'hidden'")

    pagina.keyboard.press('Escape')
    pagina.wait_for_function("!document.getElementById('confirmar-autorizar').open")
    pagina.wait_for_function(f"{_OVERFLOW} !== 'hidden'")

    # A trava e o diálogo são um par com invariante — travado se, e só se,
    # aberto. Um ciclo completo é o que separa "destrava" de "destrava uma vez":
    # se `abertoComoModal` e a trava saírem de sincronia, é na segunda abertura
    # que aparece, e a essa altura a página inteira estaria sem rolagem.
    _abrir_por_trigger(pagina, 'confirmar-autorizar')
    pagina.wait_for_function(f"{_OVERFLOW} === 'hidden'")
    pagina.keyboard.press('Escape')
    pagina.wait_for_function(f"{_OVERFLOW} !== 'hidden'")


def test_dialogo_entregue_aberto_pelo_servidor_vira_modal_com_o_erro_a_vista(
    live_server, pagina_de_decisao, req_para_decisao
):
    """O POST clássico devolve a página com `open`, e o Alpine promove a modal.

    É o caminho de quem está sem htmx. A caixa de erro tem que estar visível —
    o defeito que esta issue fecha é ela chegar dentro de um diálogo fechado,
    ou seja, `display: none`, com a tela parecendo que nada aconteceu.
    """
    pagina = pagina_de_decisao
    acao = reverse('requisicoes:recusar', kwargs={'pk': req_para_decisao.pk})

    pagina.evaluate(_POSTAR_SEM_HTMX, {'acao': acao, 'motivo': ' '})
    pagina.wait_for_url(f'{live_server.url}{acao}')

    dialogo = pagina.locator('dialog#confirmar-recusar')
    assert dialogo.locator('[data-modal-erro]').is_visible(), (
        'A caixa de erro voltou dentro de um diálogo fechado: a recusa foi '
        'rejeitada e a tela não diz nada.'
    )

    pagina.wait_for_function(
        "document.getElementById('confirmar-recusar').matches(':modal')"
    )
    pagina.wait_for_function(f"{_OVERFLOW} === 'hidden'")

    # O servidor entrega `aria-modal="false"`, porque até a promoção o resto da
    # página está mesmo operável. Depois dela a afirmação passa a ser verdadeira,
    # e quem a atualiza é o mesmo passo que chama `showModal()`.
    assert dialogo.get_attribute('aria-modal') == 'true', (
        'O diálogo virou modal e continuou se anunciando como não-modal.'
    )

    # Promovido, não duplicado: fechar tem que devolver a página ao estado
    # normal. Um diálogo que ficasse com o atributo `open` do servidor além do
    # `showModal()` continuaria na tela depois do `close()`.
    pagina.keyboard.press('Escape')
    pagina.wait_for_function("!document.getElementById('confirmar-recusar').open")
    pagina.wait_for_function(f"{_OVERFLOW} !== 'hidden'")


def test_o_corpo_do_modal_contem_a_propria_rolagem(pagina_de_decisao):
    """A rolagem que chega ao fim do corpo não passa para a tela atrás.

    `overscroll-contain` estava no `<dialog>`, que tem `max-h` e nunca ganha
    barra própria — não havia nada ali para conter. Quem rola é a caixa do
    corpo, e é ela que precisa do atributo. Sem navegador não há como saber
    qual dos dois elementos rola.
    """
    pagina = pagina_de_decisao
    _abrir_por_trigger(pagina, 'confirmar-recusar')

    rolagem = pagina.evaluate("""
      () => {
        const dialogo = document.getElementById('confirmar-recusar');
        const corpo = dialogo.querySelector('.overflow-y-auto');
        return {
          dialogoRola: dialogo.scrollHeight > dialogo.clientHeight,
          contencaoDoCorpo: getComputedStyle(corpo).overscrollBehavior,
        };
      }
    """)

    assert not rolagem['dialogoRola'], (
        'O `<dialog>` passou a rolar — a contenção precisa mudar de elemento junto.'
    )
    assert rolagem['contencaoDoCorpo'] == 'contain'
