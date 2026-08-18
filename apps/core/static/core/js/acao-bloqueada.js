/**
 * Ativação barrada em controle com `aria-disabled="true"`.
 *
 * Contraparte obrigatória do ramo `aria-disabled` de components/button.html.
 * Ao contrário do `disabled` nativo, `aria-disabled` é só um anúncio: o
 * elemento continua focável (que é justamente o ponto — sem foco, o
 * `aria-describedby` com o motivo do bloqueio nunca é alcançado por Tab) e
 * continua clicável e submetível. Sem este script, uma ação de workflow
 * bloqueada seria executável.
 *
 * Fase de captura em `document`, e com `stopPropagation`: o `@click` do Alpine
 * e o handler do HTMX ficam no próprio elemento, ou seja, rodariam antes de
 * qualquer listener de bolha. Em captura o bloqueio chega primeiro e o evento
 * nem desce até eles.
 *
 * Teclado junto do mouse porque um `<button>` focável dispara `click` com
 * Enter e Espaço; barrar só o ponteiro deixaria o teclado — exatamente quem
 * este padrão existe para atender — como a única via de executar a ação
 * bloqueada.
 */
(function () {
  'use strict';

  const SELETOR =
    'button[aria-disabled="true"], a[aria-disabled="true"], [role="button"][aria-disabled="true"]';

  function bloqueado(alvo) {
    return alvo?.closest?.(SELETOR) ?? null;
  }

  function barrar(event) {
    if (!bloqueado(event.target)) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
  }

  document.addEventListener('click', barrar, true);

  document.addEventListener(
    'keydown',
    (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') {
        return;
      }
      barrar(event);
    },
    true
  );
})();
