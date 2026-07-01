# Plano — #53: transitions.py keyed por `Operacao` (TransitionSpec)

## Scope

Reunificar `apps/requisicoes/transitions.py`: sai o mapa `estado_origem →
{destinos}`, entra a tabela keyed por `Operacao` (enum), conforme a Emenda
2026-06-26 do ADR-0011 ("Transições keyed por operação").

**Muda:**
- `apps/requisicoes/models.py`: novo `Operacao(models.TextChoices)` — vocabulário
  compartilhado, um membro por operação que hoje chama `verificar_transicao_valida`.
- `apps/requisicoes/transitions.py`: `TransicaoRequisicao` (dataclass frozen) +
  `TRANSICOES: dict[Operacao, TransicaoRequisicao]` + nova assinatura
  `verificar_transicao_valida(operacao: Operacao, requisicao: Requisicao) -> TransicaoRequisicao`.
- `apps/requisicoes/services/ciclo_vida.py`, `atendimento.py`, `cancelamento.py`:
  todos os 13 call sites migram de `verificar_transicao_valida(requisicao.estado, EstadoX)`
  para `verificar_transicao_valida(Operacao.X, requisicao)`.
- Testes de `transitions.py` (novo `apps/requisicoes/tests/test_transitions.py`)
  cobrindo a tabela isoladamente; testes de services que hoje fazem
  `pytest.raises(EstadoInvalido)` continuam válidos sem alteração de asserção
  (nenhum teste atual verifica o texto da mensagem gerada por
  `verificar_transicao_valida`, apenas o tipo da exceção ou `.code`).

**Não muda (fora de escopo, fatia futura):**
- Selector `acoes_disponiveis(papel, requisicao) -> frozenset[Operacao]` (UI/selectors) —
  vem depois, conforme o corpo da issue.
- Checagens manuais de estado já existentes em alguns services (ex.:
  `if requisicao.estado != EstadoRequisicao.AGUARDANDO_AUTORIZACAO: raise EstadoInvalido(...)`
  com mensagem amigável específica) **permanecem intactas**. Elas já eram
  redundantes com a validação de transição antes deste refactor — remover essa
  redundância não é objetivo desta issue e mudaria mensagens user-facing
  testadas/renderizadas hoje.
- Autorização/policy — a tabela continua sem saber nada de papel/permissão.
- `Operacao` não ganha membros para TR-001 (criação) e TR-003 (descarte de
  rascunho não enviado): nenhum dos dois chama `verificar_transicao_valida` hoje
  (criação não tem estado de origem; descarte é `DELETE`, não transição de
  estado) — mantém-se assim, sem adicionar vocabulário não consumido.

## Mapeamento operação → spec

Levantado lendo cada service em `apps/requisicoes/services/{ciclo_vida,atendimento,cancelamento}.py`:

| `Operacao` | `estados_origem` | `estado_destino` | `eventos_timeline` | Service |
|---|---|---|---|---|
| `EDITAR_RASCUNHO` | `{RASCUNHO}` | `RASCUNHO` | `frozenset()` (vazio — exceção deliberada) | `editar_rascunho` (TR-002) |
| `ENVIAR_PARA_AUTORIZACAO` | `{RASCUNHO}` | `AGUARDANDO_AUTORIZACAO` | `{ENVIO_AUTORIZACAO}` | `enviar_para_autorizacao` (TR-005) |
| `RETORNAR_PARA_RASCUNHO` | `{AGUARDANDO_AUTORIZACAO}` | `RASCUNHO` | `{RETORNO_RASCUNHO}` | `retornar_para_rascunho` (TR-006) |
| `RECUSAR` | `{AGUARDANDO_AUTORIZACAO}` | `RECUSADA` | `{RECUSA}` | `recusar_requisicao` (TR-011) |
| `AUTORIZAR` | `{AGUARDANDO_AUTORIZACAO}` | `AUTORIZADA` | `{AUTORIZACAO_TOTAL}` | `autorizar_requisicao` (TR-008) |
| `CANCELAR` | `{RASCUNHO, AGUARDANDO_AUTORIZACAO, AUTORIZADA, PRONTA_PARA_RETIRADA}` | `CANCELADA` | `{CANCELAMENTO}` | `cancelar_requisicao` / `cancelar_ou_descartar_requisicao` (TR-004/TR-012/TR-013/TR-014) |
| `SEPARAR_PARA_RETIRADA` | `{AUTORIZADA}` | `PRONTA_PARA_RETIRADA` | `{SEPARACAO_RETIRADA}` | `separar_para_retirada` (TR-015/TR-015B) |
| `REGISTRAR_ATENDIMENTO` | `{PRONTA_PARA_RETIRADA}` | `ATENDIDA` | `{ATENDIMENTO_TOTAL, ATENDIMENTO_PARCIAL, LIBERACAO_RESERVA}` | `registrar_atendimento` (TR-016/TR-017/TR-018) |
| `REGISTRAR_DEVOLUCAO` | `{ATENDIDA}` | `ATENDIDA` | `{DEVOLUCAO_REGISTRADA}` | `registrar_devolucao` (TR-020) |
| `ESTORNAR` | `{ATENDIDA}` | `ESTORNADA` | `{ESTORNO}` | `estornar_requisicao` (TR-021) |

**Correção pós-review (CodeRabbit, PR #7):** o campo original `evento_timeline: str`
do pseudocódigo do ADR-0011 modela só **um** evento por operação. Isso é falso
para `REGISTRAR_ATENDIMENTO` — o service emite `ATENDIMENTO_TOTAL` **ou**
`ATENDIMENTO_PARCIAL`, e opcionalmente um segundo evento `LIBERACAO_RESERVA`
quando há entrega menor que autorizada (`houve_liberacao=True`). Um campo
singular forçaria escolher um evento "canônico" arbitrário, o que é enganoso
para quem for consumir a tabela depois (selector/UI). Correção: o campo passa
a `eventos_timeline: frozenset[EventoTimeline]` — o **conjunto de eventos que
essa operação pode emitir**, não um valor normativo único. `registrar_atendimento`
declara os 3 possíveis; as demais operações declaram um conjunto unitário.

Isso também resolve o segundo finding do CodeRabbit (`EDITAR_RASCUNHO` com
`evento_timeline = None` divergindo da convenção): em vez de um valor `None`
especial que quebra a regra "toda operação registra timeline" sem sinalizar
por quê, `EDITAR_RASCUNHO` declara `frozenset()` (conjunto vazio) — mesmo tipo
de todo mundo, e o vazio já é auto-descritivo: **esta operação, hoje, não
emite nenhum evento de timeline.** Isso é uma exceção deliberada e existente no
código atual (`editar_rascunho` não chama `TimelineRequisicao.objects.create` —
edição de rascunho não é um dos 13 eventos canônicos de `EventoTimeline`), não
uma introduzida por este refactor. Este PR só a torna visível na tabela; não
muda esse comportamento nem justifica replicá-lo em novas operações sem
motivo equivalente.

`estados_origem` é `frozenset[EstadoRequisicao]` — sempre conjunto, mesmo
quando só há uma origem, para eliminar a ambiguidade que motivou a emenda
(operação → estado de origem exigido deixando de estar em condicional de
view).

## `verificar_transicao_valida` — novo contrato

```python
def verificar_transicao_valida(
    operacao: Operacao, requisicao: Requisicao
) -> TransicaoRequisicao:
    transicao = TRANSICOES[operacao]
    if requisicao.estado not in transicao.estados_origem:
        raise EstadoInvalido(
            f"Transição '{operacao.label}' inválida no estado "
            f"'{requisicao.get_estado_display()}'.",
            code='estado_origem_invalido',
        )
    return transicao
```

`TRANSICOES[operacao]` é indexação direta (não `.get`) — todo `Operacao`
definido **precisa** ter spec; se não tiver, é `KeyError` em tempo de execução
(sinaliza vocabulário incompleto, falha rápido). Nenhum código hoje chama a
função com uma operação fora da tabela.

Retorno da função passa a ser `TransicaoRequisicao` (antes era `None`); os 13
call sites migrados descartam o retorno (`eventos_timeline` não é consumido
nesta fatia — services continuam escrevendo `TimelineRequisicao` com o evento
específico que já escolhiam antes, incluindo a lógica condicional de
`registrar_atendimento` entre total/parcial/liberação). Usar o retorno para
validar ou eliminar esse hardcode é trabalho da fatia do selector, fora de
escopo aqui.

## Files touched

- `apps/requisicoes/models.py` — novo `Operacao(models.TextChoices)`.
- `apps/requisicoes/transitions.py` — reescrita completa (dataclass + dict + função).
- `apps/requisicoes/services/ciclo_vida.py` — 6 call sites (`editar_rascunho`,
  `enviar_para_autorizacao`, `retornar_para_rascunho`, `recusar_requisicao`,
  `autorizar_requisicao`, `estornar_requisicao`) + import de `Operacao`.
- `apps/requisicoes/services/atendimento.py` — 3 call sites
  (`separar_para_retirada`, `registrar_atendimento`, `registrar_devolucao`) +
  import de `Operacao`.
- `apps/requisicoes/services/cancelamento.py` — 3 call sites (dentro de
  `_cancelar_requisicao_impl`, um por branch de estado) + import de `Operacao`.
- `apps/requisicoes/tests/test_transitions.py` — **novo**, testa a tabela
  isoladamente (não existia teste dedicado antes; `transitions.py` só era
  exercitado indiretamente via `test_services.py`).
- `docs/adr/0011-*.md` — nenhuma mudança de conteúdo necessária: a emenda
  2026-06-26 já documenta o alvo; este PR apenas implementa o que ela descreve.
  (Se o CodeRabbit apontar drift residual entre a ilustração original do ADR e
  o código, ajustamos a ilustração original para apontar para a emenda, sem
  reabrir a decisão.)

## Test strategy

`test_transitions.py` (novo):
- Caminho feliz: para cada `Operacao`, `verificar_transicao_valida` retorna a
  `TransicaoRequisicao` correta quando `requisicao.estado` está em
  `estados_origem`.
- Estado de origem inválido: para cada `Operacao`, estado fora de
  `estados_origem` levanta `EstadoInvalido(code='estado_origem_invalido')`.
- `CANCELAR` especificamente: os 4 estados de origem authorized todos passam;
  qualquer outro estado (`RECUSADA`, `ATENDIDA`, `ESTORNADA`) falha.
- `TRANSICOES` contém uma entrada por membro de `Operacao` (nenhum
  `KeyError` de vocabulário incompleto) — teste de integridade da tabela.
- `estados_origem` de cada spec é de fato `frozenset` (não lista/tupla) —
  characterization test do contrato "sempre conjunto".
- `eventos_timeline` de `REGISTRAR_ATENDIMENTO` contém exatamente
  `{ATENDIMENTO_TOTAL, ATENDIMENTO_PARCIAL, LIBERACAO_RESERVA}`; o de
  `EDITAR_RASCUNHO` é `frozenset()` vazio — characterization test da correção
  pós-review.

`test_services.py` (existente): não deve precisar de nenhuma nova asserção —
os testes já cobrem `EstadoInvalido` por tipo/`.code`, que não muda. Rodar a
suíte completa após o refit para confirmar zero regressão.

## Invariants (docs/design-acesso-rapido/matriz-invariantes.md)

Este projeto não usa `docs/design-acesso-rapido/` (repo é single-context, ver
`docs/agents/domain.md`); a referência de invariantes real é
`apps/requisicoes/models.py::EstadoRequisicao` + as transições TR-001..TR-022
documentadas em `CONTEXT.md`/ADR-0011. Nenhuma transição TR-* muda de
comportamento nesta fatia — só a representação interna da tabela e a
assinatura da função de validação.

## Risks

- **Nenhuma mudança de schema/migração** — `Operacao` não é persistido em
  nenhum model; não requer `make setup` nem migração.
- **Concorrência**: `verificar_transicao_valida` continua puro (sem IO); os
  locks (`select_for_update`) e a ordem de lock em `services/*.py` não mudam.
- **Risco principal**: call site esquecido na migração (13 ocorrências em 3
  arquivos) deixaria um `verificar_transicao_valida(str, str)` chamando a
  assinatura antiga — isso quebra em import time ou no primeiro teste que
  exercitar o service, não silenciosamente. Mitigação: `ruff check` +
  suíte completa antes do PR, e busca (`grep -rn "verificar_transicao_valida"`)
  para confirmar zero call site na assinatura antiga.
- **Mensagem de erro genérica muda de texto** (não de `.code`): quem depende do
  texto exato de `EstadoInvalido` gerado *pela tabela* (não pelas checagens
  manuais dos services, que não mudam) veria o texto mudar. Busca em
  `test_services.py` confirma que nenhum teste hoje faz
  `match=` sobre essa mensagem especificamente — só sobre mensagens de
  `DadosInvalidos` de outras validações. Se o CodeRabbit encontrar um caso que
  eu perdi, ajusto o teste.
