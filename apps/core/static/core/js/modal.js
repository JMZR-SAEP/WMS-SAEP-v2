/**
 * modalController — Alpine factory para modais universais com <dialog>.
 *
 * Gerencia abertura/fechamento, foco preservado no trigger e integração com HTMX:
 * - HTMX 422 mantém o modal aberto e troca o corpo por fragment com erros.
 * - HTMX HX-Redirect dispara navegação; modal fecha automaticamente quando o dialog é desconectado.
 * - 5xx/403/404 e queda de conexão não trocam nada, então o controller injeta a
 *   caixa de erro que o servidor deixou pronta em `_modal_body.html`.
 * - Nenhuma via de fechamento vale enquanto a requisição está em voo.
 * - A rolagem do fundo fica travada enquanto o diálogo está aberto.
 *
 * Abrir ao carregar não é opção do controller: quem declara isso é o `open`
 * que `components/modal.html` emite quando `abrir_ao_carregar` é verdadeiro.
 * O init encontra o diálogo já aberto (não-modal, como o servidor o entregou)
 * e o reabre por `showModal()`.
 *
 * Uso no template:
 *   <div x-data="modalController({ id: 'confirmar-x' })">
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
      // Id do <form> a validar antes de abrir. Ausente = abre direto (modal que
      // não confirma submit de formulário da própria tela).
      validarFormId: options.validarFormId || null,
      // Seletor CSS de um alvo declarado da tela para receber o foco quando
      // `abrirSemTrigger` não encontra `[data-modal-trigger]` no documento —
      // por exemplo, uma ação de workflow que deixou de ser permitida pelo
      // servidor entre a submissão que falhou e o re-render. Sem isto o foco
      // fica onde o `close()` o encontrar, tipicamente o `<body>` (#137).
      // Ausente = mantém o comportamento anterior (no-op).
      focoFallbackSeletor: options.focoFallbackSeletor || null,
      lastTrigger: null,
      // Ancoragem do clique de backdrop: `true` só quando o `mousedown`
      // daquele clique caiu fora da caixa. Ver `backdropClick`.
      pressionouNoBackdrop: false,
      // `true` entre o `showModal()` deste controller e o evento `close`. Não é
      // o mesmo que `dialog.open`: o diálogo também está aberto quando o
      // servidor mandou o atributo `open` e ninguém o promoveu a modal ainda.
      abertoComoModal: false,
      // Desfaz a trava de rolagem do fundo. `null` quando não há trava ativa.
      // Ver `travarRolagemDeFundo`.
      liberarRolagemDeFundo: null,

      init() {
        const dialog = this.$refs.dialog;
        if (!dialog) {
          return;
        }

        // O servidor já entregou o diálogo aberto (`abrir_ao_carregar`), e
        // aberto assim ele é **não-modal**: sem top layer, sem backdrop, sem
        // inerte em volta. É o estado certo para quem está sem JS, e o errado
        // para quem tem — daí a promoção a modal aqui.
        if (dialog.open) {
          this.$nextTick(() => this.abrirSemTrigger());
        }

        dialog.addEventListener('close', () => {
          this.abertoComoModal = false;
          this.destravarRolagemDeFundo();
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
        } else {
          this.lastTrigger = this.focoFallbackAlvo();
        }
        this.openModal();
      },

      // Alvo declarado da tela para `devolverFoco` quando não há trigger no
      // documento (#137). `tabindex="-1"` é aplicado só se o alvo ainda não
      // for focável — o mesmo recurso que `_modal_body.html` já usa no corpo.
      focoFallbackAlvo() {
        if (!this.focoFallbackSeletor) {
          return null;
        }
        const alvo = document.querySelector(this.focoFallbackSeletor);
        if (!alvo) {
          return null;
        }
        if (!alvo.hasAttribute('tabindex')) {
          alvo.setAttribute('tabindex', '-1');
        }
        return alvo;
      },

      // Substitui a expressão que vivia em `_modal_body.html` (#137):
      // `getElementById(...)?.requestSubmit() ?? console.error(...)` disparava
      // o `console.error` sempre, porque `requestSubmit()` devolve `undefined`
      // e `undefined ?? X` avalia `X`. Aqui os dois casos são distintos de
      // verdade.
      //
      // Não mexe em `aria-busy`/rótulo: o botão de confirmar tem
      // `data-modal-confirm`, que já está no seletor de `alvosDoForm` de
      // `form-submit.js`, e `requestSubmit()` dispara o `submit` nativo que
      // aquele listener escuta em `document`. Duplicar a troca aqui faria os
      // dois donos brigarem pelo mesmo atributo — o `travar()` de lá capturaria
      // `aria-busy="true"` (já escrito por este método) como o valor "antes",
      // e `liberar()` devolveria o botão nesse estado errado.
      //
      // A trava de duplo envio é gravada no próprio `<form>`
      // (`data-submetendo-externo`), não numa propriedade deste componente —
      // é o que permite ao `pageshow`/bfcache no fim do arquivo desfazê-la sem
      // precisar de uma referência a cada instância do controller.
      submeterFormExterno(formId) {
        const form = document.getElementById(formId);
        if (!form) {
          console.error(`modal ${this.id}: submit_form_id ${formId} nao encontrado`);
          return;
        }
        if (form.dataset.submetendoExterno === '1') {
          return;
        }
        // Só trava se a submissão vai mesmo prosseguir. `form.noValidate` é
        // quem decide isso: com `novalidate`, `requestSubmit()` dispara
        // `submit` sempre, mesmo com campo inválido — `checkValidity()` é
        // constatação pura, indiferente ao atributo, e tratá-la sozinha como
        // "não vai prosseguir" travaria em falso o único consumidor real
        // (`form-atender-retirada` tem `novalidate`). Sem `novalidate`, um
        // campo inválido faz `requestSubmit()` barrar por dentro (nenhum
        // `submit` chega a disparar) — sem a checagem, a trava, já gravada
        // antes dessa chamada, ficava presa para sempre: a pessoa corrigia o
        // campo e o botão continuava recusando o clique. Este método também
        // não chama `reportValidity()`: quem decide se a bolha nativa aparece
        // é o `requestSubmit()` do próprio navegador, via `novalidate`.
        if (!form.noValidate && !form.checkValidity()) {
          form.requestSubmit();
          return;
        }
        form.dataset.submetendoExterno = '1';
        form.requestSubmit();
      },

      // Fechar com o POST em voo engole a resposta (#133): o modal some, o XHR
      // continua, e o swap de um 422 troca `[data-modal-body]` dentro de um
      // `<dialog>` já fechado — a recusa nunca é vista, e o `role="alert"` da
      // caixa de erro é anunciado num nó que não está renderizado.
      //
      // A trava é o `data-submitting="1"` que `form-submit.js` grava no envio e
      // apaga no `htmx:afterRequest`, que dispara em **qualquer** desfecho (2xx,
      // erro de resposta, falha de rede, abort).
      //
      // **Só form de HTMX entra na trava**, e por duas razões que apontam para
      // o mesmo lugar. A primeira é o motivo dela existir: o dano é a resposta
      // ser trocada dentro de um diálogo fechado, e só um XHR troca alguma
      // coisa — um POST clássico navega, e o diálogo vai embora com a página.
      // A segunda é que `htmx:afterRequest` é a única porta de liberação que
      // corre em tempo de página viva, e num form clássico ela nunca dispara:
      // `data-submitting="1"` fica gravado até a navegação terminar. Se a
      // navegação for abortada (`Esc` durante o carregamento interrompe o load
      // do navegador), a marca sobrevive — e sem o recorte por `hx-post` o
      // diálogo ficaria trancado sem saída, com `Esc`, backdrop e "Voltar"
      // todos mortos. Isso é real hoje: `requisicoes/atender_retirada.html` é
      // POST clássico com `data-prevent-double-submit`, e é a tela do
      // atendimento.
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
        const emVoo = 'form[data-submitting="1"][hx-post]';
        return dialog.querySelector(emVoo) || dialog.closest(emVoo);
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
        if (!dialog) {
          return;
        }
        if (dialog.open) {
          // Já está no top layer: nada a fazer. Reabrir daria
          // `InvalidStateError` em `showModal()`.
          if (this.abertoComoModal) {
            return;
          }
          // Aberto pelo atributo `open` do servidor, ou seja, não-modal.
          // `removeAttribute` e não `close()`: `close()` roda os passos de
          // fechamento e enfileira o evento `close`, que devolveria o foco ao
          // trigger e destravaria a rolagem **depois** desta abertura —
          // desfazendo em uma tarefa futura o que estamos fazendo agora.
          dialog.removeAttribute('open');
        }
        // A caixa de falha de transporte descreve a tentativa anterior, e o
        // modal reabre justamente para tentar de novo: deixá-la ali faria a
        // abertura acusar um erro que ainda não aconteceu. O `beforeRequest`
        // sozinho não cobre isto — ele só corre quando a pessoa confirma, e
        // até lá a mensagem velha fica na tela por cima de um formulário
        // intocado.
        this.limparFalhaDeTransporte();
        dialog.showModal();
        // Só agora o diálogo é modal de verdade. O template emite
        // `aria-modal="false"` quando entrega `open`, porque até esta linha o
        // resto da página está operável — e um "modal" anunciado sobre uma
        // página viva é pior do que nenhum.
        dialog.setAttribute('aria-modal', 'true');
        this.abertoComoModal = true;
        this.travarRolagemDeFundo();
        this.$nextTick(() => this.focarPrimeiroCampo());
      },

      // A trava de rolagem do fundo é explícita porque a do Alpine nunca rodou
      // aqui (#134): `x-trap.noscroll` dependia de uma expressão que o `effect`
      // não conseguia rastrear. O ciclo agora é o do próprio diálogo —
      // `showModal()` trava, o evento `close` destrava —, e `close` cobre todas
      // as saídas, inclusive o `Esc` nativo e o submit clássico.
      //
      // O gesto é o mesmo do plugin de foco do Alpine, que continua governando
      // o menu da barra de aplicação: `overflow: hidden` no `<html>` mais a
      // compensação da barra de rolagem, para a página não pular de largura ao
      // abrir. Onde o navegador já reserva a calha (`scrollbar-gutter`), a
      // compensação sairia dobrada e por isso é dispensada — a folha do projeto
      // não declara a propriedade hoje, e este ramo existe para o dia em que
      // declarar.
      //
      // São dois donos do mesmo valor global, sem contagem: este e o
      // `x-trap.noscroll` do menu. Aninhamento em LIFO se desfaz certo; um
      // intercalado, não. O que garante o LIFO hoje é o próprio menu, que fecha
      // no `@click.outside` antes de qualquer trigger de modal ser clicável.
      travarRolagemDeFundo() {
        if (this.liberarRolagemDeFundo) {
          return;
        }
        const raiz = document.documentElement;
        const overflowAnterior = raiz.style.overflow;
        const paddingAnterior = raiz.style.paddingRight;
        const larguraDaBarra = window.innerWidth - raiz.clientWidth;
        const calha = window.getComputedStyle(raiz).scrollbarGutter;

        raiz.style.overflow = 'hidden';
        if (calha && calha !== 'auto') {
          this.liberarRolagemDeFundo = () => {
            raiz.style.overflow = overflowAnterior;
          };
          return;
        }
        raiz.style.paddingRight = `${larguraDaBarra}px`;
        this.liberarRolagemDeFundo = () => {
          raiz.style.overflow = overflowAnterior;
          raiz.style.paddingRight = paddingAnterior;
        };
      },

      // Alpine chama no teardown do componente. Tirar o `<dialog>` do documento
      // enquanto ele está aberto **não** emite `close` — a especificação só o
      // remove do top layer —, e sem esta porta a página ficaria com
      // `overflow: hidden` gravado e sem rolagem até um reload. Hoje nenhum
      // caminho chega aí (o único alvo de swap é `[data-modal-body]`, e
      // `HX-Redirect` é navegação de verdade), e é justamente por ser barato
      // que não vale depender dessa coincidência.
      destroy() {
        this.destravarRolagemDeFundo();
      },

      destravarRolagemDeFundo() {
        if (!this.liberarRolagemDeFundo) {
          return;
        }
        const liberar = this.liberarRolagemDeFundo;
        this.liberarRolagemDeFundo = null;
        liberar();
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
          invalido.focus({ preventScroll: true });
          return;
        }
        const primeiroCampo = dialog.querySelector(
          'textarea, input:not([type="hidden"]):not([type="submit"]):not([type="button"]), select'
        );
        if (primeiroCampo) {
          primeiroCampo.focus({ preventScroll: true });
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
        this.focarDispensa();
      },

      focarDispensa() {
        const dialog = this.$refs.dialog;
        const dispensar = dialog && dialog.querySelector('[data-modal-dismiss]');
        if (dispensar) {
          dispensar.focus({ preventScroll: true });
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

      // Cai no fallback também quando `lastTrigger` era um trigger real que
      // desapareceu do DOM enquanto o modal estava aberto (CodeRabbit) — não
      // só quando `abrirSemTrigger` já não achou nenhum na abertura. Mesma
      // ação de workflow que ficou indisponível, só que descoberta um passo
      // depois: entre o clique que abriu e o fechamento.
      devolverFoco() {
        const alvo =
          this.lastTrigger && document.contains(this.lastTrigger)
            ? this.lastTrigger
            : this.focoFallbackAlvo();
        if (alvo) {
          alvo.focus({ preventScroll: true });
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
        // querer do componente inteiro. Com texto digitado ele não descarta; as
        // duas saídas deliberadas — `Esc` e o botão "Voltar" — continuam de pé,
        // e são elas que dizem que a pessoa quis mesmo sair.
        //
        // Recusar o gesto **em silêncio** seria a mesma falha muda que esta
        // issue fecha em outros três lugares: a pessoa age e nada acontece, sem
        // explicação. O foco vai para "Voltar" — é a saída de verdade, o leitor
        // de tela anuncia o botão, e nada é executado por encostar nele
        // (`data-modal-dismiss` é `type="button"`, garantido por
        // `test_botao_de_dispensa_nao_e_o_que_submete`). Um `confirm()` nativo
        // resolveria também, mas é vocabulário que este design system não tem.
        if (this.temTextoDigitado()) {
          this.focarDispensa();
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

  // Mesmo tratamento que `form-submit.js` dá ao bfcache: Firefox e Safari
  // podem restaurar a página como estava no momento da navegação, com
  // `data-submetendo-externo="1"` preso no `<form>` — sem isto, uma nova
  // tentativa de `submeterFormExterno` ficaria bloqueada para sempre depois
  // do botão "voltar" do navegador.
  window.addEventListener('pageshow', (event) => {
    if (!event.persisted) {
      return;
    }
    document.querySelectorAll('[data-submetendo-externo]').forEach((form) => {
      delete form.dataset.submetendoExterno;
    });
  });
})();
