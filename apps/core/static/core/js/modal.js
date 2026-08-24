/**
 * modalController — Alpine factory para modais universais com <dialog>.
 *
 * Gerencia abertura/fechamento, foco preservado no trigger e integração com HTMX:
 * - HTMX 422 mantém o modal aberto e troca o corpo por fragment com erros.
 * - HTMX HX-Redirect dispara navegação; modal fecha automaticamente quando o dialog é desconectado.
 *
 * Uso no template:
 *   <div x-data="modalController({ id: 'confirmar-x', abrirAoCarregar: false })">
 *
 * `validarFormId` (opcional) exige que o <form> daquele id esteja válido antes
 * de abrir — use sempre que o modal confirmar uma ação irreversível disparada
 * por um formulário da própria tela.
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
      // Id do <form> a validar antes de abrir. Ausente = abre direto (modal que
      // não confirma submit de formulário da própria tela).
      validarFormId: options.validarFormId || null,
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
        if (!this.formularioValido()) {
          return;
        }
        this.openModal();
      },

      // Um modal que confirma ação irreversível não pode abrir na frente de um
      // formulário inválido: a pessoa assume o risco e só então descobre que o
      // POST ia falhar de qualquer jeito — e o aviso perde credibilidade para a
      // vez em que importa. `novalidate` desliga a validação automática do
      // submit, não `checkValidity`/`reportValidity`, que continuam explícitas.
      formularioValido() {
        if (!this.validarFormId) {
          return true;
        }
        const form = document.getElementById(this.validarFormId);
        if (!form) {
          console.error(
            `modal ${this.id}: validarFormId ${this.validarFormId} nao encontrado`
          );
          return true;
        }
        if (form.checkValidity()) {
          return true;
        }
        form.reportValidity();
        return false;
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
        // Só `[aria-invalid="true"]`: as duas outras pernas que viviam aqui
        // (`[data-modal-erro] textarea|input`) procuravam controle dentro da
        // caixa de erro, e nunca houve nenhum — a caixa só tem texto. Casavam
        // com nada e escondiam que quem realmente marca o campo em erro é o
        // `aria-invalid` do próprio campo.
        const invalido = dialog.querySelector('[aria-invalid="true"]');
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
        // Modal sem campo visível é confirmação pura, e no sistema inteiro
        // esses são exatamente os que executam operação irreversível (enviar,
        // separar, autorizar, atender retirada, importar SCPI). O foco de
        // abertura não pode pousar no botão que executa: quem acionou o
        // trigger pelo teclado chega aqui com o Enter ainda pressionado, e o
        // `keydown` repete no elemento que acabou de receber o foco. A
        // WAI-ARIA APG manda o foco inicial de diálogo de confirmação para a
        // opção menos destrutiva.
        //
        // Sem botão de dispensa não há terceira perna: o foco fica onde os
        // passos nativos de `showModal()` o puseram, e `_modal_body.html` tem
        // `tabindex="-1"` justamente para que esse lugar seja o corpo do
        // diálogo — conteúdo inerte, com o `<h2>` do `aria-labelledby` e a
        // descrição do `aria-describedby`, e nada que Enter ative.
        const dispensar = dialog.querySelector('[data-modal-dismiss]');
        if (dispensar) {
          dispensar.focus();
        }
      },

      // Enter num campo de linha única submete o <form> pela regra de submissão
      // implícita do HTML, sem passar pelo rodapé — que é onde a frase que
      // descreve a consequência está. No modal de devolução o primeiro campo é
      // `<input type="number">` e recebe o foco de abertura, então a operação
      // seria confirmada por uma tecla apertada antes de a pessoa ler o que vai
      // acontecer.
      //
      // O alvo é a regra do HTML, e não uma lista de tipos: submissão implícita
      // nasce de `<input>` que não seja botão e de `<select>` — os dois estão
      // no seletor de `focarPrimeiroCampo`, então cobrir só `<input>` deixaria
      // o buraco reaberto no dia em que o primeiro modal ganhasse um `<select>`.
      //
      // Tudo o mais passa de propósito. `<textarea>` usa Enter como quebra de
      // linha; nos botões e nos links Enter é a ativação do próprio controle, e
      // o `preventDefault` do `keydown` mataria o clique ou a navegação que o
      // navegador gera como ação padrão.
      bloquearSubmitImplicito(event) {
        const alvo = event.target;
        const ehCampoDeTexto =
          alvo instanceof HTMLInputElement &&
          !['submit', 'button', 'reset', 'image'].includes(alvo.type);
        if (ehCampoDeTexto || alvo instanceof HTMLSelectElement) {
          event.preventDefault();
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
