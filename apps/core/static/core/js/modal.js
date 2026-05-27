/**
 * modalController — Alpine factory para modais universais com <dialog>.
 *
 * Gerencia abertura/fechamento, foco preservado no trigger e integração com HTMX:
 * - HTMX 422 mantém o modal aberto e troca o corpo por fragment com erros.
 * - HTMX HX-Redirect dispara navegação; modal fecha automaticamente quando o dialog é desconectado.
 *
 * Uso no template:
 *   <div x-data="modalController({ id: 'confirmar-x', abrirAoCarregar: false })">
 *     ...
 *     <dialog x-ref="dialog" ...>...</dialog>
 *   </div>
 *
 * O trigger deve setar `data-modal-trigger="confirmar-x"` e chamar `abrir($event)`.
 */
(function () {
  'use strict';

  function controller(options = {}) {
    return {
      id: options.id,
      abrirAoCarregar: Boolean(options.abrirAoCarregar),
      lastTrigger: null,

      init() {
        const dialog = this.$refs.dialog;
        if (!dialog) {
          return;
        }

        if (this.abrirAoCarregar) {
          this.$nextTick(() => this.abrirSemTrigger());
        }

        dialog.addEventListener('close', () => {
          this.devolverFoco();
        });

        dialog.addEventListener('htmx:beforeSwap', (event) => {
          if (event.detail.xhr.status === 422) {
            event.detail.shouldSwap = true;
            event.detail.isError = false;
          }
        });
        dialog.addEventListener('htmx:afterSwap', (event) => {
          if (event.target.matches('[data-modal-body]')) {
            this.focarPrimeiroCampo();
          }
        });
      },

      abrir(event) {
        if (event && event.currentTarget) {
          this.lastTrigger = event.currentTarget;
        }
        this.openModal();
      },

      abrirSemTrigger() {
        const trigger = document.querySelector(
          `[data-modal-trigger="${this.id}"]`
        );
        if (trigger) {
          this.lastTrigger = trigger;
        }
        this.openModal();
      },

      fechar() {
        const dialog = this.$refs.dialog;
        if (dialog && dialog.open) {
          dialog.close();
        }
      },

      openModal() {
        const dialog = this.$refs.dialog;
        if (!dialog || dialog.open) {
          return;
        }
        dialog.showModal();
        this.$nextTick(() => this.focarPrimeiroCampo());
      },

      focarPrimeiroCampo() {
        const dialog = this.$refs.dialog;
        if (!dialog) {
          return;
        }
        const invalido = dialog.querySelector(
          '[aria-invalid="true"], [data-modal-erro] textarea, [data-modal-erro] input'
        );
        if (invalido) {
          invalido.focus();
          return;
        }
        const primeiroCampo = dialog.querySelector(
          'textarea, input:not([type="hidden"]):not([type="submit"]):not([type="button"]), select'
        );
        if (primeiroCampo) {
          primeiroCampo.focus();
          return;
        }
        const confirmar = dialog.querySelector('[data-modal-confirm]');
        if (confirmar) {
          confirmar.focus();
        }
      },

      devolverFoco() {
        if (this.lastTrigger && document.contains(this.lastTrigger)) {
          this.lastTrigger.focus();
        }
      },

      backdropClick(event) {
        const dialog = this.$refs.dialog;
        if (!dialog || event.target !== dialog) {
          return;
        }
        const rect = dialog.getBoundingClientRect();
        const dentro =
          event.clientX >= rect.left &&
          event.clientX <= rect.right &&
          event.clientY >= rect.top &&
          event.clientY <= rect.bottom;
        if (!dentro) {
          this.fechar();
        }
      },
    };
  }

  document.addEventListener('alpine:init', () => {
    window.Alpine.data('modalController', controller);
  });
})();
