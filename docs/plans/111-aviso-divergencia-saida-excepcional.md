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

- `registrar_saida_excepcional` ganha o parâmetro opcional `_pos_saida_hook`,
  chamado dentro da mesma transação, depois das baixas e da numeração.
- Novo hook `registrar_timeline_divergencia_saida_excepcional` em
  `apps/requisicoes/services/ciclo_vida.py`, irmão do hook já existente da
  importação SCPI.
- Núcleo compartilhado entre os dois hooks, extraído do corpo atual de
  `registrar_timeline_divergencia_importacao`.
- `nova_saida_excepcional_view` injeta o hook, espelhando o que
  `confirmar_importacao_scpi_view` já faz.
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
- **Templates.** A timeline renderiza o evento por `get_evento_display`
  (`apps/requisicoes/templates/requisicoes/partials/_timeline.html:31`) e a
  notificação por `get_tipo_display`
  (`apps/notificacoes/templates/notificacoes/lista.html:26`). Ambos os rótulos
  já existem e são genéricos — o critério de aceite "template" da issue está
  satisfeito pela renderização atual, sem arquivo novo.
- **`estornar_saida_excepcional`.** O estorno devolve físico e pode resolver a
  divergência (EST-09), mas não avisará que ela sumiu. Ver "Fora de escopo".

## Arquivos tocados

| Arquivo | Mudança |
|---|---|
| `apps/estoque/services.py` | `registrar_saida_excepcional`: novo kwarg `_pos_saida_hook`, chamado ao final, dentro da transação |
| `apps/requisicoes/services/ciclo_vida.py` | Extrai núcleo compartilhado; adiciona `registrar_timeline_divergencia_saida_excepcional` |
| `apps/estoque/views.py` | `nova_saida_excepcional_view` injeta o hook (import local) |
| `apps/estoque/tests/test_services.py` | Testes do comportamento novo no service |
| `apps/estoque/tests/test_views.py` | Teste de que a view injeta o hook |
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
entra no `metadata` do evento. Então o núcleo recebe ambos prontos:

```python
def _registrar_divergencia_para_autorizadas(
    *,
    material_ids: list[int],
    estoque,
    ator,
    material_info: dict[int, dict],   # {material_id: {'codigo': ..., 'nome': ...}}
    metadata_origem: dict,            # ex.: {'saida_excepcional_id': 7, 'numero_publico': 'SXP-...'}
) -> None:
```

O `metadata` final de cada evento fica `{**metadata_origem, 'materiais': [...]}`,
o que preserva byte a byte o formato atual do hook SCPI
(`{'importacao_id': ..., 'materiais': [...]}`) — os testes existentes em
`apps/estoque/tests/test_services.py:471` continuam válidos sem edição.

`registrar_timeline_divergencia_importacao` mantém assinatura e nome públicos.
É refactor interno, não quebra de contrato: `apps/requisicoes/views.py:1083` e
os testes que o importam seguem funcionando.

### Onde o hook é chamado dentro de `registrar_saida_excepcional`

Depois de todas as baixas de `saldo_fisico`, das movimentações de ledger e da
emissão do `numero_publico`; antes do `return`. Ainda dentro do
`@transaction.atomic` da função.

Três razões para essa posição:

1. Os saldos já estão gravados, então a consulta de divergência crítica
   (`saldo_fisico__lt=F('saldo_reservado')`) enxerga o estado pós-baixa.
2. O `numero_publico` já existe, então o `metadata` do evento pode citar o
   documento pelo número que o operador vê na tela — não só pelo id.
3. Continua tudo na mesma transação, o que mantém SAE-04: se o aviso falhar, a
   saída inteira reverte. Não existe estado em que a baixa persiste sem o aviso.

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
`logger.exception` por requisição. Falha ao notificar não derruba a saída já
comprometida — a baixa e a timeline são o registro de verdade; a notificação é
entrega best-effort. Comportamento idêntico ao do caminho SCPI.

## Estratégia de testes

Todos em `apps/estoque/tests/test_services.py`, salvo indicação. Nova classe
`TestSaidaExcepcionalDivergenciaTimeline`.

### Caminho feliz

| Cenário | Asserção |
|---|---|
| Saída rebaixa físico abaixo do reservado, existe requisição `autorizada` com o material | Exatamente 1 `TimelineRequisicao` com evento `ATUALIZACAO_ESTOQUE_RELEVANTE`; `metadata['saida_excepcional_id'] == saida.pk`; `metadata['numero_publico'] == saida.numero_publico`; `metadata['materiais']` contém código e nome do material |
| Mesma saída, dois materiais críticos na mesma requisição | 1 evento agregado, `len(metadata['materiais']) == 2` — trava o "um evento agregado por requisição" do critério de aceite |
| Notificações | 1 `Notificacao` de tipo `DIVERGENCIA_ESTOQUE` para o criador e 1 para o beneficiário |
| Criador == beneficiário | 1 notificação só (dedup já garantida por `criar_notificacoes_para`) |

### Ausência de aviso quando não cabe

| Cenário | Asserção |
|---|---|
| Baixa que mantém `saldo_fisico >= saldo_reservado` | Nenhum evento, nenhuma notificação |
| Material crítico, mas requisição em `rascunho` / `aguardando_autorizacao` | Nenhum evento — só `autorizada` é avisada |
| Material crítico sem nenhuma requisição `autorizada` que o use | Nenhum evento, nenhuma notificação |
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

### Atomicidade (SAE-04)

Hook que levanta exceção → nada persistido: nenhuma `SaidaExcepcional`, nenhum
`ItemSaidaExcepcional`, `saldo_fisico` intacto, `SequenciaSaidaExcepcional` sem
avanço efetivo, nenhuma `TimelineRequisicao`. Esse é o teste que prova que a
posição escolhida para a chamada não abre janela de saída-sem-aviso.

### TR-015B continua como hoje

Teste de integração: requisição `autorizada` → saída excepcional que cria a
divergência → `separar_para_retirada` levanta `DadosInvalidos` com
`code='separacao_bloqueada_divergencia'`, requisição segue `AUTORIZADA`, estoque
inalterado. Trava o critério de aceite final da issue: o aviso é aditivo, não
substitui o bloqueio.

Os testes existentes de TR-015B (`apps/requisicoes/tests/test_services.py:1601+`)
não são tocados.

### View

`apps/estoque/tests/test_views.py`: com `registrar_saida_excepcional` mockado
(padrão já usado em `:488` e `:522`), asserir que a view chama o service com
`_pos_saida_hook=registrar_timeline_divergencia_saida_excepcional`. Prova o
wiring sem depender de banco.

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
| **SAE-01** (fluxo próprio, fora de Requisição) | Preservado pela inversão: `estoque/services.py` continua sem importar `requisicoes`. |
| **SAE-04** (registro indivisível, all-or-nothing) | Reforçado: agora o aviso também está dentro do all-or-nothing, e há teste que prova. |
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
- **Mudança de qualquer transição da requisição.**
