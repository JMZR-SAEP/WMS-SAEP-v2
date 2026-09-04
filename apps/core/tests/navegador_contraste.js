/**
 * Varredura de contraste WCAG 1.4.3 sobre a árvore renderizada (issue #166).
 *
 * Injetado via `page.evaluate()` por `medir_contraste()` em
 * `apps/core/tests/navegador.py`. Nunca é servido, nunca entra no bundle de
 * `app.css` — é módulo de teste, não estático de produção.
 *
 * Devolve um array de violações. Não lança: quem decide falhar, e com que
 * mensagem, é o lado Python.
 *
 * Fecha o limite conhecido de `test_nenhum_elemento_combina_par_de_cor_reprovado`
 * (`test_tokens_semanticos.py`), que só vê par de cor no *mesmo* elemento. Aqui
 * o fundo é resolvido subindo a árvore de ancestrais, com composição de alpha.
 *
 * Quatro efeitos de CSS estão fora do que este módulo sabe medir. Nenhum tem
 * ocorrência no produto hoje, e nenhum é apenas documentado: cada um é
 * **detectado** e sai em `naoSuportados`, que o lado Python transforma em falha.
 * Um guarda que fica cego em silêncio deixa de ser guarda — vale para os quatro:
 *
 * - `background-image` (gradiente, imagem): só `background-color` entra na
 *   composição do fundo.
 * - Pseudo-elemento com `content` textual: o tree walker anda na árvore de DOM,
 *   e `::before`/`::after` não estão nela.
 * - `opacity` de ancestral: `getComputedStyle().color` não embute a opacidade do
 *   pai, então texto dentro de um bloco a `opacity: 0.5` seria medido como se
 *   fosse opaco. Só `opacity: 0` é tratado, via `checkVisibility`.
 * - `mix-blend-mode`: a cor final na tela deixa de ser a cor computada, e a
 *   medição passaria a ser sobre outra coisa.
 *
 * Para introduzir um deles de propósito, a saída é `data-contraste-ignorar` no
 * elemento, que tira o ramo inteiro da varredura — exceção explícita e visível
 * no template, em vez de cegueira herdada.
 */
(() => {
  const LIMIAR_NORMAL = 4.5;
  const LIMIAR_GRANDE = 3.0;

  // Duas sentinelas para detectar string recusada pelo `fillStyle`: atribuição
  // inválida não lança, o canvas apenas mantém o valor anterior (medido no
  // spike da #166). São duas porque uma só confunde "recusada" com "é
  // exatamente essa cor" — a cor legítima falha contra uma das sentinelas e
  // passa na outra, então só é recusa quando as duas retêm o valor anterior.
  const SENTINELAS = ['#010203', '#fefdfc'];

  const naoConvertidas = [];

  // Efeito de CSS que a varredura não sabe medir, achado no caminho de um texto
  // que ela mediria. Deduplicado por motivo+seletor: um cabeçalho repetido em
  // 40 linhas de tabela é um problema, não quarenta.
  const naoSuportados = [];
  const jaRegistrados = new Set();

  function registrarNaoSuportado(motivo, elemento, valor) {
    const chave = `${motivo}|${seletorAproximado(elemento)}|${valor}`;
    if (jaRegistrados.has(chave)) return;
    jaRegistrados.add(chave);
    naoSuportados.push({ motivo, seletor: seletorAproximado(elemento), valor });
  }

  let _tela = null;
  let _ctx = null;

  function contexto() {
    if (_ctx === null) {
      _tela = document.createElement('canvas');
      _tela.width = 1;
      _tela.height = 1;
      _ctx = _tela.getContext('2d', { willReadFrequently: true });
    }
    return _ctx;
  }

  /**
   * Converte qualquer `<color>` CSS para sRGB 8-bit usando o canvas.
   *
   * O computado sai em `oklch()` (Tailwind v4 declara os tokens assim), que
   * nenhum parser de `rgb()` lê. Pintar 1px e ler o `getImageData` delega a
   * conversão ao pipeline de cor do navegador — exato contra referência
   * OKLab→sRGB, inclusive no clipping de cor fora do gamut.
   *
   * Devolve `null` se a string não for cor válida, para o chamador reportar em
   * vez de medir silenciosamente a cor errada.
   */
  function corCssParaSrgb(corCss) {
    const ctx = contexto();

    const reteve = SENTINELAS.every((sentinela) => {
      ctx.fillStyle = sentinela;
      ctx.fillStyle = corCss;
      return ctx.fillStyle === sentinela;
    });
    if (reteve) return null;

    ctx.clearRect(0, 0, 1, 1);
    ctx.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
    return { r, g, b, a: a / 255 };
  }

  /** Compõe `src` sobre `dst` (source-over, alpha não pré-multiplicado). */
  function compor(src, dst) {
    const alphaFinal = src.a + dst.a * (1 - src.a);
    if (alphaFinal === 0) return { r: 0, g: 0, b: 0, a: 0 };
    const canal = (s, d) => (s * src.a + d * dst.a * (1 - src.a)) / alphaFinal;
    return {
      r: canal(src.r, dst.r),
      g: canal(src.g, dst.g),
      b: canal(src.b, dst.b),
      a: alphaFinal,
    };
  }

  /**
   * Fundo efetivo de um elemento: empilha os `background-color` da raiz até ele.
   *
   * A maioria dos elementos tem `rgba(0, 0, 0, 0)` — o fundo visível vem de um
   * ancestral. Composição vai da raiz para a folha porque quem está mais perto
   * da folha pinta por cima. Base branca: é o que o navegador mostra quando
   * ninguém na cadeia é opaco.
   */
  function fundoEfetivo(elemento) {
    const cadeia = [];
    for (let el = elemento; el; el = el.parentElement) {
      cadeia.push(el);
      if (el === document.documentElement) break;
    }
    cadeia.reverse();

    let acumulado = { r: 255, g: 255, b: 255, a: 1 };
    for (const el of cadeia) {
      const estilo = getComputedStyle(el);

      // Os três efeitos que invalidariam esta composição, detectados exatamente
      // na cadeia que ela percorre — não numa varredura genérica do documento,
      // que acusaria efeito em ramo sem texto nenhum.
      if (estilo.backgroundImage !== 'none') {
        registrarNaoSuportado('background-image', el, estilo.backgroundImage);
      }
      if (estilo.mixBlendMode !== 'normal') {
        registrarNaoSuportado('mix-blend-mode', el, estilo.mixBlendMode);
      }
      // `opacity: 0` já é tratado como invisível por `checkVisibility`; o que
      // escapa é a opacidade parcial, que desbota o texto sem que a cor
      // computada mude.
      const opacidade = parseFloat(estilo.opacity);
      if (opacidade > 0 && opacidade < 1) {
        registrarNaoSuportado('opacity de ancestral', el, estilo.opacity);
      }

      const cor = corCssParaSrgb(estilo.backgroundColor);
      if (cor === null) {
        naoConvertidas.push({ propriedade: 'background-color', valor: estilo.backgroundColor });
        continue;
      }
      if (cor.a > 0) acumulado = compor(cor, acumulado);
    }
    return acumulado;
  }

  /**
   * Luminância relativa (WCAG, definição de "relative luminance").
   *
   * O ponto de corte é `0.04045`, e não o `0.03928` que circula em muita
   * implementação: aquele valor veio de uma proposta antiga do sRGB, e o W3C
   * corrigiu a definição em maio de 2021 para o número da norma IEC. Em canal
   * de 8 bits os dois dão o mesmo resultado — o corte cai entre 10 e 11 nos
   * dois casos —, mas aqui a cor pode chegar fracionária, vinda da composição
   * de alpha, e aí a faixa entre os dois valores existe de verdade.
   */
  function luminanciaRelativa({ r, g, b }) {
    const canal = (c) => {
      const n = c / 255;
      return n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b);
  }

  function razaoDeContraste(c1, c2) {
    const l1 = luminanciaRelativa(c1);
    const l2 = luminanciaRelativa(c2);
    const [maior, menor] = l1 > l2 ? [l1, l2] : [l2, l1];
    return (maior + 0.05) / (menor + 0.05);
  }

  /**
   * WCAG "texto grande": 18pt (24px) normal, ou 14pt (18.66px) com peso >= 700.
   *
   * Lê o computado, não a escala declarada em `DESIGN.md` — continua correto se
   * a escala mudar. Hoje nenhum peso do sistema chega a 700, então na prática
   * todo texto do produto cai em `LIMIAR_NORMAL`; isso é resultado esperado, não
   * ramo morto por engano.
   */
  function ehTextoGrande(estilo) {
    const px = parseFloat(estilo.fontSize);
    const peso = parseInt(estilo.fontWeight, 10) || 400;
    return px >= 24 || (px >= 18.66 && peso >= 700);
  }

  /**
   * Elemento que não conta como "texto visível" para esta medição.
   *
   * `checkVisibility` cobre `display:none`, `visibility:hidden` e `opacity:0`.
   * `contentVisibilityAuto` entra porque sem ele `content-visibility: hidden`
   * é reportado como visível (medido no spike da #166).
   *
   * O segundo laço cobre o `sr-only` do Tailwind (1x1px, `position:absolute`,
   * `overflow:hidden`): texto para leitor de tela, nunca visto — contraste não
   * se aplica.
   */
  function ocultoParaLeitura(elemento) {
    if (
      !elemento.checkVisibility({
        checkOpacity: true,
        checkVisibilityCSS: true,
        contentVisibilityAuto: true,
      })
    ) {
      return true;
    }

    for (let el = elemento; el; el = el.parentElement) {
      const estilo = getComputedStyle(el);
      if (
        estilo.position === 'absolute' &&
        parseFloat(estilo.width) <= 1 &&
        parseFloat(estilo.height) <= 1 &&
        estilo.overflow === 'hidden'
      ) {
        return true;
      }
      if (el === document.body) break;
    }
    return false;
  }

  /** Identificador legível na mensagem de falha — não precisa ser único. */
  function seletorAproximado(elemento) {
    const tag = elemento.tagName.toLowerCase();
    const id = elemento.id ? `#${elemento.id}` : '';
    const classes = [...elemento.classList].slice(0, 3);
    return `${tag}${id}${classes.length ? '.' + classes.join('.') : ''}`;
  }

  /**
   * Pseudo-elemento que pinta texto, e que por isso escaparia da varredura.
   *
   * Precisa de passe próprio: `::before`/`::after` não estão na árvore de DOM,
   * então nenhum tree walker os alcança, e o elemento que os hospeda pode não
   * ter nenhum nó de texto seu.
   *
   * Só conta `content` que renderiza texto. `content: ""` decorativo — barra,
   * ícone, seta — não pinta glifo e não tem contraste a medir.
   */
  function varrerPseudoElementos() {
    for (const elemento of document.body.querySelectorAll('*')) {
      if (elemento.closest('[data-contraste-ignorar]')) continue;
      if (ocultoParaLeitura(elemento)) continue;

      for (const pseudo of ['::before', '::after']) {
        const conteudo = getComputedStyle(elemento, pseudo).content;
        if (conteudo === 'none' || conteudo === 'normal') continue;
        // Tira as aspas para distinguir `content: ""` de `content: "Passo 1"`.
        const texto = conteudo.replace(/^["']|["']$/g, '').trim();
        if (!texto) continue;
        registrarNaoSuportado(`texto em ${pseudo}`, elemento, conteudo);
      }
    }
  }

  varrerPseudoElementos();

  const violacoes = [];
  const caminhante = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(no) {
      if (!no.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
      const pai = no.parentElement;
      if (!pai) return NodeFilter.FILTER_REJECT;
      if (pai.closest('script, style, template, noscript')) return NodeFilter.FILTER_REJECT;
      if (pai.closest('[data-contraste-ignorar]')) return NodeFilter.FILTER_REJECT;
      if (ocultoParaLeitura(pai)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  let no;
  while ((no = caminhante.nextNode())) {
    const pai = no.parentElement;
    const estilo = getComputedStyle(pai);

    const corTexto = corCssParaSrgb(estilo.color);
    if (corTexto === null) {
      naoConvertidas.push({ propriedade: 'color', valor: estilo.color });
      continue;
    }

    const fundo = fundoEfetivo(pai);
    // Texto com alpha < 1 precisa ser composto sobre o próprio fundo antes de
    // medir, senão a luminância sai errada.
    const corFinal = corTexto.a < 1 ? compor(corTexto, fundo) : corTexto;

    const contraste = razaoDeContraste(corFinal, fundo);
    const limiar = ehTextoGrande(estilo) ? LIMIAR_GRANDE : LIMIAR_NORMAL;
    if (contraste >= limiar) continue;

    const arredondar = (c) => `rgb(${Math.round(c.r)} ${Math.round(c.g)} ${Math.round(c.b)})`;
    violacoes.push({
      texto: no.nodeValue.trim().slice(0, 60),
      seletor: seletorAproximado(pai),
      corTexto: arredondar(corFinal),
      corFundo: arredondar(fundo),
      contraste: Math.round(contraste * 100) / 100,
      limiar,
    });
  }

  return { violacoes, naoConvertidas, naoSuportados };
})();
