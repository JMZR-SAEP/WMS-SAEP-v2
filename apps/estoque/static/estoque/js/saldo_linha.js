/**
 * saldoLinha — escopo Alpine da linha de item quando ela precisa mostrar
 * saldo de estoque (issue #174). Vive em `apps/estoque` porque saldo é
 * domínio de estoque (`SaldoEstoque`, `estoque.services`), e é reusado por
 * `requisicoes/rascunho_form.html` do mesmo jeito que
 * `estoque/partials/_autocomplete_item_material.html` já é — cross-app
 * reuse de peça de domínio, não duplicação por tela.
 *
 * Compõe sobre `itemFormRow` (apps/core/static/core/js/item_form_row.js,
 * exposta em `window.WMSItemFormRow`) em vez de duplicar
 * `registrarMaterial`/`aplicarPassoDaUnidade`: o componente global só sabe
 * rastrear material/unidade selecionados, e este escopo empilha o estado de
 * saldo por cima, no mesmo `x-data` da raiz da linha (não há como separar
 * isso em dois escopos Alpine aninhados sem perder o evento
 * `material-selecionado`, que borbulha até a raiz e não até um wrapper mais
 * fundo — ver o comentário de `components/item_form_row.html`).
 *
 * O autocomplete mostrava `(disponível: 4530 un)` na opção do dropdown e
 * apagava esse número no instante em que a pessoa escolhia o material — logo
 * antes de digitar a quantidade, que é exatamente quando ele decide. O campo
 * ficava ao lado, vazio, sem unidade e sem teto: 99999 unidades de um
 * material com 4530 disponíveis atravessavam criação, envio e fila do chefe
 * sem um único aviso, e o erro só aparecia depois da confirmação da
 * autorização, numa faixa no topo da página e sem número nenhum.
 *
 * O que este escopo faz é só não jogar fora o que o servidor já mandou: o
 * payload do autocomplete traz `saldo_disponivel` (ou `saldo_fisico`, na
 * saída excepcional) e `unidade`. A fonte de verdade continua sendo o
 * `clean()` do formset e, no fim, a reserva no service — isto é aviso, não
 * validação.
 *
 * Uso no template (via `linha_alpine_factory`/`linha_alpine_config` de
 * `components/item_form_row.html`):
 *   {% como_json saldoTexto=... saldoValor=... unidade=... as linha_config %}
 *   {% include "components/item_form_row.html" with
 *        linha_alpine_factory="saldoLinha" linha_alpine_config=linha_config ... %}
 */
(function () {
  'use strict';

  function saldoLinha(config = {}) {
    // Composição, não duplicação: `generico.registrarMaterial` continua
    // sendo a única implementação do rastreamento de material/unidade.
    const generico = window.WMSItemFormRow(config);

    return {
      ...generico,

      saldoTexto: config.saldoTexto || '',
      saldoValor: valorNumericoOuNulo(config.saldoValor),
      saldoRotulo: config.saldoRotulo || 'Disponível',
      unidade: config.unidade || '',

      registrarMaterial(item) {
        generico.registrarMaterial.call(this, item);
        if (!item) return;
        const temDisponivel = item.saldo_disponivel !== undefined;
        this.saldoRotulo = temDisponivel ? 'Disponível' : 'Físico';
        this.saldoTexto = temDisponivel ? item.saldo_disponivel : item.saldo_fisico;
        this.unidade = item.unidade || '';
        // `saldo_bruto` é o número em notação de máquina, para comparar; o
        // `saldo_disponivel` já vem formatado em pt-BR e com vírgula, que
        // `Number()` não lê. Ausente (payload antigo), a comparação desliga e
        // só o texto aparece — degradar para menos aviso, nunca para aviso
        // errado.
        this.saldoValor = valorNumericoOuNulo(item.saldo_bruto);
      },

      get excedeuSaldo() {
        if (this.saldoValor === null) return false;
        const pedido = Number(String(this.quantidade).replace(',', '.'));
        if (!Number.isFinite(pedido) || pedido <= 0) return false;
        return pedido > this.saldoValor;
      },
    };
  }

  // `undefined` (chave ausente do payload), `null` e `''` (saldo_item.
  // saldo_bruto vazio, quando o template só sabe passar string vazia via
  // `{% como_json %}`) significam a mesma coisa aqui: saldo desconhecido.
  // `Number('')` é `0`, não `NaN` — sem este guard, um material sem saldo
  // mapeado acenderia "Acima do saldo" para qualquer quantidade positiva.
  function valorNumericoOuNulo(valor) {
    if (valor === undefined || valor === null || valor === '') return null;
    return Number(valor);
  }

  document.addEventListener('alpine:init', () => {
    window.Alpine.data('saldoLinha', saldoLinha);
  });
})();
