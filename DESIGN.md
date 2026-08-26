---
name: WMS-SAEP
description: Sistema visual operacional server-rendered para o almoxarifado da SAEP — registro auditável em papel frio, tinta grafite e sinalética por estado.
colors:
  primary: "oklch(54.6% 0.245 262.881)"
  primary-hover: "oklch(48.8% 0.243 264.376)"
  primary-active: "oklch(42.4% 0.199 265.638)"
  primary-subtle: "oklch(97% 0.014 254.604)"
  primary-muted: "oklch(93.2% 0.032 255.585)"
  primary-muted-strong: "oklch(88.2% 0.059 254.128)"
  primary-border: "oklch(88.2% 0.059 254.128)"
  primary-border-strong: "oklch(80.9% 0.105 251.813)"
  primary-text: "oklch(48.8% 0.243 264.376)"
  primary-text-emphasis: "oklch(42.4% 0.199 265.638)"
  primary-text-strong: "oklch(37.9% 0.146 265.522)"
  success: "oklch(62.7% 0.194 149.214)"
  success-subtle: "oklch(98.2% 0.018 155.826)"
  success-muted: "oklch(96.2% 0.044 156.743)"
  success-border: "oklch(92.5% 0.084 155.995)"
  success-text: "oklch(52.7% 0.154 150.069)"
  success-text-emphasis: "oklch(44.8% 0.119 151.328)"
  success-text-strong: "oklch(39.3% 0.095 152.535)"
  warning: "oklch(76.9% 0.188 70.08)"
  warning-subtle: "oklch(98.7% 0.022 95.277)"
  warning-muted: "oklch(96.2% 0.059 95.617)"
  warning-muted-strong: "oklch(92.4% 0.12 95.746)"
  warning-border: "oklch(92.4% 0.12 95.746)"
  warning-border-strong: "oklch(87.9% 0.169 91.605)"
  warning-text-subtle: "oklch(55.5% 0.163 48.998)"
  warning-text: "oklch(47.3% 0.137 46.201)"
  warning-text-strong: "oklch(41.4% 0.112 45.904)"
  danger: "oklch(57.7% 0.245 27.325)"
  danger-hover: "oklch(50.5% 0.213 27.518)"
  danger-active: "oklch(44.4% 0.177 26.899)"
  danger-accent: "oklch(63.7% 0.237 25.331)"
  danger-subtle: "oklch(97.1% 0.013 17.38)"
  danger-muted: "oklch(93.6% 0.032 17.717)"
  danger-muted-strong: "oklch(88.5% 0.062 18.334)"
  danger-border: "oklch(88.5% 0.062 18.334)"
  danger-border-strong: "oklch(80.8% 0.114 19.571)"
  danger-border-input: "oklch(70.4% 0.191 22.216)"
  danger-text: "oklch(50.5% 0.213 27.518)"
  danger-text-emphasis: "oklch(44.4% 0.177 26.899)"
  danger-text-strong: "oklch(39.6% 0.141 25.723)"
  return: "oklch(60% 0.118 184.704)"
  return-subtle: "oklch(98.4% 0.014 180.72)"
  return-muted: "oklch(95.3% 0.051 180.801)"
  return-border: "oklch(91% 0.096 180.426)"
  return-text: "oklch(51.1% 0.096 186.391)"
  return-text-strong: "oklch(38.6% 0.063 188.416)"
  surface: "#fff"
  bg-page: "oklch(98.4% 0.003 247.858)"
  bg-subtle: "oklch(96.8% 0.007 247.896)"
  surface-overlay: "oklch(0% 0 0 / 40%)"
  text-primary: "oklch(20.8% 0.042 265.755)"
  text-secondary: "oklch(37.2% 0.044 257.287)"
  text-tertiary: "oklch(55.4% 0.046 257.417)"
  text-disabled: "oklch(70.4% 0.04 256.788)"
  text-on-primary: "#fff"
  border: "oklch(92.9% 0.013 255.508)"
  border-strong: "oklch(86.9% 0.022 252.894)"
  border-control: "oklch(55.4% 0.046 257.417)"
  border-focus: "oklch(62.3% 0.214 259.815)"
typography:
  display:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "normal"
  headline:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "normal"
  title:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: "0.0125em"
  body:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.33
    letterSpacing: "0.025em"
rounded:
  sm: "0.25rem"
  md: "0.375rem"
  lg: "0.5rem"
  xl: "0.75rem"
  2xl: "1rem"
  full: "9999px"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "3rem"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.text-on-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "0.5rem 0.75rem"
    height: "2.75rem"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.text-on-primary}"
  button-primary-active:
    backgroundColor: "{colors.primary-active}"
    textColor: "{colors.text-on-primary}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "0.5rem 0.75rem"
    height: "2.75rem"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.text-on-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "0.5rem 0.75rem"
    height: "2.75rem"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "0.5rem 0.75rem"
    height: "2.75rem"
  badge-blue:
    backgroundColor: "{colors.primary-muted}"
    textColor: "{colors.primary-text-strong}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    padding: "0.125rem 0.625rem"
  badge-teal:
    backgroundColor: "{colors.return-muted}"
    textColor: "{colors.return-text-strong}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    padding: "0.125rem 0.625rem"
  input-text:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "0.5rem 0.75rem"
    width: "100%"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.xl}"
    padding: "1rem"
  app-bar:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.text-on-primary}"
    height: "3.5rem"
  modal:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.2xl}"
    width: "36rem"
  alert-danger:
    backgroundColor: "{colors.danger-subtle}"
    textColor: "{colors.danger-text-emphasis}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "0.75rem 1rem"
  empty-state:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.xl}"
    padding: "3rem 1.5rem"
---

# Design System: WMS-SAEP

## Overview

**Creative North Star: "O Livro-Razão"**

O sistema se comporta como um livro-razão aberto sobre a mesa: linhas, colunas, carimbos de estado e uma trilha que ninguém apaga. Papel branco (`surface`) flutua sobre papel frio (`bg-page`), texto em grafite escuro, e a cor entra apenas como carimbo — nunca como enfeite. Densidade e alinhamento valem mais que expressividade; a tela existe para que uma requisição seja lida sem ambiguidade por quem autoriza e por quem separa o material.

A materialidade é Material Design 2 aplicado com parcimônia: uma barra de aplicação azul fixa no topo em elevação 4dp, papéis de conteúdo praticamente planos, e só overlays — menu e modal — subindo para 8dp e 24dp. Não há gradiente, não há vidro fosco, não há sombra colorida. O que dá profundidade é a diferença entre `bg-page` e `surface` mais uma borda de 1px, exatamente como uma folha sobre a mesa.

Os controles são diretos e sinalizáveis: cada botão diz o que faz, e quando não pode ser executado ele permanece visível, desabilitado e com o motivo em texto — a interface prefere explicar o bloqueio a esconder a operação. Alvo mínimo de 44px em todo controle, porque a mesma tela é usada com o dedo, em pé no galpão, e com teclado no escritório. O sistema recusa três coisas: o dashboard SaaS de gradiente e glassmorphism, o ERP legado de cinza-sobre-cinza ilegível, e a SPA que finge navegação com transição de página — aqui a página é renderizada no servidor e assume isso.

**Key Characteristics:**
- Papel frio sobre papel branco, borda de 1px, sombra reservada a overlays
- Cor exclusivamente semântica: seis famílias de estado, zero cor decorativa
- Corpo em 14px, rótulos estruturais em 12px caixa alta, tipografia do sistema sem webfont
- Escala MD2 de elevação com quatro degraus e nada entre eles
- Raio que cresce com a superfície: controle 6px → campo 8px → papel 12px → modal 16px
- Alvo de toque de 44px e anel de foco visível em todo controle interativo
- Uma renderização só: cartão em qualquer largura, em grade de 1 a 3 colunas

## Colors

Uma paleta de trabalho: um azul de carimbo, um grafite de registro, um papel frio e cinco famílias semânticas que existem só para dizer em que estado a coisa está.

### Primary
- **Azul de Carimbo** (`{colors.primary}`, blue-600): a única cor de ação do sistema. Fundo de botão primário, barra de aplicação, avatar do usuário, ícone de item ativo na navegação e anel de foco (em blue-500, um degrau mais claro). Nunca aparece como fundo de área grande fora da barra de aplicação.
- **Azul de Carimbo Escuro** (`{colors.primary-hover}` / `{colors.primary-active}`, blue-700/800): resposta de pressão. Hover escurece um degrau, active dois — a mesma gramática vale para o botão de perigo.
- **Papel Azulado** (`{colors.primary-subtle}` / `{colors.primary-muted}`, blue-50/100): fundo de alerta informacional, item de navegação em `aria-current="page"` e badge de estado neutro-em-andamento.

### Secondary
- **Verde de Baixa Concluída** (`{colors.success}`, green-600): requisição atendida, saldo disponível, confirmação. Aparece como ícone e como badge; raramente preenche um botão.
- **Âmbar de Pendência** (`{colors.warning}`, amber-500): a decisão está com alguém. Fila de autorização, saldo insuficiente inline, alerta de importação SCPI que exige confirmação consciente.
- **Vermelho de Recusa** (`{colors.danger}`, red-600): negação, erro de validação, divergência, estorno, sair. Única família além de `primary` com escala de botão completa (`hover`/`active`), porque só ela também é ação.

### Tertiary
- **Teal de Reversão** (`{colors.return}`, teal-600): devolução e reversão operacional. Existe precisamente para não usar vermelho num evento legítimo.
- **Cores de catálogo cru** (orange-100/900, indigo-100/900, violet-100/900, yellow-100/900): usadas só nas variantes de badge homônimas de `components/badge.html`, para diferenciar estados de domínio que já esgotaram as famílias semânticas. Não são tokens de tema e não devem vazar para fora de badge.

### Neutral
- **Grafite de Registro** (`{colors.text-primary}`, slate-900): todo texto de conteúdo e todo título.
- **Grafite Médio** (`{colors.text-secondary}`, slate-700): texto de botão secundário, label de navegação em repouso, prosa de apoio.
- **Cinza de Metadado** (`{colors.text-tertiary}`, slate-500): rótulo de coluna, timestamp, texto de ajuda, cabeçalho de seção do menu.
- **Cinza Apagado** (`{colors.text-disabled}`, slate-400): ícone de navegação em repouso e ilustração de estado vazio.
- **Papel Branco** (`{colors.surface}`, #fff): toda superfície de conteúdo — card, tabela, modal, popover.
- **Papel Frio** (`{colors.bg-page}`, slate-50): o plano da página, atrás de tudo. Também é o hover do botão secundário.
- **Papel Frio Sombreado** (`{colors.bg-subtle}`, slate-100): cabeçalho de tabela e hover de item de menu.
- **Linha de Pauta** (`{colors.border}` / `{colors.border-strong}`, slate-200/300): borda de papel e divisor de linha. São estruturais: separam superfícies que já se distinguem por tom, e ninguém precisa enxergar a linha para entender o que a coisa é.
- **Linha de Controle** (`{colors.border-control}`, slate-500): a borda que *identifica* um controle — campo, select, botão secundário, área de upload. Ali a linha é a única pista de que existe um controle, e a WCAG 1.4.11 pede 3:1. Medido contra branco: slate-300 dá 1.48:1 e slate-400 dá 2.63:1; slate-500 dá 4.77:1 e é o primeiro degrau que passa em toda superfície do sistema.

### Named Rules

**A Regra do Sinal Único.** Cor comunica estado, nunca hierarquia visual e nunca decoração. Se uma cor foi escolhida porque "ficou bonito", ela está errada. Teste: apague todas as cores e o layout ainda deve ser navegável; devolva-as e cada mancha de cor deve responder à pergunta "em que estado isto está?".

**A Regra da Reversão Não é Erro.** Devolução e reversão operacional usam teal (`{colors.return}`), jamais vermelho. Vermelho é negação, falha ou divergência; devolver material é o processo funcionando. Nenhum evento legítimo do domínio recebe a cor da recusa.

**A Regra do Token, Nunca do Shade.** Templates usam a utility semântica (`bg-primary`, `text-danger-text`), nunca a cor crua da paleta (`bg-blue-600`, `text-red-700`) nem a custom property direto no HTML. É isso que torna o rebrand da SAEP uma troca de valor em `input.css`, sem tocar template. A exceção viva é o corpo de `badge.html`, para as variantes de catálogo cru sem token semântico.

> Nota factual: a família `--color-info*` (slate) está declarada em `input.css` mas nenhum template a consome — logo não existe no `app.css` compilado. A variante `info` de `alert.html` e o nível padrão de `_messages.html` renderizam azul via `primary-*`, por decisão. Use `info-*` só quando precisar de um aviso realmente neutro, e recompile.

## Typography

**Display/Body/Label Font:** a fonte do sistema (`ui-sans-serif, system-ui, sans-serif`). Uma família só, zero webfont, zero CDN.

**Character:** neutra e institucional por omissão deliberada — a personalidade do sistema está na estrutura e na sinalética, não no desenho da letra. A escala é curta e o peso faz quase todo o trabalho de hierarquia: 400 para conteúdo, 500 para controles e títulos de barra, 600 para títulos de tela e rótulos estruturais.

### Hierarchy
- **Display** (600, 1.875rem, lh 1.2): título de tela em desktop. Um por página.
- **Headline** (600, 1.5rem, lh 1.25): título de tela em mobile e cabeçalho de seção maior.
- **Title** (500, 1.125rem, lh 1.25, ls 0.0125em): título dentro da barra de aplicação e nome da marca; trunca com reticências em vez de quebrar linha.
- **Body** (400, 0.875rem, lh 1.5): o tamanho dominante do sistema — célula de tabela, corpo de card, texto de botão, alerta, campo de formulário. Prosa longa limitada a 65–75ch.
- **Label** (600, 0.75rem, ls 0.025em, caixa alta): cabeçalho de coluna, rótulo de campo, título de seção do menu. Também é o tamanho do badge — que usa 600 mas **sem** caixa alta, porque badge carrega conteúdo de domínio.

### Named Rules

**A Regra da Caixa Alta Estrutural.** Caixa alta é exclusiva de rótulo de estrutura — `<th>`, `<label>`, cabeçalho de seção de menu. Nome de material, nome de pessoa, número de requisição e texto de estado nunca sobem para maiúsculas: são dados, e dado em caixa alta perde legibilidade e perde o desenho da palavra.

**A Regra dos 14px.** O corpo do sistema é 0.875rem, não 1rem. É uma decisão de densidade operacional — uma fila com 20 requisições precisa caber na tela do chefe de setor. Subir o corpo para 1rem quebra a densidade de todas as listas de uma vez; se um texto precisa de mais presença, mude o peso ou o tom, não o tamanho.

## Layout

Container único de 80rem (`--width-content`, `max-w-screen-xl`) centralizado, com `p-6` de respiro no `<main>`. O card de login foge desse molde: 24rem (`--width-card-sm`), centralizado vertical e horizontalmente.

A navegação tem duas encarnações do mesmo conteúdo (fonte única em `core_tags.secoes_navegacao`): uma sidebar fixa em desktop (`lg:`, ≥64rem) e, abaixo disso, um hamburger na barra de aplicação que abre um popover ancorado de 16rem com overlay de fundo. A barra de aplicação é `sticky top-0`, com 3.5rem (56dp) em mobile e 4rem (64dp) a partir de 40rem, e respeita `env(safe-area-inset-top)`.

O ritmo de espaçamento é curto e previsível: 0.25rem entre ícone e texto, 0.5rem entre controles irmãos, 1rem de padding interno de card e de linha de tabela, 1.5rem entre seções, 3rem de respiro vertical em estado vazio.

### Named Rules

**A Regra do Cartão Único.** Listagem se renderiza em cartões, em qualquer largura — grade de 1 coluna, 2 a partir de 640px e 3 a partir de 1536px, via `components/table.html#cards_abertura`. Não existe renderização em tabela.

A regra anterior mandava renderizar duas vezes, cartão abaixo de 640px e tabela acima. Ela caiu por medição, não por gosto: com a side nav de 240px e o `p-6` do `<main>`, um viewport de 1024px deixa 734px de conteúdo, e as listagens reais precisavam de 808px (saídas excepcionais) a 1081px (histórico de requisições) — colunas com `whitespace-nowrap` não comprimem. Nem a 1280px cabia: o histórico ainda estourava 91px. A tabela só caberia a partir de ~1370px de viewport, ou seja, scroll horizontal em qualquer janela de desktop que não estivesse maximizada. O cartão responde em toda largura e ainda carrega mais campos do que a tabela carregava.

Consequência para quem escreve tela nova: não reintroduzir `<table>` em listagem. Se a densidade de uma tabela parecer necessária, o problema a resolver primeiro é a largura disponível — não o chrome.

**A Regra do Chrome Sem Parâmetro.** Os fragmentos de chrome de listagem não recebem parâmetro de classe. Se um chrome precisa de um parâmetro que descreve conteúdo de célula, a abstração está errada — a célula fica explícita na tela chamadora.

## Elevation & Depth

O sistema adota a escala Material Design 2 explicitamente, com quatro degraus e nada entre eles. No repouso, profundidade vem de tom e borda: papel branco sobre papel frio, separados por 1px de `border`. Sombra é reservada a superfícies que realmente saem do fluxo do documento.

### Shadow Vocabulary
- **0dp — repouso** (sem sombra): fundo da página, seções, conteúdo inline.
- **1dp — papel** (`box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05)`, `shadow-sm`): card de listagem, wrapper de tabela, painel de decisão de workflow. É borda óptica, não elevação real — a borda de 1px continua sendo obrigatória.
- **4dp — barra de aplicação** (`0 2px 4px -1px rgb(0 0 0 / .20), 0 4px 5px 0 rgb(0 0 0 / .14), 0 1px 10px 0 rgb(0 0 0 / .12)`): exclusivo da `.app-bar` fixa.
- **8dp — menu** (`0 5px 5px -3px rgb(0 0 0 / .20), 0 8px 10px 1px rgb(0 0 0 / .14), 0 3px 14px 2px rgb(0 0 0 / .12)`): popover do hamburger.
- **24dp — modal** (`shadow-2xl` + `backdrop:bg-slate-900/60`): `<dialog>`. O backdrop **escurece e não desfoca**. O desfoque saiu na #138: era a única superfície embaçada do sistema, contradizendo o north star, e apagava o registro sobre o qual a pergunta estava sendo feita — número público, beneficiário, itens, entregue líquida — exatamente no instante em que ele serviria de âncora. O que responde "qual documento?" hoje é a linha de identidade dentro do próprio diálogo; o fundo continua atrás, legível, como contexto.

### Named Rules

**A Regra dos Quatro Degraus.** 0, 1, 8 e 24dp — mais o 4dp exclusivo da barra de aplicação. Nenhuma sombra nova é criada para um componente novo: escolha o degrau que descreve a relação com o plano da página. Sombra colorida, sombra em hover de card e sombra como ênfase visual estão fora.

**A Regra do Empilhamento Fechado.** Elevação descreve a relação com o papel; z-index descreve quem cobre quem, e a escala é fechada: barra de ação fixa `z-10`, popover ancorado `z-20`, barra de aplicação e overlay de navegação `z-30`, drawer `z-40`, skip link `z-50`, modal no top layer do `<dialog>`. A consequência prática é que **a barra de ação fixa fica abaixo do popover** — o inverso esconde o dropdown do autocomplete atrás dela no celular. Ver a tabela em `docs/design-system.md`.

## Shapes

Retângulos de cantos suaves, sem chanfro, sem forma orgânica, sem clipping decorativo. O raio cresce junto com a superfície, o que torna a hierarquia legível pela geometria: controle 0.375rem (botão, item de menu, ação da barra) → campo 0.5rem (input, select, textarea, alerta) → papel 0.75rem (card, wrapper de tabela, estado vazio) → modal 1rem. Elementos circulares (`9999px`) são reservados a badge/pill, avatar e botão-ícone da barra de aplicação.

Borda é estrutural, não decorativa: 1px sólido em toda superfície de papel com `border`/`border-strong`, `border-control` (slate-500) em todo controle cuja borda é a única delimitação — campo, select, botão secundário, upload —, e `border-dashed` exclusivamente no estado vazio — a única textura de contorno do sistema, sinalizando "aqui caberia conteúdo".

### Named Rules

**A Regra do Raio Crescente.** Se um elemento novo não sabe qual raio usar, ele responde uma pergunta: sou um controle, um campo, um papel ou um overlay? O raio segue da resposta. Um raio intermediário inventado quebra a leitura de hierarquia por geometria.

## Components

### Buttons
- **Shape:** cantos suaves (0.375rem), altura mínima de 2.75rem (44px) e padding `0.5rem 0.75rem`. A variante `link` é a única sem altura mínima e sem preenchimento.
- **Primary:** Azul de Carimbo com texto branco; hover blue-700, active blue-800.
- **Secondary:** papel branco, texto grafite médio, borda `border-control`; hover troca o fundo para papel frio e escurece o texto.
- **Danger / Danger-outline:** vermelho preenchido para a ação destrutiva confirmada; contorno vermelho sobre papel branco quando a destruição ainda é uma proposta na tela.
- **Warning-outline:** contorno âmbar para ação que exige atenção sem ser destrutiva.
- **Ghost / Link:** sem fundo, para ações terciárias e navegação inline.
- **Foco:** `focus-visible:ring-2` com offset de 1px — azul por padrão, vermelho (`danger-accent`) nas variantes destrutivas. Outline nativo é removido apenas porque o anel o substitui.
- **Desabilitado:** `opacity-60` + `cursor-not-allowed`, mantendo a variante. Ação de workflow bloqueada permanece visível, com o motivo em texto na tela amarrado por `aria-describedby` — e o botão usa `aria-disabled`, não `disabled` nativo, porque um botão desabilitado sai da ordem de tabulação e leva o motivo junto. A ativação é barrada por `core/js/acao-bloqueada.js`. Sem motivo a declarar (paginação), `disabled` nativo. Ação administrativa irrelevante é removida da marcação.
- **Loading:** o label troca por texto de progresso (`data-submit-loading-label`), `aria-busy="true"` e submit duplo bloqueado — em form HTMX, por `hx-sync="this:drop"` no próprio form, porque o `preventDefault` do `form-submit.js` roda depois do HTMX. Não há spinner de submit: o vocabulário existia sem nenhuma tela que o produzisse.

### Chips (badges de estado)
- **Style:** pill (`9999px`), fundo `-muted` (shade 100), texto `-text-strong` (shade 900), `ring-1 ring-inset` na cor `-border` (shade 200). 0.75rem semibold, sem caixa alta.
- **Variantes fortes** (`blue-strong`, `amber-strong`, `red-strong`): sobem um degrau — fundo 200, ring 300 — para o estado que precisa se destacar dentro de uma lista de badges.
- **Contrato:** o badge não conhece enum de domínio. Partials de domínio mapeiam estado → `variant`/`label`/`role`/`aria_label` antes do include. A variante desconhecida cai num badge vermelho preenchido escrito "Indisponível" — falha visível, nunca silenciosa.

### Cards / Containers
- **Corner Style:** 0.75rem.
- **Background:** papel branco sobre papel frio.
- **Shadow Strategy:** 1dp (`shadow-sm`), sempre acompanhado de borda de 1px.
- **Internal Padding:** 1rem no cartão de listagem; 1.5rem em seção maior.

### Inputs / Fields
- **Style:** papel branco, borda `border-control` (slate-500), raio 0.5rem, padding `0.5rem 0.75rem`, corpo 14px, largura total do container e **altura mínima de 2.75rem (44px)** — campo é controle acionável e segue o mesmo piso do botão. Radio e checkbox usam `size-5` dentro de uma label de 44px; `textarea` com duas linhas ou mais já passa do piso.
- **Focus:** borda blue-500 + `ring-2` blue-500, sem outline.
- **Erro:** borda `danger-border-input` (red-400), `aria-invalid="true"` e mensagem em `role="alert"` abaixo do campo, vinculada por `aria-describedby`. Texto de erro vem sempre do Form, nunca hardcoded no componente.
- **Rótulo:** acima do campo, 12px semibold caixa alta em cinza de metadado, com asterisco `danger-accent` quando obrigatório. Texto de ajuda fica entre o rótulo e o campo.
- **Readonly:** fundo papel frio, borda neutra, cursor padrão — nunca `disabled`, que impediria o envio.

### Navigation
- **Barra de aplicação:** Azul de Carimbo em `sticky`, 56dp/64dp, elevação 4dp. Marca à esquerda (ou ícone contextual de voltar/fechar em subpáginas), ações à direita. Estados de hover/active são overlays brancos de 10%/18%, e o anel de foco é branco — a barra tem sua própria gramática de interação porque tem seu próprio fundo.
- **Sidebar (≥64rem):** itens de 0.375rem de raio, 14px medium; repouso em grafite médio com ícone cinza apagado, hover em papel frio, ativo em papel frio sombreado com texto grafite e `aria-current="page"`.
- **Popover mobile:** 16rem, papel branco, raio 0.5rem, elevação 8dp, overlay `surface-overlay` (preto 40%), foco preso (`x-trap.inert.noscroll`). Item ativo pinta fundo azul suave e texto azul; "Sair" é o único item em vermelho.

### Modal (componente-assinatura)
`<dialog>` nativo com `role="dialog"`, `aria-modal`, `aria-labelledby` e foco preso. Raio 1rem, largura máxima de 36rem (42rem a partir de `sm`), altura limitada a `calc(100dvh - 2rem)` com o corpo rolando por dentro. Sob o título, uma linha fixa nomeia o registro; o backdrop escurece sem desfoque para preservar o contexto visual da tela de origem. Entrada de 180ms com `cubic-bezier(0.16, 1, 0.3, 1)` a partir de `translateY(12px) scale(0.96)`, envelopada em `prefers-reduced-motion: no-preference`. O envio é POST real com HTMX por cima; o erro re-renderiza o corpo do modal em vez de fechar a tela.

### Estado vazio
Papel branco com **borda tracejada** `border-strong`, raio 0.75rem, `px-6 py-12`, ícone de 2.5rem em cinza apagado, título 16px medium, descrição 14px em cinza de metadado e, opcionalmente, um botão primário com a próxima ação. É o único uso de traço no sistema.

### Movimento
Três durações (`--duration-fast` 150ms, `--duration-normal` 250ms, `--duration-slow` 400ms) e três curvas (`--ease-default`, `--ease-out`, `--ease-in`). Movimento só existe para explicar mudança de estado: overlay que aparece, popover que abre, modal que entra, spinner que gira. Não há transição de página, não há animação de entrada de conteúdo, não há parallax. Toda animação decorativa passa por `prefers-reduced-motion`, e o spinner usa `motion-reduce:animate-none`.

## Do's and Don'ts

### Do:
- **Do** usar as utilities semânticas dos tokens (`bg-primary`, `text-danger-text`, `border-border-strong`) em qualquer template novo — nunca a cor crua da paleta.
- **Do** manter `min-h-11` (44px) em todo controle acionável; a mesma tela é operada com o dedo, em pé, no galpão.
- **Do** renderizar listagem em cartões, reusando `components/table.html#cards_abertura` e `#card_abertura`; não há renderização em tabela.
- **Do** manter a ação de workflow bloqueada **visível e desabilitada, com o motivo em texto**; só ação administrativa irrelevante some da marcação.
- **Do** escolher um dos quatro degraus de elevação existentes (0/1/8/24dp) ao criar uma superfície nova.
- **Do** usar teal (`return`) para devolução e reversão, e reservar vermelho para negação, erro e divergência.
- **Do** dar a todo controle um `focus-visible:ring-2` com offset; remover `outline` só é aceitável porque o anel o substitui.
- **Do** deixar o texto de erro vir do Form/serviço e passar por `role="alert"` + `aria-describedby`.

### Don't:
- **Don't** introduzir gradiente, vidro fosco em qualquer superfície — inclusive o backdrop do modal — ou sombra colorida.
- **Don't** criar um raio intermediário fora da escala 0.375 / 0.5 / 0.75 / 1rem / pill.
- **Don't** subir o corpo do sistema de 0.875rem para 1rem — a densidade das filas depende disso.
- **Don't** colocar conteúdo de domínio em caixa alta; maiúscula é só para rótulo estrutural.
- **Don't** usar cinza-sobre-cinza: texto de conteúdo é grafite (slate-900/700), e cinza de metadado (slate-500) é o piso — nada mais claro carrega informação.
- **Don't** animar navegação para simular SPA; a página é renderizada no servidor e o movimento serve só a mudança de estado local.
- **Don't** ensinar semântica de domínio a componente global — `button.html` e `badge.html` recebem variante e label já resolvidos pelo partial de domínio.
- **Don't** reintroduzir `<table>` em listagem, nem contêiner `overflow-x-auto` para acomodá-la — foi exatamente o que produzia scroll horizontal em desktop estreito.
- **Don't** parametrizar os fragmentos de chrome de listagem com classes extras; se for preciso, a abstração está no lugar errado.
