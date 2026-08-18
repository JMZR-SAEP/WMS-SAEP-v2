/**
 * Anti double-submit — script único para formulários marcados com
 * `data-prevent-double-submit`.
 *
 * Consolida as 4 variantes que existiam inline (ver #73):
 * - rastreia o `submitter` real via clique, preservando `name`/`value` do
 *   botão no `FormData` (indispensável quando o form tem múltiplos botões
 *   submit com ações diferentes, ex. "Salvar rascunho" vs "Criar e enviar" —
 *   um botão `disabled` não envia seu `name=valor`);
 * - aplica `aria-busy="true"` e troca o rótulo via
 *   `data-submit-loading-label` / `[data-submit-text]`;
 * - `disabled` é aplicado com `setTimeout(0)`: se fosse síncrono, o clique
 *   no botão desabilitado descartaria seu `name=valor` do FormData antes do
 *   browser terminar de montar o submit;
 * - o bloqueio é por `form`, não por botão: um segundo submit disparado por
 *   outro botão do mesmo form (ex. clique rápido em "Salvar rascunho" logo
 *   seguido de "Criar e enviar") é descartado via `preventDefault` enquanto
 *   o primeiro submit está em andamento.
 *
 * Delegação de eventos em `document` — cobre formulários renderizados
 * depois via HTMX (fragmentos trocados por hx-swap) sem precisar de rebind
 * em `htmx:afterSwap`.
 *
 * ## O que o `preventDefault` daqui NÃO bloqueia
 *
 * Ele não bloqueia o HTMX. O HTMX escuta `submit` no próprio `<form>` (fase
 * de alvo) e não consulta `defaultPrevented` antes de emitir o XHR — quando
 * este listener roda, já em fase de bolha no `document`, a requisição saiu.
 * Form com `hx-post` precisa de `hx-sync="this:drop"` no próprio elemento; é
 * lá que o segundo envio morre. Ver `components/modal.html`, único form do
 * sistema que envia por HTMX. Aqui o guard segue valendo para o POST clássico
 * e continua sendo o que dá o feedback visual nos dois casos.
 *
 * ## Por que existe `liberar()`
 *
 * O estado era gravado e nunca desfeito. Num POST clássico isso passava
 * despercebido porque a página navegava — mas não em dois casos reais:
 *
 * - **modal com HTMX**: a resposta 422 troca `[data-modal-body]`, que contém
 *   o rodapé, devolvendo botões novos e habilitados; o `<form>` sobrevive com
 *   `submitting='1'`. Da segunda tentativa em diante o guard virava no-op e a
 *   ação irreversível ia sem `aria-busy`, sem troca de rótulo e sem spinner;
 * - **volta pelo bfcache**: Firefox e Safari restauram o DOM como estava, ou
 *   seja, com os botões desabilitados e o rótulo preso em "Enviando…", sem
 *   caminho de recuperação além de recarregar a página.
 *
 * A liberação restaura só o que este script mexeu, e por botão: `disabled`
 * volta ao valor que tinha antes (uma ação de workflow bloqueada pelo servidor
 * chega aqui já desabilitada e não pode ser reabilitada por efeito colateral),
 * `aria-busy` volta ao valor anterior — ou some, se não existia — e o rótulo
 * volta ao texto capturado no momento do envio.
 *
 * ## O spinner que saiu daqui
 *
 * Havia um ramo que revelava `[data-submit-spinner]` e aplicava
 * `pointer-events-none`/`cursor-wait`. Ele nasceu para `atender_retirada`
 * (plano 73) e morreu quando aquele botão passou a ser
 * `components/button.html`, que nunca emitiu o atributo (plano 94, "não
 * implementado agora — YAGNI"). Nenhum template do sistema o produz, então o
 * ramo era inalcançável e obrigava `liberar()` a escrever o inverso de código
 * que nunca roda. Se um spinner de submit voltar a ser necessário, ele volta
 * junto com o produtor do atributo e com um teste — não antes.
 */
(function () {
  'use strict';

  const submitters = new WeakMap();
  const emVoo = new WeakMap();

  function alvosDoForm(form) {
    return Array.from(
      form.querySelectorAll('button[type="submit"], button[data-modal-confirm]')
    );
  }

  function travar(form, alvos) {
    const rotulos = [];
    const botoes = alvos.map((btn) => {
      const ariaBusyAntes = btn.getAttribute('aria-busy');
      btn.setAttribute('aria-busy', 'true');

      const loading = btn.dataset.submitLoadingLabel;
      if (loading) {
        btn.querySelectorAll('[data-submit-text]').forEach((node) => {
          rotulos.push([node, node.textContent]);
          node.textContent = loading;
        });
      }

      return { btn, desabilitadoAntes: btn.disabled, ariaBusyAntes };
    });

    emVoo.set(form, { botoes, rotulos });
    return botoes;
  }

  function liberar(form) {
    if (form.dataset.submitting !== '1') {
      return;
    }
    delete form.dataset.submitting;
    submitters.delete(form);

    const estado = emVoo.get(form);
    emVoo.delete(form);
    if (!estado) {
      return;
    }

    estado.rotulos.forEach(([node, texto]) => {
      node.textContent = texto;
    });
    estado.botoes.forEach(({ btn, desabilitadoAntes, ariaBusyAntes }) => {
      btn.disabled = desabilitadoAntes;
      if (ariaBusyAntes === null) {
        btn.removeAttribute('aria-busy');
      } else {
        btn.setAttribute('aria-busy', ariaBusyAntes);
      }
    });
  }

  document.addEventListener('click', (event) => {
    const btn = event.target.closest?.(
      'button[type="submit"], button[data-modal-confirm]'
    );
    if (!btn) {
      return;
    }
    const form = btn.closest('form[data-prevent-double-submit]');
    if (!form) {
      return;
    }
    submitters.set(form, btn);
  });

  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }
    if (!form.matches('form[data-prevent-double-submit]')) {
      return;
    }

    if (form.dataset.submitting === '1') {
      event.preventDefault();
      return;
    }
    form.dataset.submitting = '1';

    const submitter = submitters.get(form);
    const botoes = travar(form, submitter ? [submitter] : alvosDoForm(form));

    setTimeout(() => {
      botoes.forEach(({ btn }) => {
        btn.disabled = true;
      });
    }, 0);
  });

  // `htmx:afterRequest` dispara em qualquer desfecho — 2xx, erro de resposta,
  // falha de rede ou abort —, que é exatamente a condição de liberação: a
  // requisição acabou, com ou sem sucesso.
  //
  // Quem libera é o elemento que fez a requisição (`event.detail.elt`), e só
  // quando ele é o próprio form protegido. O evento sobe pelo DOM, então um
  // `closest` a partir do alvo também acharia o form quando o emissor foi um
  // filho com requisição própria — o botão "Adicionar material" dentro do
  // formulário de rascunho é exatamente esse caso. Se essa requisição filha
  // terminasse com o form já travado, o bloqueio caía no meio do envio em
  // andamento.
  document.addEventListener('htmx:afterRequest', (event) => {
    const elt = event.detail?.elt;
    if (elt instanceof HTMLFormElement && elt.matches('form[data-prevent-double-submit]')) {
      liberar(elt);
    }
  });

  window.addEventListener('pageshow', (event) => {
    if (!event.persisted) {
      return;
    }
    document.querySelectorAll('form[data-prevent-double-submit]').forEach(liberar);
  });
})();
