/**
 * Alarga o alvo de navegação do cartão de listagem para o cartão inteiro.
 *
 * ## Por que existe
 *
 * O cartão de listagem (`components/table.html#card_abertura`) mede 483×256px
 * no desktop e 327px de largura no celular. Até a Etapa 5 da auditoria de
 * front-end, o único alvo navegável dentro dele era um botão "Ver detalhes" de
 * 109×44px — 4% da área. O design system exige alvo de 44px justamente porque
 * "a mesma tela é usada com o dedo, em pé, no galpão": o piso estava cumprido
 * no botão e ignorado no cartão que o continha.
 *
 * ## Por que não é um `::after` esticado
 *
 * A técnica usual para "cartão clicável" é dar ao link um pseudo-elemento
 * `position:absolute; inset:0` que cobre o cartão. Ela é uma linha de CSS e
 * seria errada aqui: o pseudo-elemento fica acima do conteúdo e mata a seleção
 * de texto do cartão inteiro. Copiar número público do WMS para conferir no
 * SCPI é rotina operacional declarada (`PRODUCT.md`, Positioning) — os dois
 * sistemas coexistem indefinidamente e a conferência entre eles é recorrente.
 * Trocar isso por um alvo maior seria pagar um problema com outro.
 *
 * Este listener preserva a seleção porque desiste quando há texto selecionado.
 *
 * ## Contrato
 *
 * A tela marca o link primário do cartão com `data-cartao-link`. O chrome não
 * ganhou parâmetro nenhum (guardrail da #83): ele reage à presença do link via
 * `has-[a[data-cartao-link]]`, e cartão sem link — ledger, catálogo — fica
 * inerte por não casar o seletor.
 *
 * Sem JS, o link do título continua sendo um `<a href>` comum e a tela
 * funciona: o alargamento é melhoria progressiva, não requisito.
 *
 * Delegado no documento, então cartão que chega por swap HTMX já nasce com o
 * comportamento — não há re-registro a fazer depois de trocar a listagem.
 */
(() => {
  'use strict';

  // Elementos que já resolvem o próprio clique. Sem esta guarda, clicar no
  // botão de uma ação secundária dentro do cartão dispararia a navegação do
  // cartão junto — e `label` está na lista porque clicar num rótulo aciona o
  // controle associado.
  const JA_INTERATIVO = 'a, button, input, select, textarea, label, summary, [role="button"]';

  document.addEventListener('click', (evento) => {
    // Clique com modificador é intenção explícita do usuário sobre o alvo real
    // (nova aba, download, menu de contexto). Encaminhar seria sequestrar.
    if (evento.defaultPrevented || evento.button !== 0) return;
    if (evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey) return;

    const alvo = evento.target;
    if (!(alvo instanceof Element)) return;

    const cartao = alvo.closest('article');
    if (!cartao) return;

    const link = cartao.querySelector('a[data-cartao-link]');
    if (!link) return;

    // O clique já caiu em algo acionável — inclusive no próprio link.
    if (alvo.closest(JA_INTERATIVO)) return;

    // Fim de uma seleção de texto, não um clique de navegação. É esta linha que
    // torna o alargamento compatível com copiar o número público.
    const selecao = window.getSelection();
    if (selecao && !selecao.isCollapsed && selecao.toString().trim() !== '') return;

    link.click();
  });
})();
