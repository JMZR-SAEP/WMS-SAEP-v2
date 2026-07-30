# Plano — Notificar criador e beneficiário quando a requisição fica pronta para retirada (#109)

## Escopo

`separar_para_retirada` (`apps/requisicoes/services/atendimento.py:73`) é a
transição que avisa o beneficiário de que o material está separado — e é a
única do fluxo de atendimento que muda de estado **sem** emitir notificação.
`registrar_atendimento`, no mesmo módulo, já registra o hook
(`atendimento.py:349-356`). O beneficiário descobre por fora do sistema que
pode retirar; achado R1 da auditoria do piloto, mesma origem do #108.

Diferença estrutural em relação ao #108: lá o destinatário era o **chefe do
setor beneficiário**, que não é campo da `Requisicao` e exigiu um selector novo
(`chefe_autorizador_do_setor`) e um helper próprio
(`_notificar_chefe_pos_commit`). Aqui o destinatário é o par
**criador/beneficiário**, que são FKs da própria requisição — exatamente o
roteamento de `criar_notificacoes_para`, e exatamente o que
`_notificar_pos_commit` (`atendimento.py:50`) já faz. Esta fatia não introduz
função nova em nenhuma camada: só o membro do enum, a chamada de
`transaction.on_commit` e testes.

**Muda:**

- `apps/notificacoes/models.py` — novo membro
  `SEPARACAO_RETIRADA = 'separacao_retirada', 'Separação para retirada'` em
  `TipoNotificacao`. Valor e rótulo são contrato: o valor fica persistido em
  `Notificacao.tipo`, e o rótulo é o texto exato que o teste 7 procura no HTML
  da lista, já que o template usa `get_tipo_display` sem tradução própria.
  Especificação em §1.
- `apps/requisicoes/services/atendimento.py` — `separar_para_retirada` registra
  `transaction.on_commit` para `_notificar_pos_commit` com o tipo novo, no
  mesmo formato de `registrar_atendimento`.
- `apps/notificacoes/tests/test_services.py` — 6 casos de hook, seção nova.
- `apps/notificacoes/tests/test_views.py` — 1 caso de renderização.
- `apps/requisicoes/tests/test_services.py` — reforço de 4 testes de TR-015 já
  existentes, que hoje param no `pytest.raises` e não asseram ausência de
  escrita. Ver Estratégia de testes §"Camada de service".
- `docs/estado-transicoes-requisicao.md` — TR-015 hoje diz "notifica quando
  aplicável"; passa a nomear os destinatários.

**Não muda:**

- `apps/requisicoes/services/atendimento.py::_notificar_pos_commit` — a
  assinatura `(criador_id, beneficiario_id, req_id, tipo)` já é genérica no
  `tipo`; o membro novo entra como argumento, não como caminho novo. Criar um
  `_notificar_separacao_pos_commit` seria duplicar o `try/except` por tipo onde
  hoje há um helper por módulo.
- `apps/notificacoes/services.py` — `criar_notificacoes_para` e
  `criar_notificacoes_para_destinatarios` já cobrem o roteamento e a
  deduplicação. Nada a acrescentar: o #108 já extraiu o primitivo.
- `apps/notificacoes/templates/notificacoes/lista.html` — o template renderiza
  `{{ notificacao.get_tipo_display }}` (linha 26) e monta o link para
  `requisicoes:detalhe` a partir de `requisicao_id` (linhas 27-36). Um novo
  membro de `TextChoices` aparece com rótulo PT-BR **sem edição de template**;
  o critério de aceite 3 é coberto por teste de view, não por mudança de
  arquivo. Editar aqui seria acrescentar um `if` por tipo onde há regra única.
- `apps/notificacoes/policies.py`, `selectors.py`, `context_processors.py` —
  `pode_ver_notificacao`, `notificacoes_com_numero_publico` e a contagem do
  badge operam sobre `destinatario_id`/`lida`/`requisicao_id`, agnósticos ao
  `tipo`. O membro novo entra na contagem sem regra própria.
- As pré-condições de TR-015/TR-015B — divergência crítica, físico
  insuficiente, itens autorizados > 0, estado de origem, policy. A notificação
  é efeito pós-commit, não pré-condição nova. O caminho bloqueado de TR-015B
  levanta antes do `on_commit` e, mesmo se levantasse depois, o
  `transaction.atomic` do service descartaria o callback (§2, decisão 3).
- Estoque, reservas e timeline — TR-015 mantém reserva e não baixa físico; o
  `TimelineRequisicao` de `SEPARACAO_RETIRADA` já existe e permanece igual.
- `registrar_devolucao` (TR-020) continua sem notificação. Não contradiz a
  afirmação de escopo acima: TR-020 é `ATENDIDA → ATENDIDA`
  (`atendimento.py:376`), não muda estado, e por isso fica fora da regra "toda
  transição de estado avisa quem é afetado". Se um dia devolução passar a
  notificar, é fatia própria, com tipo próprio — não carona nesta.
- `docs/matriz-invariantes.md` — ver Invariantes: esta fatia não acrescenta
  linha.

## Arquivos alterados

| Arquivo | Ação |
|---|---|
| `apps/notificacoes/models.py` | Novo membro `SEPARACAO_RETIRADA` em `TipoNotificacao` |
| `apps/requisicoes/services/atendimento.py` | `transaction.on_commit` no fim de `separar_para_retirada` |
| `apps/notificacoes/tests/test_services.py` | 6 casos de hook (seção nova) |
| `apps/notificacoes/tests/test_views.py` | 1 caso de renderização de rótulo e link |
| `apps/requisicoes/tests/test_services.py` | Reforço de 4 testes de TR-015: ausência de escrita nos caminhos negado/inválido |
| `docs/estado-transicoes-requisicao.md` | TR-015 nomeia os destinatários da notificação |

Migration: a mudança de `choices` gera `AlterField` em `Notificacao.tipo`. Sem
efeito no schema do Postgres (`CharField` sem constraint de choices), mas o
autodetector reclama enquanto não existir. Migrations locais são artefatos
efêmeros (AGENTS.md): rodar `make setup` antes de testar. Nada a versionar.

## Implementação

### 1. Novo tipo de notificação

`apps/notificacoes/models.py`:

```python
class TipoNotificacao(models.TextChoices):
    AUTORIZACAO = 'autorizacao', 'Autorização'
    RECUSA = 'recusa', 'Recusa'
    ATENDIMENTO = 'atendimento', 'Atendimento'
    DIVERGENCIA_ESTOQUE = 'divergencia_estoque', 'Divergência de estoque'
    ENVIO_AUTORIZACAO = 'envio_autorizacao', 'Envio para autorização'
    SEPARACAO_RETIRADA = 'separacao_retirada', 'Separação para retirada'
```

Nome, valor e rótulo copiados de `EventoTimeline.SEPARACAO_RETIRADA`
(`apps/requisicoes/models.py:202`), que é o termo do glossário para TR-015 —
mesma regra que o #108 aplicou a `ENVIO_AUTORIZACAO`. Duas razões para não
inventar rótulo do tipo "Pronta para retirada":

1. o mesmo evento aparece com a mesma palavra na timeline da requisição e na
   lista de notificações;
2. "Pronta para retirada" é nome de **estado** (`EstadoRequisicao`), não de
   evento. Usá-lo como rótulo de notificação criaria dois termos concorrentes
   para coisas diferentes na mesma tela.

`max_length=30` do campo comporta `separacao_retirada` (18 caracteres). O
membro vai no fim, para não sugerir reordenação de valores já persistidos.

### 2. Hook em `separar_para_retirada`

`apps/requisicoes/services/atendimento.py`, no fim da função, depois do
`TimelineRequisicao.objects.create` e antes do `return`:

```python
    _criador_id = requisicao.criador_id
    _beneficiario_id = requisicao.beneficiario_id
    _req_id = requisicao.pk
    transaction.on_commit(
        lambda: _notificar_pos_commit(
            _criador_id,
            _beneficiario_id,
            _req_id,
            TipoNotificacao.SEPARACAO_RETIRADA,
        )
    )

    return requisicao
```

Mesmo bloco de `registrar_atendimento` (`atendimento.py:349-356`), com outro
tipo — a única diferença é a quebra de linha dos argumentos, que o `ruff
format` decide. `TipoNotificacao` e `_notificar_pos_commit` já estão no módulo
(`:24` e `:50`); não há import novo.

Quatro decisões que o código embute:

1. **Ids em locais, não a instância na closure.** Os três `_`-prefixados
   existem para que a lambda capture inteiros, não o objeto `Requisicao`. A
   razão **não** é evitar leitura obsoleta: `criador_id` e `beneficiario_id`
   lidos aqui já são snapshot do momento da transição, e é justamente o
   snapshot que se quer — o destinatário certo é quem era criador/beneficiário
   quando a separação aconteceu. A razão é que a lambda sobrevive ao fim da
   função e roda depois do commit: prender nela uma instância de model
   carregada sob `select_for_update` mantém viva uma linha inteira e abre o
   caminho para alguém, numa fatia futura, ler `requisicao.estado` de dentro do
   callback — valor lido dentro da transação, usado fora dela. Capturar `int`
   fecha esse caminho por construção. É o que o irmão em `registrar_atendimento`
   já faz.
2. **Depois da timeline, não antes do `save`.** `on_commit` só dispara em
   commit bem-sucedido, então a posição dentro do bloco não muda *se* o
   callback roda. Registrar no fim mantém a ordem de leitura "transição →
   timeline → efeito colateral", que é a dos três hooks existentes, e evita a
   pergunta "isso roda mesmo se a validação abaixo levantar?".
3. **O caminho bloqueado de TR-015B não notifica, por construção.** As guardas
   de divergência e físico insuficiente levantam `DadosInvalidos` antes desta
   linha. Mesmo que uma guarda futura passasse a levantar *depois* do registro,
   o `@transaction.atomic` do service faria rollback e o callback seria
   descartado — comportamento já travado por
   `test_on_commit_nao_dispara_em_rollback`. O teste 3 assere o contrato no
   nível da transição (nenhuma notificação, requisição segue `AUTORIZADA`), não
   a posição da linha.
4. **Sem dedup entre chamadas, porque não existe segunda chamada.** Diferente
   de TR-005 (reenvio após retorno para rascunho, que o #108 decidiu notificar
   de novo), TR-015 não tem caminho de repetição: separar uma requisição já
   `PRONTA_PARA_RETIRADA` levanta `EstadoInvalido` no guard de estado de origem,
   coberto por
   `test_separar_para_retirada_idempotencia_bloqueia_segunda_execucao`. O teste
   4 desta fatia trava o mesmo ponto do lado da notificação: a tentativa
   repetida não gera par extra.

O **ator** — auxiliar ou chefe de Almoxarifado — não é destinatário.
`criar_notificacoes_para` roteia só criador/beneficiário, e o Almoxarifado
acompanha o próprio trabalho pela `fila_atendimento`, não pela caixa de
notificações. O teste 1 assere isso pelo conjunto exato de destinatários, e não
só pela contagem: contagem 2 sozinha passaria com o par errado.

### 3. Documentação

`docs/estado-transicoes-requisicao.md`, linha TR-015 (`:68`): a coluna de
efeitos hoje termina em "notifica quando aplicável", redação genérica herdada
de quando nenhuma transição de atendimento notificava. Passa a nomear os
destinatários — "notifica criador e beneficiário (uma notificação quando são a
mesma pessoa)" — alinhando com o grau de especificidade que TR-005 ganhou no
#108. TR-015B não muda: o caminho bloqueado continua sem efeito colateral, e a
linha já diz que não altera timeline nem estado.

## Estratégia de testes

Camada de hook — `apps/notificacoes/tests/test_services.py`, seção nova
`Hook de separação para retirada`. Todos os seis casos usam
`@pytest.mark.django_db(transaction=True)`, como os hooks já testados no
arquivo, para que o `on_commit` dispare de verdade — inclusive os casos 3 e 6,
em que o ponto é justamente que **nada** dispara: sob
`@pytest.mark.django_db` sem `transaction=True`, nenhum `on_commit` roda, e a
ausência de notificação passaria a provar apenas isso — não que a transição
bloqueada deixou de notificar.

O cenário base dos casos 1, 4, 5 e 6 é o de
`test_registrar_atendimento_gera_notificacoes` (`:167-215`), truncado uma
transição antes: `criar_requisicao` (`chefe_obras` para `outro_solicitante`) →
`enviar_para_autorizacao` → `autorizar_requisicao` → `separar_para_retirada`
(`chefe_almoxarifado`). Fixtures já existem em
`apps/notificacoes/tests/conftest.py` — `chefe_obras`, `chefe_almoxarifado`,
`solicitante`, `outro_solicitante`, `material_disponivel`. Nenhuma fixture
nova; um helper local `_separar` para não repetir as quatro chamadas.

| # | Caso | Esperado |
|---|---|---|
| 1 | criador (`chefe_obras`) ≠ beneficiário (`outro_solicitante`); separação por `chefe_almoxarifado` | 2 notificações `SEPARACAO_RETIRADA`; conjunto de `destinatario_id` == `{chefe_obras.pk, outro_solicitante.pk}`; `chefe_almoxarifado.pk` **não** está no conjunto — critério 1 |
| 2 | criador == beneficiário (`solicitante` para si) | 1 notificação `SEPARACAO_RETIRADA`, para `solicitante` — critério 1, metade da dedup |
| 3 | requisição autorizada, saldo físico rebaixado abaixo do reservado, `separar_para_retirada` levanta `DadosInvalidos(code='separacao_bloqueada')` | nenhuma notificação `SEPARACAO_RETIRADA`; requisição segue `AUTORIZADA` — TR-015B |
| 4 | separação seguida de segunda chamada, que levanta `EstadoInvalido` | continuam 2 notificações, não 4 — idempotência |
| 5 | `criar_notificacoes_para` monkeypatchado em `atendimento` para levantar | requisição em `PRONTA_PARA_RETIRADA`; `caplog` em `ERROR` contém `Falha ao criar notificações pós-commit`; nenhuma notificação; sem propagação — critério 2 |
| 6 | `chefe_obras` (chefe do setor beneficiário, sem papel de Almoxarifado) tenta separar; levanta `PermissaoNegada` | nenhuma notificação `SEPARACAO_RETIRADA`; requisição segue `AUTORIZADA` |

O caso 1 assere o conjunto exato, não só a contagem: sem a exclusão explícita
do ator, um hook que roteasse para `{beneficiário, almoxarife}` passaria com
contagem 2.

O caso 3 monta a divergência do jeito mais próximo do real: autoriza primeiro
(o que reserva o saldo) e só então rebaixa `saldo_fisico` para 0 por `update`
no queryset, simulando a correção de inventário superveniente que EST-07
descreve. Rebaixar antes da autorização não serve — a autorização é que cria o
`saldo_reservado` contra o qual a divergência é medida.

O caso 5 usa monkeypatch porque a falha que descreve (banco fora, bug no
service de notificação) não é alcançável por dado de domínio. O alvo é
`apps.requisicoes.services.atendimento.criar_notificacoes_para` — o símbolo já
ligado no módulo consumidor, não `apps.notificacoes.services`, que o
`from ... import` no topo de `atendimento.py` deixa de consultar em runtime.
Mesmo alvo e mesma razão do caso 7 do #108, um módulo adiante. A asserção de
estado é o que dá sentido à fail-open: sem ela, o teste passaria com um hook
que engolisse a exceção *e* a transição.

Camada de view — `apps/notificacoes/tests/test_views.py`:

| # | Caso | Esperado |
|---|---|---|
| 7 | `outro_solicitante` autenticado faz GET em `notificacoes:lista` com uma `Notificacao` `SEPARACAO_RETIRADA` apontando para requisição numerada em `PRONTA_PARA_RETIRADA` | 200; `Separação para retirada` no HTML; `href` do `requisicoes:detalhe` daquele pk; número público no HTML — critério 3 |

O caso 7 substitui a edição de template: falha se o membro não existir, se o
rótulo mudar, ou se alguém trocar o `get_tipo_display` genérico por um `if` por
tipo que esqueça o membro novo. Espelha
`test_lista_exibe_rotulo_e_link_de_envio_autorizacao` (`test_views.py:184`),
com estado e tipo desta fatia.

Camada de service (TR-015) — `apps/requisicoes/tests/test_services.py`, seção
`separar_para_retirada` já existente. A revisão do plano apontou que a matriz
acima não fecha o contrato de service exigido pelas instruções de caminho do
`.coderabbit.yaml`: caminho feliz com timeline e efeitos, estado inválido sem
escrita, permissão negada sem escrita. Verificado contra o código vivo, o
diagnóstico se confirma pela metade — e a metade que falta é justamente a que
esta fatia torna arriscada.

**Já coberto, referência nominal em vez de faixa de linhas:**
`test_separar_para_retirada_aplica_estado_e_registra_timeline` (`:1426-1449`) é
o caminho feliz completo — assere `estado == PRONTA_PARA_RETIRADA`, busca o
`TimelineRequisicao` de `SEPARACAO_RETIRADA` com `.get()` (que falha se houver
zero ou mais de um) e verifica `ator_id`, `estado_resultante` e
`metadata == {}`, além de `saldo_fisico` e `saldo_reservado` inalterados. Nada
a acrescentar ali; o caso 1 desta fatia cobre o efeito novo (notificação) do
mesmo caminho.

**Falta cobrir, e passa a ser desta fatia:** quatro testes param no
`pytest.raises` e não asseram ausência de escrita —
`test_separar_para_retirada_permissao_negada_chefe_setor` (`:1473`),
`test_separar_para_retirada_permissao_negada_solicitante` (`:1484`),
`test_separar_para_retirada_estado_invalido` (`:1495`) e
`test_separar_para_retirada_idempotencia_bloqueia_segunda_execucao` (`:1542`).
Cada um ganha, depois do `raises`, as asserções de que o estado não mudou e de
que nenhum `TimelineRequisicao` de `SEPARACAO_RETIRADA` foi criado — no caso
da idempotência, que continua havendo exatamente um, o da primeira separação.

Reforçar testes pré-existentes normalmente seria escopo de outra fatia. Aqui
não é: antes do #109 esses caminhos não tinham efeito colateral externo a
vazar, e a asserção que faltava era só rigor.

**Correção sobre o alcance destes testes, apurada por mutação durante a
implementação.** A primeira redação deste plano afirmava que eles pegariam uma
regressão que movesse o `on_commit` para antes das guardas. Testado: não
pegam. Mover o hook para logo depois do `select_for_update`, antes de
`exigir_pode_separar_para_retirada`, mantém os casos 3 e 6 verdes — o
`@transaction.atomic` do service reverte a transação quando a guarda levanta, e
todo callback registrado é descartado junto. É a decisão 3 de §2 funcionando;
a consequência é que o resultado é garantido *estruturalmente*, não por estes
testes. Remover o `@transaction.atomic` para forçar a falha também não serve
como prova: o `select_for_update` quebra antes, com
`TransactionManagementError`.

O que estes testes de fato travam, e por que ficam mesmo assim:

1. **O contrato de saída, independente do mecanismo.** Eles dizem "separação
   que falha não anuncia nada" sem depender de *como* isso é garantido hoje. A
   mudança realista que eles pegam é a notificação deixar de ser efeito
   pós-commit: trocar `transaction.on_commit` por enfileiramento imediato
   (`.delay()` de task, webhook, signal em `post_save`) dispara mesmo com
   rollback — e aí os casos 3 e 6 acusam.
2. **O contrato de service exigido pelas instruções de caminho** do
   `.coderabbit.yaml` — caminho feliz com timeline e efeitos, estado inválido
   sem escrita, permissão negada sem escrita —, que era o achado original da
   revisão do plano.

O que **não** se deve escrever sobre eles: que travam a posição do hook dentro
da função. Não travam, e a docstring de cada um diz isso explicitamente para
que a próxima pessoa não confie em garantia que não existe.

Não coberto, e por quê: badge de contagem
(`apps/notificacoes/context_processors.py` conta por `lida=False`, sem olhar
`tipo`); ordenação da lista (`ordering = ['-criado_em']` no `Meta`, não
tocada); `marcar_lida`/`marcar_todas_lidas` (operam por `destinatario_id`,
agnósticos ao tipo); permissão de leitura da notificação
(`pode_ver_notificacao` não olha `tipo`, e já tem cobertura própria); e os
demais testes de TR-015/TR-015B, por dois motivos distintos. Os dois de
TR-015B (`:1563`, `:1593`) **já** asseram ausência de escrita — estado,
`saldo_fisico`, `saldo_reservado` e contagem de `eventos` antes/depois — e
portanto não entram no reforço; o que lhes falta é só a metade de notificação,
que o caso 3 acrescenta do lado de `notificacoes`. Os de aceitação por papel
(`:1453`, `:1464`), ator e requisição inexistentes (`:1522`, `:1532`) e sem
itens autorizados (`:1504`) ficam de fora porque cobrem variações de entrada
do mesmo par de caminhos já reforçado, sem contrato próprio que esta fatia
mude.

## Invariantes

`docs/matriz-invariantes.md` **não** ganha linha nesta fatia, e isso é decisão,
não omissão. O `NOT-01` que o #108 acrescentou existe porque lá o destinatário
(`chefe ativo do setor beneficiário`) era resolvido por um selector que
*espelha* a condição de `fila_autorizacao` sem compartilhar código — o par de
filtros podia divergir, e a linha da matriz é o que trava o espelho. Aqui o
destinatário é lido de dois campos FK da própria requisição: não há espelho,
não há segunda fonte de verdade, não há divergência possível a proibir. Uma
linha `NOT-02` dizendo "notifica criador e beneficiário" só repetiria a coluna
de efeitos de TR-015, que é onde a informação pertence.

A nota de §4 (Notas por tema, `docs/matriz-invariantes.md:78`) já cobre o que
esta fatia precisa: notificação é efeito colateral pós-commit, nunca
pré-condição de transição; falha ao notificar é registrada em log e não desfaz
a transição já commitada. O caso 5 é o teste dessa nota para TR-015.

As linhas tocadas de lado:

| Regra | Relação com esta mudança |
|---|---|
| EST-02 / EST-06 (reserva e lock) | Preservados: o hook não lê nem escreve saldo, e roda **fora** da transação via `on_commit`, sem estender o tempo de lock de `select_for_update` sobre `Requisicao` e `SaldoEstoque`. |
| EST-07 / EST-08 (divergência bloqueia separação) | Preservados e travados pelo caso 3: o caminho bloqueado por TR-015B não gera notificação, porque não há transição a anunciar. Notificar aqui seria pior que não notificar — avisaria o beneficiário para buscar material que o Almoxarifado não separou. |
| REQ-08 (timeline registra eventos principais) | A timeline de `SEPARACAO_RETIRADA` continua igual. Notificação não é evento de timeline e não duplica registro. |
| REQ-03 / REQ-04 (número público) | Intocados: o hook roda depois do `save`, lê só `pk`, `criador_id` e `beneficiario_id`. O número público aparece na lista por `notificacoes_com_numero_publico`, que resolve pelo `requisicao_id` e já é coberta. |
| USR-01 (usuário inativo não acessa nem opera) | Sem filtro de atividade na resolução, e de propósito: criador e beneficiário são FKs, não resultado de query por papel. A garantia continua na leitura — `pode_ver_notificacao` exige `papel.ativo` (`apps/notificacoes/policies.py:13`) —, exatamente como nos outros três tipos roteados por `criar_notificacoes_para`. |
| PER-06 (`setor_beneficiario` é snapshot autoritativo) | Não se aplica: o roteamento desta notificação é por pessoa, não por setor. |

**Limite conhecido — notificação sem retratação.** Se a requisição
`PRONTA_PARA_RETIRADA` for cancelada em seguida (TR-013), a notificação de
separação continua na lista do beneficiário. Não é regressão desta fatia: vale
igual para `AUTORIZACAO` e para `ENVIO_AUTORIZACAO`. `Notificacao` é registro
histórico do que aconteceu, não estado corrente da requisição — e o link para
o detalhe mostra o estado atual. Retratar exigiria decidir semântica de
invalidação para os seis tipos, o que é escopo próprio.

## Riscos

| Risco | Avaliação |
|---|---|
| Duas notificações por requisição no fluxo normal (separação + atendimento) | É o objetivo do issue: são dois avisos distintos ("pode retirar" e "retirada registrada"). Sem agrupamento nesta fatia; se o piloto reclamar, a resposta é agrupar na leitura (selector), não deixar de notificar. |
| Notificação de separação para requisição depois cancelada | Documentado acima como limite conhecido, comum aos tipos já existentes. Não bloqueia. |
| Migration de `choices` | `AlterField` sem efeito de schema. Migrations locais são efêmeras (AGENTS.md): recriar do zero com `make setup` antes de testar. |
| Contrato OpenAPI | Projeto é server-rendered sem camada REST (AGENTS.md). Não se aplica. |
| Concorrência / lock | O hook não abre transação nem toca linha travada, e roda após o commit. Rollback não notifica — coberto por `test_on_commit_nao_dispara_em_rollback`. |
| Colisão com o #108 | O issue marca dependência soft: mesmo enum e mesmo template. O #108 já está em `main` (`84530e6`), o membro `ENVIO_AUTORIZACAO` já existe e o template não é tocado por nenhuma das duas fatias. Conflito de merge não se materializa. |
