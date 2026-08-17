/**
 * itensFormset — Alpine factory para o container de linhas de item de um
 * formset dinâmico (`item_form_row.html`, ADR-0016).
 *
 * Vive num elemento que envolve as linhas E o botão "adicionar", não em cada
 * linha, porque "pode remover" depende de contar linhas-irmãs ainda visíveis e
 * "qual o próximo índice" depende do TOTAL_FORMS do formset — nenhuma linha
 * isolada enxerga isso. As linhas herdam este escopo Alpine por aninhamento
 * normal do DOM (sem `x-data` próprio), então o botão de cada linha chama
 * `removerLinha($event)` direto.
 *
 * Uso no template chamador:
 *   <div x-data="itensFormset({ prefixo: 'itens' })">
 *     <div id="itens-container">
 *       {% include "components/item_form_row.html" ... %}
 *     </div>
 *     <button
 *       hx-sync="this:queue all"
 *       hx-vals='js:{"index": Number(document.getElementById("id_itens-TOTAL_FORMS").value)}'
 *       @htmx:after-request="aoAdicionarLinha($event)" ...>
 *   </div>
 */
(function () {
  'use strict';

  function factory(config = {}) {
    return {
      prefixo: config.prefixo || 'itens',

      // $el reflete o elemento onde a expressão Alpine foi avaliada (o botão
      // clicado), não a raiz do x-data — por isso guardamos a raiz aqui.
      init() {
        this._raiz = this.$el;
        this._container = this.$el.querySelector('[data-itens-container]') || this.$el;
        this._aviso = this._raiz.querySelector('[data-formset-aviso]');
        this._timerAviso = null;
        this._timerRealce = null;
      },

      _totalFormsInput() {
        return document.getElementById(`id_${this.prefixo}-TOTAL_FORMS`);
      },

      _linhasVisiveis() {
        return Array.from(
          this._container.querySelectorAll(
            '.item-form-row:not([style*="display: none"])'
          )
        );
      },

      _rotuloDaLinha(row) {
        const indice = Number.parseInt(row.dataset.index, 10);
        return Number.isNaN(indice) ? 'Item' : `Item ${indice + 1}`;
      },

      /**
       * Contabiliza a linha recém-inserida no TOTAL_FORMS.
       *
       * Só incrementa em resposta 200: num erro o HTMX não faz o swap, e somar
       * assim mesmo declararia uma linha fantasma que quebra o POST seguinte.
       *
       * O índice enviado na requisição sai deste mesmo TOTAL_FORMS (ver o
       * `hx-vals` do botão), não de uma contagem de `.item-form-row` no DOM.
       * Contar o DOM parecia equivalente e não era: era um segundo número para
       * a mesma verdade, e com `hx-sync` ausente dois cliques rápidos liam o
       * mesmo valor antes de qualquer swap — o POST ficava com dois grupos
       * `<prefixo>-N-*`, o QueryDict guardava só o último, e um material sumia
       * sem erro nenhum na tela. O `hx-sync="this:queue all"` do botão serializa
       * os cliques, e é por isso que a leitura seguinte já enxerga o incremento
       * feito aqui.
       */
      aoAdicionarLinha(event) {
        if (event?.detail?.xhr?.status !== 200) return;
        const input = this._totalFormsInput();
        if (!input) return;
        const atual = parseInt(input.value, 10);
        input.value = (Number.isNaN(atual) ? 0 : atual) + 1;

        // Sem isto, o toque em "Adicionar material" deixava o foco no botão e a
        // linha nova aparecia abaixo, em silêncio: quem usa teclado tinha de
        // tabular até lá a cada material, e quem usa leitor de tela não recebia
        // nada dizendo que algo tinha sido inserido. Numa saída de 15 itens são
        // 15 viagens que a interface pode poupar.
        //
        // `requestAnimationFrame` porque o Alpine inicializa a linha nova pelo
        // MutationObserver, em microtarefa: focar antes disso dispara um focus
        // nativo num input que ainda não tem o `@focus="buscarTodos()"` ligado,
        // e o dropdown não abre. No quadro seguinte o escopo já existe.
        const linhaNova = this._linhasVisiveis().at(-1);
        if (!linhaNova) return;
        requestAnimationFrame(() => {
          linhaNova.querySelector('input[role="combobox"]')?.focus();
          this._anunciar(this._copy('avisoAdicionado', { item: this._rotuloDaLinha(linhaNova) }));
        });
      },

      podeRemoverItem() {
        return this._linhasVisiveis().length > 1;
      },

      removerLinha(event) {
        const row = event.target.closest('.item-form-row');
        if (!row) return;

        if (!this.podeRemoverItem()) {
          this._avisarNaoPodeRemover(row);
          return;
        }

        // A linha seguinte, e não a primeira da lista: `find` devolvia sempre a
        // primeira linha visível, então remover o item 5 de 6 jogava o foco lá
        // no item 1. O fallback é a anterior, para o caso de remover a última.
        const visiveis = this._linhasVisiveis();
        const posicao = visiveis.indexOf(row);
        const vizinha = visiveis[posicao + 1] || visiveis[posicao - 1];
        const botaoFoco = vizinha?.querySelector('[data-remover-item]');

        const rotulo = this._rotuloDaLinha(row);
        row.style.display = 'none';
        const deleteInput = row.querySelector('[name$="-DELETE"]');
        if (deleteInput) deleteInput.value = 'on';
        botaoFoco?.focus();
        this._anunciar(this._copy('avisoRemovido', { item: rotulo }));
      },

      // Live region vazia e dedicada — uma por formulário, não por linha, e
      // separada da dica estática. A dica anterior fazia os dois papéis e, em
      // dois cliques dentro da janela de 4s, a segunda captura do "texto
      // original" já era o próprio aviso: a dica ficava substituída para
      // sempre. Aqui não há o que restaurar, só o que limpar.
      //
      // A região nunca é escondida — mesmo motivo que o aviso de duplicidade da
      // saída excepcional já documenta: mutação em elemento `display:none` não
      // é anunciada, porque ele não está na árvore de acessibilidade.
      //
      // A copy vive no `data-*` da própria live region, não aqui. Texto que a
      // pessoa lê é conteúdo da tela: em `.js` ele escapa do `{% trans %}`, do
      // grep de revisão de copy e da possibilidade de cada formulário dizer o
      // que faz sentido ali — "ao menos um material" é a frase da requisição,
      // não uma verdade sobre formsets.
      //
      // `{item}` é substituído pelo rótulo da linha. O placeholder fica dentro
      // da frase, e não concatenado antes dela, para que a ordem das palavras
      // continue sendo decisão de quem escreve o texto.
      _copy(chave, substituicoes = {}) {
        const texto = this._aviso?.dataset[chave];
        if (!texto) return '';
        return Object.entries(substituicoes).reduce(
          (acc, [nome, valor]) => acc.replaceAll(`{${nome}}`, valor),
          texto
        );
      },

      // `alerta` só troca o tom visual, via classe declarada em input.css. O
      // papel ARIA continua o mesmo (`role="status"`, polido) nos dois casos:
      // nem a inserção nem a recusa interrompem o que a pessoa está digitando.
      _anunciar(texto, { alerta = false } = {}) {
        clearTimeout(this._timerAviso);
        if (!this._aviso || !texto) return;
        this._aviso.textContent = texto;
        this._aviso.classList.toggle('formset-aviso--alerta', alerta);
        this._timerAviso = setTimeout(() => {
          this._aviso.textContent = '';
          this._aviso.classList.remove('formset-aviso--alerta');
        }, 4000);
      },

      // O realce sozinho comunicava o bloqueio só por cor: leitor de tela não
      // recebia nada e daltônico dependia do contorno.
      _avisarNaoPodeRemover(row) {
        this._anunciar(this._copy('avisoMinimo'), { alerta: true });
        // Timer próprio, e limpo antes de rearmar: dois cliques dentro da
        // janela de 4s deixariam o primeiro timer apagar o realce enquanto o
        // segundo aviso ainda está na tela.
        clearTimeout(this._timerRealce);
        row.classList.add('item-form-row--bloqueada');
        this._timerRealce = setTimeout(
          () => row.classList.remove('item-form-row--bloqueada'),
          4000
        );
      },
    };
  }

  document.addEventListener('alpine:init', () => {
    window.Alpine.data('itensFormset', factory);
  });
})();
