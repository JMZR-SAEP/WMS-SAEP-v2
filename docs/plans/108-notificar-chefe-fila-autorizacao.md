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
  `TipoNotificacao.ENVIO_AUTORIZACAO`.
- `apps/notificacoes/services.py` — novo service irmão
  `criar_notificacoes_para_destinatarios`; `criar_notificacoes_para` passa a
  delegar nele, mantendo a assinatura atual intacta.
- `apps/requisicoes/services/ciclo_vida.py` — novo helper
  `_notificar_chefe_pos_commit`; `enviar_para_autorizacao` registra
  `transaction.on_commit`.
- `apps/notificacoes/tests/test_services.py` — casos de service e de hook.
- `apps/notificacoes/tests/test_views.py` — renderização do rótulo e do link.
- `docs/estado-transicoes-requisicao.md` — TR-005 passa a listar o efeito
  colateral de notificação, hoje ausente na descrição da transição.

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
- `apps/requisicoes/selectors.py::fila_autorizacao` — a fila continua sendo a
  fonte de verdade de *quem autoriza*; a notificação apenas avisa. Ver
  Invariantes para o acoplamento entre as duas.
- Estoque, reservas, timeline — TR-005 não toca saldo (EST-02) e o
  `TimelineRequisicao` de `ENVIO_AUTORIZACAO` já existe e permanece igual.

## Arquivos alterados

| Arquivo | Ação |
|---|---|
| `apps/notificacoes/models.py` | Novo membro em `TipoNotificacao` |
| `apps/notificacoes/services.py` | Novo `criar_notificacoes_para_destinatarios`; `criar_notificacoes_para` delega |
| `apps/requisicoes/services/ciclo_vida.py` | Novo `_notificar_chefe_pos_commit`; `on_commit` em `enviar_para_autorizacao` |
| `apps/notificacoes/tests/test_services.py` | 2 casos de service + 5 casos de hook |
| `apps/notificacoes/tests/test_views.py` | 1 caso de renderização |
| `docs/estado-transicoes-requisicao.md` | TR-005 ganha o efeito de notificação |

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


def criar_notificacoes_para_destinatarios(
    *,
    destinatarios_ids: Iterable[int | None],
    requisicao_id: int,
    tipo: str,
) -> None:
    """Cria notificações para os destinatários informados, deduplicando.

    Ignora ``None`` e ids repetidos preservando a ordem de entrada. É o
    primitivo de roteamento; ``criar_notificacoes_para`` é o atalho para o par
    criador/beneficiário.
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

Continua um único `bulk_create` por chamada, sem `transaction.atomic` — igual ao
que existe hoje. O helper não abre transação porque é chamado de dentro de
`on_commit`, isto é, já fora da transação de domínio.

### 3. Hook em `enviar_para_autorizacao`

`apps/requisicoes/services/ciclo_vida.py`, novo helper ao lado de
`_notificar_pos_commit`:

```python
def _notificar_chefe_pos_commit(*, setor_id: int, ator_id: int, req_id: int) -> None:
    try:
        chefe_id = (
            Setor.objects.filter(pk=setor_id, ativo=True, chefe__is_active=True)
            .values_list('chefe_id', flat=True)
            .first()
        )
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
   `setor_sem_autorizador` já consultou `Setor` com o mesmo filtro
   (`ativo=True, chefe__is_active=True`) e poderia devolver o `chefe_id` de
   graça, trocando `.exists()` por `.values_list(...).first()`. O plano **não**
   faz isso: o critério de aceite 3 fala em "sem chefe ativo **no momento do
   commit**", e só re-resolvendo é que uma desativação concorrente entre a
   guarda e o commit deixa de gerar notificação para um chefe que já não
   autoriza mais. O custo é uma query indexada por PK num callback já fora do
   caminho crítico da transição. Snapshotar o id na guarda seria uma query a
   menos e um destinatário errado na janela de corrida.
2. **O filtro repete `fila_autorizacao`, e isso é o ponto.**
   `apps/requisicoes/selectors.py:139-176` concede a fila a quem tem
   `ator.setor_chefiado` com `setor_chefiado.ativo` e `ator.is_active`. O
   `Setor.objects.filter(pk=..., ativo=True, chefe__is_active=True)` é a mesma
   condição escrita do lado do setor (`Setor.chefe` é `OneToOneField`, então
   `setor.chefe` e `user.setor_chefiado` são o mesmo vínculo). Notificar quem
   não vê a fila seria pior que não notificar. Ver Invariantes.
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

### 4. Documentação

`docs/estado-transicoes-requisicao.md`, linha TR-005 da tabela de transições
(`:60`): a coluna de efeitos hoje diz "Registra envio; entra na fila do chefe do
setor do beneficiário; não reserva nem baixa estoque" e omite notificação.
Acrescentar "notifica o chefe ativo do setor do beneficiário, exceto no
auto-envio". As linhas TR-011 (recusa) e TR-013 (cancelamento de autorizada) já
carregam "notifica envolvidos quando aplicável"; TR-005 fica alinhada, e com
redação mais específica porque o destinatário aqui não é o par
criador/beneficiário.

## Estratégia de testes

Camada de service — `apps/notificacoes/tests/test_services.py`, seção nova
`criar_notificacoes_para_destinatarios`:

| # | Caso | Esperado |
|---|---|---|
| 1 | `destinatarios_ids=[a, b, a]` | 2 notificações, ordem de entrada preservada |
| 2 | `destinatarios_ids=[None, a]` | 1 notificação, para `a` — `None` ignorado |

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

Camada de view — `apps/notificacoes/tests/test_views.py`:

| # | Caso | Esperado |
|---|---|---|
| 8 | `chefe_obras` autenticado faz GET em `notificacoes:lista` com uma `Notificacao` `ENVIO_AUTORIZACAO` apontando para requisição numerada | 200; `Envio para autorização` no HTML; `href` para `requisicoes:detalhe` daquele pk — critério 5 |

O caso 8 é o que substitui a edição de template: ele falha se o novo membro não
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

`docs/matriz-invariantes.md` não tem linha para notificações — elas são efeito
colateral, não invariante de domínio. As linhas tocadas de lado:

| Regra | Relação com esta mudança |
|---|---|
| USR-04 (setor ativo tem chefe ativo) | A guarda `setor_sem_autorizador` já a reforça no envio. O hook **não** a assume verdadeira no commit: trata `chefe_id is None` como caminho normal, o que é a resposta correta enquanto USR-04 for invariante de backlog (ACE-002) e não constraint de banco. |
| USR-06 (setor inativo não recebe nova requisição) | O filtro `ativo=True` no hook impede notificar chefe de setor desativado na janela entre guarda e commit. |
| USR-01 (usuário inativo não acessa nem opera) | `chefe__is_active=True` impede criar notificação para usuário inativo, que não conseguiria abri-la. |
| REQ-03 / REQ-04 (número público) | Intocados: o hook roda depois do `save`, lê só `pk` e `setor_beneficiario_id`, e não participa da emissão nem da preservação do número. |
| REQ-08 (timeline registra eventos principais) | A timeline de `ENVIO_AUTORIZACAO` continua igual. Notificação não é evento de timeline e não duplica registro. |
| EST-02 (envio não reserva nem baixa estoque) | Preservado: nenhuma linha de saldo é lida ou escrita. |
| EST-06 (operações críticas em transação com lock) | Preservado e reforçado: o efeito de notificação fica **fora** da transação, via `on_commit`, então não estende o tempo de lock de `select_for_update` sobre a `Requisicao`. |
| PER-06 (`setor_beneficiario` é o snapshot autoritativo da fila) | Respeitado: o hook parte de `requisicao.setor_beneficiario_id`, o mesmo campo que `fila_autorizacao` filtra. Destinatário e fila não podem divergir por caminho de roteamento. |

Invariante nova, não escrita em matriz mas travada pelos testes 3 e 6:
**quem recebe `ENVIO_AUTORIZACAO` é subconjunto de quem vê a requisição em
`fila_autorizacao`.** O superusuário é o único que vê a fila sem receber
notificação — direção segura (vê sem ser avisado), e o inverso (avisado sem ver)
é o que os filtros `ativo`/`is_active` impedem.

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
