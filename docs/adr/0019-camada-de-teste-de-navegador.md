# ADR-0019 — Camada de teste de comportamento em navegador

## Status

Aceita

## Contexto

A pirâmide da ADR-0010 vai de Models a Views e termina no contrato HTTP. Nada abaixo disso executa
JavaScript. O projeto tem 923 linhas de JS em `apps/core/static/core/js/` — seis arquivos que
governam foco, ciclo de `<dialog>`, bloqueio de duplo envio, combobox de autocomplete e linhas
dinâmicas de formset — e nenhuma delas é exercitada por teste.

A auditoria da Etapa 3 do plano `docs/plans/audit-frontend-restante.md` encontrou dois defeitos que
existiam há meses e só aparecem em runtime:

1. `x-trap.inert.noscroll="$refs.dialog.open"` em `components/modal.html` **nunca ativa**. `$refs` é
   `mergeProxies`, não `reactive()`, e `.open` é propriedade IDL nativa de `HTMLDialogElement` — o
   `effect` do Alpine não rastreia nada, roda uma vez no init com o diálogo fechado e nunca mais.
   O `.noscroll` é código morto e a página atrás rola com o modal aberto. Medido lado a lado contra
   `base_auth.html`, que liga o mesmo diretivo a um dado Alpine e funciona.
2. A expressão gerada em `components/_modal_body.html` — `getElementById(...)?.requestSubmit() ??
   console.error(...)` — **sempre** executa o `console.error`, porque `requestSubmit()` devolve
   `undefined` e `undefined ?? X` avalia `X`. Toda confirmação de retirada bem-sucedida grava um
   erro falso no console.

Nenhum dos dois aparece no HTML renderizado, que é o único instrumento que o projeto tem hoje para o
front. `apps/core/tests/test_modal.py` são 5 testes e cobrem só o contrato XOR de
`validar_contrato_modal` e a presença de uma string de `hx-sync`.

Existe cargo relacionado: `playwright` está em `devDependencies` do `package.json` desde `d700fd4`
(2026-05-23, `chore: add Playwright dev dependency`, corpo vazio), sem nenhum spec, sem
`playwright.config`, sem diretório `e2e/`. Três meses de dependência instalada e zero uso.

O custo a proteger é concreto: **2162 testes em 7,85s** com `-n logical`. A suíte é instantânea, e
isso é uma característica que o projeto usa — agentes rodam a suíte inteira a cada mudança. Um
navegador é a coisa mais lenta que entraria no pipeline, por ordem de grandeza.

O que já existe e reduz o custo de entrada:

- `apps/core/tests/marcacao.py` é uma lane de varredura estática de template, com parser de
  atributos que respeita aspas, usada por 5 módulos de teste. Guarda de forma de código já tem casa.
- O job `pytest` do CI já sobe PostgreSQL 16 como service.
- `django.contrib.staticfiles` está em `INSTALLED_APPS` e `app.css` é versionado — o servidor de
  teste do Django serve os assets sem passo de build.
- `--strict-markers` já está ligado no comando padrão, e não há nenhum marker registrado.

## Decisão

### A camada existe, e é a menor possível

A pirâmide da ADR-0010 ganha um degrau abaixo de Views:

```text
Models    → invariantes estruturais e properties semânticas
Policies  → matriz de autorização por papel/contexto
Selectors → visibilidade e escopo de leitura por papel
Services  → orquestração, atomicidade, efeitos de transição
Views     → contrato HTTP: autenticação, autorização de acesso, renderização
Navegador → comportamento que só existe com layout, top layer e XHR reais
```

Esta camada **não** é uma suíte E2E. Ela não cobre fluxo de usuário, não navega entre telas, não
substitui teste de view e não faz asserção visual. É o menor conjunto de casos que prova
comportamento que nenhuma outra camada alcança.

### Critério de admissão

Um teste só entra na camada Navegador se depende de pelo menos uma destas quatro coisas (a quarta
entrou pela Emenda de 2026-09-04, abaixo):

1. **Layout real** — geometria, `getBoundingClientRect`, rolagem, tamanho computado.
2. **Top layer e semântica nativa de `<dialog>`** — `showModal()`, contenção de foco, `::backdrop`.
3. **Ida e volta de XHR real** — o ciclo do htmx com resposta de verdade, incluindo swap e erro.
4. **Cascade resolvida e pipeline de cor** — valor que só existe depois da cascade (fundo herdado de
   um ancestral, cor efetiva de um par pai/filho) e conversão de espaço de cor (`oklch()` → sRGB).

Se o conserto puder ser provado por um atributo no HTML renderizado, ele **não** entra aqui. Essa é
a regra que impede a camada de crescer até virar a suíte que ninguém roda.

### As três lanes de teste de front, e a fronteira entre elas

| Lane | Instrumento | Prova | Exemplos |
|---|---|---|---|
| **Marcação** | `apps/core/tests/marcacao.py` | Forma do código-fonte do template | Expressão de `x-trap` não referencia propriedade DOM; nenhum controle sem piso de 44px; nenhuma cor crua fora da allowlist |
| **Render** | `pytest` + Django test client / `render_to_string` | Atributo presente no HTML gerado | `<dialog open>` quando `abrir_ao_carregar`; `aria-labelledby` apontando pro id certo; título do 422 igual ao do render inicial; `role`, `tabindex`, `loading_label` |
| **Navegador** | `pytest-playwright` + `live_server` | Comportamento em execução | Trava de scroll com modal aberto; foco inicial; fechar durante requisição em voo; 5xx dentro do modal |

Em caso de dúvida sobre onde um teste mora, a ordem de preferência é Marcação → Render → Navegador.
Subir de lane é decisão consciente e precisa de justificativa no próprio teste.

### Instrumento

`pytest-playwright` com a fixture `live_server` do `pytest-django`, no mesmo runner e na mesma
linguagem do resto da suíte.

Alternativas descartadas e por quê:

- **vitest + jsdom / happy-dom** — Node já está no CI pelo job `css-build`, então o ecossistema não
  seria novo. Mas jsdom não faz layout: `getBoundingClientRect` devolve zeros, não há trava de
  scroll para observar, e `<dialog>` é implementado parcialmente. Os dois defeitos que motivaram
  este ADR moram exatamente onde jsdom não alcança, e o ciclo do htmx exigiria fingir o htmx — o
  que testa o fingimento. Cobriria o foco inicial e nada mais do que está bloqueado.
- **`playwright` do npm** — obrigaria a subir o Django separado, fora do controle do teste, e
  duplicaria comando, linguagem de asserção e configuração. Sai do `package.json` (ver Consequências).
- **Nenhuma camada, só guarda estática** — a guarda de `x-trap` é barata e entra de qualquer jeito,
  mas não existe forma estática de provar que um 5xx dentro do modal produz mensagem visível. Esse
  é o achado P1 de uma ação irreversível falhando em silêncio, e `docs/design-system.md` já registra
  a regra da casa: *"regra sem mecanismo vira sugestão"*.

### Organização e marcador

```text
apps/<app>/tests/test_navegador_<assunto>.py
```

Todo teste da camada leva `@pytest.mark.navegador`, registrado em `[tool.pytest.ini_options]` —
`--strict-markers` já está ligado, então o marcador é obrigatório e não pode ser digitado errado em
silêncio.

O comando padrão do projeto **exclui** a camada:

```bash
uv run pytest -q -ra --tb=short --strict-markers --disable-warnings -n logical -m "not navegador"
```

A camada roda por comando próprio:

```bash
uv run pytest -m navegador
```

Motivo: a suíte de 7,85s é ferramenta de loop curto, usada a cada mudança. Diluí-la com boot de
navegador destrói o que ela tem de melhor. Quem precisa da camada a invoca; o CI a invoca sempre.

### Escopo por arquivo de JS

Classificação obrigatória pela ADR, revisável quando a etapa correspondente do plano de auditoria
chegar:

| Arquivo | Linhas | Status | Escopo |
|---|---|---|---|
| `modal.js` | 173 | **Coberto** | Só os casos de layout, top layer e XHR: trava de scroll, foco inicial, fechar em voo, 5xx no modal. `focarPrimeiroCampo`, `devolverFoco` e `abrirSemTrigger` entram porque dependem de `<dialog>` real |
| `form-submit.js` | 186 | **Parcial** | O bloqueio de duplo envio e a liberação por `htmx:afterRequest` entram. A restauração por `pageshow`/bfcache fica **fora de escopo declarado** — bfcache não é dirigível de forma confiável em automação |
| `autocomplete.js` | 202 | **Adiado** | Combobox ARIA, navegação por seta, debounce e cancelamento de requisição em voo são o alvo da Etapa 4 do plano de auditoria. A camada os recebe quando aquela etapa chegar |
| `item_form_row.js` | 189 | **Adiado** | Foco após inserir linha via HTMX e índice de formset são o alvo da Etapa 1. Mesmo tratamento |
| `mensagens.js` | 122 | **Adiado** | Dispensa de flash message é o alvo da issue #119 (Etapa 2). Mesmo tratamento |
| `acao-bloqueada.js` | 51 | **Coberto** | Barra a ativação de `aria-disabled` em fase de captura, valendo para submit, HTMX e `@click` do Alpine. Só um navegador prova as três |

> O plano `docs/plans/audit-frontend-restante.md` diz "4 arquivos, 586 linhas". A contagem real é
> **6 arquivos, 923 linhas**. O plano é corrigido junto com este ADR.

### CI

Job próprio, **bloqueante para merge**, com `needs: [pytest]`.

```text
ruff-format ─┐
ruff-check  ─┼─→ pytest ─→ navegador
mypy        ─┘   migrations
```

`needs: [pytest]` e não `needs: [ruff-format, ruff-check, mypy]`: teste de navegador só informa
alguma coisa se a suíte de unidade já está verde, e boot de navegador em cima de suíte vermelha é
minuto de CI queimado sem sinal.

Bloqueante e não informativo: um check não-bloqueante vermelho vira paisagem e para de ser lido — e
o que esta camada guarda é falha silenciosa em ação irreversível. Se ela ficar instável a ponto de
travar entrega, o remédio é encolher o escopo, não afrouxar o gate.

O job instala só o Chromium (`playwright install --with-deps chromium`). Sem matrix de navegador:
o produto é interno, atrás de login, e a stack é a mesma que a ADR-0012 já fixou sem matrix.

## Consequências

O comando de teste do projeto muda. `AGENTS.md`, `docs/CONVENTIONS.md` e `docs/ci-pipeline.md`
passam a documentar dois comandos: o padrão, que exclui `navegador`, e o da camada.

`tests/test_ci_workflow.py` ganha asserção do job novo. A linha que exige
`count('needs: [ruff-format, ruff-check, mypy]') == 2` continua valendo, porque o job novo depende
de `pytest`, não dos gates de qualidade.

`playwright` sai de `devDependencies` do `package.json`. O pacote Python traz o próprio driver, e
manter os dois seria duas fontes de versão de navegador. O job `css-build` continua rodando
`npm ci` normalmente.

A camada Navegador é a única do projeto que depende de binário externo baixado em tempo de setup.
Quem clona o repo e roda o comando padrão não precisa dele; quem roda `-m navegador` precisa de
`playwright install chromium` uma vez. Isso é dito em `docs/ci-pipeline.md`.

A guarda estática de `x-trap` entra em `marcacao.py` independentemente desta camada, e é ela quem
pega a classe de bug que originou este ADR. A camada Navegador prova o efeito; a guarda de marcação
impede a reincidência barata. As duas se somam, nenhuma substitui a outra.

Sete das dez issues da Etapa 3 (#130, #131, #135, #136, #137 na maior parte, #138, e metade da #134)
**não** dependem desta camada e podem ser feitas com os instrumentos que já existem. O bloqueio real
era sobre #132, #133 e a metade da #134 que trata de trava de scroll.

## Trade-off

O pipeline fica mais lento e ganha uma dependência de navegador. Em troca, a única classe de defeito
que o projeto comprovadamente não detecta — comportamento em runtime que não deixa rastro no HTML —
passa a ter mecanismo.

O risco real não é técnico, é de manutenção: projeto piloto, equipe pequena, e suíte de navegador
que ninguém depura quando pisca vira passivo. É por isso que o escopo está fechado por critério de
admissão explícito, e não por bom senso. Uma camada de cinco casos que todo mundo entende vale mais
que uma de cinquenta que ninguém lê.

Decisão revisável. Critérios de revisão: se um caso novo entrar sem passar pelo critério de
admissão, o escopo furou. Se a instabilidade obrigar a rodar de novo com frequência, o problema é o
caso, não o gate. O gatilho de contagem que esta seção trazia foi substituído pela Emenda de
2026-09-04.

## Emenda — 2026-09-04 (varredura de contraste, issue #166)

Dois ajustes ao critério de admissão e ao gatilho de revisão. Não revogam o ADR: um acrescenta uma
dependência que a lista original não previa, o outro troca um gatilho que nunca disparou por um que
mede o custo real.

### Quarto critério de admissão: cascade resolvida e pipeline de cor

A issue #166 pediu uma varredura de contraste que resolve o fundo efetivo de cada nó de texto
subindo a cadeia de ancestrais, compõe alpha e converte `oklch()` para sRGB. O guarda estático de
`test_tokens_semanticos.py` não alcança o caso, e o próprio docstring dele registra o porquê: ele vê
par de cor no **mesmo elemento**, e o defeito que originou a regra tinha o fundo no `<div>` pai e a
cor no `<span>` filho.

Isso não cabia em nenhum dos três critérios originais. Não é geometria, não é `<dialog>`, não é XHR
— é o valor computado depois da cascade, mais a conversão de espaço de cor que o navegador faz e
nenhum parser de template faz. A lista ganha o quarto item em vez de o teste ser encaixado à força
num dos três, porque a lista fechada é o mecanismo que segura o escopo desta camada, e alargá-la por
interpretação a esvazia.

O limite continua valendo na direção oposta: se o conserto puder ser provado por um atributo no HTML
renderizado, ele não entra aqui.

### O gatilho de ~15 casos sai; o relógio entra

O texto original marcava revisão em "~15 casos". Quando a #166 chegou, a camada estava em **48 casos
em 9 arquivos** — 3,2× o gatilho — e nenhuma revisão tinha sido disparada. O número não falhou por
descuido de quem o escreveu: ele mede crescimento, e crescimento por casos legitimamente admitidos
não é o risco que o Trade-off descreve. O risco é a camada ficar lenta ou instável a ponto de
ninguém rodar.

O gatilho passa a ser o relógio, que é o custo que a ADR diz proteger desde o Contexto: a suíte
padrão roda em segundos e a lane roda em **~50s** com 59 casos. Se a lane passar de ~3min, o escopo
precisa de revisão — encolhendo casos, não afrouxando o gate.
