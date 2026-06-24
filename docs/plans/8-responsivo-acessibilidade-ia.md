# Plano — Issue #8: Movimentações de estoque: responsivo mobile, acessibilidade e IA

## Escopo

### O que muda
- `historico_movimentacoes.html`: barra de filtros ganha disclosure (`<details>`/`<summary>` nativo) no mobile; campos empilhados full-width `min-h-11`; chip "só saídas" sempre visível (já está fora do formulário).
- `.design/INFORMATION_ARCHITECTURE.md`: registrar rota `/estoque/movimentacoes/` e item de menu "Movimentações" (RBAC: almox/chefe setor com `pode_consultar_movimentacoes_estoque`).

### O que NÃO muda
- Lógica de backend (selectors, view, policies) — já entregue nas issues #6 e #7.
- Templates de partials (`_tabela_movimentacoes.html`, `_badge_tipo_movimentacao.html`, `_chip_so_saidas.html`, `_paginacao.html`, `_delta_movimentacao.html`) — já corretos.
- `_topbar_nav.html` — item "Movimentações" já existe condicionado a `pode_consultar_movimentacoes_estoque`.
- Schema, modelos, migrations.

## Arquivos tocados

| Arquivo | Ação |
|---|---|
| `apps/estoque/templates/estoque/historico_movimentacoes.html` | Modificar: filtros em disclosure `<details>`/`<summary>` nativo no mobile |
| `.design/INFORMATION_ARCHITECTURE.md` | Modificar: adicionar rota e item de nav estoque |

## Estratégia de implementação

### 1. Barra de filtros responsiva — disclosure nativo no mobile

Objetivo: em `< sm` o formulário de filtros fica colapsado em um `<details>`/`<summary>` nativo; ao clicar, expande. Chip "só saídas" permanece fora do disclosure e sempre visível. No desktop (`>= sm`) o formulário é sempre visível, independente de JS.

**Abordagem**: elemento `<details>` nativo como wrapper do formulário. O `<summary>` com texto "Filtros" fica visível apenas no mobile (`sm:hidden`); no desktop é ocultado e o conteúdo do `<details>` é forçado visível via `sm:!block` no wrapper interno.

**Por que `<details>`/`<summary>` e não Alpine `x-show`**: o `<details>` nativo funciona sem JavaScript (progressive enhancement), fornece `aria-expanded` gerenciado pelo browser em `<summary>`, e é semanticamente correto. Alpine pode ser adicionado como enhancement opcional (animação), mas não é o mecanismo de controle.

**Pattern concreto**:

```html
<details class="mb-6">
  {# Summary visível só no mobile — desktop oculta o summary via CSS #}
  <summary
    class="sm:hidden mb-4 flex min-h-11 cursor-pointer list-none items-center
           justify-between rounded-xl border border-slate-200 bg-white px-4 py-2
           text-sm font-medium text-slate-700 shadow-sm
           focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
  >
    Filtros
    <span aria-hidden="true" class="ml-2">▼</span>
  </summary>

  {# Conteúdo: no desktop forçado visível via sm:!block (override do display:none do details) #}
  <div class="sm:!block">
    <form method="get" ...>
      ...
    </form>
  </div>
</details>
```

`sm:!block` gera `@media (min-width: 640px) { display: block !important }`, sobrescrevendo o `display: none` que o browser aplica ao conteúdo de `<details>` quando não está aberto. No mobile, o toggle nativo do `<details>` gerencia a visibilidade sem JS.

### 2. Atualizar IA global

Adicionar seção `/estoque/` no site map e entrada na tabela de navegação do módulo estoque.

## Estratégia de testes

Não há mudança de comportamento de backend — os testes existentes da view e selectors permanecem.

Testes a adicionar em `apps/estoque/tests/test_views.py`:
- **Disclosure estrutura**: `GET /estoque/movimentacoes/` por usuário com permissão → response contém `<details` e `<summary` (estrutura do disclosure nativo).
- **Chip sempre visível**: response contém `id="chip-so-saidas"` fora do `<details>` (o chip aparece antes do disclosure no HTML).
- **`aria-live` presente**: response contém `aria-live="polite"` no contêiner `#resultados-movimentacoes`.

## Invariantes relevantes

- Chip "só saídas" **sempre visível** — não pode entrar no disclosure.
- O form de filtros **não pode criar novo alvo de swap** (id `resultados-movimentacoes` é único e fica no template base).
- `aria-live` e `aria-atomic` no wrapper de resultados — já presente, não tocar.

## Riscos

- `<details>` sem `open` oculta conteúdo via CSS do browser → sobrescrito no desktop por `sm:!block` (`!important`). Verificar que Tailwind JIT compila a classe.
- `<summary>` com `list-none` remove o marcador padrão (triângulo) — necessário para evitar double-indicator; verificar em todos os browsers alvo.
