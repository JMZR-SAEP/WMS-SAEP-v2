// Travessia por teclado nos cartões de fila (#194). Setas ↓/↑ movem o foco
// entre os links `[data-cartao-link]` dentro do wrapper que carrega
// `x-data="travessiaFila()"`. Enter não precisa de handler: o navegador já
// ativa um <a> focado nativamente — só a navegação por seta é comportamento
// novo. Escopado ao `$el` do componente (não a `document`), o que também
// cumpre WCAG 2.1.4: fora do container, as setas não fazem nada aqui.
document.addEventListener('alpine:init', () => {
  window.Alpine.data('travessiaFila', () => ({
    proximo() {
      this._mover(1)
    },
    anterior() {
      this._mover(-1)
    },
    _mover(direcao) {
      const links = Array.from(this.$el.querySelectorAll('[data-cartao-link]'))
      if (links.length === 0) return
      const atual = links.indexOf(document.activeElement)
      const proximoIndice =
        atual === -1
          ? direcao > 0
            ? 0
            : links.length - 1
          : (atual + direcao + links.length) % links.length
      links[proximoIndice].focus()
    },
  }))
})
