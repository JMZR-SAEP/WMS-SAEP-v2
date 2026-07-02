# Plano — Issue #58: consolidar cancelamento (`cancelar_requisicao` dirigido por variante + handlers)

## Escopo

**Muda:**
- `apps/requisicoes/services/cancelamento.py`: uma única entrada pública
  `cancelar_requisicao(*, ator_id, requisicao_id, justificativa='') -> Requisicao`,
  dirigida por `CancelamentoInfo` (já existente em `transitions.py`, de #57).
  Dispatch via tabela `_HANDLERS: dict[CancelamentoVariant, Callable]` com dois
  handlers — `_efeito_descarte` (delete) e `_efeito_cancelamento` (transição +
  timeline; libera reserva via comando do estoque quando `info.libera_reserva`).
  Nenhum dos handlers ramifica por `requisicao.estado` — só consultam as flags
  de `CancelamentoInfo` (`requer_justificativa`, `libera_reserva`), conforme
  ADR-0011 (emenda 2026-06-26).
- Remove `cancelar_ou_descartar_requisicao`, `descartar_rascunho` (público) e
  `_descartar_rascunho_impl`/`_cancelar_requisicao_impl` (as duas impls e o
  branching de ~120 linhas somem junto com a consolidação).
- `apps/requisicoes/views.py`: `cancelar_requisicao_view` passa a chamar
  `cancelar_requisicao` (não mais `cancelar_ou_descartar_requisicao`). A
  distinção "foi descarte ou cancelamento" para a mensagem de sucesso passa a
  usar `resultado.pk is None` (delete de Django zera o pk da instância) no
  lugar do sentinel `Optional[Requisicao]` antigo.
- `apps/requisicoes/services/__init__.py`: remove os dois exports públicos.

**Não muda:**
- `transitions.py` (`CancelamentoInfo`, `cancelamento_info`, `TRANSICOES`) —
  já é a fonte única da variante desde #57, só passa a ser consumida também
  pelo service (já é consumida pela view em `_detalhe_context`).
- `policies.py` (`pode_cancelar_requisicao`/`exigir_pode_cancelar_requisicao`)
  — permissão não depende de variante, só de estado+papel; contrato
  `(papel: PapelEfetivo, requisicao)` de #52 já está correto.
- URL/endpoint (`requisicoes/<pk>/cancelar/`), templates, templatetags
  (`requisicoes_tags.py` já usa `CancelamentoInfo`/`CancelamentoVariant` de
  #57).
- Regra de negócio observável: mesmos estados cancelam da mesma forma, mesmas
  mensagens de sucesso na view, mesmo comportamento de liberação de reserva.

## Comportamento herdado que precisa ser preservado exatamente

- **Ordem de validação**: `cancelamento_info(requisicao)` (estado — pode
  lançar `EstadoInvalido`) roda **antes** de `exigir_pode_cancelar_requisicao`
  (papel — lança `PermissaoNegada`). Isso reproduz o comportamento atual de
  `_cancelar_requisicao_impl`, onde o teste
  `test_cancelar_requisicao_estado_invalido_nao_altera_ou_cria_timeline` espera
  `EstadoInvalido` (não `PermissaoNegada`) para uma requisição em estado não
  cancelável, mesmo quando o ator teria permissão.
- **Justificativa "tudo ou nada" via flag**: dentro do handler de
  cancelamento, `justificativa` só é preservada quando
  `info.requer_justificativa` é `True`; caso contrário é sempre descartada
  (`''`), independente do que o chamador enviar. Isso substitui o
  comportamento hoje espalhado entre o wrapper público `cancelar_requisicao`
  (zerava justificativa só para `AGUARDANDO_AUTORIZACAO`) e
  `cancelar_ou_descartar_requisicao` (não zerava — bug de inconsistência entre
  os dois entrypoints antigos). A nova regra única cobre RASCUNHO-enviado e
  AGUARDANDO_AUTORIZACAO da mesma forma (ambos `requer_justificativa=False`).
- **Descarte não grava timeline nem exige ator sem permissão** — mesmo
  comportamento de `_descartar_rascunho_impl`, só que agora inline no handler,
  sem checagens de estado redundantes (já garantidas por
  `cancelamento_info`).

## Arquivos tocados

- `apps/requisicoes/services/cancelamento.py` — reescrita completa do módulo.
- `apps/requisicoes/services/__init__.py` — remove exports de
  `cancelar_ou_descartar_requisicao` e `descartar_rascunho`.
- `apps/requisicoes/views.py` — troca de import/chamada em
  `cancelar_requisicao_view`.
- `apps/requisicoes/tests/test_services.py` — migra os testes que chamavam
  `descartar_rascunho`/`cancelar_ou_descartar_requisicao` para
  `cancelar_requisicao`; remove o teste duplicado de
  `cancelar_ou_descartar_requisicao_aguardando_autorizacao_ignora_justificativa`
  (a mesma cobertura já existe via `cancelar_requisicao`, e o comportamento
  correto é o de `cancelar_requisicao`: ignora a justificativa).
- `apps/requisicoes/tests/test_views.py` — sem mudança de comportamento
  esperada (endpoint HTTP inalterado); roda como regressão.

## Estratégia de testes

- **Happy path — descarte**: rascunho nunca enviado é removido sem timeline
  (existente, migrado para chamar `cancelar_requisicao`).
- **Happy path — cancelamento simples**: RASCUNHO numerado e
  AGUARDANDO_AUTORIZACAO cancelam com transição + timeline, sem liberar
  reserva, justificativa sempre `''` mesmo se enviada.
- **Happy path — cancelamento pós-autorização**: AUTORIZADA e
  PRONTA_PARA_RETIRADA cancelam liberando reserva via
  `liberar_reservas_para_cancelamento`, exigindo justificativa não vazia.
- **Permissão negada**: ator sem permissão não altera estado nem estoque, para
  descarte e para cancelamento (cobertura já existente, migrada).
- **Erro de domínio**: estado não cancelável lança `EstadoInvalido` sem
  escrever timeline; justificativa ausente em variante que exige lança
  `DadosInvalidos` com `code='justificativa_cancelamento_obrigatoria'`.
- Suíte completa roda ao final (`uv run pytest -q -ra --tb=short
  --strict-markers --disable-warnings -n logical`).

## Riscos

- **Regressão de mensagem de sucesso na view**: a troca do sentinel
  `Optional[Requisicao]` (`is None`) para `resultado.pk is None` depende do
  comportamento documentado do Django (`Model.delete()` zera o pk da própria
  instância após a exclusão). Mitigado pelos testes de view existentes
  (`test_descartar_rascunho_post_redireciona_para_lista` e os testes de
  cancelamento pós-autorização), que não mudam de assinatura e continuam
  cobrindo o fluxo HTTP completo.
- **Comportamento de justificativa inconsistente entre os dois entrypoints
  antigos**: ao unificar, um dos dois comportamentos observados hoje deixa de
  existir. Escolhido preservar o de `cancelar_requisicao` (ignora
  justificativa quando não exigida) por ser o nome mantido pelo issue e o
  comportamento já coberto por teste; o teste do outro entrypoint
  (`cancelar_ou_descartar_requisicao_...ignora_justificativa`, que esperava a
  justificativa preservada) é removido junto com a função.
- **Liberação de reserva**: sem mudança na chamada a
  `liberar_reservas_para_cancelamento`/`ItemLiberacaoReserva` — mantém uso do
  comando do estoque, não manipulação direta de saldo.
