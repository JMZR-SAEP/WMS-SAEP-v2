# Plano — Issue #63: Achados médios da auditoria UI/UX

## Escopo

### O que muda
- **M1**: Side nav persistente em lg+ (amendment Q5/B2 já documentado no brief)
- **M2**: Remover campo "Atualizada em" do cabeçalho de detalhe
- **M3**: Coluna "Material" do histórico padronizada (contagem sempre primária, nome como secundário em item único)
- **M4**: Badge "Cancelada" cor diferente de "Recusada"
- **M5**: Scroll shadow na tabela de itens do form de atendimento
- **M6**: Reordenar cards de ação em "Pronta para retirada" (registrar retirada antes de cancelar)

### O que NÃO muda
- Drawer mobile/tablet — comportamento atual inalterado
- `_topbar_nav.html` e classes `app-bar__menu-*` — não tocados
- Back-arrow em subtelas — padrão inalterado
- Nenhuma mudança em models, services, policies ou selectors

## Arquivos tocados

| Arquivo | Achados |
|---|---|
| `apps/core/templates/base_auth.html` | M1: flex wrapper, aside sidebar, inner max-w wrapper em main, lg:hidden no hamburger |
| `apps/requisicoes/templates/requisicoes/partials/_side_nav_requisicoes.html` | M1: novo partial (Tailwind inline) |
| `apps/requisicoes/templates/requisicoes/base.html` | M1: block sidebar_nav |
| `apps/requisicoes/templates/requisicoes/detalhe.html` | M2: remove Atualizada em; M6: reordenar cards |
| `apps/requisicoes/templates/requisicoes/partials/_estado_badge.html` | M4: split recusada/cancelada |
| `apps/requisicoes/templates/requisicoes/partials/_tabela_historico_requisicoes.html` | M3: coluna Material |
| `apps/requisicoes/templates/requisicoes/atender_retirada.html` | M5: scroll-shadow-x + CSS |

## Detalhe de cada achado

### M1 — Side nav lg+
- `base_auth.html`: wrap `<main>` em `<div class="lg:flex">` com `<aside class="hidden lg:flex lg:w-60 ...">` e inner `<div class="mx-auto max-w-screen-xl">` no main (vários templates não têm max-w próprio)
- Hamburger wrapper: adicionar `lg:hidden`
- Novo block `{% block sidebar_nav %}{% endblock %}` no aside
- Aside tem: link Início + block sidebar_nav + rodapé conta (nome, matrícula, logout)
- Novo `_side_nav_requisicoes.html`: seções Requisições e Almoxarifado com as mesmas guards de permissão de `_topbar_nav.html`, classes Tailwind inline, pill ativo (`bg-slate-100 rounded-md`)
- `requisicoes/base.html`: estende `sidebar_nav` com include do novo partial

### M2 — Remover "Atualizada em"
- `detalhe.html` linhas 98–101: remover `<div>` com `dt="Atualizada em"` / `dd={{ requisicao.atualizado_em }}`

### M3 — Coluna Material no histórico
- Ambos mobile (card) e desktop (tabela) em `_tabela_historico_requisicoes.html`
- Atual: `{% if req.quantidade_itens == 1 %}{{ nome }}{% else %}{{ N }} itens{% endif %}`
- Novo: sempre mostra `N item(s)` como primário; para 1 item, nome como secondary text-xs
- Template: `{{ req.quantidade_itens }} {{ req.quantidade_itens|pluralize:"item,itens" }}` + `{% if req.quantidade_itens == 1 %}<br><span class="text-xs text-slate-400">{{ req.itens.all.0.material.nome }}</span>{% endif %}`

### M4 — Badge Cancelada vs Recusada
- `_estado_badge.html` linha 17: `{% elif estado == 'recusada' or estado == 'cancelada' %}` → split em dois elif
- `recusada`: mantém `bg-red-200 text-red-900 ring-red-300`
- `cancelada`: `bg-orange-100 text-orange-800 ring-1 ring-inset ring-orange-200`

### M5 — Scroll shadow no form de atendimento
- `atender_retirada.html` linha 80: `<div class="overflow-x-auto">` → `<div class="overflow-x-auto scroll-shadow-x rounded-sm">`
- Adicionar `{% block extra_head %}` com o mesmo CSS `.scroll-shadow-x` de `detalhe.html`

### M6 — Reordenar cards em "Pronta para retirada"
- `detalhe.html`: mover `{% if pode_atender_retirada %}` (linhas 395–416) para ANTES de `{% if pode_cancelar and requisicao.estado != 'rascunho' %}` (linhas 362–393)

## Estratégia de testes

Todos em `apps/requisicoes/tests/test_views.py` exceto onde indicado.

| Achado | Teste | Tipo |
|---|---|---|
| M1 | `test_side_nav_renderiza_para_autenticado` — GET minhas → `Minhas requisições` aparece em `<aside>` | view/template |
| M1 | `test_side_nav_oculto_em_mobile_via_classe` — response contém `hidden lg:flex` | content |
| M2 | `test_detalhe_nao_exibe_campo_atualizado_em` — GET detalhe → "Atualizada em" não no HTML | view |
| M3 | `test_historico_material_mostra_contagem_para_multi` — req com 2 itens → "2 itens" no HTML | view |
| M3 | `test_historico_material_mostra_nome_secundario_para_item_unico` — req 1 item → "1 item" + nome material | view |
| M4 | `test_badge_cancelada_cor_diferente_de_recusada` — req cancelada → `bg-orange-100` no HTML; req recusada → `bg-red-200` | view |
| M5 | `test_atender_retirada_tabela_tem_scroll_shadow` — GET atender → `scroll-shadow-x` no HTML | view |
| M6 | `test_detalhe_pronta_retirada_registrar_antes_cancelar` — GET detalhe pronta_para_retirada → índice de `id="atender-retirada-titulo"` < índice de `id="cancelamento-titulo"` no HTML (âncoras `aria-labelledby` estáveis, não substring "Cancelar") | view |

## Invariantes

Nenhuma mudança de estado, transição ou regra de domínio. Mudanças puramente de template/apresentação.

## Riscos

- `max-w-screen-xl` removido de `<main>` e movido para inner div — templates sem wrapper próprio (`rascunho_form`, `copiar_confirmacao`, telas de estoque sem max-w, notificações) continuam corretos porque o inner div do base_auth preserva o constraint
- Side nav não tem Alpine state — sem risco de conflito com `x-data` do drawer
- Coluna Material usa `req.itens.all.0` — já presente no código atual; sem N+1 novo (QuerySet já eager ou aceito como está)
