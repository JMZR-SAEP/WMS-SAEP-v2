/**
 * Dismiss de flash message — contraparte de core/partials/_message_item.html.
 *
 * Auto-dismiss assimétrico, e a assimetria é WCAG 2.2.1 (Timing Adjustable): a
 * norma exige poder desligar, ajustar ou estender qualquer limite de tempo.
 * `success`/`info` recebem `auto: true` porque a informação permanece na tela
 * depois que a faixa some; `warning`/`error` recebem `auto: false` explícito,
 * porque neles a faixa *é* a fonte da informação. Quem decide isso é o template
 * — este arquivo só executa. Política no markup, mecanismo aqui.
 *
 * Pausar preserva o tempo restante em vez de reiniciar: passar o mouse por cima
 * para ler não pode custar o resto do prazo.
 */
(function () {
  'use strict';

  const DURACAO_MS = 8000;
  const ANCORA_DE_FOCO = '#conteudo';

  function componente({ auto = false } = {}) {
    return {
      visivel: true,
      _timer: null,
      _restanteMs: DURACAO_MS,
      _iniciadoEm: 0,
      // Hover e foco são motivos independentes de pausa, e podem se sobrepor:
      // com um booleano só, tirar o mouse de uma faixa que ainda está focada
      // retomaria a contagem e a mensagem sumiria debaixo do foco do teclado —
      // exatamente o que a pausa por focus-within existe para impedir.
      _pausadoPorHover: false,
      _pausadoPorFoco: false,

      init() {
        if (auto) {
          this._retomarSeLivre();
        }
      },

      /**
       * Reposiciona o foco só quando ele está dentro do item que vai sumir.
       *
       * Mover o foco sempre seria pior que não mover: o auto-dismiss dispara 8s
       * depois, provavelmente no meio de uma digitação, e arrastaria o foco para
       * longe do campo em uso — trocaria uma correção de 2.1.1 por uma falha de
       * 3.2.1. A condição não é "quem fechou" e sim onde o foco está agora, o
       * que cobre teclado, clique e timer de uma vez, sem o componente precisar
       * adivinhar a modalidade de entrada.
       */
      _reposicionarFoco() {
        if (!this.$el.contains(document.activeElement)) {
          return;
        }
        // `#conteudo` é o alvo do skip link, declarado nos três layouts.
        // `document.body` é rede de segurança para um template que o esqueça.
        const destino = document.querySelector(ANCORA_DE_FOCO) ?? document.body;
        destino.focus?.();
      },

      fechar() {
        this._limparTimer();
        this._reposicionarFoco();
        this.visivel = false;
      },

      pausar(motivo) {
        this._marcar(motivo, true);
        if (this._timer === null) {
          return;
        }
        this._limparTimer();
        this._restanteMs -= Date.now() - this._iniciadoEm;
      },

      retomar(motivo) {
        this._marcar(motivo, false);
        this._retomarSeLivre();
      },

      _marcar(motivo, ativo) {
        if (motivo === 'foco') {
          this._pausadoPorFoco = ativo;
        } else {
          this._pausadoPorHover = ativo;
        }
      },

      _retomarSeLivre() {
        if (this._pausadoPorHover || this._pausadoPorFoco) {
          return;
        }
        if (!auto || !this.visivel || this._timer !== null) {
          return;
        }
        if (this._restanteMs <= 0) {
          this.fechar();
          return;
        }
        this._iniciadoEm = Date.now();
        this._timer = window.setTimeout(() => {
          this._timer = null;
          this.fechar();
        }, this._restanteMs);
      },

      _limparTimer() {
        if (this._timer !== null) {
          window.clearTimeout(this._timer);
          this._timer = null;
        }
      },

      // Sem isso o timer continua rodando sobre um item que o HTMX já removeu.
      destroy() {
        this._limparTimer();
      },
    };
  }

  document.addEventListener('alpine:init', () => {
    window.Alpine.data('mensagemFlash', componente);
  });
})();
