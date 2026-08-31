# Convenções de implementação — WMS-SAEP

Regras operacionais para implementar features nos apps de domínio. Decisão de
fundo: [ADR-0004](adr/0004-arquitetura-em-camadas.md). ADRs relacionados:
[0001](adr/0001-papeis-de-dominio-derivados.md) (papéis derivados),
[0002](adr/0002-auditoria-por-models-de-dominio.md) (auditoria),
[0003](adr/0003-numero-publico-contador-anual.md) (número público).

## Layout de um app de domínio

```
apps/<app>/
  models.py        schema, constraints, choices, properties simples
  transitions.py   (só requisicoes) tabela declarativa da máquina de estados
  services.py      comandos de domínio; único ponto de mutação
  policies.py      autorização contextual
  selectors.py     leituras não triviais, filas, escopos de visibilidade
  forms.py         validação de input
  views.py         views finas
  urls.py
  admin.py
  tests/
```

`services.py`, `policies.py`, `selectors.py` começam como arquivo único.
Promover a pacote (`services/` com um módulo por caso de uso) só quando o
volume justificar. Arquivos nascem com conteúdo — não criar stubs vazios.

## Onde colocar cada coisa

| Preciso de... | Camada |
|---|---|
| Novo campo, constraint, choice, property trivial | `models.py` |
| Mutar estado de domínio (criar, transicionar, baixar saldo) | `services.py` |
| Decidir se um ator pode fazer algo | `policies.py` |
| Listar/filtrar com escopo de visibilidade ou fila | `selectors.py` |
| Validar dados de um formulário | `forms.py` |
| Receber request e devolver response | `views.py` |
| Regra de transição estado→estado | `transitions.py` |

## Regras

**Views são finas.** Fluxo: ler input → chamar service com IDs →
traduzir exceção de domínio para HTTP → renderizar ou redirect. A view passa
`request.user.id`, nunca `request.user`. Nenhuma regra de domínio, query de
escopo ou decisão de autorização própria na view.

**Services são o único ponto de mutação de domínio.** Um service (ADR-0011):
- assinatura keyword-only obrigatória: `def criar_X(*, ator_id: int, ...) -> Entidade`;
- recebe IDs, carrega entidades internamente com relações necessárias;
- abre `transaction.atomic` quando há escrita de domínio;
- valida transição via `transitions.py` (`verificar_transicao_valida`);
- chama `exigir_pode_*` da policy antes de aplicar efeitos;
- registra os eventos de `TimelineRequisicao`;
- dispara notificações apenas via `transaction.on_commit`;
- retorna a entidade principal alterada (sem garantia de relações carregadas);
- lança exceções de `apps.core.exceptions`, nunca exceções HTTP do Django.

**Policies são autorização contextual compartilhada.** Duas funções PT-BR
por operação (ADR-0011): `pode_*(ator, obj) -> bool` (fonte de verdade) e
`exigir_pode_*(ator, obj)` (delega para `pode_*`, lança `PermissaoNegada`).
Services chamam `exigir_pode_*`. Templates/views podem chamar `pode_*`.
`exigir_pode_*` nunca reimplementa a regra — sempre chama `pode_*`.

**Exceções de domínio** (`apps/core/exceptions.py`, ADR-0011):
- `PermissaoNegada` — ator sem permissão;
- `EstadoInvalido` — transição de estado inválida;
- `DadosInvalidos` — dados estruturalmente válidos mas inválidos para o domínio;
- `ConflitoDominio` — conflito de estado, saldo, unicidade lógica ou corrida.
Views traduzem explicitamente para HTTP. `IntegrityError` não é caminho normal
para erro de domínio previsível.

**Selectors concentram leitura não trivial.** Filas de autorização e
atendimento, escopo de visibilidade por papel e listagens filtradas. Leitura
trivial pode usar o ORM direto na view.

**Models não orquestram.** Guardam schema, constraints, choices e properties
simples (ex.: `saldo_disponivel`). Não importam services, não disparam casos
de uso em `save()`, não geram timeline por signals.

**Auditoria é por model de domínio** (ADR-0002): `TimelineRequisicao`,
`MovimentacaoEstoque`, `ReservaEstoque`. Sem `django-simple-history`.

**Estoque** (ADR-0004 + EST-06): toda mutação de saldo passa por
`estoque.services`, sob `transaction.atomic` + `select_for_update` sobre
`SaldoEstoque`, em ordem determinística. Nenhum outro app escreve saldo.
Exceção única documentada: ver `#seed-bootstrap-exceptions` abaixo.

## Seed e dados de desenvolvimento

Decisão de fundo: [ADR-0009](adr/0009-seed-dev-dados-minimos-ambiente.md).

O command `seed_dev` (`apps/core/management/commands/seed_dev.py`) é a fonte
de verdade para dados canônicos do ambiente local. Use `make seed-dev` para
inicializar ou convergir o banco.

### Seed bootstrap exceptions

O seed pode escrever diretamente em tabelas protegidas por services **apenas**
quando todas as condições forem satisfeitas:

1. A escrita representa estado inicial de ambiente, não evento operacional de domínio.
2. A função está isolada, nomeada com sufixo `_bootstrap_exception` e contém
   comentário `# SEED BOOTSTRAP EXCEPTION` apontando para este documento.
3. A escrita é idempotente e convergente.
4. O seed não cria histórico, timeline ou auditoria artificial.
5. Fluxos de aplicação continuam obrigados a usar os services de domínio.

Atualmente, apenas `_seed_saldos_iniciais_bootstrap_exception()` usa esse
padrão. Não reutilizar fora do seed.

### Regras para agentes de IA

```
Não usar get_or_create para entidades canônicas do seed — usar update_or_create.
Não usar id numérico como referência de seed.
Não sobrescrever registros fora da lista declarada no seed.
Não criar Requisicao, TimelineRequisicao ou movimentação no seed_dev.
Não incrementar SequenciaRequisicao.ultimo_numero no seed.
SequenciaRequisicao usa get_or_create, nunca update_or_create.
seed_dev não importa factory_boy. Factories não importam dados do seed_dev.
Chefia (Setor.chefe) só é atribuída após todos os usuários existirem.
```

## Testes

Decisão de fundo: [ADR-0010](adr/0010-estrategia-de-testes.md).

| Camada | Arquivo | Responsabilidade |
|--------|---------|-----------------|
| Models | `test_models.py` | Constraints não triviais, properties semânticas |
| Policies | `test_policies.py` | Matriz de autorização (chamada direta) |
| Selectors | `test_selectors.py` | Visibilidade e escopo (chamada direta, IDs) |
| Services | `test_services.py` | 3 testes/transição: feliz, estado inválido, permissão negada |
| Views | `test_views.py` | Contrato HTTP: auth, permissão, smoke, redirect+mutação mínima |

**Anatomia por transição de service:** caminho feliz (estado + efeitos + timeline), estado inválido (nenhuma escrita), permissão negada (nenhuma escrita).

**Regras para agentes:**

```
Não duplicar matrix de policy em service tests.
Não duplicar matrix de selector em view tests.
Policy tests usam banco real (papéis derivados de FK/query).
Selector tests comparam sets de IDs, não HTML.
View tests verificam redirect + um estado principal para POST de mutação.
Não usar factory_boy nesta fase.
Não usar seed_dev como pré-condição de teste.
Testes de concorrência real (threads) são a exceção, não a regra.
tests.py arquivo único vira pacote tests/ quando precisar de 2+ módulos.
```

## Mensagens ao usuário

### Fluxo PRG com HTMX

Ações de transição (POST) sempre retornam redirect após sucesso. Para chamadas
HTMX, usar `HX-Redirect` em vez de redirect HTTP normal:

```python
def htmx_redirect(request, url):
    if request.headers.get("HX-Request") == "true":
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url)
```

Fragments HTMX ficam para leitura/interação auxiliar (GET). Nunca para
transições de escrita.

### Níveis e ARIA

| Nível | Uso | ARIA role | Auto-dismiss |
|-------|-----|-----------|-------------|
| `success` | Ação de domínio concluída | `status` | 8s |
| `info` | Estado informativo neutro (ex: logout) | `status` | 8s |
| `warning` | Ação não aplicada; estado atual é compreensível | `alert` | Não |
| `error` | Ação falhou; usuário deve corrigir/não tem permissão | `alert` | Não |

Todas as mensagens têm botão de dismiss manual.

### Mapeamento de exceções

```
PermissaoNegada   → messages.error
DadosInvalidos    → messages.error
EstadoInvalido    → messages.warning (padrão)
ConflitoDominio   → messages.warning (padrão)
```

Views podem sobrescrever o nível quando o contexto exigir.

### Texto das mensagens

`ErroDominio.message` é a fonte do texto exibido — sempre em PT-BR, orientado
ao usuário, sem termos técnicos de implementação (`SaldoEstoque`, `select_for_update`).
Views exibem `str(exc)` diretamente; não mantêm tabela paralela de textos.

`ErroDominio.code` é identificador estável para testes e APIs futuras.

```python
# service:
raise EstadoInvalido(
    "Esta requisição já foi atendida e não pode mais ser cancelada.",
    code="estado_origem_invalido",
)

# view:
except EstadoInvalido as exc:
    messages.warning(request, str(exc))
```

Mensagens de sucesso incluem `numero_publico` quando disponível:
`"Requisição REQ-2026-0042 autorizada com sucesso."` Rascunhos sem número
recebem mensagem genérica.

### Login e sessão

```
Login inválido    → form error (AuthenticationForm)
Logout            → messages.info("Sessão encerrada.")
Acesso sem login  → redirect limpo para login (sem message)
```

## URLs

- Slugs em PT-BR (ver `AGENTS.md`, Convenção de idioma). App namespace declarado
  com `app_name` no `urls.py` do app.
- O segmento de identificador é sempre o `pk` numérico. **Nunca expor
  `numero_publico` como segmento de URL** — ele pode ser nulo em rascunho.
- Sem query params para navegação básica. `?next=<url>` apenas para preservar a
  origem no link "← Voltar" de uma tela de detalhe.
- Filtros e ordenação de listagem vivem na querystring (`?estado=`, `?ordem=`).
  A URL é a fonte de verdade do recorte, e a querystring canônica é montada em
  `apps/core/querystring.py` — não monte querystring à mão no template.

A consequência de a URL ser a fonte de verdade é que o recorte é compartilhável e
sobrevive a um reload. Isso é propriedade do sistema, registrada aqui; a tela não
a explica ao operador (ver "Vocabulário de interface").

## Vocabulário de interface

Labels da UI. Mapeiam os termos do glossário de `CONTEXT.md` para o contexto
visual — o glossário define o conceito, esta tabela define como ele aparece na
tela.

| Conceito (CONTEXT.md) | Label na UI | Notas |
|---|---|---|
| Requisição | Requisição | Nunca "pedido", "solicitação" |
| Numero público | REQ-2026-0042 | Formatado; fallback "Rascunho" |
| Solicitante | (implícito) | Nunca aparece como label de papel |
| Beneficiário | Beneficiário | Nome + matrícula |
| Criador | Criado por | Campo de cabeçalho |
| Setor beneficiário | Setor | No detalhe; no contexto de autorização "Setor" é sempre o do beneficiário |
| Aguardando autorização | Aguardando autorização | Badge de estado; nunca "pendente" |
| Pronta para retirada | Pronta para retirada | Nunca "separada", "pronta" sozinho |
| Chefe de setor | (implícito) | Papel derivado; não aparece como label |
| Auxiliar de almoxarifado | (implícito) | Idem |
| Enviar para autorização | Enviar para autorização | Botão; nunca "submeter" |
| Retornar para rascunho | Retornar para rascunho | Botão; nunca "rejeitar", "voltar" |
| Separar para retirada | Separar para retirada | Botão |
| Atendimento parcial | Atendimento parcial | Label de evento de timeline |

### Identificadores na interface

**PK interno nunca vaza para a UI.** O identificador visível de um registro é o
número público; o fallback quando ele não existe é um literal — `"Rascunho"` na
requisição, `"Sem número"` na saída excepcional — e nunca o `__str__` do model,
que devolve `Rascunho #<pk>` / `Saída #<pk>`. O `__str__` serve admin e log, que
é para onde foi escrito. Quem responde "qual documento é este" quando não há
número é o contexto (beneficiário, setor, data), não o pk.

A mesma regra governa a URL: o segmento de rota é o `pk`, mas ele não é
apresentado como identidade em lugar nenhum da tela.

### Texto de apoio de tela

O parágrafo sob o título de uma tela orienta a tarefa de quem opera: o que a
lista contém e por quais recortes ela se estreita. Ele não narra o mecanismo da
implementação.

A regra veio de medição de custo (issue #160, 2026-08-28). O histórico de
requisições e o de movimentações fechavam o parágrafo com "o recorte fica na URL
e pode ser compartilhado" — era o único texto de ajuda das duas telas, e gastava
metade dele explicando querystring, que nenhum papel do `PRODUCT.md` pediu. A
frase saiu das duas; a propriedade continua verdadeira e continua registrada na
seção URLs acima.

Vale para tela nova: se uma frase do texto de apoio descreve URL, querystring,
swap parcial ou cache — coisas que o operador não executa —, ela pertence a este
documento, não à tela. Não é decisão visual (por isso não está no `DESIGN.md`):
é vocabulário de interface.

## Checklist ao adicionar uma feature

- O caso de uso vive em `services.py`? A view ficou fina?
- A policy é chamada por view e por service?
- Mutação de domínio está dentro de `transaction.atomic`?
- Transições de requisição passam por `transitions.py`?
- O evento foi registrado em `TimelineRequisicao`?
- Notificações só em `transaction.on_commit`?
- Há teste de caminho feliz, permissão negada e violação de domínio
  (ver `docs/matriz-invariantes.md`)?
