# Plano — Piso de 44px nos controles de recuperação e o mecanismo que o vigia

Issue: [#120](https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/120) — origem: Etapa 2 (Feedback e
estado) de `docs/plans/audit-frontend-restante.md`.

## Escopo

### O que muda

1. **Alvo de toque dos dois infratores nomeados na issue**
   - `apps/core/templates/components/error_summary.html` — as âncoras de erro (uma por item do
     `<ul>`) passam a ter alvo de 44px de altura.
   - `apps/core/templates/components/empty_state.html` — o CTA secundário passa a ter alvo de 44px
     de altura.

2. **Raio dentro da escala nas mesmas duas linhas**
   - `rounded` pelado (0.25rem no Tailwind v4) é degrau abaixo do menor da escala do design system
     (controle 0.375 → campo 0.5 → papel 0.75 → modal 1rem → pill). Vira `rounded-md` nos dois
     arquivos.

3. **O mecanismo: `test_nenhum_controle_abaixo_do_piso_de_44px` passa a enxergar ausência**
   - Hoje o teste procura os literais `min-h-9`/`min-h-10` linha a linha. Ele pega quem escolheu
     conscientemente um número menor e é cego para quem não escreveu piso nenhum — que é
     exatamente o caso dos dois infratores acima.
   - O teste passa a varrer também cada `<a>` e `<button>` de `apps/**/*.html` e a falhar quando o
     clicável não tem piso comprovável.

4. **Colateral obrigatório para o teste ficar verde por mérito, não por exceção**

   A varredura de ausência revela dois clicáveis além dos dois da issue. Nenhum dos dois pode
   virar exceção sem reintroduzir o silêncio que esta issue existe para fechar:

   - `apps/core/static/core/css/input.css` — `.app-bar__brand` (o link do logotipo, consumido por
     `base_auth.html`) não declara piso: é um flex com logo de 1.75rem, ~28px de alvo. Ganha
     `min-height: var(--size-touch-target)`. **Sem efeito visual**: o link vive dentro de
     `.app-bar__inner`, que já tem `min-height: var(--app-bar-height)` (3.5rem mobile / 4rem
     desktop) e alinha os filhos por `align-items: center` — 44px cabe folgado nos 56px.
   - `apps/notificacoes/templates/notificacoes/lista.html` — o link "Requisição N" de cada cartão
     de notificação (`text-xs text-text-tertiary hover:underline`) é a **única** navegação da
     linha, ou seja, ação isolada, e o próprio design system manda ação isolada receber o piso
     (mesma frase que justifica o `min-h-11` à mão na linha 13 deste mesmo arquivo). Recebe
     `inline-flex items-center min-h-11`.

   O segundo item tem custo visual reconhecido: cada linha da lista de notificações cresce ~24px.
   É o preço correto de um alvo de 44px, e está registrado aqui para não parecer efeito colateral
   não intencional na revisão.

### O que NÃO muda

- O desenho dos dois controles da issue além do alvo: cor, tipografia, sublinhado, anel de foco e
  espaçamento entre itens ficam como estão.
- `_FORMA_LINK` em `apps/core/templatetags/core_tags.py:130` também usa `rounded` pelado. Está
  **fora de escopo** — é a variante `link` de `button.html`, superfície da Etapa 1 do plano de
  auditoria, e mexer nela mudaria o raio de todo `link` do sistema num PR sobre feedback. Fica
  registrado como achado para issue própria.
- A exceção declarada no design system (variante `link` de `button.html` como texto inline em
  prosa, WCAG 2.5.8) continua valendo e continua passando.
- Nenhuma mudança de schema, model, service, policy ou migration. Nenhuma mudança em `app.css`
  (artefato de build).

## Arquivos tocados

| Arquivo | Mudança |
|---|---|
| `apps/core/templates/components/error_summary.html` | `<a>` do item de erro: `block min-h-11 py-2.5` e `rounded` → `rounded-md` |
| `apps/core/templates/components/empty_state.html` | CTA secundário: `inline-block` → `inline-flex items-center min-h-11 px-1`, `rounded` → `rounded-md` |
| `apps/core/static/core/css/input.css` | `.app-bar__brand` ganha `min-height: var(--size-touch-target)` |
| `apps/notificacoes/templates/notificacoes/lista.html` | link "Requisição N": `inline-flex items-center min-h-11` |
| `apps/core/tests/test_components.py` | `test_nenhum_controle_abaixo_do_piso_de_44px` reformulado |
| `docs/design-system.md` | linha do "Piso de 44px" descreve o mecanismo novo (varredura de ausência), não só os literais |

A entrada de `docs/design-system.md` não está nos critérios de aceite da issue e está aqui de
propósito: a tabela de regras invioláveis nomeia, na coluna "O que verifica", o mecanismo de cada
regra. Se o mecanismo muda de natureza e a tabela continua descrevendo o antigo, a documentação
passa a prometer uma verificação que não é a que roda — a mesma classe de drift que a issue
denuncia.

Nenhum símbolo Python muda de assinatura; a única edição em `apps/` fora de template/CSS é o corpo
da função de teste.

## Como o teste passa a provar o piso

A regra que o teste passa a exigir: **todo `<a>` e `<button>` de `apps/**/*.html` tem piso
comprovável**. "Comprovável" tem três formas, nesta ordem:

1. **Literal no template** — `min-h-11` na lista de classes do próprio elemento.
2. **Piso vindo do CSS** — o elemento carrega uma classe cujo bloco em
   `apps/core/static/core/css/input.css` declara `height` ou `min-height` igual a
   `var(--size-touch-target)`. A lista é **derivada do CSS na hora do teste**, não escrita à mão:
   `.skip-link`, `.app-bar__nav-icon`, `.app-bar__nav-toggle`, `.app-bar__action`,
   `.app-bar__action-icon`, `.app-bar__menu-item`, `.campo` — e o que vier depois, sem editar o
   teste. Uma lista fixa aqui seria a mesma classe de erro que a issue denuncia: mecanismo que só
   conhece o que existia no dia em que foi escrito.
3. **Piso delegado ao componente** — a classe do elemento sai de `{% classes_botao %}`. É o caso
   dos dois ramos de `components/button.html`, e só dele. O piso de `_FORMA_BOTAO`
   (`core_tags.py:129`) e a exceção de `_FORMA_LINK` (linha 130) já têm teste próprio; repetir a
   verificação aqui duplicaria a regra em dois lugares.

Três cuidados de varredura, todos já resolvidos por `apps/core/tests/marcacao.py`:

- **`<a` seguido de newline casa.** O helper `elementos()` usa `<(a|button)(?=[\s/>])`, e `\s`
  inclui `\n`. O `<a\n` de `error_summary.html:45` e o de `empty_state.html:21` são exatamente esse
  caso — um `<(a|button)[ >]` ingênuo não os veria, e o teste nasceria já cego para os dois
  infratores que ele existe para pegar.
- **Atributo com `>` dentro não trunca o elemento.** `elementos()` respeita aspas.
- **Classe condicional não vira esconderijo.** `classes()` troca `{% ... %}`/`{{ ... }}` por espaço
  antes de partir a lista, então `min-h-11` só conta se estiver escrito literalmente.

Um quarto cuidado é novo e entra neste PR: **markup dentro de `{% comment %}` não é markup**. Os
blocos de documentação de `components/modal.html`, `components/pagination.html` e
`components/button.html` contêm exemplos de uso com `<button ...>` e `<a ...>` que não renderizam
nada. Sem removê-los, o teste falharia com quatro falsos positivos e a correção óbvia seria
afrouxar o teste. Os blocos são substituídos por igual número de `\n` para que os números de linha
relatados continuem verdadeiros.

A verificação antiga (`min-h-9`/`min-h-10` linha a linha) **continua**: ela cobre um caso que a
varredura por elemento não cobre — o número menor escrito em algo que não é `<a>` nem `<button>`.

## Estratégia de teste

Alinhada à ADR-0010. Nenhum teste novo precisa de banco.

| Caso | O que prova | Onde |
|---|---|---|
| Caminho feliz — âncora de erro | `error_summary.html` renderizado com 2 erros produz `<a>` com `min-h-11` e `rounded-md` | `apps/core/tests/test_components.py` |
| Caminho feliz — CTA secundário | `empty_state.html` com `cta_secundario=True` produz `<a>` com `min-h-11` e `rounded-md` | idem |
| Ausência de `rounded` pelado | `rounded` não aparece como classe isolada em nenhum dos dois arquivos | idem |
| Regressão do mecanismo | O teste reformulado **falha** se um `<a>` sem piso for reintroduzido — provado por um caso sintético em memória, não por reverter o arquivo | idem |
| Exceção legítima | `button.html` com `variant="link"` continua passando, e a razão está escrita no teste | idem |
| `<a` com newline | Um `<a\n  class="...">` sintético sem piso é detectado | idem |
| Piso derivado do CSS | Um elemento com `class="skip-link"` passa sem `min-h-11` literal | idem |
| Guarda global | A varredura sobre `apps/**/*.html` real fica verde | `test_nenhum_controle_abaixo_do_piso_de_44px` |

Os casos sintéticos existem porque um guarda que só é exercitado pela árvore real não prova que
detecta — prova apenas que hoje não há infrator. É essa diferença que deixou os dois controles
desta issue passarem em silêncio.

**Não há caso de permissão negada, violação de domínio ou erro de contrato**: a mudança não toca
service, policy, selector nem view. A tabela da ADR-0010 para essas quatro faces não se aplica a um
PR de template, CSS e teste-guarda; registrado aqui para que a ausência seja decisão e não
esquecimento.

## Invariantes

De `docs/design-system.md`, "Regras invioláveis":

| Regra | Como este PR se comporta |
|---|---|
| **Piso de 44px** | É o objeto do PR. Sai de "regra com mecanismo cego" para "regra com mecanismo que enxerga ausência". |
| **Raio crescente** | Restaurada nas duas linhas: `rounded` (0.25rem) está abaixo do menor degrau; vira `rounded-md` (0.375rem, o degrau de controle). |
| **Token, nunca shade** | Preservada — nenhuma cor muda, nenhuma custom property entra no HTML. |
| **Campo tem uma definição só** | Não tocada; `.campo` continua a única definição e continua entrando na lista de pisos derivada do CSS. |
| **Botão tem uma definição só** | Preservada — o CTA secundário de `empty_state.html` continua sendo o link cru que já era; este PR corrige seu alvo, não muda quem o define. |
| **Quatro degraus de elevação** | Não tocada. |
| **Reversão não é erro** | Não tocada. |

## Riscos

| Risco | Mitigação |
|---|---|
| **O teste novo fica verde por vacuidade** — se a varredura não achar nenhum elemento (regex errado, caminho errado), ele passa sem provar nada | Asserção positiva de contagem mínima de clicáveis varridos, além dos casos sintéticos que devem falhar |
| **Falso positivo em markup de documentação** | Blocos `{% comment %}` removidos antes da varredura, preservando numeração de linha |
| **A derivação da lista de classes de CSS pega lixo** — um regex ingênuo sobre seletores captura `.5rem` como se fosse uma classe `5` | O padrão de nome de classe exige começar por letra, `_` ou `-` |
| **Crescimento de ~24px por linha na lista de notificações** | Consciente e declarado no escopo; é o alvo de 44px sendo cumprido, não regressão |
| **Alteração em `input.css` colide com a Etapa 0 do plano de auditoria** | A mudança é uma linha, aditiva, sem efeito visual, e só existe para o clicável passar por mecanismo em vez de exceção |
| **Concorrência, contrato OpenAPI, mutação de estoque, máquina de estados** | Nenhum: o PR não toca Python de domínio, banco, nem serialização |

## Ordem de execução

1. Reformular `test_nenhum_controle_abaixo_do_piso_de_44px` — vermelho, com os 4 infratores reais
   listados na mensagem de falha.
2. Corrigir `error_summary.html` e `empty_state.html` (alvo + raio) — 2 dos 4 saem.
3. Corrigir `.app-bar__brand` em `input.css` e o link de `notificacoes/lista.html` — verde.
4. Adicionar os testes sintéticos de detecção (`<a` com newline, ausência de piso, exceção
   `variant="link"`, piso vindo do CSS) e os testes de renderização dos dois componentes.
5. Atualizar a linha do "Piso de 44px" em `docs/design-system.md`.
6. `uv run ruff format .`, `uv run ruff check .`, `uv run mypy apps`, suíte completa.

## Critérios de aceite (da issue)

- [ ] Âncoras de `error_summary.html` com alvo ≥ 44px
- [ ] CTA secundário de `empty_state.html` com alvo ≥ 44px
- [ ] Nenhum `rounded` pelado nos dois arquivos
- [ ] Desenho visual dos dois controles inalterado além do alvo
- [ ] O teste detecta **ausência** de `min-h-11`, não só valores menores
- [ ] O teste falha se os dois infratores forem revertidos
- [ ] Exceções legítimas continuam passando, declaradas no próprio teste
- [ ] O regex casa `<a` seguido de newline
- [ ] `uv run pytest`, `ruff check`, `ruff format --check` e `mypy apps` verdes
