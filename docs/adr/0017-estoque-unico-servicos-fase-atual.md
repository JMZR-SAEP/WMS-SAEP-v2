# ADR-0017 — Estoque único nos services de estoque (fase atual)

## Status

Aceita

## Contexto

O model `Estoque` (`apps/estoque/models.py`) admite múltiplos registros e seu
docstring declara que "o schema admite estoques futuros (por exemplo, por
equipe) sem alteração estrutural". O schema, portanto, está deliberadamente
aberto a multi-estoque.

Os services de estoque, porém, localizam saldo apenas por `material_id`, sem
qualquer `estoque_id`. Ver `reservar_saldos_para_autorizacao`,
`liberar_reservas_para_cancelamento`,
`consumir_e_liberar_reservas_para_atendimento`, `registrar_devolucao_estoque`,
`estornar_requisicao_estoque` (`apps/estoque/services.py`) e
`separar_para_retirada` (`apps/requisicoes/services/atendimento.py`). Todos
tratam "mais de um `SaldoEstoque` para o mesmo material" como erro
(`saldo_ambiguo` / `separacao_bloqueada`).

Não existe conceito de roteamento requisição→estoque: `Requisicao` e
`ItemRequisicao` não referenciam `Estoque`, e `OrigemMovimentacaoEstoque`
aponta só para `requisicao_id`/`saida_excepcional_id`. A escolha do estoque em
`confirmar_importacao_scpi_view` é feita por `Estoque.objects.filter(ativo=True)
.first()`.

Consequência: criar um segundo `Estoque` com saldo para um material já usado
quebra **globalmente** autorização, separação, atendimento e cancelamento de
qualquer setor, com uma mensagem que não indica a causa. O schema aberto
convida o próximo desenvolvedor a criar um segundo estoque assumindo que
funciona — e ele não funciona.

## Decisão

Nesta fase, os services de estoque assumem **um único `Estoque` ativo**. Essa
suposição é intencional e é a razão de o schema aberto não estar acompanhado de
lógica multi-estoque.

Enquanto vigorar:

1. Existe exatamente um `Estoque` ativo. A criação de um segundo é barrada no
   admin (`EstoqueAdmin.has_add_permission`) e conferida por checklist de
   go-live; uma query de detecção
   (`GROUP BY material_id HAVING count(*) > 1` em `SaldoEstoque`) evidencia
   violação.
2. Não se adota `UniqueConstraint`/`CheckConstraint` de estoque único no banco,
   justamente para não cimentar como invariante permanente o que é limitação de
   fase — o alvo futuro é multi-estoque.

Habilitar multi-estoque, no futuro, exige (nova ADR):

- um conceito explícito de roteamento requisição→estoque (qual estoque atende
  qual requisição/beneficiário);
- escopo por `estoque_id` em todos os selectors e services de saldo, removendo
  o tratamento de multiplicidade como erro.

## Consequências

O schema de `Estoque` permanece aberto a múltiplos registros, mas nenhum
caminho de código suporta mais de um estoque ativo nesta fase.

A proteção contra um segundo estoque vive no admin e no processo (checklist +
detecção), não no banco — cobre o caminho acidental via interface; a criação
por shell/seed permanece responsabilidade do operador.

O ledger de bootstrap da importação SCPI (ADR-0015, LED-01) continua fora do
razão nesta fase, independentemente desta decisão.

## Trade-off

Aceita-se uma proteção não-hermética (admin + processo, sem constraint de
banco) em troca de manter o schema pronto para a evolução multi-estoque
declarada no domínio. A alternativa — constraint de banco — fecharia todos os
caminhos, inclusive shell, mas exigiria removê-la e migrar quando multi-estoque
chegasse, além de contradizer a intenção registrada no próprio model.
