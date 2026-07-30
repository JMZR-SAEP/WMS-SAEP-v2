# Plano — Notificar chefe quando requisição entra na fila de autorização (#108)

## Escopo

`enviar_para_autorizacao` (`apps/requisicoes/services/ciclo_vida.py:318`) é a única
transição do ciclo de vida que muda o estado da requisição **sem** emitir
notificação. `TipoNotificacao` (`apps/notificacoes/models.py:5`) tem quatro
membros — `AUTORIZACAO`, `RECUSA`, `ATENDIMENTO`, `DIVERGENCIA_ESTOQUE` — e
nenhum deles cobre "entrou na fila". O chefe do setor beneficiário só descobre
que há requisição aguardando abrindo `requisicoes:fila_autorizacao` por conta
própria. Achado R1 da auditoria do piloto.

Os três hooks de notificação existentes (`_notificar_pos_commit` em
`ciclo_vida.py:57` e em `atendimento.py:50`, e `_notificar_divergencia` em
`ciclo_vida.py:753`) roteiam para o par **criador/beneficiário**, que são campos
FK da própria `Requisicao`. O destinatário desta fatia é o **chefe ativo do setor
beneficiário** — que não é campo da requisição e precisa ser resolvido a partir
de `Setor`. Daí a única mudança de assinatura do issue.

**Muda:**

- `apps/notificacoes/models.py` — novo membro
  `ENVIO_AUTORIZACAO = 'envio_autorizacao', 'Envio para autorização'` em
  `TipoNotificacao`. O par valor/rótulo é contrato: o valor é o que fica
  persistido em `Notificacao.tipo`, e o rótulo é o texto exato que o teste 13
  procura no HTML da lista, já que o template usa `get_tipo_display` sem
  tradução própria. Especificação completa em §1.
- `apps/notificacoes/services.py` — novo service irmão
  `criar_notificacoes_para_destinatarios`; `criar_notificacoes_para` passa a
  delegar nele, mantendo a assinatura atual intacta.
- `apps/requisicoes/selectors.py` — novo selector
  `chefe_autorizador_do_setor`, ao lado de `fila_autorizacao`.
- `apps/requisicoes/services/ciclo_vida.py` — novo helper
  `_notificar_chefe_pos_commit`; `enviar_para_autorizacao` registra
  `transaction.on_commit`.
- `apps/requisicoes/tests/test_selectors.py` — casos do selector novo.
- `apps/notificacoes/tests/test_services.py` — casos de service e de hook.
- `apps/notificacoes/tests/test_views.py` — renderização do rótulo e do link.
- `docs/estado-transicoes-requisicao.md` — TR-005 passa a listar o efeito
  colateral de notificação, hoje ausente na descrição da transição.
- `docs/matriz-invariantes.md` — nova linha `NOT-01`, tema Notificações.

**Não muda:**

- `apps/notificacoes/templates/notificacoes/lista.html` — o template já renderiza
  `{{ notificacao.get_tipo_display }}` e já monta o link para
  `requisicoes:detalhe` a partir de `requisicao_id` (linhas 26 e 28-34). Um novo
  membro de `TextChoices` aparece na lista com rótulo PT-BR **sem edição de
  template**; o critério de aceite 5 é coberto por teste de view, não por
  mudança de arquivo. Editar o template aqui seria adicionar um `if` por tipo
  onde hoje há uma regra única.
- `criar_notificacoes_para` (comportamento e assinatura) — os três chamadores
  existentes continuam passando `criador_id`/`beneficiario_id`. Generalizar a
  assinatura in-place obrigaria a tocar em `ciclo_vida.py` (2 chamadas),
  `atendimento.py` (1 chamada) e nos testes que já a exercitam, sem ganho: o
  par criador/beneficiário continua sendo o roteamento certo para os outros
  quatro tipos.
- A guarda `setor_sem_autorizador` de `enviar_para_autorizacao` — continua
  levantando `ConflitoDominio` antes de emitir número. A notificação é efeito
  pós-commit, não pré-condição nova.
- `apps/notificacoes/policies.py` e `selectors.py` — `pode_ver_notificacao` e
  `notificacoes_com_numero_publico` operam sobre `destinatario_id` e
  `requisicao_id`, agnósticos ao `tipo`. Nada a ajustar.
- `fila_autorizacao` (comportamento) — a fila continua sendo a fonte de verdade
  de *quem autoriza*; a notificação apenas avisa. O selector novo entra no mesmo
  arquivo, mas não altera o corpo da fila. Ver Invariantes para o acoplamento
  entre as duas.
- Estoque, reservas, timeline — TR-005 não toca saldo (EST-02) e o
  `TimelineRequisicao` de `ENVIO_AUTORIZACAO` já existe e permanece igual.

## Arquivos alterados

| Arquivo | Ação |
|---|---|
| `apps/notificacoes/models.py` | Novo membro em `TipoNotificacao` |
| `apps/notificacoes/services.py` | Novo `criar_notificacoes_para_destinatarios`; `criar_notificacoes_para` delega |
| `apps/requisicoes/selectors.py` | Novo `chefe_autorizador_do_setor` |
| `apps/requisicoes/services/ciclo_vida.py` | Novo `_notificar_chefe_pos_commit`; `on_commit` em `enviar_para_autorizacao` |
| `apps/requisicoes/tests/test_selectors.py` | 4 casos do selector novo + equivalência com `fila_autorizacao` |
| `apps/notificacoes/tests/test_services.py` | 2 casos de service + 5 casos de hook |
| `apps/notificacoes/tests/test_views.py` | 1 caso de renderização |
| `docs/estado-transicoes-requisicao.md` | TR-005 ganha o efeito de notificação |
| `docs/matriz-invariantes.md` | Linha `NOT-01` em §3 e bullet em §4 |

Migration: a mudança de `choices` gera `AlterField` em `Notificacao.tipo`. Sem
efeito no schema do Postgres (`CharField` sem constraint de choices), mas o
autodetector reclama enquanto não existir. Migrations locais são artefatos
efêmeros (AGENTS.md): rodar `make setup` antes de testar.

## Implementação

### 1. Novo tipo de notificação

`apps/notificacoes/models.py`:

```python
class TipoNotificacao(models.TextChoices):
    AUTORIZACAO = 'autorizacao', 'Autorização'
    RECUSA = 'recusa', 'Recusa'
    ATENDIMENTO = 'atendimento', 'Atendimento'
    DIVERGENCIA_ESTOQUE = 'divergencia_estoque', 'Divergência de estoque'
    ENVIO_AUTORIZACAO = 'envio_autorizacao', 'Envio para autorização'
```

Valor e rótulo copiados de `EventoTimeline.ENVIO_AUTORIZACAO`
(`apps/requisicoes/models.py:197`), que é o termo do glossário para TR-005. Duas
razões para não inventar um rótulo novo do tipo "Aguardando sua autorização":

1. o mesmo evento passa a aparecer com o mesmo nome na timeline da requisição e
   na lista de notificações — o chefe lê a mesma palavra nos dois lugares;
2. `Notificacao.tipo` não carrega destinatário no rótulo, e o mesmo rótulo é
   renderizado por `get_tipo_display` para qualquer destinatário futuro.

`max_length=30` do campo comporta `envio_autorizacao` (17 caracteres). O membro
vai no fim para não sugerir reordenação de valores já persistidos.

### 2. Service irmão de destinatários

`apps/notificacoes/services.py`:

```python
from collections.abc import Iterable


@transaction.atomic
def criar_notificacoes_para_destinatarios(
    *,
    destinatarios_ids: Iterable[int | None],
    requisicao_id: int,
    tipo: str,
) -> None:
    """Cria notificações para os destinatários informados, deduplicando.

    Ignora ``None`` e ids repetidos. É o primitivo de roteamento;
    ``criar_notificacoes_para`` é o atalho para o par criador/beneficiário.
    """
    destinatarios = list(
        dict.fromkeys(uid for uid in destinatarios_ids if uid is not None)
    )
    Notificacao.objects.bulk_create(
        [
            Notificacao(
                destinatario_id=uid,
                tipo=tipo,
                requisicao_id=requisicao_id,
            )
            for uid in destinatarios
        ]
    )


def criar_notificacoes_para(
    *,
    criador_id: int,
    beneficiario_id: int,
    requisicao_id: int,
    tipo: str,
) -> None:
    """Cria notificações para criador e beneficiário, deduplicando se iguais."""
    criar_notificacoes_para_destinatarios(
        destinatarios_ids=[criador_id, beneficiario_id],
        requisicao_id=requisicao_id,
        tipo=tipo,
    )
```

A deduplicação por `dict.fromkeys` é exatamente a que `criar_notificacoes_para`
já fazia — está sendo movida, não reescrita, e os testes existentes dela
(`test_criar_notificacoes_mesmo_usuario_uma_notificacao`) continuam valendo como
teste de regressão da delegação. O filtro de `None` é novo e existe porque
`Setor.chefe_id` é nullable: o chamador não deve precisar repetir a guarda.

Continua um único `bulk_create` por chamada. O `@transaction.atomic` é exigência
de `docs/CONVENTIONS.md:48-51` — service é ponto de mutação, escrita vai dentro
de `transaction.atomic` — e alinha o novo service com
`marcar_notificacao_lida`/`marcar_todas_notificacoes_lidas`, que já o carregam.
`criar_notificacoes_para` não ganha decorator próprio: delega, e o atomic
aninhado seria savepoint sem escrita própria para proteger.

`transaction.on_commit` **não** substitui isso: ele agenda *quando* o callback
roda, não em que transação a escrita dele acontece. Rodar em autocommit deixaria
o `bulk_create` sem bloco explícito num caminho que o projeto trata como
mutação; um `bulk_create` de uma linha só sobreviveria por acidente do
statement-level atomicity do Postgres, não por contrato.

### 3. Selector de resolução do chefe

`apps/requisicoes/selectors.py`, logo abaixo de `fila_autorizacao`:

```python
def chefe_autorizador_do_setor(setor_id: int) -> int | None:
    """Id do chefe que hoje pode autorizar requisições do setor, ou ``None``.

    Espelha, do lado do setor, a condição que ``fila_autorizacao`` aplica do
    lado do ator: setor ativo e chefe ativo. Devolve ``None`` para setor
    inexistente, setor inativo, setor sem chefe e chefe inativo — os quatro
    casos em que ninguém veria a requisição na fila.
    """
    return (
        Setor.objects.filter(pk=setor_id, ativo=True, chefe__is_active=True)
        .values_list('chefe_id', flat=True)
        .first()
    )
```

A leitura fica aqui, e não num `apps/accounts/selectors.py` novo, por dois
motivos: o arquivo não existe, e a regra que esta query codifica é "quem
autoriza requisição deste setor" — a mesma de `fila_autorizacao`, uma função
acima. Separá-las em apps diferentes deixaria as duas metades da mesma
invariante longe uma da outra, e é justamente a distância entre elas que o
`NOT-01` da matriz passa a proibir. `Setor` é import novo no módulo, que já
importa `User` do mesmo pacote (`apps/requisicoes/selectors.py:15`).

### 4. Hook em `enviar_para_autorizacao`

`apps/requisicoes/services/ciclo_vida.py`, novo helper ao lado de
`_notificar_pos_commit`:

```python
def _notificar_chefe_pos_commit(*, setor_id: int, ator_id: int, req_id: int) -> None:
    try:
        chefe_id = chefe_autorizador_do_setor(setor_id)
        if chefe_id is None or chefe_id == ator_id:
            return
        criar_notificacoes_para_destinatarios(
            destinatarios_ids=[chefe_id],
            requisicao_id=req_id,
            tipo=TipoNotificacao.ENVIO_AUTORIZACAO,
        )
    except Exception:
        logger.exception(
            'Falha ao criar notificação de envio pós-commit: '
            'requisicao_id=%s setor_id=%s',
            req_id,
            setor_id,
        )
```

e, no fim de `enviar_para_autorizacao`, depois do `TimelineRequisicao.objects.create`:

```python
    _setor_id = requisicao.setor_beneficiario_id
    _req_id = requisicao.pk
    transaction.on_commit(
        lambda: _notificar_chefe_pos_commit(
            setor_id=_setor_id, ator_id=ator_id, req_id=_req_id
        )
    )

    return requisicao
```

Quatro decisões que o código embute:

1. **O chefe é resolvido pós-commit, não no corpo da transação.** A guarda
   `setor_sem_autorizador` já consulta `Setor` com o mesmo filtro e poderia
   devolver o `chefe_id` de graça — bastaria trocar o `.exists()` dela por uma
   chamada a `chefe_autorizador_do_setor`. O plano **não** faz isso: o critério
   de aceite 3 fala em "sem chefe ativo **no momento do commit**", e só
   re-resolvendo é que uma desativação concorrente entre a guarda e o commit
   deixa de gerar notificação para um chefe que já não autoriza mais. O custo é
   uma query indexada por PK num callback já fora do caminho crítico da
   transição. Snapshotar o id na guarda seria uma query a menos e um
   destinatário errado na janela de corrida.
2. **A condição é espelhada, não compartilhada — e o teste 12 é o que segura o
   espelho.** `apps/requisicoes/selectors.py:139-176` concede a fila partindo do
   ator (`ator.setor_chefiado`, `setor_chefiado.ativo`, `ator.is_active`);
   `chefe_autorizador_do_setor` escreve a mesma condição partindo do setor
   (`Setor.chefe` é `OneToOneField`, então `setor.chefe` e `user.setor_chefiado`
   são o mesmo vínculo). As duas **não** compartilham código: têm sentidos
   opostos (ator→requisições vs. setor→ator) e tipos de retorno diferentes
   (`QuerySet[Requisicao]` vs. `int | None`), e forçar um predicado comum
   exigiria reescrever `fila_autorizacao`, que esta fatia decidiu não tocar.
   Espelho sem trava é exatamente o risco que a revisão do plano apontou: os
   dois filtros podem divergir numa fatia futura. A trava é o teste de
   equivalência (caso 12), que assere os dois lados sob os mesmos estados de
   setor/chefe. Notificar quem não vê a fila seria pior que não notificar — é o
   que `NOT-01` proíbe.
3. **`chefe_id == ator_id` cobre o auto-envio (critério 4).** O chefe que cria e
   envia a própria requisição — caso normal, a policy de criação permite
   beneficiário no próprio setor — não recebe notificação de algo que acabou de
   fazer. A comparação é por id, não por papel: o superusuário que envia em nome
   de terceiro continua notificando o chefe, porque `ator_id != chefe_id`.
4. **Fail-open com `logger.exception`, igual aos hooks irmãos (critério 3).** A
   transição já commitou quando o callback roda; levantar aqui não desfaz nada e
   só polui o response. Note a assimetria deliberada dentro do helper: chefe
   ausente é `return` silencioso (situação de domínio esperada, coberta por
   teste), enquanto falha de banco ou de import é `logger.exception` (defeito).

**Reenvio (critério 2)** não precisa de código: `retornar_para_rascunho` →
`enviar_para_autorizacao` chama o service de novo, e cada chamada registra o seu
próprio `on_commit`. A `Notificacao` não tem unicidade por
`(destinatario, requisicao, tipo)`, então a segunda notificação é criada. É o
comportamento desejado — o chefe precisa ser avisado de novo — e o teste 5 o
trava contra uma futura deduplicação por requisição.

### 5. Documentação

`docs/estado-transicoes-requisicao.md`, linha TR-005 da tabela de transições
(`:60`): a coluna de efeitos hoje diz "Registra envio; entra na fila do chefe do
setor do beneficiário; não reserva nem baixa estoque" e omite notificação.
Acrescentar "notifica o chefe ativo do setor do beneficiário, exceto no
auto-envio". As linhas TR-011 (recusa) e TR-013 (cancelamento de autorizada) já
carregam "notifica envolvidos quando aplicável"; TR-005 fica alinhada, e com
redação mais específica porque o destinatário aqui não é o par
criador/beneficiário.

`docs/matriz-invariantes.md`, §3, nova linha após o bloco `SAE-*`:

| ID | Tema | Invariante | Camada/reforço esperado | Testes mínimos | Ref. |
|---|---|---|---|---|---|
| NOT-01 | Notificações | Destinatário de `ENVIO_AUTORIZACAO` é chefe ativo de setor ativo — subconjunto de quem vê a requisição em `fila_autorizacao`. O superusuário vê a fila sem receber a notificação; o inverso (notificado sem ver) é proibido. | Selector `chefe_autorizador_do_setor` espelha a condição de `fila_autorizacao` (não há código compartilhado: sentidos e tipos de retorno são opostos); o espelho é travado por teste de equivalência. Hook pós-commit fail-open. | Equivalência `chefe_autorizador_do_setor` × `fila_autorizacao` nos mesmos estados de setor/chefe; chefe ativo notificado; chefe inativo, setor inativo e setor sem chefe não geram notificação; auto-envio do próprio chefe não notifica. | #108 |

E um bullet em §4 (Notas por tema): notificação é efeito colateral pós-commit,
nunca pré-condição de transição; falha ao notificar não desfaz a transição já
commitada.

Esta linha existe porque o plano chamava a relação de invariante enquanto a
deixava fora da matriz — inconsistência apontada na revisão do plano. Ou vira
contrato, ou deixa de ser chamada de invariante; vira contrato, porque é o que
justifica o teste de equivalência da decisão 2.

## Estratégia de testes

Camada de service — `apps/notificacoes/tests/test_services.py`, seção nova
`criar_notificacoes_para_destinatarios`:

| # | Caso | Esperado |
|---|---|---|
| 1 | `destinatarios_ids=[a, b, a]` | 2 notificações; `set` de `destinatario_id` == `{a, b}` |
| 2 | `destinatarios_ids=[None, a]` | 1 notificação, para `a` — `None` ignorado |

O caso 1 asserta contagem e conjunto, **não** ordem. `dict.fromkeys` preserva a
ordem de entrada dentro do `bulk_create`, mas uma consulta sem `order_by` não
tem ordem garantida pelo banco, e ordem de destinatários não é contrato de nada
neste fluxo — o que importa é que `a` repetido gere uma linha só. Vale a regra
de `docs/CONVENTIONS.md`: comparar conjuntos de IDs. A docstring do service diz
"deduplicando", sem prometer ordem.

Camada de hook — mesmo arquivo, seção `Hooks em requisicoes.services`. Os casos
3, 4, 5 e 7 usam `@pytest.mark.django_db(transaction=True)`, como os hooks já
testados ali, para que o `on_commit` dispare de verdade. O caso 6 é a exceção e
usa `@pytest.mark.django_db` **sem** `transaction=True`: a fixture
`django_capture_on_commit_callbacks` só consegue interceptar os callbacks
enquanto eles estão pendentes num `atomic` aberto — com `transaction=True` o
commit é real, o callback já rodou e a captura volta vazia.

| # | Caso | Esperado |
|---|---|---|
| 3 | `solicitante` cria e `enviar_para_autorizacao` | 1 `Notificacao` com `tipo=ENVIO_AUTORIZACAO` e `destinatario=chefe_obras`; criador e beneficiário **sem** notificação — critério 1 |
| 4 | `chefe_obras` cria para si e envia | **nenhuma** notificação — critério 4 |
| 5 | envio → `retornar_para_rascunho` → envio | 2 notificações `ENVIO_AUTORIZACAO` para `chefe_obras` — critério 2 |
| 6 | envio com `django_capture_on_commit_callbacks(execute=False)`; desativa `chefe_obras`; executa os callbacks | nenhuma notificação e nenhuma exceção; requisição em `AGUARDANDO_AUTORIZACAO` — critério 3 |
| 7 | envio com `criar_notificacoes_para_destinatarios` monkeypatchado para levantar | transição persistida e `logger.exception` chamado; sem propagação — critério 3 (metade "não quebra") |

O caso 3 asserta os dois lados (chefe recebe **e** criador/beneficiário não
recebem): sem a segunda metade, um hook que chamasse `criar_notificacoes_para`
por engano passaria, e o piloto ganharia notificação de "envio" para quem
enviou.

O caso 6 é o teste do critério 3 tal como redigido — "no momento do commit". Ele
é o que distingue as duas implementações discutidas na decisão 1: com o
`chefe_id` snapshotado na guarda, ele falha. É, portanto, o teste que trava a
decisão, não só o comportamento.

O caso 7 usa monkeypatch porque a falha que ele descreve (banco fora, bug no
service de notificação) não é alcançável por dado de domínio. O alvo do patch é
`apps.requisicoes.services.ciclo_vida.criar_notificacoes_para_destinatarios` — o
símbolo já ligado no módulo consumidor, não `apps.notificacoes.services`, que o
`from ... import` no topo de `ciclo_vida.py` deixa de consultar em runtime.
Asserta `caplog` em nível `ERROR` e o estado da requisição — a fail-open só vale
se a transição sobreviver.

Camada de selector — `apps/requisicoes/tests/test_selectors.py`, seção nova
`chefe_autorizador_do_setor` (chamada direta, comparando IDs, conforme
`docs/CONVENTIONS.md`):

| # | Caso | Esperado |
|---|---|---|
| 8 | setor ativo com chefe ativo | `chefe_obras.pk` |
| 9 | setor ativo com chefe inativo | `None` |
| 10 | setor inativo com chefe ativo | `None` |
| 11 | setor sem chefe (`chefe_id is None`) e `pk` inexistente | `None` nos dois |
| 12 | equivalência, parametrizada em (setor ativo × chefe ativo), (setor ativo × chefe inativo), (setor inativo × chefe ativo): `chefe_autorizador_do_setor(setor.pk) == chefe.pk` **sse** a requisição do setor aparece em `fila_autorizacao(chefe.pk)` | os dois lados concordam nos três estados |

Os casos 9 a 11 são o contrato do `NOT-01` no nível em que ele é barato de
testar: os quatro caminhos que devolvem `None` são exatamente os quatro em que
`fila_autorizacao` não mostraria a requisição a ninguém. O caso 6 continua sendo
o teste de que o hook *usa* esse contrato no momento certo.

O caso 12 é o que a revisão do plano exigiu ao apontar que "espelhado" não é
"compartilhado": ele falha assim que `fila_autorizacao` e
`chefe_autorizador_do_setor` divergirem em qualquer um dos três estados, o que
nenhum dos casos 8-11 pegaria sozinho — eles só olham um lado do espelho. O
estado "setor sem chefe" fica fora da parametrização porque não há usuário para
passar a `fila_autorizacao`; ele já é o caso 11.

Camada de view — `apps/notificacoes/tests/test_views.py`:

| # | Caso | Esperado |
|---|---|---|
| 13 | `chefe_obras` autenticado faz GET em `notificacoes:lista` com uma `Notificacao` `ENVIO_AUTORIZACAO` apontando para requisição numerada | 200; `Envio para autorização` no HTML; `href` para `requisicoes:detalhe` daquele pk — critério 5 |

O caso 13 é o que substitui a edição de template: ele falha se o novo membro não
existir, se o rótulo mudar, ou se alguém trocar o `get_tipo_display` genérico do
template por um `if` por tipo que esqueça o membro novo.

Não coberto, e por quê: badge HTMX de contagem
(`apps/notificacoes/context_processors.py` conta por `lida=False`, sem olhar
`tipo` — o membro novo entra na contagem sem regra própria); ordenação da lista
(`ordering = ['-criado_em']` no `Meta`, não tocada); `marcar_lida` /
`marcar_todas_lidas` (operam por `destinatario_id`, agnósticos ao tipo); a
guarda `setor_sem_autorizador` (já tem cobertura própria no plano #103 e não
muda aqui).

## Invariantes

`docs/matriz-invariantes.md` não tinha linha para notificações. Esta fatia
acrescenta `NOT-01` (ver Implementação §5): **quem recebe `ENVIO_AUTORIZACAO` é
subconjunto de quem vê a requisição em `fila_autorizacao`.** O superusuário é o
único que vê a fila sem receber notificação — direção segura (vê sem ser
avisado); o inverso, avisado sem ver, é o que a condição espelhada impede — e o
espelho só vale enquanto o teste de equivalência (caso 12) o segurar.
Travada pelos testes 3, 6 e 9-12 — o 12 é o único que detecta divergência entre
`chefe_autorizador_do_setor` e `fila_autorizacao`, e ficar de fora desta lista
era resíduo da renumeração. A exceção do superusuário não ganha teste próprio
aqui: ela não é regra nova, é `fila_autorizacao` devolvendo `base_qs` inteiro
para `is_superuser` (`apps/requisicoes/selectors.py:165-166`), já coberto na
seção de fila de `test_selectors.py`. O que esta fatia acrescenta é apenas *não*
notificá-lo, o que o caso 3 já assere ao exigir exatamente um destinatário.

**Limite conhecido — janela TOCTOU entre resolver e gravar.** O callback resolve
o chefe e grava a notificação em dois statements; uma desativação concorrente
entre os dois persiste uma linha `ENVIO_AUTORIZACAO` para chefe já inativo. O
plano **não** fecha essa janela com lock, por três razões:

1. **Lock não a fecha.** Uma desativação um instante *depois* do INSERT produz a
   mesma linha. Atividade é estado mutável; notificação é registro histórico
   imutável. Não existe ponto de serialização que torne "destinatário ativo"
   durável — só se poderia estreitar a janela, nunca eliminá-la.
2. **A contenção já existe, e é do lado da leitura.**
   `pode_ver_notificacao` exige `papel.ativo`
   (`apps/notificacoes/policies.py:13`), com teste próprio já verde
   (`test_inativo_nao_pode_ver_propria_notificacao`), e USR-01 barra o login. A
   linha órfã é inerte: ninguém consegue abri-la. A invariante que importa é
   "inativo não lê notificação", e ela é garantida por policy, não pela ausência
   do registro.
3. **O custo cai no lugar errado.** `select_for_update` sobre `Setor` num
   callback pós-commit abriria transação e lock num caminho cujo contrato é
   justamente não afetar a transição já commitada — trocaria uma linha inerte
   por contenção de lock no cadastro de setores.

O caso 6 continua cobrindo a janela que *importa* e que é fechável: desativação
entre o commit da transição e a execução do callback, em que o chefe é resolvido
já inativo e nada é gravado.

Registrar em vez de deixar implícito é resposta direta à revisão do plano: uma
regra que o código passa a depender e que nenhum documento carrega vira, na
próxima fatia, um filtro divergente entre fila e notificação.

As demais linhas tocadas de lado:

| Regra | Relação com esta mudança |
|---|---|
| USR-04 (setor ativo tem chefe ativo) | A guarda `setor_sem_autorizador` já a reforça no envio. O hook **não** a assume verdadeira no commit: trata `chefe_id is None` como caminho normal, o que é a resposta correta enquanto USR-04 for invariante de backlog (ACE-002) e não constraint de banco. |
| USR-06 (setor inativo não recebe nova requisição) | O filtro `ativo=True` do selector cobre a janela entre a guarda e o commit: setor desativado nesse intervalo é resolvido como `None` e nada é notificado. A janela entre resolver e gravar tem o mesmo limite TOCTOU descrito acima, contido do mesmo jeito — chefe de setor desativado deixa de ver a fila, e a policy de leitura da notificação exige `papel.ativo`. |
| USR-01 (usuário inativo não acessa nem opera) | Duas camadas, com forças diferentes. Na resolução, `chefe__is_active=True` faz o caminho normal não escolher usuário inativo como destinatário — proteção, não garantia: a janela TOCTOU documentada acima continua podendo persistir a linha. A garantia está na leitura: `pode_ver_notificacao` exige `papel.ativo`, então mesmo a linha criada na janela permanece inacessível. |
| REQ-03 / REQ-04 (número público) | Intocados: o hook roda depois do `save`, lê só `pk` e `setor_beneficiario_id`, e não participa da emissão nem da preservação do número. |
| REQ-08 (timeline registra eventos principais) | A timeline de `ENVIO_AUTORIZACAO` continua igual. Notificação não é evento de timeline e não duplica registro. |
| EST-02 (envio não reserva nem baixa estoque) | Preservado: nenhuma linha de saldo é lida ou escrita. |
| EST-06 (operações críticas em transação com lock) | Preservado e reforçado: o efeito de notificação fica **fora** da transação, via `on_commit`, então não estende o tempo de lock de `select_for_update` sobre a `Requisicao`. |
| PER-06 (`setor_beneficiario` é o snapshot autoritativo da fila) | Respeitado: o hook parte de `requisicao.setor_beneficiario_id`, o mesmo campo que `fila_autorizacao` filtra. Destinatário e fila não podem divergir por caminho de roteamento. |

## Riscos

| Risco | Avaliação |
|---|---|
| Query extra por envio | Uma, por PK indexada, dentro de `on_commit` — fora da transação e fora do lock. TR-005 não é caminho de alto volume (um envio por requisição, mais reenvios). Aceito em troca da correção da janela de corrida (decisão 1). |
| Volume de notificações para o chefe | Cada envio e cada reenvio gera uma linha. É o objetivo do issue, mas em setor movimentado a lista do chefe passa a ser dominada por este tipo. Sem agrupamento nesta fatia: agrupar exige decidir janela e chave de agregação, o que é escopo próprio. Se o piloto reclamar, a resposta é agrupar na leitura (selector), não deixar de notificar. |
| Notificação para chefe que perdeu a chefia entre guarda e commit | É precisamente o que a decisão 1 elimina, e o teste 6 trava. |
| Requisição fica sem ninguém avisado | Possível quando o chefe é desativado na janela — a requisição continua na fila, visível para o superusuário, e a guarda impede *novos* envios para o setor. Fail-open é a escolha certa: perder o aviso é menos grave que travar a transição já commitada. |
| Migration de `choices` | `AlterField` sem efeito de schema. Migrations locais são efêmeras (AGENTS.md): recriar do zero com `make setup` antes de testar. Nada a versionar. |
| Contrato OpenAPI | Projeto é server-rendered sem camada REST (AGENTS.md). Não se aplica. |
| Concorrência / lock | O hook não abre transação nem toca linha travada. `on_commit` só dispara após commit bem-sucedido — rollback não notifica, comportamento já coberto por `test_on_commit_nao_dispara_em_rollback`. |
