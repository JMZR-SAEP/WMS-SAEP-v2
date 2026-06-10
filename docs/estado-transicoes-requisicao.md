# Estados e Transições da Requisição — WMS-SAEP

## 1. Objetivo

Síntese operacional da máquina de estados de requisições. Use este arquivo para implementar enums, tabela declarativa de transições, services, policies, timeline, movimentações de estoque e testes.

Fontes de alinhamento: `docs/processos-almoxarifado.md` e `docs/matriz-invariantes.md`.

## 2. Princípios

- Transições devem ser declarativas e aplicadas por uma função/service única.
- Services validam domínio, estado, permissões contextuais, estoque/reserva e registram timeline.
- Policies validam ator, papel, setor, beneficiário e objeto.
- Views e services chamam a mesma policy quando houver autorização contextual.
- Toda transição de estado roda em `transaction.atomic()` e faz `select_for_update` na linha da `Requisicao`, revalidando o estado de origem sob lock antes de qualquer efeito — inclusive transições que não tocam estoque (envio, retorno, recusa, cancelamento). Services de transição recebem `requisicao_id`, nunca uma instância já carregada.
- Quando a transição também muda saldo/reserva, a ordem de aquisição de locks é determinística: `Requisicao` primeiro, depois os `SaldoEstoque` afetados em ordem crescente de `(estoque_id, material_id, id)`.
- Eventos de timeline e efeitos de estoque são persistidos na mesma transação da mudança de estado. Ver ADR-0005.
- Timeline registra os eventos principais e é visível a usuários autorizados no escopo da requisição.
- Notificações são side effects pós-commit; nunca decidem sucesso da transação.

## 3. Estados canônicos

| Estado | Técnico | Papel no fluxo | Itens editáveis? | Estoque/reserva | Final? |
|---|---|---|---|---|---|
| Rascunho | `rascunho` | Criação/correção antes da autorização. | Sim, somente pelo criador enquanto permanecer rascunho. | Sem reserva/baixa. | Não |
| Aguardando autorização | `aguardando_autorizacao` | Fila do chefe do setor do beneficiário. | Não; deve retornar para rascunho. | Sem reserva/baixa. | Não |
| Recusada | `recusada` | Recusa da requisição inteira com motivo. | Não; estado final, retomada apenas por cópia (REQ-09). | Sem reserva/baixa. | Sim |
| Autorizada | `autorizada` | Aprovada integralmente pelo chefe do setor do beneficiário e disponível para separação pelo Almoxarifado. | Não | Reserva integral criada na autorização; sem baixa físico. | Não |
| Pronta para retirada | `pronta_para_retirada` | Quantidades autorizadas foram separadas e aguardam coleta/retirada final. | Não | Reserva mantida; sem baixa físico. | Não |
| Atendida | `atendida` | Retirada final registrada pelo Almoxarifado, total ou parcial sobre o autorizado. | Não | Baixa entregue; consome reserva entregue e libera reserva não entregue. | Sim |
| Cancelada | `cancelada` | Encerrada antes da retirada final. | Não | Se autorizada ou pronta para retirada, libera reserva; não baixa físico. | Sim |
| Estornada | `estornada` | Saída atendida revertida formalmente. | Não | Movimentação inversa de estorno. | Sim |

## 4. Eventos de timeline

| Evento | Técnico | Quando | Responsável | Justificativa |
|---|---|---|---|---|
| Criação | `criacao` | Criação do rascunho com ao menos um item. | Criador | Não |
| Envio | `envio_autorizacao` | Rascunho vai para autorização. | Criador | Não |
| Retorno para rascunho | `retorno_rascunho` | Requisição volta de aguardando autorização para rascunho. | Criador ou beneficiário | Opcional |
| Recusa | `recusa` | Chefe recusa a requisição inteira. | Chefe do setor do beneficiário | Sim |
| Autorização total | `autorizacao_total` | Todos os itens autorizados integralmente. | Chefe do setor do beneficiário | Não |
| Cancelamento | `cancelamento` | Cancelamento em estado permitido. | Conforme estado | Só se autorizada ou pronta para retirada |
| Separação para retirada | `separacao_retirada` | Quantidades autorizadas foram separadas e estão prontas para retirada. | Almoxarifado | Não |
| Atendimento total | `atendimento_total` | Tudo que foi autorizado foi entregue. | Almoxarifado | Não |
| Atendimento parcial | `atendimento_parcial` | Entrega menor que autorizada, com ao menos um item entregue. | Almoxarifado | Sim, por item |
| Liberação de reserva | `liberacao_reserva` | Cancelamento de autorizada ou atendimento parcial. | Ator da transição | Conforme transição |
| Devolução registrada | `devolucao_registrada` | Entrada por devolução vinculada. | Almoxarifado | Sim |
| Estorno | `estorno` | Reversão total/parcial pelo chefe de Almoxarifado. | Chefe de Almoxarifado | Sim |
| Atualização de estoque relevante | `atualizacao_estoque_relevante` | Operação ou importação afeta saldo/divergência de material relacionado. Para requisições em estado `autorizada`: quando importação SCPI cria divergência crítica superveniente em material de item autorizado, o evento é registrado na timeline dessa requisição (descoberta ativa). Um evento agregado por requisição por importação, listando os materiais afetados. A requisição não muda de estado automaticamente; a separação fica bloqueada até resolução do estoque ou cancelamento via TR-013. | Ator da operação | Não |

## 5. Matriz compacta de transições

| ID | De -> Para | Ação | Atores | Regras críticas | Efeitos | Ref. |
|---|---|---|---|---|---|---|
| TR-001 | N/A -> Rascunho | Criar requisição | Solicitante para si; auxiliar de setor para si ou usuários do próprio setor; chefe de setor para usuários do próprio setor; Almoxarifado para qualquer usuário | Usuário ativo; beneficiário permitido; setor do beneficiário ativo; ao menos um item; material ativo, sem divergência crítica, com saldo disponível inicial; quantidade solicitada positiva e compatível com saldo disponível inicial. **Verificação de elegibilidade prévia e advisory — não reserva estoque e não garante disponibilidade futura; a barreira definitiva é TR-008.** | Cria cabeçalho, itens, criador, beneficiário e snapshot do setor do beneficiário; sem número público; registra criação | 1.1, 1.2, 1.5, 11; REQ-01, REQ-02, REQ-05, REQ-07, EST-08, EST-10 |
| TR-002 | Rascunho -> Rascunho | Editar rascunho | Criador | Estado `rascunho` (vale para rascunho nunca enviado e para rascunho retornado); ao menos um item; materiais ativos, sem divergência crítica e com saldo disponível inicial. **Verificação de elegibilidade prévia e advisory — não reserva estoque e não garante disponibilidade futura (ver TR-001).** | Atualiza itens e observação geral; não gera número público; não reserva nem baixa estoque | 1.3, 1.4; REQ-02, REQ-05, REQ-06 |
| TR-003 | Rascunho -> descartado | Descartar rascunho nunca enviado | Criador | Nunca enviado; sem número público | Remove definitivamente a requisição e todos os eventos de timeline associados, inclusive o evento de criação. Comportamento intencional: rascunhos sem número público e sem envio não são processos auditáveis. Sem consumo de número público, sem reserva e sem movimentação de estoque. | 1.3, 1.4; REQ-02 |
| TR-004 | Rascunho -> Cancelada | Cancelar rascunho já numerado | Criador | Já possui número público; preserva número público | Encerra logicamente sem justificativa obrigatória; bloqueia edição, envio e atendimento; sem reserva e sem baixa de estoque | 1.3, 1.4; REQ-04, REQ-06 |
| TR-005 | Rascunho -> Aguardando autorização | Enviar | Criador | Ao menos um item; gera `REQ-AAAA-NNNNNN` apenas no primeiro envio; reenvios preservam número público | Registra envio; entra na fila do chefe do setor do beneficiário; não reserva nem baixa estoque | 1.3, 1.4; REQ-03, REQ-04, REQ-05, EST-02 |
| TR-006 | Aguardando autorização -> Rascunho | Retornar para rascunho | Criador ou beneficiário | Estado `aguardando_autorizacao`; preserva número público; não gera novo número | Sai da fila do chefe; volta para rascunho editável; não altera itens por si só; beneficiário perde acesso e o rascunho volta a creator-only; registra retorno na timeline | 1.3, 1.4; REQ-04, REQ-06 |
| TR-008 | Aguardando autorização -> Autorizada | Autorizar | Chefe do setor do beneficiário | Beneficiário pertence ao setor do chefe; todos os itens solicitados são autorizados integralmente; itens ativos, sem divergência crítica; saldo disponível atual suficiente para reservar tudo; transação e lock de estoque | Persiste `autorizada = solicitada` para todos os itens; cria reserva integral; não baixa físico; notifica envolvidos quando aplicável | 1.3, 1.4; PER-03, ITEM-01, EST-02, EST-05, EST-06, EST-08 |
| TR-010 | Aguardando autorização -> Aguardando autorização | Bloquear autorização inválida | Chefe do setor do beneficiário | Tentativa de autorizar parcialmente; divergência crítica; item inativo; saldo disponível atual insuficiente para reservar todos os itens solicitados | Não transiciona; orientar recusa inteira ou resolução da divergência/indisponibilidade antes da autorização | 1.3, 1.4; ITEM-01, EST-05, EST-08 |
| TR-011 | Aguardando autorização -> Recusada | Recusar inteira | Chefe do setor do beneficiário | Beneficiário pertence ao setor do chefe; motivo obrigatório | Registra motivo, chefe e data; sai da fila; sem reserva e sem baixa de estoque; notifica envolvidos quando aplicável | 1.3, 1.4; PER-03 |
| TR-012 | Aguardando autorização -> Cancelada | Cancelar antes da autorização | Criador ou beneficiário | Estado `aguardando_autorizacao`; sem justificativa obrigatória | Remove da fila; encerra logicamente; preserva número público; sem reserva e sem baixa de estoque | 1.3, 1.4; REQ-04 |
| TR-013 | Autorizada -> Cancelada | Cancelar autorizada | Criador, beneficiário, auxiliar de Almoxarifado ou chefe de Almoxarifado | Justificativa obrigatória; ainda sem retirada final; transação e lock de estoque. **Caminho de resolução intencional e único escape documentado quando divergência crítica superveniente (EST-07) inviabiliza TR-015 — a requisição não muda de estado automaticamente por divergência; o Almoxarifado deve cancelar via esta transição.** | Libera reservas automaticamente; não altera físico; registra cancelamento e liberação de reserva; notifica envolvidos quando aplicável | 1.3, 1.4; EST-04, EST-06 |
| TR-014 | Pronta para retirada -> Cancelada | Cancelar pronta para retirada | Criador, beneficiário, auxiliar de Almoxarifado ou chefe de Almoxarifado | Justificativa obrigatória; ainda sem retirada final; transação e lock de estoque | Libera reservas automaticamente; desfaz separação operacional quando aplicável; não altera físico; registra cancelamento e liberação de reserva; notifica envolvidos quando aplicável | 1.3, 1.4; EST-04, EST-06 |
| TR-015 | Autorizada -> Pronta para retirada | Separar para retirada | Auxiliar ou chefe de Almoxarifado | Requisição autorizada integralmente; itens autorizados > 0; para cada item autorizado, dentro do lock transacional: material sem divergência crítica (`saldo_fisico >= saldo_reservado`, EST-07) **e** `saldo_fisico >= quantidade_autorizada` do item; transação e lock de estoque. Quando bloqueada por divergência ou físico insuficiente, mantém estado `autorizada` e orienta cancelamento via TR-013. Ver TR-015B. | Registra separação; mantém reserva; não baixa físico; notifica quando aplicável | 1.3; EST-02, EST-06, EST-07 |
| TR-015B | Autorizada -> Autorizada | Bloquear separação por divergência/físico insuficiente | Qualquer ator que tente TR-015 | Algum item autorizado possui material com divergência crítica (`saldo_fisico < saldo_reservado`) ou `saldo_fisico < quantidade_autorizada` do item | Não transiciona; não altera estoque, reserva, entregue nem timeline de atendimento; mensagem de erro indica material afetado e orienta resolução do estoque ou cancelamento via TR-013 | EST-07; TR-013 |
| TR-016 | Pronta para retirada -> Atendida | Atendimento total | Auxiliar ou chefe de Almoxarifado | Todos os itens autorizados foram entregues; entregue = autorizado nos itens autorizados; físico suficiente; retirada registrada; transação e lock de estoque | Baixa físico na quantidade efetivamente retirada; consome reserva; registra responsável, retirante e observação quando houver; notifica envolvidos quando aplicável | 1.2, 1.3, 1.4; ITEM-02, EST-03, EST-06 |
| TR-017 | Pronta para retirada -> Atendida | Atendimento parcial | Auxiliar ou chefe de Almoxarifado | Ao menos um item entregue > 0; entregue <= autorizado; algum item entregue menor que autorizado ou zerado; justificativa para entrega menor que autorizada ou zero; físico suficiente para entregue; transação e lock de estoque | Baixa físico apenas do entregue; consome reserva entregue; libera reserva não entregue; finaliza como `atendida`, sem estado separado de atendimento parcial e sem pendência | 1.3, 1.4; ITEM-02, ITEM-03, ITEM-05, ITEM-06, EST-03, EST-04, EST-06 |
| TR-018 | Pronta para retirada -> Pronta para retirada | Bloquear atendimento sem entrega | Auxiliar ou chefe de Almoxarifado | Todos os itens seriam entregues com zero | Não finaliza; orientar cancelamento com justificativa | 1.3, 1.4; ITEM-06 |
| TR-019 | Atendida/Estornada -> mesmo estado | Bloquear cancelamento | Qualquer usuário | Estado final operacional | Não transiciona; orientar estorno quando aplicável | 1.3, 1.4 |
| TR-020 | Atendida -> Atendida | Registrar devolução | Auxiliar ou chefe de Almoxarifado | Vinculada a requisição atendida; quantidade > 0 e <= entregue líquida do item; justificativa ou observação conforme regra operacional; transação e lock de estoque | Aumenta físico; não altera status nem reserva; registra devolução na timeline e movimentação de estoque | 1.4; EST-01, EST-06 |
| TR-021 | Atendida -> Estornada | Estornar requisição | Chefe de Almoxarifado | Justificativa obrigatória; quantidade > 0 e <= entregue líquida do item; estorno total reverte a entregue líquida atual; preserva histórico original; transação e lock de estoque | Registra movimentação inversa; devolve físico conforme estorno total ou parcial; encerra definitivamente a requisição | 1.3, 1.4; EST-06 |
| TR-022 | Estornada -> Estornada | Bloquear ações pós-estorno | Qualquer usuário | Requisição estornada | Permite somente consulta à timeline e ao histórico por usuários autorizados; bloqueia corrigir, reenviar, separar, atender, cancelar e nova devolução operacional | 1.3, 1.4 |

## 6. Regras rápidas de quantidade e estoque

- Quantidades ficam separadas: `solicitada`, `autorizada`, `entregue`.
- Na autorização, `autorizada = solicitada` para todos os itens; no atendimento, `entregue <= autorizada`.
- Autorização parcial e autorização zero não são permitidas; o chefe autoriza integralmente ou recusa a requisição inteira.
- Entrega parcial e entrega zero exigem justificativa no item correspondente pelo Almoxarifado.
- Requisição atendida precisa de ao menos um item entregue > 0.
- Item autorizado com zero não é permitido; item entregue com zero libera a reserva correspondente no atendimento parcial.
- Atendimento parcial encerra a requisição como `atendida`; não cria estado separado nem pendência automática.
- Se todo o autorizado foi entregue, o status é `atendida`.
- Autorização reserva integralmente o solicitado e não baixa físico.
- Separação para retirada muda o status para `pronta_para_retirada`, mantém reserva e não baixa físico.
- Atendimento baixa físico somente do entregue e consome/libera reserva.
- Cancelamento de autorizada libera reserva e não altera físico.
- Devolução aumenta físico e não altera status.
- Estorno preserva histórico e registra movimentação inversa.
- Entregue líquida de um item = quantidade entregue − Σ devoluções − Σ estornos do item; derivada das `MovimentacaoEstoque`, nunca armazenada; calculada dentro da transação do service com a `Requisicao` travada (ADR-0005).
- Devolução (TR-020) e estorno (TR-021) operam apenas quantidade > 0 e <= entregue líquida atual do item; estorno total reverte a entregue líquida atual, não a quantidade entregue bruta — evita double-count com devoluções anteriores.
- Saldo disponível = saldo físico - saldo reservado, sempre recalculado no ponto crítico.
- Material divergente bloqueia novas requisições e autorizações até resolução.
- Material inativo não entra em nova requisição, mas permanece em histórico.
- Rascunho nunca enviado não consome número público; número público nasce apenas no primeiro envio e é preservado em reenvios, retorno para rascunho ou cancelamento lógico.
- Rascunho nunca enviado (`numero_publico` nulo) e rascunho retornado (`numero_publico` preenchido) são o mesmo estado `rascunho` e seguem as mesmas regras de edição; a distinção "nunca enviada" só governa descarte/exclusão (TR-003) versus cancelamento lógico (TR-004).

## 7. Ações bloqueadas por estado

| Estado | Bloqueios principais |
|---|---|
| Rascunho | Autorizar, separar, atender, devolver, estornar, baixar estoque. |
| Aguardando autorização | Editar itens diretamente, autorizar parcialmente, separar, atender, devolver, estornar, cancelar como autorizada. |
| Recusada | Autorizar, separar, atender, devolver, estornar, cancelar, editar e reenviar; estado final, retomada apenas por cópia. |
| Autorizada | Editar, reenviar, autorizar novamente, devolver antes de atendimento, estornar antes de atendimento. |
| Pronta para retirada | Editar, reenviar, autorizar novamente, devolver antes de atendimento, estornar antes de atendimento. |
| Atendida | Editar, reenviar, autorizar, separar, atender novamente, cancelar. |
| Cancelada | Editar, reenviar, autorizar, separar, atender, devolver, estornar. |
| Estornada | Corrigir, reenviar, autorizar, separar, atender, cancelar, registrar nova devolução operacional. |
