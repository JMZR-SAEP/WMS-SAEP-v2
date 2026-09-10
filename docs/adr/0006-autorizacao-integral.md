# ADR-0006 — Autorização de requisição é integral (tudo-ou-nada)

## Status

Aceita

## Contexto

A documentação continha uma contradição: `docs/estado-transicoes-requisicao.md` §6 mencionava o estado `atendida` "mesmo que solicitado > autorizado", enquanto ITEM-01, TR-008, TR-010 e a `matriz-permissoes.md` afirmam que a autorização é integral. O cenário `solicitado > autorizado` só existiria se houvesse autorização parcial por item — que as demais regras proíbem.

Havia duas saídas: permitir autorização parcial (o chefe aprova quantidade menor por item) ou fixar autorização integral.

## Decisão

A autorização de uma requisição é integral e tudo-ou-nada.

Após a autorização, `quantidade_autorizada` é igual a `quantidade_solicitada` para todos os itens. Antes da autorização, `quantidade_autorizada` permanece `null`.

Não existe autorização parcial por item nem autorização com quantidade zero. Se a requisição não pode ser autorizada integralmente — material inativo, divergência crítica, saldo insuficiente para reservar tudo — ela é recusada como um todo (TR-010 orienta a recusa inteira).

A parcialidade permitida no fluxo ocorre apenas no atendimento: `quantidade_entregue` pode ser menor que `quantidade_autorizada` ou igual a zero, sempre com justificativa por item.

A cláusula "mesmo que solicitado > autorizado" foi removida de `docs/estado-transicoes-requisicao.md` §6.

## Consequências

`quantidade_autorizada` só assume dois estados: `null` (não autorizada) ou igual a `quantidade_solicitada`.

O service de autorização não recebe quantidades por item; confirma `autorizada = solicitada` para todos os itens, ou a transição não ocorre.

O chefe não aprova "parte" de uma requisição. Um único item indisponível obriga a recusa inteira.

> **Substituído pela Emenda 2026-09-10 (issue #170).** "Recusar" deixou de encerrar
> a requisição — o criador não precisa recriar ou copiar nada; a requisição volta
> para rascunho e ele ajusta e reenvia a mesma. Ver a Emenda ao final desta ADR.

A divergência entre solicitado e entregue é resolvida apenas no atendimento, nunca na autorização.

## Trade-off

A autorização integral remove flexibilidade do chefe — ele não negocia item a item. Em troca: o fluxo não acumula itens parcialmente autorizados "pendentes", a reserva de estoque é sempre pelo total solicitado, e o estado da requisição fica simples (`autorizada` = tudo reservado). Aceita-se a rigidez em favor da simplicidade e da previsibilidade do estoque.

## Emenda — 2026-09-10 (issue #170)

O trecho original desta ADR descrevia a recusa como encerramento: "o beneficiário recria ou copia a requisição sem o item problemático". A decisão de domínio de 2026-09-10 (issue #170) mudou o modelo: "recusar" deixou de ser uma transição para um estado terminal (`recusada`, removido de `EstadoRequisicao`) e virou uma variante de "retornar para rascunho" (TR-006 absorve a antiga TR-011) — o chefe do setor do beneficiário devolve por decisão, com motivo obrigatório, e a requisição preserva o número público, voltando para rascunho editável e reenviável pelo criador.

TR-010 (esta ADR) continua valendo sem mudança: o chefe não autoriza parcialmente, e um único item indisponível obriga recusar/retornar a requisição inteira. Só o desfecho da recusa muda — não é mais preciso recriar nem copiar a requisição para tentar de novo sem o item problemático; o criador ajusta o rascunho existente e reenvia.

Ver `docs/estado-transicoes-requisicao.md` (TR-006/TR-011) e `docs/matriz-permissoes.md` para o detalhe atualizado da transição.
