# Information Architecture: WMS-SAEP

Cobre o escopo dos três briefs produzidos: login, telas operacionais (listas) e detalhe da requisição. Outros módulos (estoque, materiais, admin operacional) são fora do escopo desta IA.

## Site Map

```
/                               → redirect por papel (ver fluxo de login)
/login/                         → Tela de login (accounts:login)
/logout/                        → POST logout (accounts:logout)

/requisicoes/
  minhas/                       → Minhas Requisições (todos os papéis autenticados)
  nova/                         → Criar nova requisição (todos os papéis autenticados)
  historico/                    → Histórico de Requisições (aux setor, chefe setor, almoxarifado, superuser)
  autorizacoes/                 → Fila de Autorização (chefe de setor)
  atendimentos/                 → Fila de Atendimentos (aux/chefe almoxarifado)
  <id>/                         → Detalhe da Requisição
    editar/                     → Editar rascunho [fora de escopo atual]
    atender/                    → Formulário de atendimento [fora de escopo atual]
    devolucao/                  → Registrar devolução [fora de escopo atual]

/admin/                         → Django admin (superuser)

/estoque/
  movimentacoes/                → Histórico de Movimentações (estoque:historico_movimentacoes)
                                   [visível: almoxarifado (chefe/aux) + chefe/aux de setor]
```

Páginas marcadas `[fora de escopo atual]` são mapeadas na IA para completude, mas não têm brief ainda.

## Redirect Pós-Login

`/` é o destino padrão após autenticação. A view em `core:home` detecta o papel efetivo e redireciona:

| Papel efetivo | Destino |
|---|---|
| Solicitante | `/requisicoes/minhas/` |
| Auxiliar de setor | `/requisicoes/minhas/` |
| Chefe de setor | `/requisicoes/autorizacoes/` |
| Auxiliar de almoxarifado | `/requisicoes/atendimentos/` |
| Chefe de almoxarifado | `/requisicoes/atendimentos/` |
| Superuser | `/admin/` |

Usuário com múltiplos papéis: hierarquia de prioridade `chefe_almox > aux_almox > chefe_setor > aux_setor > solicitante`. Superuser sempre vai para admin.

`LOGIN_REDIRECT_URL = '/'` em `settings.py`.

## Navigation Model

### Navegação principal (sidebar em `lg:`, drawer abaixo disso)

Fonte única em `core_tags.secoes_navegacao`, que lê a constante `NAVEGACAO` e filtra cada
item pela flag de permissão já presente no contexto — a tag não reimplementa policy. Seção
sem nenhum item visível é descartada inteira.

**Três seções, 11 itens no total.** Este é o catálogo completo; ninguém vê os 11 exceto o
superuser.

| Seção | Itens | Flag |
|---|---|---|
| Navegação | Início | (sem flag — sempre visível) |
| Requisições | Nova requisição | (sem flag) |
| | Minhas requisições | (sem flag) |
| | Fila de autorizações | `pode_ver_fila_autorizacao` |
| | Histórico de requisições | `pode_consultar_historico_requisicoes` |
| Almoxarifado | Atendimento | `pode_ver_fila_atendimento` |
| | Saídas excepcionais | `pode_consultar_saidas_excepcionais` |
| | Catálogo de materiais | `pode_consultar_catalogo_estoque` |
| | Movimentações | `pode_consultar_movimentacoes_estoque` |
| | Importar SCPI | `pode_visualizar_preview_scpi` |
| | Histórico de importações SCPI | `pode_consultar_historico_scpi` |

O limite de "máximo 4 links por papel" caiu quando o almoxarifado ganhou catálogo,
movimentações e importação SCPI. O que substituiu o limite não é um número, é o
agrupamento: os itens do almoxarifado ficam sob um cabeçalho próprio, então quem tem os
seis não escolhe entre onze links soltos.

Contagem medida sobre o elenco de `seed_dev`, renderizando a navegação de cada usuário:

| Usuário do seed | Links visíveis |
|---|---|
| Solicitante (`OBRAS003`) | 4 |
| Auxiliar de setor (`OBRAS002`) | 6 |
| Chefe de setor (`OBRAS001`) | 7 |
| Auxiliar de almoxarifado (`ALMOX002`) | 8 |
| Chefe de almoxarifado (`ALMOX001`) | 10 |
| Superuser (`SUPER001`) | 11 |

Os números são do elenco, não do papel puro: papel é efetivo e acumula, então `ALMOX001`
também é chefe do próprio setor e por isso enxerga a fila de autorizações. "Importar SCPI"
é o único item que nem o chefe de almoxarifado vê — `pode_visualizar_preview_scpi` exige
superusuário.

> **Módulo Estoque** — navegação secundária dentro da área de almoxarifado (`_topbar_nav.html`):
>
> | Papel | Links visíveis |
> |---|---|
> | Chefe de almoxarifado | Atendimento · Saídas excepcionais · Catálogo de materiais · **Movimentações** · Importar SCPI · Histórico de importações SCPI |
> | Auxiliar de almoxarifado | Atendimento · Saídas excepcionais · Catálogo de materiais · **Movimentações** · Importar SCPI · Histórico de importações SCPI |
> | Chefe de setor | **Movimentações** (escopo do próprio setor) |
> | Auxiliar de setor | **Movimentações** (escopo do próprio setor) |
>
> Condição RBAC para "Movimentações": `pode_consultar_movimentacoes_estoque` (derivado de `_eh_almoxarifado` ou vínculo de setor).

### Utility navigation (top nav, extremidade direita)

```
[nome do usuário]   Sair
```

"Nome do usuário" mostra `user.nome`. Sem dropdown de perfil nesta fase.

### Secondary navigation

Sidebar fixa a partir de `lg:` (64rem), em `core/partials/_side_nav.html`. Dentro do detalhe da
requisição: ícone de voltar na barra de aplicação, para a lista de origem (preservada via query
param `?next=`).

### Mobile navigation

Abaixo de `lg:`, hamburger na barra de aplicação abre um popover ancorado de 16rem com scrim e
foco preso (`x-trap.inert.noscroll`). Mesmo conteúdo da sidebar, mesma fonte de dados.

## Content Hierarchy

### `/login/`
1. Campos de autenticação — ação primária da tela
2. Mensagem de erro de credencial (se existir) — bloqueia o fluxo
3. Copy institucional (título, subtítulo, helper) — orienta sem distrair
4. Footer restritivo — informação secundária

### `/requisicoes/minhas/`
1. Lista de requisições (número, estado, beneficiário, data, ação) — razão de estar na tela
2. Empty state com CTA "Nova Requisição" — próxima ação óbvia se lista vazia
3. Top nav — orientação e saída

### `/requisicoes/autorizacoes/`
1. Lista de requisições pendentes (número, beneficiário, setor, data enviada, qtd itens, "Analisar") — trabalho pendente
2. Empty state — confirmação de fila zerada
3. Top nav

### `/requisicoes/atendimentos/`
1. Lista de requisições a atender (número, beneficiário, setor, data autorizada, qtd itens, "Atender") — trabalho pendente
2. Empty state
3. Top nav

### `/requisicoes/<id>/`
1. Cabeçalho (número, estado, beneficiário, setor, criador, datas) — contexto da decisão
2. Itens (tabela com colunas por estado) — objeto da operação
3. Ações disponíveis — trabalho do usuário neste momento
4. Timeline — auditoria e contexto histórico

## User Flows

### Solicitante cria e acompanha requisição

```
1. Login → / → redirect → /requisicoes/minhas/
2. Clica "Nova Requisição" → /requisicoes/nova/ [escopo futuro]
3. Preenche itens, submete → POST → redirect → /requisicoes/<id>/
4. Clica "Enviar para autorização" → POST → redirect → /requisicoes/<id>/ (estado: aguardando)
5. Acompanha em /requisicoes/minhas/
6. Notificado quando autorizada/recusada
```

### Chefe de setor autoriza requisição

```
1. Login → / → redirect → /requisicoes/autorizacoes/
2. Vê fila de requisições aguardando autorização do seu setor
3. Clica "Analisar" → /requisicoes/<id>/
4. Lê cabeçalho + itens + timeline
5. Decide:
   - "Autorizar" → POST → redirect → /requisicoes/<id>/ (estado: autorizada)
   - "Recusar" → abre modal → preenche motivo → POST → redirect → /requisicoes/<id>/ (estado: recusada)
```

### Almoxarife atende requisição

```
1. Login → / → redirect → /requisicoes/atendimentos/
2. Vê fila de requisições autorizadas
3. Clica "Atender" → /requisicoes/<id>/
4. Lê cabeçalho + itens + timeline
5. Clica "Separar para retirada" → POST → redirect → /requisicoes/<id>/ (estado: pronta_para_retirada)
6. Clica "Atender" → /requisicoes/<id>/atender/ [escopo futuro]
7. Preenche quantidades entregues por item → POST → redirect → /requisicoes/<id>/ (estado: atendida)
```

### Criador cancela requisição

```
1. Acessa /requisicoes/minhas/
2. Clica "Ver" na requisição → /requisicoes/<id>/
3. Clica "Cancelar" → modal com justificativa (se exigida pelo estado)
4. Confirma → POST → redirect → /requisicoes/<id>/ (estado: cancelada)
```

## Naming Conventions

Labels usadas na interface. Mapeiam os termos do `CONTEXT.md` para o contexto visual.

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

## Component Reuse Map

| Componente | Usado em | Variações |
|---|---|---|
| Top nav global | Todas as telas pós-login | Links condicionais por papel |
| Badge de estado | Listas + detalhe | Mesmo mapeamento cor/label |
| Tabela de requisições | Minhas Req, Fila Auth, Fila Atend | Colunas diferem por tela |
| Empty state | As 3 listas | Copy diferente; CTA só em Minhas Req |
| Modal de confirmação | Detalhe (recusa, cancel, estorno) | Textarea obrigatório vs opcional |
| Feed de timeline | Detalhe | — |
| `_messages.html` | Todas as telas | Já existe; integrado ao chrome |
| Link `← Voltar` | Detalhe | Query param `?next=` preserva origem |

## Content Growth Plan

| Seção | Crescimento esperado | Estratégia |
|---|---|---|
| Minhas Requisições | Cresce com o tempo (histórico do usuário) | Paginação + filtro por estado (fase seguinte) |
| Fila de Autorização | Fluxo contínuo; itens saem ao autorizar/recusar | Sem paginação inicial; fila tende a ser pequena |
| Fila de Atendimentos | Idem fila de autorização | Idem |
| Timeline | Cresce por requisição (13 eventos possíveis) | Sem paginação; quantidade é razoável por requisição |

## URL Strategy

### Padrões

```
/requisicoes/                    → namespace `requisicoes`
/requisicoes/minhas/             → lista por papel
/requisicoes/historico/          → histórico system-wide (aux setor, chefe setor, almox, superuser)
/requisicoes/autorizacoes/       → fila de autorização
/requisicoes/atendimentos/       → fila de atendimento
/requisicoes/nova/               → criação
/requisicoes/<id>/               → detalhe (pk numérico)
/requisicoes/<id>/editar/        → edição de rascunho
/requisicoes/<id>/atender/       → formulário de atendimento
/requisicoes/<id>/devolucao/     → registro de devolução
```

### Regras

- Slugs em PT-BR — conforme AGENTS.md.
- `<id>` é o `pk` numérico da `Requisicao`. Nunca expor `numero_publico` como segmento de URL (pode ser nulo em rascunho).
- Sem query params para navegação básica. `?next=<url>` apenas para preservar origem no link "← Voltar".
- Filtros e ordenação nas listas: query params (`?estado=`, `?ordem=`) — fase seguinte.
- App namespace: `requisicoes` em `urls.py` com `app_name = 'requisicoes'`.
- Root URL config inclui: `path('requisicoes/', include('apps.requisicoes.urls'))`.

### Reversão de URLs (Django)

```python
reverse('requisicoes:minhas')
reverse('requisicoes:autorizacoes')
reverse('requisicoes:atendimentos')
reverse('requisicoes:detalhe', args=[requisicao.pk])
reverse('requisicoes:atender', args=[requisicao.pk])
```
