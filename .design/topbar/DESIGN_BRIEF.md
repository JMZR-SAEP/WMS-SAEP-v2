# DESIGN_BRIEF — Top App Bar (MD2)

> Componente reutilizável de Top App Bar seguindo Material Design 2, integrado ao layout autenticado do WMS-SAEP. Substitui o `.site-header` legado.

## Objetivo

Prover uma barra superior consistente para todas as telas autenticadas, oferecendo branding, título contextual, navegação principal e slots para ações específicas de tela — pinned, acessível e responsiva.

## Escopo desta entrega

| Decisão | Valor |
|---|---|
| Stack | Django template + Tailwind v4 (`@layer components`) + Alpine 3 inline (mínimo) |
| Local | `apps/core/templates/base_auth.html` (não é include separado) |
| API | Slots via `{% block %}` no `base_auth.html` |
| Variant | **regular** apenas |
| Scroll behavior | **pinned** (`position: sticky`) |
| Elevação | Borda inferior + sombra sutil **estática** (sem listener de scroll) |
| Acessibilidade | `role="banner"` no header, `<nav aria-label="Navegação principal">`, focus visível, labels PT-BR em ícones |
| Cor | Mantém `slate-900` (continuidade de marca); texto `slate-50` |
| Altura | `--app-bar-height` (CSS var) — 3.5rem mobile, 4rem ≥ sm |
| Menu hamburger | Abre um **drawer** lateral (popover) com seções Navegação e Conta |

## API (slots)

Blocks expostos no `base_auth.html`:

| Block | Default | Quando sobrescrever |
|---|---|---|
| `topbar_leading` | Brand (logo + nome) | Subtelas: trocar por nav icon (back/close) + título contextual |
| `topbar_title` | _(vazio; título vai no leading no pattern atual)_ | Reservado para futuro uso isolado |
| `topbar_actions` | _(vazio)_ | Botões/links de ação principal da tela |
| `topbar_overflow` | _(vazio; não renderiza UI)_ | Reservado para futura impl de menu more_vert |

Pattern de uso em subtela:

```django
{% block topbar_leading %}
  <a href="{{ voltar_url }}" class="app-bar__nav-icon" aria-label="Voltar">
    <svg ...>...</svg>
  </a>
  <h1 class="app-bar__title">{{ titulo }}</h1>
{% endblock %}

{% block topbar_actions %}
  <button class="app-bar__action" type="submit" form="form-x">Salvar</button>
{% endblock %}
```

## Classes CSS (em `@layer components`)

- `.app-bar` — header sticky, surface, borda+sombra estática
- `.app-bar__inner` — container max-width + flex layout
- `.app-bar__leading` — grupo esquerdo (brand OU nav-icon + título)
- `.app-bar__brand` — logo + nome (default leading)
- `.app-bar__nav-icon` — botão ícone de navegação (back/close/menu), 48dp touch target, focus visível
- `.app-bar__title` — título da tela, ellipsis, 16/18px medium
- `.app-bar__nav` — navegação principal (lista de links)
- `.app-bar__nav-link` — link de navegação, estado `aria-current="page"`
- `.app-bar__nav-toggle` — botão hamburguer mobile (Alpine `x-data`)
- `.app-bar__actions` — grupo de ações da tela à direita
- `.app-bar__action` — botão/link de ação individual
- `.app-bar__user` — bloco de identidade (avatar + nome + logout)

CSS custom property `--app-bar-height` permite que `<main>` calcule offset e que futuros variants (`dense`, `prominent`) ajustem altura sem reescrita.

## Acessibilidade

- `<header role="banner">` com `<nav aria-label="Navegação principal">` interna.
- Todo ícone interativo tem `aria-label` PT-BR (“Voltar”, “Abrir menu de navegação”, “Sair”).
- Focus visível via `outline: 2px solid` + `outline-offset: 2px`.
- Contraste WCAG AA: `slate-50` sobre `slate-900` ≈ 16:1.
- Navegação por teclado nativa (Tab/Shift+Tab); botões `<button>` e links `<a>`.
- Conteúdo principal recebe `padding-top` ou margin equivalente a `--app-bar-height` para evitar sobreposição.

## Responsividade

| Breakpoint | Comportamento |
|---|---|
| Todos os viewports | Toggle hamburger abre drawer lateral (popover) com seções Navegação e Conta. Sem variant inline em desktop. |

`flex-wrap` permite que o nav vá para baixo quando aberto no mobile sem quebrar o leading/user.

### Amendments — Remediação QA 2026-05-26

**Decisão Q5 (B2):** padrão Material App Bar uniforme em todos os viewports — drawer único, sem render inline em `lg+`.

- Toggle hamburger SEMPRE visível em telas-lista (`/requisicoes/minhas/`, `/requisicoes/autorizacoes/`, `/requisicoes/atendimentos/`).
- Subtelas (detalhe, atender, rascunho_form) substituem hamburger por **back-arrow** no `topbar_leading` (pattern Material). Drawer não é acessível enquanto subtela está aberta — usuário volta antes de navegar para outra seção. Isso é intencional e ergonômico para fluxos transacionais.
- Drawer mobile DEVE ter **backdrop overlay** (`fixed inset-0 bg-slate-900/40`) que escurece o conteúdo atrás e fecha o drawer ao receber click. Resolve P2-06.

**Findings remediados por amend (não exigem código):** P1-02 (drawer em desktop é intencional), P1-03 (back-arrow em subtela é intencional), P2-07 (drawer em tablet é intencional).

### Amendment — Side Nav Desktop (2026-07-03, issue #63 M1)

**Decisão Q5 (B2) revertida para lg+.** Auditoria UI/UX 2026-07 identificou dois problemas no padrão de drawer único: (1) hierarquia visual fraca em viewports largos — app parece "mobile demais" em 1280px; (2) cliques extras desnecessários para papéis com fluxo repetitivo (ex.: chefe verificando fila de autorização várias vezes ao dia).

#### Decisões aprovadas

| Dimensão | Decisão |
|---|---|
| **Breakpoint** | `lg+` (≥ 1024px) — abaixo disso: comportamento atual inalterado |
| **Tipo** | Side nav persistente fixo — sem toggle, sem colapsar |
| **Largura** | `w-60` (240px) |
| **Cor** | Light — `bg-white border-r border-slate-200` |
| **Layout** | Flex no fluxo: wrapper `lg:flex` envolve `<aside>` + `<main>` abaixo do app bar |
| **Hamburguer em lg+** | Oculto (`lg:hidden`) — drawer continua existindo para mobile/tablet |
| **Item ativo** | Pill — `bg-slate-100 rounded-md` no item inteiro |
| **Estilo** | Tailwind inline no novo partial `_side_nav_requisicoes.html` (sem novas classes `@layer`) |
| **Subtelas em desktop** | Side nav sempre visível — `{% block topbar_menu %}{% endblock %}` só suprime o hambúrguer, não o side nav |
| **Conta/logout** | Rodapé do side nav (nome + matrícula + botão Sair) |

#### Estrutura de blocos

`base_auth.html` expõe novo block:

```django
{# wrapper flex abaixo do app bar #}
<div class="lg:flex">
  <aside class="hidden lg:flex lg:w-60 lg:shrink-0 lg:flex-col ...">
    {# Início (core:home) sempre presente #}
    {% block sidebar_nav %}{% endblock %}  {# domínio injeta seções aqui #}
    {# rodapé: nome + matrícula + logout #}
  </aside>
  <main class="flex-1 min-w-0 ...">
    <div class="mx-auto max-w-screen-xl p-6">
      {% include "core/partials/_messages.html" %}
      {% block content %}{% endblock %}
    </div>
  </main>
</div>
```

`requisicoes/base.html` estende `sidebar_nav`:

```django
{% block sidebar_nav %}
  {% include "requisicoes/partials/_side_nav_requisicoes.html" %}
{% endblock %}
```

#### Novos arquivos

- `apps/requisicoes/templates/requisicoes/partials/_side_nav_requisicoes.html` — seções "Requisições" e "Almoxarifado" com Tailwind inline e mesmas guards de permissão de `_topbar_nav.html`. Partial de domínio vive no app dono (`requisicoes`), não em `core`, conforme ADR-0008.

#### Imutável

- `_topbar_nav.html` e classes `app-bar__menu-*` não mudam — drawer mobile continua funcionando.
- Back-arrow em subtelas (`{% block topbar_leading %}`) inalterado.
- Subtelas abaixo de `lg`: nenhuma mudança de comportamento.

---

## Fora do escopo (documentado, não implementado)

| Item | Por quê | Quando reabrir |
|---|---|---|
| `variant: dense` | App mobile-first; sem caso de uso | Quando tela densa (admin/relatório) surgir |
| `variant: prominent` | Requer collapseOnScroll p/ valor real | Quando branding/hero de tela exigir |
| `behavior: hideOnScroll` | Quebra UX com swaps htmx | Se telas longas de leitura forem adicionadas |
| `behavior: collapseOnScroll` | Acoplado a `prominent` | Junto com `prominent` |
| Modo contextual (`selectedCount`, `onCancelContextualMode`) | Nenhuma tela tem multi-select hoje | Quando primeiro multi-select for projetado |
| Overflow menu interativo (`more_vert` + dropdown) | Sem ação secundária na fila | Quando alguma tela tiver ≥ 3 ações |
| Elevação dinâmica ao rolar | Listener de scroll + Alpine sem ganho real (já há borda) | Se design pedir distinção forte |

## Critérios de aceitação

- [ ] Header aparece no topo, sticky, em todas as telas autenticadas.
- [ ] Brand (logo + WMS-SAEP) é o leading default.
- [ ] Subtelas (`detalhe.html`, `rascunho_form.html`) renderizam back + título via `{% block topbar_leading %}` sem usar classes legadas.
- [ ] Nav principal (Minhas requisições / Nova requisição) acessível por teclado, com `aria-current="page"` na rota ativa.
- [ ] Toggle mobile funciona via Alpine; nav colapsa <640px.
- [ ] `<main>` não fica sobreposto pelo header.
- [ ] Borda inferior + sombra sutil estática visíveis.
- [ ] Classes `.site-header*` / `.site-nav*` removidas completamente do `input.css` e `app.css`.
- [ ] `npm run css:build` recompila sem erro.
- [ ] `uv run ruff format --check .` e `uv run ruff check .` passam.

## Call-sites a migrar

- `apps/requisicoes/templates/requisicoes/detalhe.html` (linhas 7-16): `.site-header-back`, `.site-header-title` → `.app-bar__nav-icon`, `.app-bar__title`.
- `apps/requisicoes/templates/requisicoes/rascunho_form.html` (linhas 12-28): mesmo padrão.

## Referências

- [Material Design 2 — App bars: top](https://m2.material.io/components/app-bars-top)
- ADR-0008 — Server-rendered frontend e design system
- `docs/design-system.md` — Filosofia Pragmatic Minimal
