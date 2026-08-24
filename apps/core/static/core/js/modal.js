/**
 * modalController — Alpine factory para modais universais com <dialog>.
 *
 * Gerencia abertura/fechamento, foco preservado no trigger e integração com HTMX:
 * - HTMX 422 mantém o modal aberto e troca o corpo por fragment com erros.
 * - HTMX HX-Redirect dispara navegação; modal fecha automaticamente quando o dialog é desconectado.
 * - 5xx/403/404 e queda de conexão não trocam nada, então o controller injeta a
 *   caixa de erro que o servidor deixou pronta em `_modal_body.html`.
 * - Nenhuma via de fechamento vale enquanto a requisição está em voo.
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
      // Ancoragem do clique de backdrop: `true` só quando o `mousedown`
      // daquele clique caiu fora da caixa. Ver `backdropClick`.
      pressionouNoBackdrop: false,

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

        // `Esc` tem duas rotas, e o `@keydown.escape` de `modal.html` só cobre
        // uma. Ele está no `<dialog>`, então depende de o foco estar dentro —
        // e depois do clique em confirmar não está: `form-submit.js` desabilita
        // o botão que acabou de ser acionado, o navegador tira o foco dele e o
        // `keydown` passa a ter o `<body>` como alvo. O fechamento nativo do
        // `<dialog>` continua valendo dali, e é ele que emite `cancel`.
        //
        // Ou seja: esta é a única porta por onde a trava de requisição em voo
        // alcança o `Esc` no exato instante em que ela importa (#133).
        dialog.addEventListener('cancel', (event) => {
          if (this.formularioEmVoo()) {
            event.preventDefault();
          }
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

        // Uma tentativa nova apaga o desfecho da anterior. Sem isto, a caixa de
        // falha de transporte continuaria na tela durante o reenvio, dizendo
        // que a conexão caiu enquanto o pedido ainda está em voo.
        dialog.addEventListener('htmx:beforeRequest', () => {
          this.limparFalhaDeTransporte();
        });

        // Os dois desfechos que não trocam nada, e por isso passavam em
        // silêncio (#133). O 422 não chega aqui: o `htmx:beforeSwap` acima zera
        // o `isError`, e o htmx só emite `htmx:responseError` quando o desfecho
        // continua sendo erro. A checagem de status é redundância barata contra
        // uma mudança nessa ordem.
        dialog.addEventListener('htmx:responseError', (event) => {
          if (event.detail && event.detail.xhr && event.detail.xhr.status === 422) {
            return;
          }
          this.mostrarFalhaDeTransporte('servidor');
        });
        dialog.addEventListener('htmx:sendError', () => {
          this.mostrarFalhaDeTransporte('conexao');
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

      // Fechar com o POST em voo engole a resposta (#133): o modal some, o XHR
      // continua, e o swap de um 422 troca `[data-modal-body]` dentro de um
      // `<dialog>` já fechado — a recusa nunca é vista, e o `role="alert"` da
      // caixa de erro é anunciado num nó que não está renderizado.
      //
      // A trava é o `data-submitting="1"` que `form-submit.js` grava no envio e
      // apaga no `htmx:afterRequest`, que dispara em **qualquer** desfecho (2xx,
      // erro de resposta, falha de rede, abort). Não há caminho em que a marca
      // sobreviva ao fim da requisição, então não há caminho em que o diálogo
      // fique preso.
      //
      // Os dois modos do componente entram pela mesma porta: no modo
      // `action_url` o `<form>` está **dentro** do diálogo; no modo
      // `submit_form_id` o diálogo costuma estar **dentro** do formulário que
      // ele confirma.
      fechar() {
        const dialog = this.$refs.dialog;
        if (!dialog || !dialog.open) {
          return;
        }
        if (this.formularioEmVoo()) {
          return;
        }
        dialog.close();
      },

      formularioEmVoo() {
        const dialog = this.$refs.dialog;
        if (!dialog) {
          return null;
        }
        return (
          dialog.querySelector('form[data-submitting="1"]') ||
          dialog.closest('form[data-submitting="1"]')
        );
      },

      // Clona para dentro do slot o molde que o servidor já renderizou em
      // `_modal_body.html`. Montar a caixa aqui seria uma segunda grafia de "o
      // formulário falhou", que é a divergência que `{% erros_do_formulario %}`
      // existe para fechar — e um status code cru não é copy de produto.
      mostrarFalhaDeTransporte(chave) {
        const dialog = this.$refs.dialog;
        const slot = this.slotDeFalhaDeTransporte();
        const molde =
          dialog &&
          dialog.querySelector(
            `template[data-modal-erro-transporte="${chave}"]`
          );
        if (!slot || !molde) {
          return;
        }
        // `replaceChildren` e não `append`: uma segunda falha substitui a
        // primeira em vez de empilhar duas caixas dizendo a mesma coisa.
        slot.replaceChildren(molde.content.cloneNode(true));
      },

      limparFalhaDeTransporte() {
        const slot = this.slotDeFalhaDeTransporte();
        if (slot) {
          slot.replaceChildren();
        }
      },

      slotDeFalhaDeTransporte() {
        const dialog = this.$refs.dialog;
        return dialog
          ? dialog.querySelector('[data-modal-erro-transporte-slot]')
          : null;
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
      // O alvo são as duas origens reais de submissão implícita, e não uma
      // lista de tipos. `<input>` é a regra do HTML, que nomeia os estados de
      // texto. `<select>` **não** está nessa lista da especificação, mas o
      // navegador submete assim mesmo (medido no Chromium: Enter com o select
      // fechado dispara o submit), e ele está no seletor de
      // `focarPrimeiroCampo` — cobrir só `<input>` deixaria o buraco reaberto
      // no dia em que o primeiro modal ganhasse um `<select>`.
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

      // O `<dialog>` ocupa a área do backdrop para efeito de eventos: um ponteiro
      // fora da caixa chega com `target === dialog`. Só a geometria separa
      // "fora da caixa" de "dentro da caixa".
      noBackdrop(event) {
        const dialog = this.$refs.dialog;
        if (!dialog || event.target !== dialog) {
          return false;
        }
        const rect = dialog.getBoundingClientRect();
        const dentro =
          event.clientX >= rect.left &&
          event.clientX <= rect.right &&
          event.clientY >= rect.top &&
          event.clientY <= rect.bottom;
        return !dentro;
      },

      backdropMouseDown(event) {
        this.pressionouNoBackdrop = this.noBackdrop(event);
      },

      // Fechar por backdrop exige que o `mousedown` **e** o `mouseup` tenham
      // caído fora da caixa (#133).
      //
      // O `click` sozinho não distingue clique de arrasto: uma seleção de texto
      // que começa dentro do modal e termina no backdrop emite `click` no
      // ancestral comum, que é o próprio `<dialog>` — e a versão anterior lia
      // isso como "clicou fora", descartando a justificativa inteira. O caminho
      // inverso (pressiona no backdrop, solta dentro) morre na outra ponta,
      // porque o `click` chega com as coordenadas do `mouseup`.
      backdropClick(event) {
        const ancorado = this.pressionouNoBackdrop;
        this.pressionouNoBackdrop = false;
        if (!ancorado || !this.noBackdrop(event)) {
          return;
        }
        // Justificativa de estorno e de cancelamento são obrigatórias e podem
        // ter parágrafos, e o backdrop é o gesto mais fácil de disparar sem
        // querer do componente inteiro. Com texto digitado ele fica inerte; as
        // duas saídas deliberadas — `Esc` e o botão "Voltar" — continuam de pé,
        // e são elas que dizem que a pessoa quis mesmo sair.
        if (this.temTextoDigitado()) {
          return;
        }
        this.fechar();
      },

      // "Preenchido" é o que difere do que o servidor renderizou, e não o que
      // tem valor: um campo com default (a quantidade do modal de devolução)
      // chega preenchido sem que ninguém tenha digitado nada, e travar o
      // backdrop nele seria travar quase todo modal do sistema.
      //
      // Só texto: `<select>`, caixa e rádio são escolha de um clique, refeita
      // com outro clique, e não é isso que o backdrop destrói.
      temTextoDigitado() {
        const dialog = this.$refs.dialog;
        if (!dialog) {
          return false;
        }
        const campos = dialog.querySelectorAll(
          'textarea, input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"])'
        );
        return Array.from(campos).some(
          (campo) => campo.value !== campo.defaultValue
        );
      },
    };
  }

  document.addEventListener('alpine:init', () => {
    window.Alpine.data('modalController', controller);
  });
})();
