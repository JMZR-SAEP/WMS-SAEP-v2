/**
 * autocomplete — Alpine factory para combobox ARIA com busca remota (debounce 300ms).
 *
 * Cobre o contrato comum às buscas de beneficiário/material do projeto:
 * digitar invalida a seleção anterior; foco com campo vazio lista tudo;
 * Enter confirma o item ativo; Esc/blur fecham o dropdown.
 *
 * O componente NÃO renderiza o hidden input do valor selecionado — isso fica
 * a cargo do template chamador, que deve declarar um elemento com
 * `x-ref="hiddenInput"` dentro do mesmo escopo `x-data`.
 *
 * Config aceito por `autocomplete(config)`:
 *   endpoint       (obrigatório) URL do JSON de busca (?q=)
 *   minChars       (opcional, default 2) abaixo disso a busca não dispara
 *   campoDisplay   (opcional, default 'label') campo do item usado para
 *                  preencher o texto exibido após seleção
 *   initialId      (opcional) valor inicial do hidden input (edição)
 *   initialLabel   (opcional) texto inicial exibido (edição)
 *   onSelect(item) (opcional) callback; retornar `false` veta a seleção —
 *                  nesse caso o componente não altera query/hidden/dropdown
 *   onInvalidate() (opcional) callback chamado quando a edição invalida a
 *                  seleção anterior (hidden zerado) — usar para sincronizar
 *                  estado externo (ex. guarda de duplicidade por linha)
 *   eventoSelecao  (opcional) nome do CustomEvent que borbulha na seleção,
 *                  com o item em `detail`. Sem ele nenhum evento é emitido.
 *
 * Uso no template chamador:
 *   <div x-data="autocomplete({ endpoint: '{% url ... %}', minChars: 2 })">
 *     <input type="hidden" x-ref="hiddenInput" name="...">
 *     {% include "components/autocomplete.html" with ... %}
 *   </div>
 */
(function () {
  'use strict';

  function factory(config = {}) {
    return {
      endpoint: config.endpoint,
      minChars: config.minChars ?? 2,
      campoDisplay: config.campoDisplay || 'label',
      onSelect: typeof config.onSelect === 'function' ? config.onSelect : null,
      onInvalidate: typeof config.onInvalidate === 'function' ? config.onInvalidate : null,
      eventoSelecao: config.eventoSelecao || null,

      idBase: '',
      query: '',
      resultados: [],
      aberto: false,
      // Guarda a caixa "faltam N caracteres" a não sobreviver ao blur: ela é
      // independente de `aberto` de propósito (não é o listbox), mas sem
      // `focado` ficava flutuando sobre o formulário depois que o campo
      // perdia o foco, e também aparecia sozinha na carga inicial de uma
      // edição sempre que o rótulo pré-selecionado era mais curto que
      // `minChars`.
      focado: false,
      buscando: false,
      // `erro` separa "a busca falhou" de "a busca não achou nada". Sem ele,
      // um 403 do endpoint caía no mesmo ramo de zero resultados e a tela
      // dizia "Nenhum material elegível encontrado." para quem, na verdade,
      // não tinha permissão — e um 500 ou uma queda de rede não diziam nada:
      // o spinner sumia e o componente ficava mudo.
      erro: false,
      ativo: -1,
      // `vinculado` é o espelho reativo de `hiddenInput.value` (ver
      // `_sincronizarVinculo()`): `true` quando o texto do campo corresponde a
      // um item escolhido da lista, `false` quando é texto digitado que não
      // vinculou nada. Até #151 as duas situações tinham o mesmo desenho.
      vinculado: false,
      // Texto que a região `role="status"` anuncia quando o vínculo morre
      // (vinculado -> desvinculado). Some 300ms depois, no callback do debounce.
      _anuncioVinculo: '',
      // Gate de submit no cliente: `true` quando o envio foi barrado por haver
      // texto sem vínculo neste combobox.
      erroGateVisivel: false,
      _debounceTimer: null,
      _abortController: null,

      init() {
        this.idBase = 'autocomplete-' + proximoId();
        if (config.initialId) {
          if (this.$refs.hiddenInput) {
            this.$refs.hiddenInput.value = config.initialId;
          }
          this.query = (config.initialLabel || '').trim();
        }
        this._sincronizarVinculo();
      },

      buscarComDebounce() {
        this._abortController?.abort();
        this._abortController = null;
        this.buscando = false;
        this.resultados = [];
        this.erro = false;
        this.erroGateVisivel = false;
        this.fecharDropdown();

        // Instante exato em que o vínculo morre: o hidden é zerado a cada tecla.
        // `tinhaVinculo` é lido ANTES de zerar para separar "apagou um caractere
        // de um item escolhido" (anuncia a quebra) de "segue digitando um texto
        // que nunca vinculou" (silêncio — não houve mudança de estado).
        const tinhaVinculo = !!this.$refs.hiddenInput?.value;
        if (this.$refs.hiddenInput) {
          this.$refs.hiddenInput.value = '';
        }
        this._sincronizarVinculo();
        if (tinhaVinculo) {
          this._anuncioVinculo = 'Seleção desfeita. Escolha um item da lista.';
        }
        if (this.onInvalidate) {
          this.onInvalidate();
        }
        clearTimeout(this._debounceTimer);
        const query = this.query;
        this._debounceTimer = setTimeout(() => {
          // A região live já leu "Seleção desfeita."; limpar aqui evita que ele
          // encubra a contagem da busca que vem a seguir.
          this._anuncioVinculo = '';
          this._buscarComGate(query);
        }, 300);
      },

      // Foco com campo vazio só lista tudo quando a tela pediu isso
      // explicitamente com `minChars: 0` (ex. beneficiários, escopo pequeno e
      // limitado a 20 no servidor). Com um piso declarado, listar tudo no foco
      // contradiz o próprio piso e gasta uma ida à rede por foco — inclusive
      // nos foques acidentais de quem tabula o formulário inteiro.
      async buscarTodos() {
        if (!this.query) {
          if (this.minChars > 0) return;
          await this.buscar('');
        } else if (this.resultados.length > 0) {
          this.aberto = true;
        } else {
          await this._buscarComGate(this.query);
        }
      },

      // O piso vale também para a busca vazia. O `q.length > 0` que existia
      // aqui abria uma exceção que o resto do componente não reconhece:
      // `buscarTodos()` recusa listar tudo quando há piso declarado, mas o
      // gate deixava `q === ''` passar direto para `buscar('')`.
      //
      // Quem paga é o Esc. O input de material é `type="search"`, então o Esc
      // nativo do Chrome limpa o campo e emite `input` — e 300ms depois o
      // dropdown reabria sozinho com o catálogo inteiro, exatamente o gesto
      // que a pessoa fez para fechá-lo. De quebra, cada limpeza de campo
      // gastava uma ida à rede que o piso existe para evitar.
      async _buscarComGate(q) {
        if (this.minChars > 0 && q.length < this.minChars) {
          this.resultados = [];
          this.erro = false;
          this.fecharDropdown();
          return;
        }
        await this.buscar(q);
      },

      async buscar(q) {
        this._abortController?.abort();
        const controller = new AbortController();
        this._abortController = controller;

        this.buscando = true;
        try {
          const res = await fetch(`${this.endpoint}?q=${encodeURIComponent(q ?? '')}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            signal: controller.signal,
          });
          // `res.ok` antes de `res.json()`: um 403 devolve JSON válido
          // (`{"error": ...}`) sem a chave `resultados`, o que virava lista
          // vazia e mentia dizendo que a busca não achou nada; um 500 devolve
          // a página de erro em HTML e estourava no parse.
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          if (this._abortController !== controller) return;
          this.resultados = data.resultados || [];
          this.erro = false;
          this.aberto = true;
          this.ativo = -1;
        } catch (e) {
          if (e.name === 'AbortError') return;
          // Resposta fora de ordem também não pode pintar erro: se este
          // controller já não é o corrente, uma busca mais nova mandou.
          if (this._abortController !== controller) return;
          this.resultados = [];
          this.erro = true;
          this.aberto = true;
          this.ativo = -1;
        } finally {
          if (this._abortController === controller) {
            this.buscando = false;
            this._abortController = null;
          }
        }
      },

      selecionar(item) {
        const aceito = this.onSelect ? this.onSelect(item) !== false : true;
        if (!aceito) {
          // Veto não destrutivo: query/hidden/dropdown ficam como estavam.
          return;
        }
        this.query = item[this.campoDisplay] ?? item.label ?? '';
        if (this.$refs.hiddenInput) {
          this.$refs.hiddenInput.value = item.id;
        }
        this._sincronizarVinculo();
        this._anuncioVinculo = '';
        this.erroGateVisivel = false;
        this.fecharDropdown();
        // Síncrono, e não só via blur no $nextTick: se o label do item
        // selecionado for mais curto que `minChars`, `focado` continuar `true`
        // até o blur rodar deixava `mensagemPoucosCaracteresVisivel()` piscar
        // "faltam N caracteres" bem onde o listbox acabou de fechar.
        this.focado = false;
        // Evento que borbulha, e não uma chamada ao escopo pai a partir do
        // `onSelect`. Uma arrow function escrita dentro da expressão `x-data`
        // captura o escopo léxico do momento da avaliação; o `with` do Alpine
        // que dá acesso ao escopo pai já não está ativo quando ela roda, e
        // referenciar o método do pai lá dentro estoura `is not defined`. O
        // evento sobe pelo DOM e chega a quem quiser ouvir, sem acoplar o
        // componente a quem o envolve.
        //
        // O NOME vem de quem instancia. Este componente atende as buscas de
        // beneficiário e de material, e emitir `material-selecionado` em toda
        // seleção fazia um combobox de pessoa despachar um evento de material —
        // um listener acima recebendo o objeto errado é bug silencioso, e um
        // componente genérico não tem por que conhecer um tipo do domínio.
        if (this.eventoSelecao) {
          this.$el.dispatchEvent(
            new CustomEvent(this.eventoSelecao, {
              detail: item,
              bubbles: true,
            })
          );
        }
        this.$nextTick(() => this.$refs.displayInput?.blur());
      },

      limpar() {
        this._abortController?.abort();
        this.query = '';
        this.resultados = [];
        this.erro = false;
        this.erroGateVisivel = false;
        if (this.$refs.hiddenInput) {
          this.$refs.hiddenInput.value = '';
        }
        this._sincronizarVinculo();
        this.fecharDropdown();
      },

      fecharDropdown() {
        this.aberto = false;
        this.ativo = -1;
      },

      // Seta para baixo com o popup fechado REABRE o popup, conforme o padrão
      // combobox da APG. Antes ela só incrementava `ativo`: depois de
      // selecionar um item o dropdown fecha mas `resultados` continua em
      // memória, então a tecla apontava `aria-activedescendant` para uma
      // <li> dentro de um <ul> em `display:none`. Para quem enxerga, nada
      // acontecia; para o leitor de tela, o foco virtual ia parar numa opção
      // invisível de um listbox anunciado como fechado.
      selecionarProximo() {
        if (!this.aberto && this.resultados.length > 0) {
          this.aberto = true;
          this.ativo = 0;
          this._rolarParaAtivo();
          return;
        }
        if (this.ativo < this.resultados.length - 1) {
          this.ativo++;
          this._rolarParaAtivo();
        }
      },

      selecionarAnterior() {
        if (!this.aberto && this.resultados.length > 0) {
          this.aberto = true;
          this.ativo = this.resultados.length - 1;
          this._rolarParaAtivo();
          return;
        }
        if (this.ativo > 0) {
          this.ativo--;
          this._rolarParaAtivo();
        }
      },

      _rolarParaAtivo() {
        this.$nextTick(() => {
          const el = document.getElementById(this.idBase + '-opt-' + this.ativo);
          if (el) el.scrollIntoView({ block: 'nearest' });
        });
      },

      confirmarSelecao() {
        if (this.ativo >= 0 && this.resultados[this.ativo]) {
          this.selecionar(this.resultados[this.ativo]);
        }
      },

      mensagemVaziaVisivel() {
        // `>= this.minChars` (e não `Math.max(minChars, 1)`): com `minChars: 0`
        // o piso virava 1 e uma busca de campo vazio sem resultados abria uma
        // caixa vazia, sem explicação nenhuma dentro.
        return (
          !this.buscando &&
          !this.erro &&
          this.query.length >= this.minChars &&
          this.resultados.length === 0
        );
      },

      // Estado "digite mais": `0 < query.length < minChars`. Sem isto, o único
      // feedback de quem digita 1 caractere com `minChars: 2` é nenhum —
      // dropdown fechado, sem spinner, sem mensagem — indistinguível de "sem
      // resultados" ou "campo quebrado". Independente de `aberto`: esta caixa
      // não é o listbox e não deve marcar `aria-expanded="true"`.
      mensagemPoucosCaracteresVisivel() {
        return (
          this.focado &&
          this.minChars > 0 &&
          this.query.length > 0 &&
          this.query.length < this.minChars
        );
      },

      mensagemPoucosCaracteres() {
        const faltam = this.minChars - this.query.length;
        return faltam === 1
          ? 'Falta 1 caractere para buscar.'
          : `Faltam ${faltam} caracteres para buscar.`;
      },

      // Texto da região live. O spinner é `aria-hidden` e o listbox não é
      // anunciado ao abrir, então uma busca bem-sucedida não produzia som
      // nenhum para quem usa leitor de tela: só o caso de zero resultados
      // falava. Volta '' enquanto busca para não anunciar contagem velha.
      anuncioResultados() {
        // Mudança de vínculo (vinculado -> desvinculado) tem prioridade: é a
        // transição que, sem anúncio, fica indistinguível de "nada mudou".
        if (this._anuncioVinculo) return this._anuncioVinculo;
        if (this.buscando) return '';
        if (this.erro) return 'A busca falhou.';
        // '' — não o texto —, mesmo padrão do caso de zero resultados logo
        // abaixo: a caixa visível de "faltam N caracteres" já é
        // `role="status" aria-live="polite"` e anuncia sozinha. Devolver o
        // texto aqui também duplicava o anúncio pro leitor de tela.
        if (this.mensagemPoucosCaracteresVisivel()) return '';
        if (!this.aberto) return '';
        const total = this.resultados.length;
        if (total === 0) return '';
        return total === 1
          ? '1 resultado disponível.'
          : `${total} resultados disponíveis.`;
      },

      // Espelho reativo de `hiddenInput.value`. Alpine não observa escrita
      // direta em propriedade de nó do DOM, então `x-show`/`:class` não
      // reagiriam a um getter que só lesse o ref. Este campo NÃO é verdade
      // paralela: nunca recebe um literal, só o resultado de
      // `!!this.$refs.hiddenInput?.value`, reavaliado em todo ponto que mexe no
      // hidden (init, selecionar, buscarComDebounce, limpar). A fonte continua
      // sendo o hidden; isto é o cache que a reatividade do Alpine exige.
      _sincronizarVinculo() {
        this.vinculado = !!this.$refs.hiddenInput?.value;
      },

      // Gate de submit no cliente: há texto digitado neste combobox sem
      // `hiddenInput` correspondente. É conveniência — o `clean()` do servidor
      // continua sendo a autoridade final. Chamado pelo listener de `submit`
      // deste arquivo via `Alpine.$data(escopo).sinalizarGate()`.
      sinalizarGate() {
        this.erroGateVisivel = true;
        this.$refs.displayInput?.focus();
      },

      mensagemGate() {
        return 'Selecione um item da lista. O texto digitado não corresponde a nenhum item.';
      },
    };
  }

  let _uidSeq = 0;
  function proximoId() {
    _uidSeq += 1;
    return _uidSeq;
  }

  // Gate de submit no cliente — barra o envio quando um combobox tem texto
  // digitado mas nenhum item vinculado (`hiddenInput` vazio). É conveniência: o
  // `clean()` do servidor continua rejeitando o mesmo caso, com ou sem JS.
  //
  // Percorre só comboboxes visíveis (um `x-show` fechado, ou a linha de formset
  // marcada para remoção, não conta) e para na primeira linha culpada, pondo o
  // foco nela — o `role="group" aria-label="Item N"` da linha dá o contexto ao
  // leitor de tela.
  function escopoDeComboboxSemVinculo(form) {
    const combos = form.querySelectorAll('input[role="combobox"]');
    for (const combo of combos) {
      if (combo.offsetParent === null) continue;
      const escopo = combo.closest('[x-data]');
      const hidden = escopo?.querySelector('input[x-ref="hiddenInput"]');
      if (!hidden) continue;
      if (combo.value.trim() !== '' && hidden.value.trim() === '') {
        return escopo;
      }
    }
    return null;
  }

  // Captura (`true`) para correr antes do HTMX (que escuta `submit` no próprio
  // form) e antes do guard de duplo-submit (form-submit.js, em bolha no
  // document). `stopPropagation` impede que qualquer um dos dois trate um envio
  // que este gate já barrou.
  document.addEventListener(
    'submit',
    (event) => {
      const form = event.target;
      if (!(form instanceof HTMLFormElement)) return;
      const escopo = escopoDeComboboxSemVinculo(form);
      if (!escopo) return;
      event.preventDefault();
      event.stopPropagation();
      const dados = window.Alpine?.$data(escopo);
      if (dados?.sinalizarGate) {
        dados.sinalizarGate();
      } else {
        escopo.querySelector('input[role="combobox"]')?.focus();
      }
    },
    true
  );

  document.addEventListener('alpine:init', () => {
    window.Alpine.data('autocomplete', factory);
  });
})();
