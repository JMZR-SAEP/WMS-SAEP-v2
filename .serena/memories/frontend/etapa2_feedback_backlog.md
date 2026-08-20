# Etapa 2 do audit de front-end — camada de feedback e estado

Contexto base para trabalhar as issues #119–#128 em conversas novas. Auditoria feita em
2026-08-18 com `/impeccable audit` + `/impeccable critique` (dual-agent).

## De onde isso vem

- Plano mestre: `docs/plans/audit-frontend-restante.md`. A Etapa 2 cobre os cinco arquivos abaixo.
- Snapshot do critique: `.impeccable/critique/2026-08-18T11-33-52Z__apps-core-templates-components-feedback-e-estado.md`
  (Design Health Score 24/40; Audit Health Score 14/20).
- As 19 telas full-page já foram auditadas antes. A Etapa 0 (tokens/`input.css`) **não** foi feita —
  vários achados desta etapa são sintoma de decisão que vive lá.

Arquivos auditados:

- `apps/core/templates/components/alert.html`
- `apps/core/templates/components/error_summary.html`
- `apps/core/templates/components/empty_state.html`
- `apps/core/templates/components/badge.html`
- `apps/core/templates/core/partials/_messages.html`

## Decisões do dono do produto (2026-08-18) — não reabrir

1. **Dismiss de flash messages foi decidido e nunca implementado.** `docs/CONVENTIONS.md:174-181`
   está certo como intenção; `_messages.html` é que está incompleto. Corrigir o código, não o doc.
   `docs/plans/77-alert-component.md:70-73` e `.design/TASKS.md:23` afirmam falsamente que já existe.
2. **Divergência SCPI exige decisão do chefe de almoxarifado.** Logo `variant="warning"` está
   correto em `preview_importacao_scpi.html:270` — não trocar o token. O que falta é a copy nomear
   o dono da decisão e a próxima ação (conferir e ajustar no SCPI).
3. **`alert.html` precisa ser destrinchado.** Hoje faz banner estático, painel de decisão de
   workflow e casca vazia hidratada por JS. O desenho final não foi fixado — passa por
   `/impeccable shape` antes de código.
4. **`alert.html` e `_messages.html` seguem separados**, sem `_feedback_box.html` compartilhado.
   Condição: paridade bem documentada **e verificada por teste**.

## As 10 issues (JMZR-SAEP/WMS-SAEP-v2), todas com `needs-triage`

| # | Escopo | Tipo | Blocked by | Comando |
|---|---|---|---|---|
| 119 | Contrato de dismiss em `_messages.html` (+ higiene do arquivo, posicionamento em login) | AFK | — | `/impeccable harden` |
| 120 | Piso de 44px em `error_summary` e `empty_state` + corrigir o teste que não vê ausência | AFK | — | `/impeccable adapt` |
| 121 | `badge.html`: fallback preserva dado, `text-white`→token, guarda de rótulo longo | AFK | — | `/impeccable harden` |
| 122 | Política de falha de componente + fechar o guard de cor crua | **HITL** | — | `/impeccable harden` |
| 123 | Copy da importação SCPI: nomear quem decide | AFK | — | `/impeccable clarify` |
| 124 | ✅ **feita** (PR #15) — paridade alinhada, documentada e testada | AFK | 119 | `/impeccable polish` |
| 125 | `error_summary` confiável + adotado nas 3 telas de formset longo | AFK | 120 | `/impeccable harden` |
| 126 | `empty_state`: uma implementação só, anúncio no swap HTMX, copy uniforme | AFK | 120 | `/impeccable onboard` |
| 127 | Destrinchar `alert.html`: extrair painel de decisão | **HITL** | 124 | `/impeccable shape` → `distill` |
| 128 | Regra da Reversão Não é Erro no estorno | **HITL** | 127 | `/impeccable colorize` |

Ordem sugerida: 119 e 120 primeiro (destravam 124/125/126 e têm o maior impacto operacional);
121 e 123 em paralelo a qualquer hora; **122 antes de 127**, porque a política de falha decide
como o `alert.html` reduzido deve se comportar. 122 e 128 não devem ter código escrito antes da
decisão que as bloqueia.

## Fatos medidos que não precisam ser remedidos

- Contraste do ícone do `alert.html` sobre o fundo `-subtle` da própria variante:
  `warning` 2.07:1 (**falha 1.4.11**), `success` 3.07:1, `danger` 4.36:1, `info` 4.82:1.
  Os ícones do `_messages.html` usam `currentColor` e não têm esse problema — alinhar
  `alert.html` a esse padrão mata o achado e elimina 4 ramos condicionais.
- Texto: todos os pares de texto/fundo dos 5 alvos passam AA. A exceção é `text-text-disabled`
  (slate-400, 2.63:1), que carrega texto real em 6 lugares — só a ocorrência dentro do clone de
  estado vazio (`preview_importacao_scpi.html:259`) é escopo da Etapa 2; as outras 5 são Etapa 7/8.
- Badges: as 14 variantes passam AA com folga (pior par 6.94:1).
- `min-h-11` aparece **0 vezes** nos 5 alvos. Só 2 clicáveis existem neles:
  `error_summary.html:45` e `empty_state.html:21` — ambos sem piso.
- `rounded` **pelado** vale 0.25rem, abaixo do menor degrau da escala. Aparece em
  `error_summary.html:47` e `empty_state.html:23`.
- 12 classes de paleta crua no repo inteiro, **todas** em `badge.html` (orange/indigo/violet/yellow).

## Guardas existentes e seus buracos

- `apps/core/tests/test_components.py:434` (`test_nenhum_controle_abaixo_do_piso_de_44px`) só procura
  `min-h-9`/`min-h-10`. **Não detecta ausência total de piso.** Corrigido na issue 120.
- `apps/core/tests/test_tokens_semanticos.py:30-32` — o regex cobre `blue|red|amber|green|teal`;
  as 4 famílias realmente usadas pelo `badge.html` (`orange|indigo|violet|yellow`) ficam de fora.
  O teste passa vacuamente. Corrigido na issue 122.
- `apps/requisicoes/tests/test_views.py:2713` conta `role="alert"` == 1 e `role="status"` == 1 em
  `_messages.html`. Qualquer mudança de marcação lá precisa preservar essa contagem.
- `docs/design-system.md` avisa: *"regra sem mecanismo vira sugestão"*. Já aconteceu 3 vezes neste
  conjunto. Toda issue desta etapa fecha com teste, não só com correção.

## O que a #124 fixou (não reabrir)

- **`warning` é a exceção da escala de sufixos.** É a única família com
  `-text-subtle`, então sua escada anda um degrau: 700/**800**/900 em
  `-text-subtle`/`-text`/`-text-strong`, e **não existe `-text-emphasis` em
  âmbar**. Nas outras três, `-text` é 700 e o 800 se chama `-text-emphasis`.
  A tabela de sufixos de `docs/design-system.md` dizia só "700" e mentia para
  âmbar; agora marca a exceção. Consequência: `text-warning-text` é o
  equivalente de `-text-emphasis`, não um degrau abaixo.
- **A #119 moveu a marcação da faixa para `_message_item.html`.** Qualquer issue
  desta etapa escrita antes de 2026-08-19 que cite `_messages.html:<linha>` está
  apontando para o arquivo errado — hoje ele só resolve a variante.
- **Superfície de banner e de faixa são a mesma**: `rounded-lg`, `px-4 py-3`,
  degrau 800 de texto, ícone em `currentColor`. Tabela em
  `docs/design-system.md` §Paridade entre o banner e a faixa de flash, verificada
  por `apps/core/tests/test_paridade_feedback.py`. O `layout="row"` do
  `alert.html` fica fora: tem `shadow-sm`, é papel, leva `rounded-xl`.
- **Margem negativa do botão de fechar acompanha o padding da caixa.** Com
  `py-3` e `-my-2`, o alvo de 44px empurra a faixa para 52px contra os 45px do
  banner — as classes batem na tabela e a altura real diverge. `-mr-3` (e não
  `-mr-4`) preserva os 4px que o anel de foco precisa.
- **Teste de paridade tem três lados**, e é de propósito: constante no módulo de
  teste, tabela do design system, HTML renderizado. Comparar só os dois
  templates entre si passa se alguém mudar os dois para o mesmo valor errado.

## Armadilhas técnicas que já custaram tempo

- **`detect.mjs` do Impeccable devolve `[]` para estes arquivos e isso é "não medido", não "limpo".**
  É parser de HTML estático; 100% do estado visual vive dentro de `{% if %}`. Para medir de verdade,
  renderizar os estados pelo engine do Django (`render_to_string`) e analisar o HTML final.
- **Live region só dispara com mudança.** Conteúdo já presente no carregamento não é anunciado — é o
  que `error_summary.html:10-11` documenta e o que os três `aria_live` de `preview_importacao_scpi.html`
  (linhas 93, 266, 270) ignoram. Depois de um POST full-page, o mecanismo que funciona é foco programático.
- **`focus-visible` não casa em foco programático** após navegação que não foi por teclado.
  `error_summary.html:32` usa `focus-visible:ring-2` e o foco é via `x-init` — usar `focus:`.
- **Badge de dado estático nunca recebe `role="status"`/`alert`** — uma listagem de 20 linhas viraria
  20 live regions. Está documentado em `badge.html:13-16` e no checklist do design system.
- **`gh issue create --label` falha em silêncio neste repo.** A conta ativa do `gh` é `joaozuneda6`,
  que pode abrir issue no `JMZR-SAEP` mas não rotular (`AddLabelsToLabelable`). Rotular num segundo
  passe com `GH_TOKEN=$(gh auth token --user joaorighetto)` na própria invocação, sem trocar a conta
  ativa. Ver `mem:project_overview` para a topologia de remotes.
- **Esta memória já se perdeu uma vez.** `.serena/memories/` é versionado, mas arquivo novo nasce
  untracked e não sobrevive a troca de branch nem a limpeza da working tree. Commitar junto com o
  trabalho da branch em que foi criado.

## Contradição aberta na fonte da verdade

`DESIGN.md` lista **"estorno"** entre os usos legítimos de `danger`, e logo abaixo a Named Rule
*"A Regra da Reversão Não é Erro"* diz que **nenhum evento legítimo do domínio recebe a cor da recusa**.
As duas não podem estar certas. Hoje o caminho do estorno é vermelho (`detalhe.html:327`) e o estado
final é teal (`_estado_badge.html:23`). Resolver no doc antes de tocar código — é o primeiro passo da
issue 128.

## Onde o domínio manda na UI (não reabrir na implementação)

- Ações disponíveis vêm de transições + policies; a tela apresenta, não decide.
- Ação de workflow bloqueada fica **visível e desabilitada, com o motivo em texto** amarrado por
  `aria-describedby`; usa `aria-disabled`, não `disabled` nativo.
- Componente global não conhece enum de domínio: `variant`/`label` chegam resolvidos pelo partial.
- Listagem se renderiza em cartões, nunca em `<table>`.
