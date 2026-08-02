# Plano — Issue #111: avisar requisições autorizadas quando a saída excepcional cria divergência

## Decisão (HITL)

A issue exigia decisão de produto antes de implementar: **bloquear** a baixa que
criaria divergência crítica (EST-07) ou **permitir e avisar**.

**Decisão: permitir e avisar.**

Justificativa apoiada na documentação viva:

1. **ADR-0013** define a saída excepcional com "baixa direta de `saldo_fisico`;
   sem alteração de `saldo_reservado`". Validar `saldo_disponivel` na baixa
   inverteria esse contrato: o reservado passaria a limitar a baixa
   administrativa, tornando a reserva de uma requisição um veto sobre o registro
   da realidade física.
2. **TR-013** (`docs/estado-transicoes-requisicao.md`) já descreve o cancelamento
   como "caminho de resolução intencional e único escape documentado quando
   divergência crítica superveniente (EST-07) inviabiliza TR-015". Ou seja: a
   divergência superveniente já é um estado previsto pelo domínio, com caminho
   de resolução definido. Falta apenas o aviso.
3. **EST-07 / EST-09** (`docs/matriz-invariantes.md`) modelam a divergência como
   estado que nasce e se resolve, não como erro a barrar.
4. A realidade física manda. Se o material foi perdido, avariado ou vencido,
   recusar a baixa deixa o sistema afirmando um saldo que não existe — e sem
   saída para o operador, já que a reserva só é liberada por TR-013, que depende
   de alguém saber que precisa cancelar.

Bloquear foi descartado porque exigiria emendar ADR-0013 e criaria um impasse
operacional. O híbrido (confirmação explícita na UI) foi descartado por custo
de superfície sem ganho de segurança: o aviso já entrega a informação a quem
precisa agir, e a confirmação recairia sobre o chefe de Almoxarifado, que não é
quem decide sobre as requisições afetadas.

**Registro da decisão**: emenda em `docs/matriz-invariantes.md` (EST-07) e nova
seção em `docs/processos-saida-excepcional.md`. Não abre ADR novo — a decisão
estende um padrão já existente (o hook de divergência da importação SCPI) em
vez de introduzir arquitetura nova.

## Escopo

### O que muda

- `registrar_saida_excepcional` ganha o parâmetro **keyword-only** opcional
  `_pos_saida_hook=None`, chamado dentro da mesma transação, depois das baixas e
  da numeração. A assinatura inteira já é keyword-only (`def registrar_saida_excepcional(*, ator_id, estoque_id, motivo, observacao, itens, _pos_saida_hook=None)`),
  conforme ADR-0011 e `docs/CONVENTIONS.md` — o novo parâmetro entra depois de
  `itens`, dentro do mesmo bloco `*`.
- Novo hook `registrar_timeline_divergencia_saida_excepcional` em
  `apps/requisicoes/services/ciclo_vida.py`, irmão do hook já existente da
  importação SCPI. Retorna `list[int]` com os ids das requisições avisadas; o
  hook SCPI passa a retornar o mesmo. O service **ignora** o retorno, mantendo
  seu contrato de retornar `SaidaExcepcional`.
- Núcleo compartilhado entre os dois hooks, extraído do corpo atual de
  `registrar_timeline_divergencia_importacao`.
- `nova_saida_excepcional_view` injeta o hook, espelhando o que
  `confirmar_importacao_scpi_view` já faz, e captura o retorno para emitir um
  `messages.warning` ao operador quando a baixa criou divergência.
- Renderização do evento `atualizacao_estoque_relevante` na timeline da
  requisição, exibindo origem e materiais afetados.
- Emenda de documentação (matriz de invariantes + processo de saída
  excepcional).

### O que NÃO muda

- **A validação da baixa.** `registrar_saida_excepcional` continua validando
  apenas `saldo_fisico < quantidade`. Nenhuma checagem de `saldo_disponivel`.
- **TR-015B.** A separação continua bloqueada por divergência crítica, com a
  mesma mensagem orientando cancelamento via TR-013. Nenhuma linha de
  `separar_para_retirada` é tocada.
- **O estado das requisições afetadas.** Elas permanecem `autorizada`. A
  divergência avisa, não transiciona — coerente com TR-013 ser o escape.
- **A reserva.** `saldo_reservado` não é alterado pela saída excepcional
  (ADR-0013).
- **Models, choices e migrations.** `EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE`
  e `TipoNotificacao.DIVERGENCIA_ESTOQUE` já existem. Zero migrations.
- **O model `Notificacao`.** Continua sem corpo de mensagem — os campos são
  `destinatario`, `tipo`, `requisicao_id`, `lida`, `criado_em`
  (`apps/notificacoes/models.py:14`). A lista renderiza `get_tipo_display` e
  linka para o detalhe da requisição
  (`apps/notificacoes/templates/notificacoes/lista.html:26-35`). Ver "Contrato
  visível do aviso" para por que o texto rico mora na timeline, não aqui.
- **`estornar_saida_excepcional`.** O estorno devolve físico e pode resolver a
  divergência (EST-09), mas não avisará que ela sumiu. Ver "Fora de escopo".

## Arquivos tocados

| Arquivo | Mudança |
|---|---|
| `apps/estoque/services.py` | `registrar_saida_excepcional`: novo kwarg `_pos_saida_hook`, chamado ao final, dentro da transação |
| `apps/requisicoes/services/ciclo_vida.py` | Extrai núcleo compartilhado; adiciona `registrar_timeline_divergencia_saida_excepcional` |
| `apps/estoque/views.py` | `nova_saida_excepcional_view` injeta o hook (import local) e emite `messages.warning` quando houve divergência |
| `apps/requisicoes/templates/requisicoes/partials/_timeline.html` | Renderiza origem e materiais afetados no evento `atualizacao_estoque_relevante` |
| `apps/estoque/tests/test_services.py` | Testes do comportamento novo no service |
| `apps/estoque/tests/test_views.py` | Testes do wiring do hook e do aviso ao operador |
| `apps/requisicoes/tests/test_views.py` | Teste de renderização do evento na timeline |
| `apps/notificacoes/tests/test_services.py` | Testes das notificações geradas pela nova origem |
| `docs/matriz-invariantes.md` | Emenda em EST-07 |
| `docs/processos-saida-excepcional.md` | Nova seção sobre divergência criada pela baixa |

## Decisões de implementação

### Por que hook injetado na view, e não import direto no service

`apps/estoque/services.py` não importa `apps.requisicoes` — verificado: nenhum
import desse tipo existe fora dos testes do app. Essa fronteira é o que impede
`estoque` de depender do ciclo de vida da requisição.

O padrão já resolvido no projeto é a inversão por parâmetro:
`confirmar_importacao_scpi(..., _pos_importacao_hook=...)`
(`apps/estoque/services.py:630`), com a composição feita na view
(`apps/requisicoes/views.py:1119`). O service declara um ponto de extensão; a
camada de view escolhe o que plugar.

A saída excepcional espelha isso. A única diferença é que a view dona do fluxo
mora em `apps/estoque/views.py`, então é ela quem passa a importar
`apps.requisicoes.services.ciclo_vida`. O import é local à função, como já é o
caso em `apps/requisicoes/views.py:1082`, evitando ciclo no carregamento dos
módulos. O invariante que importa — `estoque/services.py` livre de
`requisicoes` — fica preservado.

### Núcleo compartilhado entre os dois hooks

O corpo atual de `registrar_timeline_divergencia_importacao` faz cinco coisas
que valem para qualquer origem de divergência: consultar saldos críticos com
lock, achar as requisições `autorizada` que tocam esses materiais, agregar um
evento por requisição, `bulk_create` da timeline e agendar as notificações em
`transaction.on_commit`.

Só duas coisas variam por origem: de onde vêm código e nome do material, e o que
entra no `metadata` do evento. Então o núcleo recebe ambos prontos e devolve
quem foi avisado:

```python
def _registrar_divergencia_para_autorizadas(
    *,
    material_ids: list[int],
    estoque,
    ator,
    material_info: dict[int, dict],   # {material_id: {'codigo': ..., 'nome': ...}}
    metadata_origem: dict,            # ex.: {'saida_excepcional_id': 7, 'numero_publico': 'SXP-...'}
) -> list[int]:                       # ids das requisições avisadas; [] quando não há divergência
```

Os dois hooks propagam esse `list[int]` como retorno próprio. Todos os caminhos
de saída antecipada do núcleo (sem materiais, sem saldo crítico, sem requisição
autorizada) devolvem `[]`, nunca `None` — o chamador nunca precisa de guarda de
nulo.

O `metadata` final de cada evento fica `{**metadata_origem, 'materiais': [...]}`,
o que preserva byte a byte o formato atual do hook SCPI
(`{'importacao_id': ..., 'materiais': [...]}`) — os testes existentes em
`apps/estoque/tests/test_services.py:471` continuam válidos sem edição.

**Sobre o contrato do hook SCPI.** `registrar_timeline_divergencia_importacao`
mantém nome e assinatura, mas o retorno deixa de ser `None` e passa a ser
`list[int]`. É mudança aditiva e retrocompatível — o único chamador de produção
(`apps/requisicoes/views.py:1119`) descarta o retorno, e
`confirmar_importacao_scpi` também o ignora — mas é **observável**, então não é
refactor puramente interno. Ganha teste próprio: o hook SCPI retorna os ids das
requisições avisadas no caminho com divergência e `[]` nos caminhos sem, e a
importação continua devolvendo a mesma `ImportacaoSCPI` de antes.

### Onde o hook é chamado dentro de `registrar_saida_excepcional`

Depois de todas as baixas de `saldo_fisico`, das movimentações de ledger e da
emissão do `numero_publico`; antes do `return`. Ainda dentro do
`@transaction.atomic` da função.

Três razões para essa posição:

1. Os saldos já estão gravados, então a consulta de divergência crítica
   (`saldo_fisico__lt=F('saldo_reservado')`) enxerga o estado pós-baixa.
2. O `numero_publico` já existe, então o `metadata` do evento pode citar o
   documento pelo número que o operador vê na tela — não só pelo id.
3. Continua tudo na mesma transação, o que mantém SAE-04: se o **hook** falhar,
   a saída inteira reverte, e não existe estado em que a baixa persiste sem o
   evento de timeline. Falha na entrega da notificação é outra coisa — acontece
   depois do commit e não reverte nada. Ver "Duas classes de falha".

A consulta que o hook faz — saldos críticos e requisições `autorizada` — serve
**apenas para selecionar quem será notificado**. Ela nunca é pré-condição da
baixa.
Saldo sem reserva, saldo sem divergência ou material sem nenhuma requisição
autorizada resultam em zero eventos e zero notificações, com a
`SaidaExcepcional`, os `ItemSaidaExcepcional`, as `MovimentacaoEstoque` e o
`saldo_fisico` gravados normalmente. Isso preserva SAE-01 e a definição de
`CONTEXT.md` da saída excepcional como fluxo independente de Requisição, reserva
e autorização. Há teste dedicado a esse cenário.

Materiais candidatos = apenas os da própria saída (`quantidade_por_material`).
São os únicos cujo físico mudou.

### Lock e ordenação

`registrar_saida_excepcional` já trava os `SaldoEstoque` envolvidos com
`select_for_update()` ordenado por `material_id`, antes de qualquer escrita. O
núcleo compartilhado re-seleciona um **subconjunto** desses mesmos saldos, na
mesma transação. Locks já detidos não são readquiridos, então não há nova ordem
de aquisição e nenhum risco de deadlock introduzido (EST-06).

### Notificações pós-commit

Reusa o `transaction.on_commit` do núcleo, com o mesmo `try/except` +
`logger.exception` por requisição, conforme `docs/CONVENTIONS.md` exige para
efeitos pós-transação.

### Duas classes de falha, dois comportamentos

A distinção importa e o plano a fixa explicitamente:

| Momento da falha | O que acontece | Por quê |
|---|---|---|
| Exceção **dentro do hook** (consulta de saldos críticos, `bulk_create` da timeline, agendamento do `on_commit`) — tudo antes do commit | **Rollback total.** Nenhuma `SaidaExcepcional`, nenhum `ItemSaidaExcepcional`, nenhuma `MovimentacaoEstoque`, `saldo_fisico` intacto, nenhuma `TimelineRequisicao`. | O hook roda dentro do `atomic` do service. SAE-04 (all-or-nothing) cobre a fatia inteira, incluindo o aviso. |
| Exceção **dentro do callback de `transaction.on_commit`** (criação das `Notificacao`) — depois do commit | **Sem rollback.** `logger.exception` por requisição e segue. A saída, o ledger e a timeline permanecem gravados. | Depois do commit não há o que reverter. A timeline é o registro durável do aviso; a notificação é entrega best-effort. |

Não há retry automático. É a política vigente do projeto para notificações
pós-commit (mesma do hook SCPI e do hook de separação para retirada), não uma
decisão nova desta issue. Introduzir fila ou retry é mudança transversal a todos
os tipos de notificação — fora de escopo, ver "Fora de escopo".

Cada uma das duas classes ganha teste próprio (ver "Estratégia de testes").

### Contrato visível do aviso

`get_evento_display` e `get_tipo_display` entregam só rótulos genéricos
("Atualização de estoque relevante", "Divergência de estoque"). Sozinhos, não
dizem ao requisitante **o que** aconteceu nem **o que fazer**. O plano fecha essa
lacuna em duas superfícies distintas, cada uma com o meio que ela suporta.

**Timeline da requisição — texto rico, em PT-BR.** É onde o `metadata` já existe
e onde o usuário chega ao clicar na notificação
(`apps/notificacoes/templates/notificacoes/lista.html:26-35` linka para
`requisicoes:detalhe`). `_timeline.html` ganha um bloco condicional para o evento
`atualizacao_estoque_relevante`, no mesmo lugar onde hoje renderiza
`evento.justificativa`, exibindo:

- a origem: `Saída excepcional SXP-AAAA-NNNNNN` quando `metadata.numero_publico`
  existe; `Importação SCPI` no caminho já existente;
- os materiais afetados (`código — nome`), a partir de `metadata.materiais`;
- a orientação: o saldo físico ficou abaixo do reservado, a separação está
  bloqueada, e a resolução é cancelar a requisição (TR-013) ou repor o estoque.

Isso satisfaz o critério de aceite "template" da issue com um bloco de template,
sem model novo e sem migration. Beneficia as duas origens de EST-07.

**Flash message ao operador — nível `warning`.** Quem registra a baixa é o chefe
de Almoxarifado, que hoje só recebe `messages.success` com o número do documento.
Quando o hook retorna requisições avisadas, a view emite também um
`messages.warning` informando que a baixa criou divergência crítica e quantas
requisições autorizadas foram afetadas. O `role="alert"` vem de graça: o partial
de mensagens já renderiza `warning` dentro de `<div role="alert">`
(`apps/core/templates/core/partials/_messages.html:5`). Essa é a superfície onde
o contrato de mensagens do projeto (PRG + HX-Redirect, níveis
error/warning/success/info) se aplica — e a view já usa `htmx_redirect`, então a
mensagem sobrevive ao redirect.

**Fora dessas duas: o model `Notificacao`.** Persistir a mensagem exigiria campo
novo + migration, e o campo passaria a valer para os seis tipos de notificação e
todos os seus testes. A issue #111 pede a notificação `divergencia_estoque` —
o tipo que já existe, do jeito que o caminho SCPI já usa. Enriquecer o model é
mudança transversal com issue própria. Também não cabe `role="alert"` na lista
de notificações: `alert` é live region assertiva para conteúdo dinâmico, e a
lista é conteúdo estático paginado — marcá-la assim seria regressão de
acessibilidade, não melhoria.

## Estratégia de testes

Todos em `apps/estoque/tests/test_services.py`, salvo indicação. Nova classe
`TestSaidaExcepcionalDivergenciaTimeline`.

### Caminho feliz

| Cenário | Asserção |
|---|---|
| Saída rebaixa físico abaixo do reservado, existe requisição `autorizada` com o material | Exatamente 1 `TimelineRequisicao` com evento `ATUALIZACAO_ESTOQUE_RELEVANTE`; `metadata['saida_excepcional_id'] == saida.pk`; `metadata['numero_publico'] == saida.numero_publico`; `metadata['materiais']` contém código e nome do material |
| Mesma saída, dois materiais críticos na mesma requisição | 1 evento agregado, `len(metadata['materiais']) == 2` — trava o "um evento agregado por requisição" do critério de aceite |
| **Duas requisições autorizadas distintas compartilhando o mesmo material crítico** | Exatamente 1 evento **por requisição** (2 no total), cada um com o `saida_excepcional_id` e o `numero_publico` da mesma saída e com o material em `metadata['materiais']`; notificações emitidas para os usuários notificados de cada requisição (criador e beneficiário). Trava a ausência de agregação cruzada e de omissão: a agregação é por requisição, nunca por material nem global |
| Notificações | 1 `Notificacao` de tipo `DIVERGENCIA_ESTOQUE` para o criador e 1 para o beneficiário |
| Criador == beneficiário | 1 notificação só (dedup já garantida por `criar_notificacoes_para`) |

### Ausência de aviso quando não cabe

| Cenário | Asserção |
|---|---|
| Baixa que mantém `saldo_fisico >= saldo_reservado` | Nenhum evento, nenhuma notificação |
| Material crítico, mas requisição em `rascunho` / `aguardando_autorizacao` | Nenhum evento — só `autorizada` é avisada |
| **`saldo_reservado == 0` e nenhuma requisição `autorizada`** | Nenhum evento, nenhuma notificação — **e** `SaidaExcepcional` gravada com `numero_publico` emitido, `ItemSaidaExcepcional` gravado, `MovimentacaoEstoque` de `saida_excepcional` gravada e `saldo_fisico` reduzido pelo valor exato. Prova que o hook apenas seleciona usuários notificados e nunca vira pré-condição da baixa (SAE-01) |
| `_pos_saida_hook=None` (default) | Saída registra normalmente, zero eventos — compatibilidade retroativa do service para todos os chamadores existentes, inclusive a fixture `saida_registrada` |

O filtro `quantidade_autorizada__gt=0` do núcleo não ganha teste próprio: sob
ITEM-04 uma requisição `autorizada` não pode ter item autorizado em zero, então
o caso é inalcançável pelos services. O filtro permanece como guarda defensiva
herdada do hook SCPI.

### Permissão e violação de domínio

Já cobertos pelos testes atuais de `registrar_saida_excepcional`
(`apps/estoque/tests/test_services.py:88-193`: documento vazio, material
duplicado, saldo inexistente, quantidade inválida, saldo físico insuficiente
sem persistir nada, ator sem permissão). Nenhum muda de resultado — o hook não participa de nenhum desses
caminhos, porque todos levantam antes de qualquer escrita. Rodar como
regressão, sem editar.

### Atomicidade (SAE-04) e a fronteira do commit

Dois testes, um para cada classe de falha descrita em "Duas classes de falha":

1. **Hook levanta antes do commit** → nada persistido: nenhuma
   `SaidaExcepcional`, nenhum `ItemSaidaExcepcional`, nenhuma
   `MovimentacaoEstoque`, `saldo_fisico` intacto, `SequenciaSaidaExcepcional` sem
   avanço efetivo, nenhuma `TimelineRequisicao`. Prova que a posição escolhida
   para a chamada não abre janela de saída-sem-aviso.
2. **`criar_notificacoes_para` levanta dentro do `on_commit`** (patch no ponto de
   uso, teste com `transaction=True` para o `on_commit` realmente disparar) →
   **nada reverte**: `SaidaExcepcional`, `MovimentacaoEstoque`, `saldo_fisico` e
   `TimelineRequisicao` continuam gravados; zero `Notificacao`; o
   `logger.exception` é emitido (asserido via `caplog`). Prova que a entrega da
   notificação é best-effort e não compromete o registro de domínio.

### TR-015B continua como hoje

Teste de integração: requisição `autorizada` → saída excepcional que cria a
divergência → `separar_para_retirada` levanta `DadosInvalidos` com
`code='separacao_bloqueada_divergencia'` e a requisição segue `AUTORIZADA`.

A asserção de estoque compara o estado **imediatamente após a saída excepcional**
com o estado após a tentativa bloqueada — não com o estado inicial, que a baixa
legitimamente já alterou. Ou seja: `saldo_fisico` e `saldo_reservado` idênticos
antes e depois da tentativa, e nenhuma `MovimentacaoEstoque` nova criada pela
separação. Trava o critério de aceite final da issue: o aviso é aditivo, não
substitui o bloqueio, e o caminho bloqueado continua sem efeito colateral.

Os testes existentes de TR-015B (`apps/requisicoes/tests/test_services.py:1601+`)
não são tocados.

### View e superfícies visíveis

`apps/estoque/tests/test_views.py`:

- Com `registrar_saida_excepcional` mockado (padrão já usado em `:488` e `:522`),
  asserir que a view passa um `_pos_saida_hook` não nulo. Prova o wiring sem
  depender de banco.
- Fluxo com banco: saída que cria divergência → `messages` contém um `warning`
  além do `success`, citando o número de requisições afetadas. Saída sem
  divergência → só o `success`, nenhum `warning`.

`apps/requisicoes/tests/test_views.py`: detalhe da requisição afetada renderiza,
no bloco do evento `atualizacao_estoque_relevante`, o `numero_publico` da saída,
o código do material afetado e a orientação de cancelamento (TR-013). Caso
espelho para a origem SCPI, que não tem `numero_publico`, garantindo que o
template não quebra nem exibe rótulo vazio.

### Notificações

`apps/notificacoes/tests/test_services.py`: caso da nova origem, espelhando
`test_divergencia_estoque_gera_notificacoes_para_requisicao_afetada:318` e
`test_divergencia_estoque_deduplica_criador_igual_beneficiario:356`.

## Invariantes

| Invariante | Efeito |
|---|---|
| **EST-07** (divergência crítica: físico < reservado) | Confirmado como estado válido de domínio. A saída excepcional passa a ser uma origem reconhecida e **avisada** de EST-07, ao lado da importação SCPI. Emenda na matriz registra isso. |
| **EST-08** (material divergente bloqueia separação, TR-015B) | Preservado sem alteração. O aviso é aditivo. |
| **EST-09** (divergência resolve quando físico >= reservado) | Inalterado. A resolução continua não gerando aviso — ver Fora de escopo. |
| **EST-06** (transação e lock) | Preservado. Hook roda dentro do `atomic` existente e só re-seleciona saldos já travados. |
| **EST-01/EST-02** (disponível = físico − reservado; reserva não baixa físico) | Inalterados. A baixa continua mexendo só em `saldo_fisico`. |
| **SAE-01** (fluxo próprio, fora de Requisição) | Preservado em duas frentes: `estoque/services.py` continua sem importar `requisicoes` (inversão por parâmetro), e a existência de reserva ou de requisição autorizada nunca condiciona o registro da baixa — o hook só seleciona os usuários a notificar. Teste dedicado com `saldo_reservado == 0`. |
| **SAE-04** (registro indivisível, all-or-nothing) | Reforçado até a fronteira do commit: o hook e a timeline entram no all-or-nothing; a entrega da notificação, que roda depois do commit, não. Um teste para cada lado da fronteira. |
| **LED-01/LED-03** (ledger) | Inalterados. As movimentações da baixa continuam iguais; o hook não escreve no ledger. |
| **REQ-08** (timeline registra eventos principais) | Novo caso de uso do evento já existente `atualizacao_estoque_relevante`. |
| **TR-013 / TR-015 / TR-015B** | Nenhuma transição muda. TR-013 segue sendo o escape; a diferença é que agora alguém fica sabendo que precisa usá-lo. |

## Riscos

1. **Requisições autorizadas de outro estoque.** O filtro de `ItemRequisicao` no
   hook atual não filtra por estoque — ele parte dos `saldos_criticos`, que já
   são por estoque, mas o item da requisição não carrega estoque. Sob ADR-0017
   (estoque único nesta fase) isso é inócuo. É limitação **herdada** do hook
   SCPI, não introduzida aqui; o refactor a preserva em vez de mudar
   comportamento por baixo do pano. Registrar, não corrigir nesta issue.

2. **Volume de notificações.** Uma baixa que atinja muitos materiais reservados
   pode gerar muitas notificações de uma vez. Mitigado pela agregação: um evento
   e um par de notificações por *requisição*, não por material. Mesmo perfil do
   caminho SCPI, que importa arquivos inteiros.

3. **Refactor do hook SCPI.** Extrair o núcleo mexe em código com testes
   existentes. Mitigação: assinatura pública e formato de `metadata` preservados
   byte a byte, e a suíte atual de `TestConfirmarImportacaoScpiTimelineRequisicoes`
   roda sem edição como rede de segurança.

4. **Import `estoque/views.py` → `requisicoes/services`.** Nova aresta entre
   apps na camada de view. Mitigada por import local à função. Se o projeto
   depois adotar um registry de hooks, esse é o ponto único a trocar.

5. **Nenhum risco de contrato OpenAPI ou de schema.** Projeto é
   server-rendered sem API REST; a mudança não altera models nem migrations.

## Fora de escopo

- **Aviso de resolução de divergência (EST-09).** Nem `estornar_saida_excepcional`
  nem `registrar_devolucao_estoque` avisam quando a divergência deixa de
  existir. Assimetria consciente: o aviso de criação exige ação (cancelar via
  TR-013); o de resolução seria só informativo. Vale issue própria se a operação
  pedir.
- **Superfície de UI para divergências ativas.** Uma tela "requisições
  bloqueadas por divergência" resolveria o problema por consulta em vez de por
  push. É complementar, não substituta, e não cabe nesta fatia.
- **Confirmação explícita no formset da saída excepcional.** Descartado na
  decisão HITL.
- **Corpo de mensagem persistido em `Notificacao`.** Hoje o model guarda só
  `tipo` + `requisicao_id`. Dar-lhe texto próprio é campo novo, migration e
  revisão dos seis tipos existentes e de todos os seus testes. Vale issue
  própria; enquanto isso, o texto rico vive na timeline, que é o destino do link
  da notificação.
- **Retry ou fila para notificações pós-commit.** Hoje a política é
  best-effort + `logger.exception`, igual para todos os hooks. Mudar isso é
  transversal ao app `notificacoes`.
- **Mudança de qualquer transição da requisição.**
