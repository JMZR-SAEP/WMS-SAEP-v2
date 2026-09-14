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
 *   {% como_json saldoTexto=... saldoValor=... unidade=... motivo=... as linha_config %}
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
      // Motivo de inelegibilidade (requisições) — só existe para o material
      // conhecido no render inicial (`saldo_item.motivo`, quando o item já
      // vinha inelegível). Ver `registrarMaterial` abaixo pro porquê de
      // qualquer seleção nova sempre limpar isto.
      motivo: config.motivo || '',

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
        // O autocomplete de requisições só lista material elegível
        // (`materiais_para_requisicao`, apps/requisicoes/views.py::
        // buscar_materiais) e o de estoque nem tem noção de elegibilidade —
        // qualquer material que chega aqui por seleção já passou por esse
        // filtro. `motivo` só reflete o material do render inicial; ele nunca
        // sobrevive a uma troca de material na mesma linha, senão o painel
        // mostraria "Sem saldo disponível" para um material recém-escolhido
        // que nem tem esse problema (achado do CodeRabbit no PR #214).
        this.motivo = '';
      },

      get excedeuSaldo() {
        if (this.saldoValor === null) return false;
        const pedido = Number(String(this.quantidade).replace(',', '.'));
        if (!Number.isFinite(pedido) || pedido <= 0) return false;
        return pedido > this.saldoValor;
      },

      // Sobrescreve o `alerta` genérico de `itemFormRow` (config-only, sem
      // significado de domínio) com uma leitura reativa do mesmo `motivo` que
      // já dirige o painel de saldo: mesma classe de bug que o painel tinha
      // antes do PR #214 (achado do CodeRabbit), só que na borda da linha —
      // `borda_alerta` chegava calculado uma vez, no render do servidor
      // (`saldo_item|saldo_insuficiente` em rascunho_form.html), e não
      // acompanhava a troca de material na mesma linha. `motivo` já é limpo
      // por `registrarMaterial` em toda seleção nova, então a borda some
      // sozinha junto com o painel.
      get alerta() {
        return Boolean(this.motivo);
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
