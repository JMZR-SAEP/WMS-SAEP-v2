# Plano — Issue #56: `acoes_disponiveis(papel, requisicao) -> frozenset[Operacao]`

Ref: ADR-0011 (Emenda 2026-06-26, seção "Transições keyed por operação"), CONTEXT.md ("Ações disponíveis").

## Scope

**O que muda:**
- Novo selector `acoes_disponiveis(papel: PapelEfetivo, requisicao: Requisicao) -> frozenset[Operacao]` em `apps/requisicoes/selectors.py`. Composição em duas etapas, na ordem definida pelo ADR: primeiro filtra por `TRANSICOES[operacao].estados_origem` (estado atual permite a operação?), depois pela policy correspondente (`pode_<operacao>(papel, requisicao)`).
- `_detalhe_context` (`apps/requisicoes/views.py`) passa a projetar as flags `pode_enviar`, `pode_editar`, `pode_retornar`, `pode_autorizar`, `pode_recusar`, `pode_separar_retirada`, `pode_atender_retirada`, `pode_cancelar`, `pode_devolver`, `pode_estornar` a partir de `Operacao.X in acoes_disponiveis(papel, requisicao)`, chamado uma única vez no topo da função. Isso remove as 10 condicionais `requisicao.estado == X and pode_Y(papel, requisicao)` duplicadas (shadow do grafo de `transitions.py`).
- Nenhuma mudança de assinatura em `policies.py` ou `transitions.py` — o selector só compõe o que já existe.

**O que NÃO muda (fora de escopo):**
- `pode_copiar` continua como está hoje (`requisicao.estado in {ATENDIDA, RECUSADA} and pode_copiar_requisicao(...)`). Cópia cria uma **nova** requisição (rascunho) — não é uma transição do registro atual e não tem `Operacao` correspondente em `TRANSICOES`. CONTEXT.md define "Ações disponíveis" como o conjunto de Operações executáveis **sobre a Requisição no estado atual**; copiar não se encaixa nessa definição. O ADR/issue citam "~11 flags" de forma aproximada — as 10 que mapeiam 1:1 para `Operacao` são as substituídas.
- Nenhum novo membro em `Operacao`, nenhuma nova entrada em `TRANSICOES`.
- Nenhuma mudança de template/HTML — os nomes das chaves do contexto (`pode_enviar`, etc.) permanecem idênticos, só a fonte do valor muda.
- Nenhuma mudança em CONTEXT.md/ADR — a emenda 2026-06-26 já documenta o contrato-alvo; este PR só implementa.

## Files touched

- `apps/requisicoes/selectors.py` — adiciona `acoes_disponiveis` + mapa privado `Operacao -> policy_fn`.
- `apps/requisicoes/views.py` — `_detalhe_context` passa a usar o selector.
- `apps/requisicoes/tests/test_selectors.py` — testes diretos do selector, papel × estado, sem HTTP (adicionados ao módulo existente, não em arquivo novo).
- `docs/plans/56-acoes-disponiveis-selector.md` — este plano.

## Test strategy

Testes diretos do selector adicionados a `apps/requisicoes/tests/test_selectors.py` (módulo existente, sem fragmentar a suíte), chamando `acoes_disponiveis` diretamente e comparando o `frozenset[Operacao]` retornado. Segue o padrão puro (sem DB) de `test_policies.py`: `PapelEfetivo` construído diretamente, `Requisicao` como `SimpleNamespace`/instância não persistida com `estado` setado.

Matriz por operação (cobre as 10 operações de `TRANSICOES`):
1. Estado correto + papel autorizado → `Operacao.X` presente no frozenset.
2. Estado correto + papel **não** autorizado → `Operacao.X` ausente.
3. Estado incorreto (fora de `estados_origem`) + papel autorizado → `Operacao.X` ausente (tabela vence antes mesmo de avaliar a policy).
4. Ao menos um caso de `CANCELAR` com múltiplos `estados_origem` (rascunho, aguardando autorização, autorizada, pronta para retirada) confirmando que todos entram no conjunto quando autorizado.
5. Retorno é sempre `frozenset` (imutabilidade), nunca lista/dict.
6. Papel inativo (`ativo=False`) → conjunto vazio (todas as policies negam ator inativo).

Não duplica a matriz completa de autorização já coberta em `test_policies.py` — cada caso aqui cobre só a composição estado+policy, reaproveitando os cenários mínimos que já existem por policy.

## Invariants

- Nenhuma alteração ao grafo de estados (`docs/estado-transicoes-requisicao.md`) — o selector só lê `TRANSICOES`, não modifica.
- `acoes_disponiveis` não faz IO (sem query) — recebe `Requisicao` já carregada e `PapelEfetivo` já resolvido, mantendo o contrato "papel resolvido uma vez pelo chamador" (ADR-0011 emenda).
- A tabela nunca codifica autorização (regra explícita do ADR) — o selector só combina, nunca embute lógica de papel dentro de `transitions.py`.

## Risks

- Baixo risco de regressão comportamental: cada flag proietada preserva exatamente a mesma condição (`estado==X and policy(...)`) já validada por `test_views.py`/`test_policies.py`; a suíte completa roda ao final para confirmar equivalência.
- Risco de escopo: interpretação de "11 flags" vs. 10 `Operacao` — documentado acima e sinalizado explicitamente para revisão do CodeRabbit/usuário antes de avançar para implementação.
- Sem mudança de schema/migration — não aplica reset de ambiente.
