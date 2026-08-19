# Plano — `badge.html`: fallback que não perde dado, token no lugar da cor crua e guarda de rótulo longo

Issue: [#121](https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/121) — origem: Etapa 2 (Feedback e
estado) de `docs/plans/audit-frontend-restante.md`.

## Escopo

### O que muda

Um arquivo de template, um arquivo de teste novo (ampliado) e uma linha de teste de token. Os três
defeitos da issue são independentes entre si e cada um fecha com mecanismo próprio.

#### 1. O ramo de fallback (`badge.html:49`) para de descartar dado

Hoje o ramo `{% else %}` é o único dos 14 que não emite `prefixo_sr` e o único que joga o `label`
fora. Um leitor de tela numa listagem ouve "Indisponível" sem saber de que campo, e quem depura
não encontra em lugar nenhum nem o rótulo que chegou nem a variante que não foi mapeada.

O ramo passa a emitir, na ordem:

1. `prefixo_sr` como `sr-only`, exatamente como os outros 13 ramos — mesma marcação, mesma
   condicional `{% if prefixo_sr %}`;
2. **"Indisponível" visível**, inalterado — é o sinal alto que a issue manda preservar;
3. o `label` recebido como `sr-only` entre parênteses, logo depois do sinal — sob
   `{% if label %}`, porque `label` sem valor renderizaria "Indisponível ()" e o leitor de tela
   anunciaria um par de parênteses vazio.

O leitor de tela passa a ouvir "Estado: Indisponível (Aguardando autorização)": o alerta primeiro,
o dado original em seguida. Nada some da tela e nada some da árvore de acessibilidade.

**`role` e `aria_label` continuam propagados literalmente no ramo, sem mudança.** Eles já vinham
sendo emitidos pelo `{% else %}` de hoje e continuam sendo — a reescrita do ramo é aditiva, não
substitui a assinatura de abertura do `<span>`. Como o ramo inteiro é reescrito, essa preservação
deixa de ser óbvia por leitura do diff, então ela ganha teste próprio
(`test_fallback_preserva_role_e_aria_label`) em vez de ficar só declarada aqui.

Além disso o ramo ganha `data-badge-variant="{{ variant }}"`. A issue diz, no diagnóstico do
defeito 1, que "o valor cru que não foi mapeado não aparece em lugar nenhum" — e o valor que **não
foi mapeado** é a `variant`, não o `label`. O `sr-only` resolve o lado do leitor de tela; o
`data-` resolve o lado da depuração, que é quem precisa saber qual string de variante chegou.
É um atributo, só no ramo de fallback, e é assertável em teste.

**Por que não trocar "Indisponível" pelo próprio `label`.** Seria mais informativo e é
exatamente o que a issue proíbe: num sistema de livro-razão, estado não mapeado deve gritar. Um
badge que mostra o rótulo certo com a cor errada esconde o defeito de mapeamento em vez de
denunciá-lo.

#### 2. `text-white` vira `text-text-on-primary`

`text-white` é a única cor crua do arquivo fora da exceção declarada no design system (a exceção
cobre `orange-100`, `indigo-100`, `violet-100`, `yellow-100` — as quatro variantes de catálogo, e
mais nada). O token do sistema para texto sobre superfície de marca é `--color-text-on-primary`,
já declarado em `input.css:102` como `var(--color-white)`.

A utility gerada por esse token no Tailwind v4 é **`text-text-on-primary`** — o prefixo `text-` da
utility mais o nome do token, que por acaso também começa com `text-`. O nome é feio e é o correto;
está registrado aqui para não virar "typo" na revisão.

**Sem mudança de pixel**: `--color-text-on-primary` resolve para `var(--color-white)`, o mesmo
valor que `text-white` produzia. O contraste do fallback (branco sobre `bg-danger` = red-600,
4.76:1) fica idêntico e continua passando AA para texto pequeno em negrito. Não há trabalho de cor
neste PR.

#### 3. Guarda de rótulo longo nos 14 ramos

Hoje nenhum dos 14 ramos tem largura máxima, quebra ou truncamento. O rótulo mais longo do domínio
("Aguardando autorização", 22 caracteres) ainda cabe, então o risco é teórico — e é exatamente por
isso que a guarda entra agora, antes de existir o estado que a torna necessária.

A guarda tem duas partes, idênticas nos 14 ramos:

- no `<span>` raiz do badge: **`max-w-48`** (12rem = 192px na escala do Tailwind v4, `--spacing` ×
  48). Não é valor arbitrário: é degrau da escala. O tamanho segue o precedente já vivo no repo —
  `preview_importacao_scpi.html:160` usa `max-w-[12rem]` para o nome de arquivo — e foi escolhido
  para caber com folga o rótulo real mais longo: 22 caracteres a `text-xs` semibold medem ~132px,
  bem abaixo dos 192px. **Nenhum rótulo do domínio hoje é afetado.**
- no `<span>` interno que embrulha o **texto visível** do ramo: **`min-w-0 break-words`**. Nos 13
  ramos de variante esse texto é o `{{ label }}`; no ramo de fallback é a string "Indisponível".
  A marcação é a mesma nos 14, que é o que o critério "comportamento idêntico entre elas" cobra.

**Por que quebra de linha e não truncamento.** A issue aceita "truncamento ou largura máxima". Este
PR escolhe quebrar porque o defeito 1 do mesmo arquivo é literalmente *o componente descartar
dado*: fechar esse buraco no fallback e abrir outro por CSS no mesmo commit seria incoerente. Com
`break-words` o rótulo comprido ocupa duas linhas dentro do pill e continua inteiro — para o olho
e para o leitor de tela. Um pill de duas linhas com `rounded-full` vira losango; é feio e é
honesto, e só acontece acima de 192px de texto, ou seja, num estado de domínio que ainda não
existe.

**Por que o `<span>` interno e o `min-w-0` são necessários.** O badge é `inline-flex`. O texto solto
vira um item de flex anônimo, e item de flex tem `min-width: auto`, o que o impede de encolher
abaixo do próprio `min-content`. `overflow-wrap: break-word` (o que a utility `break-words` faz)
**não** reduz o `min-content` de uma palavra longa — ele só quebra a palavra quando a caixa já é
mais estreita que ela. Sem `min-w-0` num item nomeado, um rótulo de 40 caracteres sem espaço
estouraria o `max-w-48` em vez de quebrar. Com o `<span>` interno carregando `min-w-0`, a caixa
encolhe até o limite do pai e a palavra quebra.

**Por que não `title="{{ label }}"`**, apesar do precedente em `preview_importacao_scpi.html:160`.
Lá o `title` existe porque o texto é truncado com reticências e some. Aqui nada some. E `title` num
badge que já carrega `prefixo_sr` produziria anúncio duplicado no leitor de tela ("Estado:
Autorizada, Autorizada") em toda listagem. Decisão deliberada, registrada para não parecer omissão.

### O que NÃO muda

- **Contraste.** As 14 variantes foram medidas na auditoria e passam AA com folga (pior par:
  `red-900` sobre `red-200` = 6.94:1). A issue declara explicitamente que não há trabalho de cor
  aqui. Nenhuma cor deste arquivo muda de valor.
- **As 4 variantes de catálogo** (`orange`, `indigo`, `violet`, `yellow`) continuam com cor crua.
  É a exceção declarada em `docs/design-system.md:36` e continua valendo.
- **`CLASSE_CRUA_RE` em `apps/core/tests/test_tokens_semanticos.py:30-32`** continua cobrindo só
  `blue|red|amber|green|teal`. Fechar esse buraco é escopo da **issue #122** ("Política de falha de
  componente + fechar o guard de cor crua"), que é HITL. Este PR não toca no regex compartilhado —
  em vez disso adiciona uma guarda **local** em `test_components_badge.py`, que prova o critério de
  aceite deste issue sem antecipar a decisão do #122.
- **A política de falha do componente** (fallback alto do badge × fallback silencioso do alert ×
  `_estado_badge.html:25`, que anula o fallback alto mapeando o `{% else %}` para `slate`) é
  decisão da issue #122. Este PR melhora o fallback que existe; não decide se ele deve existir.
- **Os 13 ramos de variante não são colapsados.** A duplicação das 14 linhas quase idênticas é
  achado registrado em `docs/plans/audit-design-system.md:189` e tem `/impeccable distill` próprio.
  Colapsar aqui inflaria o diff e misturaria refatoração com correção de borda.
- **Nenhum consumidor de `badge.html` muda.** `_estado_badge.html`, `_estado_saida_badge.html`,
  `table.html`, as telas de fila e as de estoque continuam chamando o componente com os mesmos
  parâmetros.
- **Nenhum comportamento de domínio, permissão, transição ou persistência.** É PR de template.

## Arquivos tocados

| Arquivo | O que muda |
|---|---|
| `apps/core/templates/components/badge.html` | 14 ramos ganham `max-w-48` na raiz e `<span class="min-w-0 break-words">` em volta do texto; o ramo de fallback ganha `prefixo_sr`, `label` em `sr-only`, `data-badge-variant` e troca `text-white` por `text-text-on-primary`; o bloco `{% comment %}` de cabeçalho documenta o contrato novo do fallback e a guarda de rótulo |
| `apps/core/tests/test_components_badge.py` | testes novos: fallback preserva `prefixo_sr`/`label`/sinal/variante crua; guarda de rótulo presente nos 14 ramos; nenhuma cor crua fora das 4 variantes de catálogo |
| `apps/core/tests/test_tokens_semanticos.py` | `text-text-on-primary` entra em `UTILITIES_ESPERADAS` — prova que o token novo realmente compila para utility no `app.css`, e não só que a cor crua sumiu do template |
| `docs/plans/121-badge-fallback-token-rotulo-longo.md` | este plano |

`apps/core/static/core/css/input.css` **não** muda: `--color-text-on-primary` já existe.

## Como cada defeito ganha mecanismo

O design system avisa que "regra sem mecanismo vira sugestão", e a memória da Etapa 2 registra que
isso já aconteceu três vezes neste conjunto de arquivos. Cada um dos três defeitos fecha com teste.

### Defeito 1 — fallback

Testes de comportamento, renderizando o template com `render_to_string` (o `detect.mjs` do
Impeccable devolve `[]` para este arquivo porque 100% do estado visual vive dentro de `{% if %}`;
a única medição válida é renderizar pelo engine do Django):

**Asserção por estrutura, não por substring.** `assert 'Estado: ' in html` passaria com o prefixo
visível, fora do `sr-only`, ou na ordem errada — os três defeitos que estes testes existem para
impedir. Os testes do fallback parseiam o HTML renderizado com
`xml.etree.ElementTree.fromstring` (o badge é um único elemento bem-formado, sem dependência
nova) e afirmam sobre a árvore: quais filhos existem, com que classe, e em que ordem o texto
aparece.

- `test_fallback_emite_prefixo_sr_dentro_de_sr_only` — variante desconhecida +
  `prefixo_sr="Estado: "` → existe um `<span class="sr-only">` cujo texto é exatamente
  `Estado: `, e ele é o **primeiro** filho do badge;
- `test_fallback_mantem_indisponivel_como_texto_visivel` — a string "Indisponível" está no texto
  **fora** de qualquer `sr-only`, ou seja, no conteúdo visível do badge;
- `test_fallback_preserva_label_em_sr_only_depois_do_sinal` — o `label` recebido aparece dentro de
  um `<span class="sr-only">`, entre parênteses, e a posição desse `sr-only` na árvore é
  **posterior** à do texto visível "Indisponível";
- `test_fallback_preserva_role_e_aria_label` — variante desconhecida + `role="status"` +
  `aria_label="Estado: Indisponível"` → ambos os atributos no elemento raiz, com o valor recebido
  (contrato que já existia e não pode se perder na reescrita do ramo);
- `test_fallback_expoe_variant_crua_para_depuracao` — o elemento raiz tem
  `data-badge-variant="estado-que-nao-existe"`;
- `test_fallback_sem_label_nao_emite_parenteses_vazios` — sem `label`, não existe `sr-only` com
  `()`;
- `test_fallback_sem_prefixo_sr_nao_inventa_sr_only` — sem `prefixo_sr`, o único `sr-only` do
  fallback é o do `label`.

### Defeito 2 — token

- `test_fallback_usa_token_semantico_e_nao_text_white` — `text-text-on-primary` presente,
  `text-white` ausente;
- `test_badge_nao_tem_cor_crua_fora_das_quatro_variantes_de_catalogo` — varre o arquivo com
  `(?:bg|text|border|ring|divide)-([a-z]+)-\d`, coleta as famílias encontradas e exige que o
  conjunto seja exatamente `{orange, indigo, violet, yellow}`. Guarda local, deliberadamente
  independente do `CLASSE_CRUA_RE` compartilhado (#122);
- `test_tokens_semanticos.py::test_css_build_gera_tokens_e_utilities_novas` — com
  `text-text-on-primary` na lista, o teste falha se o nome da utility estiver errado ou se o
  Tailwind não a gerar. É o teste que separa "tirei a cor crua" de "coloquei o token certo".

### Defeito 3 — guarda de rótulo longo

Duas camadas, porque só a de comportamento não enxergaria um ramo novo escrito sem guarda:

- **Comportamento**: parametrizado nas 13 variantes conhecidas mais uma desconhecida (14 casos) —
  cada render contém `max-w-48` e `min-w-0 break-words`;
- **Estrutura**: `test_guarda_de_rotulo_longo_em_todos_os_ramos_do_arquivo` lê `badge.html` e
  fatia o arquivo **por ramo**, não por contagem global.

  A delimitação **não** pode ser por `{% if %}`/`{% elif %}`/`{% else %}` genérico nem pelo
  primeiro `</span>`: cada ramo carrega condicionais internas (`{% if role %}`,
  `{% if aria_label %}`, `{% if prefixo_sr %}`) e `<span>`s internos (`sr-only`, e agora o da
  guarda), de modo que uma contagem ingênua de tags daria muito mais que 14 e o primeiro
  `</span>` fecharia um filho, não a raiz.

  A delimitação correta é pela **cadeia de variantes**: o teste corta o arquivo nos marcadores
  `{% if variant == '...' %}`, `{% elif variant == '...' %}` e no `{% else %}` que fecha a cadeia
  — os únicos que abrem ramo — e trata cada fatia como um ramo. Dentro de cada fatia afirma:
  exatamente um `max-w-48` e exatamente um `min-w-0 break-words`. O teste também exige que o
  número de fatias seja 14, para que um ramo novo não passe despercebido nem um ramo existente
  possa ser removido em silêncio.

  Comparar totais (`arquivo.count('min-w-0 break-words') == 14`) seria falso conforto: dois no
  ramo `blue` compensariam zero no ramo `teal` e o teste passaria. Por isso a asserção é por
  fatia.

  Um 15º ramo escrito sem guarda quebra este teste, que é o ponto: a guarda vale para os ramos que
  ainda não existem.

O critério "um rótulo de 40+ caracteres não estoura o cartão de listagem a 375px" não é assertável
em `pytest` — não há navegador na suíte (o `playwright` do `package.json` é devDependency de QA
manual, precedente em `docs/plans/gh5-modal-universal.md:139`). É verificado no navegador antes de
abrir o PR e a evidência vai no corpo do PR: `historico_requisicoes.html` a 375px com um rótulo
sintético de 40+ caracteres, antes e depois.

## Estratégia de teste

| Camada | O que prova |
|---|---|
| Caminho feliz | as 13 variantes conhecidas continuam produzindo as mesmas classes de cor, o mesmo `rounded-full` e o mesmo `label` visível — os testes existentes de `test_components_badge.py` seguem verdes sem edição |
| Contrato do componente | `role` e `aria_label` continuam propagados literalmente e continuam ausentes por padrão (testes existentes); `prefixo_sr` agora vale nos 14 ramos, não em 13 |
| Caso de borda | variante desconhecida: sinal preservado, `prefixo_sr` preservado, `label` preservado, `role`/`aria_label` preservados, `variant` crua exposta |
| Regressão de sistema | zero cor crua fora das 4 de catálogo; utility do token novo realmente compilada no `app.css` |
| Regressão estrutural | guarda de rótulo longo presente em **todos** os ramos do arquivo, incluindo os que forem escritos depois |

Sem teste de DB, sem teste de view, sem factory: é template puro, renderizado por
`render_to_string`. Segue o padrão já estabelecido em `test_components_badge.py`.

## Invariantes

`docs/matriz-invariantes.md` cobre invariantes de domínio (saldo, reserva, transição de estado,
ledger). **Nenhuma é tocada** — este PR não roda código de domínio.

Os invariantes de fato relevantes aqui são os do design system, e todos os cinco continuam válidos:

- **Token, nunca shade** — o PR *aumenta* a conformidade: sai a última cor crua fora da exceção
  declarada. As 4 variantes de catálogo permanecem como exceção viva e documentada.
- **Componente global não conhece enum de domínio** — `variant`/`label` continuam chegando
  resolvidos pelo partial de domínio. O `data-badge-variant` expõe a string que chegou, não
  interpreta nenhuma.
- **Badge de dado estático nunca vira live region** — `role` continua opcional e propagado
  literalmente; nada neste PR adiciona `role="status"`/`alert`.
- **Raio crescente** — `rounded-full` (pill) inalterado nos 14 ramos.
- **Piso de 44px** — não se aplica: badge não é controle acionável. Nenhum `<a>`/`<button>` entra
  no arquivo, então `test_nenhum_controle_abaixo_do_piso_de_44px` (endurecido na issue #120)
  continua sem ter o que cobrar aqui.

## Riscos

| Risco | Probabilidade | Mitigação |
|---|---|---|
| A utility `text-text-on-primary` não é gerada pelo Tailwind (nome do token com prefixo repetido) | baixa | `UTILITIES_ESPERADAS` passa a exigi-la; o teste roda `npm run css:build` e falha se o seletor não existir no `app.css`. Se falhar, o caminho alternativo é `text-(--color-text-on-primary)`, mas isso é custom property no HTML — proibido pela mesma regra — então a saída correta seria renomear o token, o que é escopo de outra issue e vira blocker |
| `max-w-48` não é degrau real da escala do Tailwind v4 | baixa | verificado no `app.css` compilado antes do commit; se não existir, cai para `max-w-[12rem]`, o valor com precedente vivo no repo |
| O `<span>` interno quebra alinhamento vertical do pill | baixa | o `<span>` interno é item de flex de um `inline-flex items-center`; sem `flex-` nenhum ele se comporta como o texto anônimo que substitui. Verificado no navegador nas quatro telas de listagem que usam badge |
| `max-w-48` aperta o badge em cartão estreito e força quebra num rótulo que hoje cabe | baixa | 192px contra ~132px do rótulo real mais longo; verificado a 375px antes do PR |
| Consumidor com `shrink-0` em volta do badge (`table.html:32`, `lista_saidas_excepcionais.html:27`) anula a guarda | nenhuma | a guarda é `max-width` **no próprio badge**, não `max-w-full` relativo ao pai. `shrink-0` no pai não afeta um limite absoluto |
| O `sr-only` do `label` no fallback vaza para o texto visível | nenhuma | `sr-only` é a mesma classe já usada pelo `prefixo_sr` nos outros 13 ramos |
| `break-words` é nome legado — o Tailwind v4.1 introduziu `wrap-break-word` para a mesma declaração | nenhuma | `break-words` continua gerando `overflow-wrap: break-word` na versão em uso e é o nome adotado em 8 templates do repo (`table.html:30`, `lista_minhas.html:30`, `historico_requisicoes.html:59`, entre outros). Trocar o nome é migração de nomenclatura do repo inteiro, não escopo deste PR |

## Ordem de execução

0. **Confirmar a branch atual** com `git branch --show-current` antes de qualquer commit — o
   `AGENTS.md` proíbe commitar direto na `main`, e a checagem vale para todos os commits desta
   ordem, não só para o primeiro.
1. Plano commitado e revisado (esta etapa).
2. **RED**: testes do defeito 1 (fallback) — falham contra o template atual.
3. **GREEN**: reescrever o ramo `{% else %}` de `badge.html`.
4. **RED**: teste do defeito 2 (token + cor crua local) — falha.
5. **GREEN**: `text-white` → `text-text-on-primary`; adicionar a utility em `UTILITIES_ESPERADAS`.
6. **RED**: testes do defeito 3 (comportamento + estrutura) — falham.
7. **GREEN**: `max-w-48` + `<span class="min-w-0 break-words">` nos 14 ramos.
8. **REFACTOR**: atualizar o `{% comment %}` de cabeçalho do componente com o contrato novo.
9. `ruff format .`, `ruff check .`, `mypy apps`, suíte completa.
10. QA manual no navegador a 375px com rótulo sintético de 40+ caracteres; evidência para o PR.

## Critérios de aceite (da issue)

- [ ] O ramo de fallback emite `prefixo_sr` quando passado
- [ ] O ramo de fallback preserva o `label` recebido, sem esconder o sinal "Indisponível"
- [ ] `text-white` foi substituído pelo token semântico (`text-text-on-primary`)
- [ ] Nenhuma classe de paleta crua sobra fora das 4 variantes de catálogo declaradas como exceção
- [ ] Todas as 14 variantes têm guarda de rótulo longo, com comportamento idêntico entre elas
- [ ] Um rótulo de 40+ caracteres não estoura o cartão de listagem a 375px de viewport
- [ ] Teste cobrindo: fallback preserva `label` e `prefixo_sr`; nenhuma variante perde o rótulo;
      guarda de rótulo longo presente nos 14 ramos
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run mypy apps`
      verdes
