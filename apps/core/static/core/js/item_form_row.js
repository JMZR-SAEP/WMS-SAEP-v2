/**
 * itensFormset — Alpine factory para o container de linhas de item de um
 * formset dinâmico (`item_form_row.html`, ADR-0016).
 *
 * Vive no container (ex. `#itens-container`), não em cada linha, porque
 * "pode remover" depende de contar linhas-irmãs ainda visíveis — uma linha
 * isolada não enxerga as demais. As linhas herdam este escopo Alpine por
 * aninhamento normal do DOM (sem `x-data` próprio), então o botão de cada
 * linha chama `removerLinha($event)` direto.
 *
 * Uso no template chamador:
 *   <div id="itens-container" x-data="itensFormset()">
 *     {% include "components/item_form_row.html" ... %}
 *   </div>
 */
(function () {
  'use strict';

  function factory() {
    return {
      // $el reflete o elemento onde a expressão Alpine foi avaliada (o botão
      // clicado), não a raiz do x-data — por isso guardamos o container aqui.
      init() {
        this._container = this.$el;
      },

      podRemoverItem() {
        return this._container.querySelectorAll('.item-form-row:not([style*="display: none"])').length > 1;
      },

      removerLinha(event) {
        const row = event.target.closest('.item-form-row');
        if (!row) return;

        if (!this.podRemoverItem()) {
          this._avisarNaoPodeRemover(row);
          return;
        }

        const outraLinhaVisivel = Array.from(
          this._container.querySelectorAll('.item-form-row:not([style*="display: none"])')
        ).find((linha) => linha !== row);
        const botaoFoco = outraLinhaVisivel?.querySelector('button[aria-label="Remover item"]');

        row.style.display = 'none';
        const deleteInput = row.querySelector('[name$="-DELETE"]');
        if (deleteInput) deleteInput.value = 'on';
        botaoFoco?.focus();
      },

      _avisarNaoPodeRemover(row) {
        // Cor vem do token do design system, nunca de um hex hardcoded:
        // rebrand troca o valor em input.css sem tocar este arquivo.
        const cor = 'var(--color-danger-accent)';
        const aviso = document.querySelector('.aviso_quantidade');
        // O realce sozinho comunicava o bloqueio só por cor: leitor de tela não
        // recebia nada e daltônico dependia do outline. O texto muda dentro do
        // `role="status"` do próprio aviso — uma live region por formulário, não
        // por linha — e volta ao normal junto com o realce.
        const textoOriginal = aviso ? aviso.textContent : null;
        if (aviso) {
          aviso.textContent = 'É preciso manter ao menos um material.';
          aviso.style.color = cor;
        }
        row.style.outline = `2px solid ${cor}`;
        setTimeout(() => {
          if (aviso) {
            aviso.textContent = textoOriginal;
            aviso.style.color = '';
          }
          row.style.outline = '';
        }, 4000);
      },
    };
  }

  document.addEventListener('alpine:init', () => {
    window.Alpine.data('itensFormset', factory);
  });
})();
