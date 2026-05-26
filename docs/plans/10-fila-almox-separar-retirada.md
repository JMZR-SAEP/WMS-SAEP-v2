# Plano: Fila do Almoxarifado — separar para retirada (#10)

## Scope

**Inclui:**

- Policy `pode_ver_fila_atendimento(ator)` + `exigir_pode_ver_fila_atendimento` em `apps/requisicoes/policies.py`, autorizando aux/chefe de almoxarifado e `superuser`.
- Policy `pode_separar_para_retirada(ator, requisicao)` + `exigir_pode_separar_para_retirada` em `apps/requisicoes/policies.py`, autorizando os mesmos papéis operacionais sobre requisições em estado `autorizada`.
- Selector `fila_atendimento(ator_id)` em `apps/requisicoes/selectors.py`, filtrando `estado__in=[autorizada, pronta_para_retirada]`, anotando `Count('itens')`, com ordenação determinística e visibilidade restrita ao almoxarifado (superuser sempre vê).
- Transição declarativa em `apps/requisicoes/transitions.py`: `autorizada -> pronta_para_retirada`.
- Service `separar_para_retirada(*, ator_id, requisicao_id)` em `apps/requisicoes/services.py`:
  - trava a `Requisicao` sob `select_for_update`;
  - revalida estado e permissão sob lock;
  - aplica `autorizada -> pronta_para_retirada` sem baixar saldo físico;
  - **não toca em reservas** (saldo segue reservado da autorização integral);
  - registra `TimelineRequisicao` com evento `separacao_retirada` e `estado_resultante=pronta_para_retirada`;
  - traduz problemas em exceções de domínio canônicas (`PermissaoNegada`, `EstadoInvalido`, `DadosInvalidos`).
- View `fila_atendimento_view` (GET) em `apps/requisicoes/views.py`, exigindo papel, com 403 quando não autorizado.
- View `separar_retirada_view` (POST) em `apps/requisicoes/views.py`, com PRG/HX-Redirect e tradução de `PermissaoNegada`, `EstadoInvalido` e `DadosInvalidos` em mensagens.
- URLs novas:
  - `requisicoes/atendimentos/` -> `fila_atendimento_view` (`name=atendimentos`).
  - `requisicoes/<int:pk>/separar-retirada/` -> `separar_retirada_view` (`name=separar_retirada`).
- Template novo `apps/requisicoes/templates/requisicoes/fila_atendimento.html`, espelhando o padrão visual de `fila_autorizacao.html` (lista mobile + tabela desktop, botão `Atender` que navega ao detalhe).
- Atualização de `detalhe.html`:
  - bloco de ações de retirada visível quando `pode_separar_retirada` é verdadeiro;
  - botão POST direto `Separar para retirada` com `data-confirm-message`.
- Flag `pode_separar_retirada` em `_detalhe_context`.
- Atualização de `_topbar_nav.html` para incluir link `Atendimento` para almoxarifado/superuser (alinhado ao brief de telas operacionais).
- Testes por camada (ADR-0010):
  - `test_policies.py`: visibilidade da fila e permissão de separação, papel correto e negação.
  - `test_selectors.py`: composição da fila por papel (almox, chefe-almox, superuser, chefe-setor negado, usuário inativo), inclui `autorizada` e `pronta_para_retirada`, exclui demais estados.
  - `test_services.py`: caminho feliz, permissão negada, estado de origem inválido, requisição inexistente, ator inexistente, mantém reserva e saldo físico, registra timeline com `estado_resultante`.
  - `test_views.py`: GET da fila por papel (200/403), POST feliz com PRG/HX-Redirect e mensagem com número público, contrato HTTP (405 em GET), botão visível no detalhe.

**Não inclui:**

- Tela de atendimento (`/requisicoes/<pk>/atender/`) e baixa física de saldo.
- Cancelamento, devolução, estorno.
- Filtros, paginação ou polling nas filas.
- Mudanças de schema/model.
- Modal global de confirmação.

## Files Touched

| Arquivo | Operação |
|---|---|
| `apps/requisicoes/transitions.py` | Declarar `autorizada -> pronta_para_retirada` |
| `apps/requisicoes/policies.py` | Adicionar `pode_ver_fila_atendimento`/`exigir_*` e `pode_separar_para_retirada`/`exigir_*` |
| `apps/requisicoes/selectors.py` | Adicionar `fila_atendimento(ator_id)` |
| `apps/requisicoes/services.py` | Adicionar `separar_para_retirada(*, ator_id, requisicao_id)` |
| `apps/requisicoes/views.py` | Adicionar `fila_atendimento_view`, `separar_retirada_view`; expor `pode_separar_retirada` em `_detalhe_context` |
| `apps/requisicoes/urls.py` | Rotas `atendimentos/` e `<int:pk>/separar-retirada/` |
| `apps/requisicoes/templates/requisicoes/fila_atendimento.html` | Template novo da fila |
| `apps/requisicoes/templates/requisicoes/detalhe.html` | Bloco da ação `Separar para retirada` |
| `apps/requisicoes/templates/requisicoes/_topbar_nav.html` | Link `Atendimento` para almoxarifado/superuser |
| `apps/requisicoes/tests/test_policies.py` | Permissão da fila e da separação |
| `apps/requisicoes/tests/test_selectors.py` | Composição da fila de atendimento |
| `apps/requisicoes/tests/test_services.py` | Caminho feliz, falhas, timeline, idempotência da reserva |
| `apps/requisicoes/tests/test_views.py` | GET da fila por papel, POST e detalhe |

## UX Direction

Direção: **Pragmatic Minimal / Accessible & Ethical**. Reusa o padrão visual já estabelecido pelas telas operacionais.

Regras aplicadas:

- Fila de atendimento é triagem; única ação por linha é `Atender`, navegando ao detalhe.
- No detalhe, ação primária para `autorizada` no papel de almoxarifado é `Separar para retirada` — POST direto com `data-confirm-message`, sem modal e sem input extra.
- Sucesso/erro retornam via mensagens padrão com `HX-Redirect` para o detalhe.
- Mantém contraste e foco já usados nos demais blocos do detalhe.

## Implementation Order

1. RED `policies` + `transitions` + `selectors`: novas permissões, transição declarativa e composição da fila.
2. RED `services.separar_para_retirada`: feliz, permissão negada, estado origem inválido, requisição/ator inexistentes; verificar manutenção da reserva e saldo físico.
3. GREEN service: implementação atômica com `select_for_update` e timeline.
4. RED `views`/`urls`/`templates`: GET da fila por papel, POST do detalhe, botão visível, contrato HTTP.
5. GREEN views/templates/topbar.
6. Revisão a11y/UX da fila e do botão do detalhe.
7. `rtk make test`.

## Test Strategy

### Policies

- `pode_ver_fila_atendimento` é `True` para aux/chefe de almoxarifado ativo, `False` para chefe/aux de setor comum, `False` para inativos, `True` para superuser.
- `pode_separar_para_retirada` é `True` para aux/chefe almox quando a requisição está `autorizada`, `False` para os demais papéis e `False` em qualquer outro estado de origem.
- `exigir_*` propagam mensagens de `PermissaoNegada` com `code` previsível.

### Selectors

- `fila_atendimento` inclui requisições `autorizada` e `pronta_para_retirada`, exclui demais estados.
- Aux/chefe almox vê fila completa; chefe de setor comum e solicitante recebem queryset vazio.
- Superuser vê todas as requisições elegíveis.
- Usuário inativo recebe queryset vazio.
- Ordenação determinística por `atualizado_em, criado_em, id`.

### Services

- Caminho feliz: aux ou chefe almox executa `autorizada -> pronta_para_retirada`, sem alterar saldo físico, sem alterar `saldo_reservado`, com timeline `separacao_retirada` e `estado_resultante=pronta_para_retirada`.
- Permissão negada para chefe de setor comum, solicitante ou usuário inativo.
- Estado origem inválido: `rascunho`, `aguardando_autorizacao`, `pronta_para_retirada`, `recusada`, `cancelada`, `atendida`, `estornada` levantam `EstadoInvalido` com `code='estado_origem_invalido'`.
- Ator/requisição inexistentes levantam `DadosInvalidos` com `code` específico.
- Transition validation: garantir que `verificar_transicao_valida` aceita `autorizada -> pronta_para_retirada` e rejeita demais destinos.

### Views

- GET `/requisicoes/atendimentos/` autenticado: 200 para almox/superuser, 403 para demais papéis, 302 quando anônimo.
- POST `/requisicoes/<pk>/separar-retirada/` autenticado e autorizado: 302 PRG, mensagem `success` contendo `numero_publico`, requisição passa a `pronta_para_retirada`.
- POST com `HX-Request` retorna `HX-Redirect` para o detalhe.
- GET no endpoint de POST retorna 405.
- Botão `Separar para retirada` aparece no detalhe somente quando `pode_separar_retirada` é verdadeiro.

## Invariants

Pontos relevantes do `docs/matriz-invariantes.md`:

- **EST-02**: separar para retirada **não** baixa saldo físico nem altera `saldo_reservado`; o teste deve assertir ambos.
- **EST-06**: operações críticas usam transação e lock; transição precisa estar declarada em `TRANSICOES_VALIDAS` antes de qualquer efeito.
- **PER-08**: views e services chamam a mesma policy contextual; visibilidade segue o selector único `requisicoes_visiveis_para`.
- **REQ-08**: toda transição registra evento de timeline com ator real, estado resultante e metadata vazio quando não há dados extras.

## Risks

- **Concorrência**: dois almoxarifados separando a mesma requisição simultaneamente — mitigado por `select_for_update` e revalidação de estado sob lock.
- **OpenAPI/contrato HTTP**: nenhuma mudança em endpoints JSON; rotas novas seguem o padrão PRG/HTMX existente.
- **Reservas**: ação não toca em estoque; risco de regressão se alguém alterar o helper de reserva em paralelo. Mitigação: teste asserta `saldo_fisico` e `saldo_reservado` imutáveis antes/depois.
- **Redirect pós-login**: fora desta slice (próxima issue). Mantemos apenas a navegação por topbar para acessar a fila.

## Open Questions

- Nenhuma. Brief, IA e ADRs cobrem o escopo dessa slice.
