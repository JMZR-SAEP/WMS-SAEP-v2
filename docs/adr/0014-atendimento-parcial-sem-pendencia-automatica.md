# ADR-0014 — Atendimento parcial encerra a requisição sem pendência automática

## Status

Aceita

## Contexto

Uma requisição pode ser atendida parcialmente: o Almoxarifado entrega quantidade menor que a autorizada em um ou mais itens (TR-017). Surgiu a questão de como o ciclo de vida da requisição deve se comportar após uma entrega parcial.

As alternativas consideradas foram:

1. **Criar estado `atendida_parcialmente` ou `pendente_entrega`** — a requisição permaneceria "aberta" enquanto houvesse saldo autorizado e não entregue.
2. **Gerar automaticamente requisição complementar** — ao registrar entrega parcial, o sistema criaria nova requisição para o saldo não entregue.
3. **Exigir decisão manual no momento da entrega** — o Almoxarifado escolheria entre "encerrar" ou "manter pendente" antes de confirmar o atendimento parcial.
4. **Encerrar como `atendida`, sem pendência automática** — a requisição original é finalizada; qualquer complementação é iniciativa explícita do setor beneficiário.

## Decisão

Uma requisição parcialmente entregue é encerrada no estado `atendida`.

O sistema não cria estado separado para atendimento parcial e não mantém pendência operacional automática para o saldo não entregue. Também não gera automaticamente requisição complementar.

A diferença entre `quantidade_autorizada` e `quantidade_entregue` permanece registrada nos itens da requisição e pode ser consultada para relatórios ou usada como base para cópia manual (REQ-09). Caso o setor ainda precise do saldo não entregue, deve iniciar nova requisição explicitamente.

## Alternativas rejeitadas

**Estado `atendida_parcialmente` ou `pendente_entrega`:** aumentaria a complexidade da máquina de estados, filtros, permissões, telas e relatórios. Exigiria definir quem resolve a pendência, quando ela expira, se há múltiplas entregas e como o Almoxarifado prioriza complementações. O nome `pendente_entrega` sugere obrigação ativa do Almoxarifado mesmo quando a falta decorre de indisponibilidade real de estoque.

**Requisição complementar automática:** transforma falta de saldo em nova demanda sem manifestação explícita do setor. Pode gerar acúmulo de pendências e requisições que não façam mais sentido após a entrega parcial.

**Decisão manual no momento da entrega:** aumenta fricção operacional e complexidade do fluxo. O Almoxarifado já registra justificativa por item para qualquer entrega menor que autorizada; exigir decisão adicional sobre o destino da pendência é redundante.

## Consequências

- `atendida` pode representar atendimento total ou parcial. O grau de atendimento é inferido pelos campos dos itens (`quantidade_autorizada` vs. `quantidade_entregue`), nunca pelo estado.
- Relatórios que precisem distinguir total de parcial calculam a diferença por item, não por estado da requisição.
- Não há SLA ou prazo automático para saldo não entregue.
- O setor beneficiário deve solicitar complemento explicitamente, podendo usar cópia (REQ-09) quando disponível.
- A timeline da requisição registra claramente se o atendimento foi total (`atendimento_total`) ou parcial (`atendimento_parcial`), com justificativa por item entregue abaixo do autorizado.

## Trade-off

A decisão simplifica a máquina de estados e elimina a complexidade de fluxos de complementação automática. Em troca, a responsabilidade de iniciar complementação recai sobre o setor beneficiário, que precisa perceber que recebeu menos do que pediu e criar nova requisição. Aceita-se essa transferência de responsabilidade em favor da simplicidade operacional e da previsibilidade do ciclo de vida da requisição.
