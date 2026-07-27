# Plano — Envio exige setor beneficiário com autorizador (#103)

## Escopo

Impedir que uma requisição entre em `aguardando_autorizacao` quando o
`setor_beneficiario` não tem chefe capaz de autorizá-la. Hoje o envio é aceito,
o número público é emitido e a requisição fica presa: `fila_autorizacao` sai
vazia para todos e `autorizar_requisicao` levanta `PermissaoNegada` para
qualquer ator.

**Muda:**

- `apps/requisicoes/services/ciclo_vida.py` — `enviar_para_autorizacao` ganha um
  guard antes da emissão do número público: setor beneficiário sem chefe ativo
  levanta `ConflitoDominio(code='setor_sem_autorizador')`.
- `apps/requisicoes/views.py` — `enviar_rascunho_view` e `nova_requisicao`
  passam a capturar `ConflitoDominio`. Sem isso o guard vira HTTP 500 nas duas
  telas que chamam o serviço.
- `apps/requisicoes/tests/test_services.py` — testes do guard + ajuste das
  fixtures/testes de envio que hoje dependem de um setor sem chefe.
- `apps/requisicoes/tests/test_composites.py` — cobertura da herança do guard
  por `criar_e_enviar_requisicao` (nada persistido) + ajuste de fixtures.
- `apps/requisicoes/tests/test_views.py` — cobertura da tradução HTTP do novo
  erro + ajuste dos testes de envio existentes.
- `docs/estado-transicoes-requisicao.md` — linha TR-005 passa a registrar a
  pré-condição "setor do beneficiário com chefe ativo".

**Não muda:**

- `apps/accounts/models.py` — `Setor.chefe` continua `null=True`. A decisão do
  grill é explícita: "setor sempre tem chefe" é impossível no bootstrap
  (criar setor exige um chefe que ainda não existe). Sem mudança de schema →
  **sem migration nova**.
- `apps/requisicoes/policies.py` — `pode_enviar_rascunho` não muda. O guard é
  regra de estado do agregado (o setor destino consegue receber autorização?),
  não de permissão do ator; ADR-0011 põe isso em service, e o issue diz
  "Camada: service".
- `apps/requisicoes/policies.py` — `pode_recusar_requisicao` /
  `pode_autorizar_requisicao` não mudam. O bug é o envio aceitar o que ninguém
  pode despachar, não a policy de autorização estar errada.
- `apps/accounts/papeis.py` — `papel_efetivo` não muda; o guard consulta o setor
  diretamente, não o papel de um ator.
- Cadastro de setor (admin, services de accounts) — nenhum guard novo lá; o
  grill descartou explicitamente essa alternativa.
- Requisições já presas em produção/piloto — nada de data migration nem de
  varredura. As saídas já existem e são acionáveis por criador/beneficiário:
  TR-006 (retornar para rascunho) e TR-012 (cancelar). Fora do escopo do issue.
- Desativação de setor/chefe com requisições já em `aguardando_autorizacao` —
  vetor conhecido, endereçado por checklist operacional e comunicação, não por
  código. O guard só cobre o instante do envio.
- `docs/matriz-invariantes.md` — USR-04 já descreve o invariante e aponta o
  backlog ACE-002. O guard **não** implementa USR-04 (não impede setor ativo sem
  chefe de existir); só impede que essa situação prenda uma requisição. A linha
  continua válida como está.

## Arquivos alterados

| Arquivo | Ação |
|---|---|
| `apps/requisicoes/services/ciclo_vida.py` | Guard em `enviar_para_autorizacao`, após a validação de itens e antes da emissão do número |
| `apps/requisicoes/views.py` | `except ConflitoDominio` em `enviar_rascunho_view` e em `nova_requisicao` |
| `apps/requisicoes/tests/test_services.py` | 3 testes novos; fixture `rascunho` e testes de envio passam a exigir chefe ativo |
| `apps/requisicoes/tests/test_composites.py` | 1 teste novo (guard + rollback total); fixtures ajustadas |
| `apps/requisicoes/tests/test_views.py` | 2 testes novos (tradução HTTP nas duas telas); testes de envio ajustados |
| `docs/estado-transicoes-requisicao.md` | Pré-condição de TR-005 |

## Implementação

### Guard no service

Posição dentro de `enviar_para_autorizacao` (hoje `ciclo_vida.py:319`), logo
após `_validar_itens(itens_envio)` e imediatamente antes do bloco
`if requisicao.numero_publico is None:`:

```python
tem_autorizador = Setor.objects.filter(
    pk=requisicao.setor_beneficiario_id,
    ativo=True,
    chefe__is_active=True,
).exists()
if not tem_autorizador:
    raise ConflitoDominio(
        f'O setor {requisicao.setor_beneficiario.nome} não tem chefe ativo '
        'para autorizar a requisição. Procure o suporte antes de enviar.',
        code='setor_sem_autorizador',
    )
```

Quatro decisões que o código embute:

1. **Uma única query `EXISTS` no caminho feliz.** O nome do setor só é
   carregado quando o guard falha (o acesso a `requisicao.setor_beneficiario`
   está dentro do `raise`). Não se usa `select_related` no `select_for_update()`
   da linha 339 de propósito: em PostgreSQL, `select_for_update` com
   `select_related` também trava as linhas de `Setor` e `User` juntadas, e não
   há motivo para bloquear cadastro por causa de um envio.
2. **Três causas, um código.** `ativo=True` e `chefe__is_active=True` cobrem os
   três cenários do issue — setor sem chefe, chefe desativado, setor desativado.
   Todos produzem exatamente o mesmo sintoma (`setor_chefiado_ativo_id is None`
   em `papel_efetivo`, `apps/accounts/papeis.py:45-50`) e a mesma ação do
   usuário (procurar o suporte), então distinguir códigos ou mensagens não daria
   ao solicitante nenhuma decisão diferente. A mensagem é redigida para valer nos
   três: "não tem chefe ativo", não "não tem chefe cadastrado".
3. **Depois da validação de itens.** Preserva a precedência de erros já coberta
   por testes: ator inexistente e requisição inexistente (`DadosInvalidos`),
   permissão (`PermissaoNegada`), transição (`EstadoInvalido`) e itens
   (`DadosInvalidos`) continuam ganhando do guard. Antes da emissão do número
   porque o critério de aceite é justamente não consumir a sequência anual num
   envio que vai ficar preso.
4. **`ConflitoDominio`, não `DadosInvalidos`.** Os dados enviados estão
   corretos; o que está errado é o estado do cadastro no momento do envio —
   definição literal de `ConflitoDominio` em `apps/core/exceptions.py:45`.
   Também é o que o issue pede.

`ciclo_vida.py` hoje importa `DadosInvalidos` e `EstadoInvalido` de
`apps.core.exceptions` e, de `apps.accounts.models`, só `User`. O guard exige
acrescentar **dois** imports: `ConflitoDominio` e `Setor`.

### Herança pelo composto

`criar_e_enviar_requisicao` (`apps/requisicoes/services/composites.py:18`)
delega para `enviar_para_autorizacao` dentro de um `transaction.atomic()`
próprio, então o guard já é herdado sem nenhuma alteração de código: a exceção
propaga e o `criar_requisicao` da mesma transação é revertido. O critério de
aceite "nada é persistido no fluxo composto" é **verificado por teste**, não
implementado.

### Tradução HTTP

Duas views chamam os serviços afetados e nenhuma das duas captura
`ConflitoDominio` hoje — o guard viraria 500 em ambas:

- `enviar_rascunho_view` (`views.py:784`) — acrescenta
  `except ConflitoDominio` com `messages.warning` + `htmx_redirect` para o
  detalhe, exatamente o mesmo bloco já usado em `views.py:596`, `740` e `903`.
  O padrão PRG + `HX-Redirect` e o nível `warning` para conflito de estado são o
  contrato de mensagens já vigente.
- `nova_requisicao` (`views.py:230`, ramo `acao == 'enviar'`) — acrescenta
  `except ConflitoDominio` com `messages.warning`; o fluxo cai no `render` que
  já existe e devolve o formulário preenchido, sem perder o que o usuário
  digitou.

## Estratégia de testes

### Impacto nas fixtures existentes

`setor_obras` (`apps/requisicoes/tests/conftest.py:20`) é criado **sem chefe**;
só a fixture `chefe_obras` (`conftest.py:80`) atribui um. Todo teste que hoje
envia uma requisição de `setor_obras` sem pedir `chefe_obras` passa a bater no
guard. Isso é sinal correto, não dano colateral: o cenário do issue é
exatamente esse.

Correção: a fixture local `rascunho` (`test_services.py:256`) passa a depender
de `chefe_obras`, o que cobre de uma vez os testes de envio que a usam
(`test_services.py:390, 439, 456, 480, 492, 502, 512`). Os testes que montam a
requisição na mão pedem `chefe_obras` explicitamente:

| Arquivo | Testes a ajustar |
|---|---|
| `test_services.py` | `test_enviar_sequencia_anual_incrementa` (404), fixture `requisicao_aguardando` (866), `test_retornar_para_rascunho_restaura_visibilidade_creator_only` (903) |
| `test_composites.py` | `test_criar_e_enviar_requisicao_cria_e_envia_em_uma_chamada` (24), `test_criar_e_enviar_requisicao_rollback_total_se_envio_falhar` (46) |
| `test_views.py` | `test_nova_requisicao_post_acao_enviar_cria_e_envia` (138), `test_enviar_rascunho_post_criador_redireciona_detalhe` (899), `test_enviar_rascunho_htmx_retorna_hx_redirect` (958) |

A lista acima é o levantamento estático; a suíte completa é a autoridade final e
qualquer outro teste que quebrar entra no mesmo ajuste. Três casos **não**
precisam de chefe e ficam como estão, porque falham antes do guard:
`test_enviar_sem_itens_levanta_dados_invalidos` (466, `DadosInvalidos` na
validação de itens), `test_enviar_por_terceiro_levanta_permissao_negada` (492,
`PermissaoNegada` na policy) e
`test_enviar_rascunho_post_estado_invalido_mostra_warning`
(`test_views.py:924`, `EstadoInvalido` na verificação de transição) — eles
passam a documentar a precedência da decisão 3. Também não mudam:
`test_tr015b_bloqueia_quando_um_item_diverge_em_req_multi_item`
(`test_services.py:1505`), a fixture `requisicao_pronta_retirada_multi`
(`test_services.py:1576`) e os quatro testes de
`apps/notificacoes/tests/test_services.py` — todos já pedem `chefe_obras`.

Nenhum ajuste enfraquece asserção existente: só acrescenta pré-condição de
cadastro que o domínio agora exige.

### Casos novos

Camada de service, em `test_services.py`, na seção TR-005:

| # | Caso | Setup | Esperado |
|---|---|---|---|
| 1 | Setor sem chefe | `setor_obras` sem `chefe_obras`, rascunho com item | `ConflitoDominio`, `code == 'setor_sem_autorizador'`; estado segue `RASCUNHO`, `numero_publico is None`, `SequenciaRequisicao` não incrementada, sem evento de timeline |
| 2 | Setor com chefe inativo | `chefe_obras` com `is_active=False` | idem caso 1 |
| 3 | Setor inativo com chefe ativo | `setor_obras.ativo=False`, `chefe_obras` ativo | idem caso 1 — cobre a decisão 2 |
| 4 | Setor com chefe ativo | `chefe_obras` | envio bem-sucedido; `numero_publico` emitido (caminho feliz, já coberto pelos testes existentes após o ajuste de fixture) |

Casos 1, 2 e 4 são o critério de aceite literal do issue. O caso 3 protege a
decisão 2, que um refactor ingênuo (`chefe_id__isnull=False` sem `ativo=True`)
desfaria silenciosamente. A asserção de sequência não consumida é o que
diferencia "recusou" de "recusou sem estragar nada" — é o dano real do bug.

Camada de composto, em `test_composites.py`:

| # | Caso | Esperado |
|---|---|---|
| 5 | `criar_e_enviar_requisicao` com setor sem chefe | `ConflitoDominio`; `Requisicao.objects.count() == 0` e `TimelineRequisicao.objects.count() == 0` — rollback total, critério de aceite explícito |

Camada de view, em `test_views.py` (contrato de tradução HTTP):

| # | Caso | Esperado |
|---|---|---|
| 6 | POST em `requisicoes:enviar_rascunho` com setor sem chefe | 302 para o detalhe (204 + `HX-Redirect` sob HTMX), `messages.WARNING`, não 500 |
| 7 | POST em `requisicoes:nova_requisicao` com `acao='enviar'` e setor sem chefe | 200 re-renderizando o formulário, `messages.WARNING`, nenhuma `Requisicao` criada |

Não coberto, e por quê: comportamento de `fila_autorizacao` (nada muda nela);
recuperação de requisições já presas (TR-006/TR-012 já têm cobertura própria);
desativação de setor após o envio (fora do escopo, é o vetor deixado para
processo).

## Invariantes

| ID | Relação com esta mudança |
|---|---|
| USR-04 | "Todo setor operacional ativo possui um chefe ativo." O guard **não** implementa o invariante — continua sendo possível existir setor ativo sem chefe (bootstrap). O que muda é a consequência: a violação deixa de produzir requisição presa e passa a produzir recusa explícita no envio. A linha da matriz (backlog ACE-002) permanece aberta e correta. |
| USR-06 | "Setor inativo não recebe nova requisição." O filtro `ativo=True` do guard reforça o invariante no ponto do envio. Nenhuma reescrita necessária. |
| REQ-03 / REQ-04 / REQ-05 | Numeração pública e preservação em reenvio. O guard roda **antes** da emissão, então nenhum número é consumido por envio recusado; reenvio de rascunho retornado com setor já regularizado continua preservando o número (REQ-04). Sem mudança de definição. |
| EST-02 | Envio não reserva nem baixa estoque. O guard não toca estoque; permanece verdadeiro por construção. |
| PER-* | Nenhuma policy muda. Um superusuário continua podendo autorizar (`pode_recusar_requisicao` tem bypass para `eh_superusuario`), mas o envio será recusado mesmo assim — ver "Riscos". |

## Riscos

| Risco | Avaliação |
|---|---|
| Superusuário poderia autorizar, mas o envio é bloqueado | Real e aceito. `pode_recusar_requisicao` (`policies.py:293`) libera superusuário antes de olhar `setor_chefiado_ativo_id`, então tecnicamente existiria um autorizador. Bloquear mesmo assim é deliberado: superusuário é escape técnico, não autorizador operacional, e depender dele deixaria a requisição fora do fluxo de chefia que a autorização representa. Registrar no PR. |
| Quebra em massa de testes existentes | Esperada e mapeada acima. Todas as quebras são "cenário do issue exercitado sem querer"; o ajuste é acrescentar `chefe_obras` às fixtures, nunca afrouxar asserção. |
| Bloqueio de operação real no piloto | É o objetivo declarado do issue: falhar cedo com mensagem acionável em vez de falhar silenciosamente depois. A mensagem nomeia o setor e diz o que fazer. |
| Requisições já em `aguardando_autorizacao` sem autorizador | Não são tocadas pelo guard. Saem por TR-006 ou TR-012, já implementadas e acessíveis ao criador/beneficiário. Sem data migration. |
| Corrida: chefe desativado entre o guard e o `save` | Janela existente e não fechada. `select_for_update` trava a requisição, não o setor nem o usuário; travar cadastro por causa de envio seria pior que o problema. Efeito de perder a corrida é o mesmo estado de hoje, recuperável por TR-006/TR-012. |
| Custo de query | Um `EXISTS` por envio, no caminho feliz; uma query extra só quando o envio é recusado. Irrelevante. |
| Contrato OpenAPI | Projeto é server-rendered sem camada REST (AGENTS.md). Não se aplica. |
| Migrations / schema | Nenhuma mudança de model. Nada a resetar, `make setup` não é necessário. |
| Máquina de estados | `transitions.py` não muda: TR-005 continua sendo `RASCUNHO → AGUARDANDO_AUTORIZACAO`. O guard é pré-condição de negócio, não aresta nova. |
