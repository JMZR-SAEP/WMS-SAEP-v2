# Build Tasks: WMS-SAEP — Login, Telas Operacionais, Detalhe

Gerado de:
- `.design/login/DESIGN_BRIEF.md`
- `.design/telas-operacionais/DESIGN_BRIEF.md`
- `.design/detalhe-requisicao/DESIGN_BRIEF.md`
- `.design/INFORMATION_ARCHITECTURE.md`

Data: 2026-05-21 | Última sincronização: 2026-06-23

---

## Fundação — Layout e Componentes Globais

- [x] **Refatorar `base.html` em dois layouts**: criar `base_auth.html` (com top nav) e manter `base.html` como layout mínimo para páginas sem autenticação (login). Top nav no `base_auth.html` com slots de nav links e usuário. _Modifica: `apps/core/templates/base.html`. Cria: `apps/core/templates/base_auth.html`._

- [ ] **Componente `button.html`**: implementar `apps/core/templates/components/button.html` com parâmetros `variant` (primary/secondary/danger/ghost), `size` (sm/md), `type`, `label`, `disabled`, `loading`/`loading_label`. Usar tokens `--color-primary`, `--color-danger`. _Novo componente. Depende de: tokens em `input.css` (já prontos)._

- [ ] **Componente `form_field.html`**: implementar wrapper de campo Django com `<label>` vinculada, `help_text`, erros inline (`aria-invalid`, `aria-describedby`), estado de foco `focus:border-blue-500 focus:ring-2`. _Novo componente._

- [ ] **Componente `status_badge.html`**: implementar `<span>` compacto com parâmetros `variant` (slate/blue/amber/green/red/teal) e `label`. Sem semântica de domínio. _Novo componente._

- [x] **Refatorar `_messages.html`**: aplicar tokens semânticos — `success`→verde, `error`→vermelho, `warning`→âmbar, `info`→slate. `role="alert"` para error/warning, `role="status"` para success/info. Auto-dismiss 8s para success/info via Alpine.js. _Modifica: `apps/core/templates/core/partials/_messages.html`._

---

## Login

- [x] **Tela de login estilizada**: reescrever `apps/accounts/templates/accounts/login.html` usando `base.html` (sem top nav). Card centrado `max-w-sm` em fundo `bg-slate-50`. Header com "WMS SAEP" + subtítulo. Campos matrícula/senha com `form_field.html`. Erros de credencial com `role="alert"` inline no card (acima dos campos). Botão "Entrar" full-width. Footer restritivo. `autofocus` em matrícula. Anti-double-submit via Alpine `x-data`. _Reusa: `form_field.html`, `button.html`. Valida direção visual do design system inteiro._

---

## Routing e Chrome Pós-Login

- [x] **Top nav com links condicionais por papel**: implementar chrome em `base_auth.html`. Links por papel: solicitante/aux.setor → "Minhas Requisições", "Nova Requisição"; chefe de setor → "Minhas Requisições", "Autorizações"; aux/chefe almox → "Atendimento"; superuser → "Admin". `aria-current="page"` no link ativo. Hamburger mobile → dropdown Alpine `x-show`. _Novo. Depende de: `base_auth.html`._

- [x] **Redirect pós-login por papel**: atualizar `apps/core/views.py::home` para detectar papel efetivo e redirecionar (`chefe_almox` > `aux_almox` > `chefe_setor` > `aux_setor` > `solicitante` > superuser→admin). `LOGIN_REDIRECT_URL = '/'` em settings. _Modifica: `core/views.py`, `settings.py`. Sem template novo._

- [x] **URLs do app `requisicoes`**: criar `apps/requisicoes/urls.py` com namespace `requisicoes` e rotas `minhas/`, `autorizacoes/`, `atendimentos/`, `<int:pk>/`. Incluir no root urlconf em `requisicoes/`. _Novo arquivo. Modifica: root `urls.py`._

---

## Selectors — Filas e Visibilidade

- [x] **Selector `minhas_requisicoes`**: criar `apps/requisicoes/selectors.py` com `minhas_requisicoes(ator_id)` → queryset de requisições onde `criador_id=ator_id OR beneficiario_id=ator_id`, excluindo rascunhos de terceiros quando `beneficiario != criador`. Order: `-criado_em`. `select_related('criador', 'beneficiario', 'setor_beneficiario')`. _Novo arquivo._

- [x] **Selector `fila_autorizacao`**: `fila_autorizacao(ator_id)` → requisições `estado=aguardando_autorizacao` do setor chefiado pelo ator. Chefe de almox vê apenas setor almoxarifado. Inclui `Count('itens')`. _Modifica: `selectors.py`._

- [x] **Selector `fila_atendimento`**: `fila_atendimento(ator_id)` → requisições `estado__in=['autorizada', 'pronta_para_retirada']`. Visível apenas para aux/chefe almox. Inclui `Count('itens')`. _Modifica: `selectors.py`._

---

## Telas de Lista Operacional

- [x] **Partial `_estado_badge.html`**: criar `apps/requisicoes/templates/requisicoes/partials/_estado_badge.html` mapeando `EstadoRequisicao` → variante de `status_badge.html`. rascunho→slate, aguardando→amber, autorizada→blue, pronta_para_retirada→blue, atendida→green, recusada/cancelada→red, estornada→teal. Fallback "Rascunho" para `numero_publico` nulo. _Novo partial de domínio. Reusa: `status_badge.html`._

- [x] **Tela Minhas Requisições** (`/requisicoes/minhas/`): view `MinhasRequisicoesView` + template. Tabela com colunas: número público (ou "Rascunho"), estado (badge), beneficiário, data contextual, botão "Ver". Empty state com CTA "Nova Requisição". `@login_required`. _Reusa: `_estado_badge.html`, `button.html`. Depende de: selector `minhas_requisicoes`, `base_auth.html`, top nav._

- [x] **Tela Fila de Autorização** (`/requisicoes/autorizacoes/`): view `FilaAutorizacaoView` + template. Tabela: número público, beneficiário, setor, data enviada, qtd itens, botão "Analisar". Empty state neutro. `@login_required` + verificação de papel (403 se não for chefe). _Reusa mesmos componentes. Depende de: selector `fila_autorizacao`._

- [x] **Tela Fila de Atendimentos** (`/requisicoes/atendimentos/`): view `FilaAtendimentoView` + template. Tabela: número público, beneficiário, setor, data autorizada, qtd itens, botão "Atender". Empty state neutro. `@login_required` + verificação de papel. _Reusa mesmos componentes. Depende de: selector `fila_atendimento`._

---

## Detalhe da Requisição

- [x] **View de detalhe** (`/requisicoes/<pk>/`): view `DetalheRequisicaoView` + template base. Cabeçalho (número/estado/beneficiário/setor/criador/datas/observação). Tabela de itens com colunas dinâmicas por estado (solicitada/autorizada/entregue conforme disponibilidade). Link "← Voltar" com `?next=` preservado. `get_object_or_404` + verificação de visibilidade (403 se sem acesso). _Novo. Reusa: `_estado_badge.html`, `base_auth.html`._

- [ ] **Partial `_acoes_requisicao.html`**: partial que renderiza bloco de ações disponíveis para o par (estado, papel_efetivo). Sem botões disabled por regra de negócio — apenas o permitido aparece. Ações POST direto: enviar, autorizar, separar para retirada. Ações com modal: recusar, cancelar, retornar para rascunho, estornar. _Novo partial. Reusa: `button.html`._

- [x] **Feed de timeline**: seção de timeline na página de detalhe. Lista vertical mais-recente-primeiro. Cada item: tipo de evento (label PT-BR), ator (nome + matrícula), data/hora, justificativa (se existir) em texto menor. _Novo. Inline no template de detalhe ou partial `_timeline.html`._

---

## Modal e Ações com Input

- [x] **Componente `modal.html`**: implementar `apps/core/templates/components/modal.html` com `role="dialog"`, `aria-modal="true"`, `aria-labelledby`. Trap de foco via Alpine.js. Fecha com Escape. Parâmetros: `title`, `body` (slot), botões confirm/cancel. _Novo componente global. Risco mais alto — padrão HTMX+modal precisa ser validado._

- [x] **Ação: Recusar requisição**: botão "Recusar" abre modal (HTMX ou Alpine). Textarea "Motivo da recusa" obrigatório. POST `/requisicoes/<pk>/recusar/` → service `recusar_requisicao(ator_id, requisicao_id, motivo)` → HX-Redirect para detalhe. Erro de validação retorna fragment do modal com erro inline. _Reusa: `modal.html`, `button.html`. Inclui policy + service._

- [x] **Ação: Cancelar requisição**: botão "Cancelar" abre modal. Justificativa condicional (obrigatória se estado autorizada/pronta_para_retirada). POST `/requisicoes/<pk>/cancelar/` → service. _Reusa: `modal.html`. Inclui policy + service._

- [x] **Ação: Retornar para rascunho**: modal com observação opcional. POST `/requisicoes/<pk>/retornar-rascunho/` → service. _Reusa: `modal.html`._

- [x] **Ações POST direto** (Enviar, Autorizar, Separar para retirada): botões sem modal. POST com CSRF → service → HX-Redirect. Mensagem `messages.success` com `numero_publico`. _Reusa: `button.html`. Inclui policy + service por ação._

---

## Responsivo e Acessibilidade

- [ ] **Responsividade das tabelas de lista**: testar e ajustar `sm`/`md` breakpoints. Mobile: colunas essenciais visíveis, restante colapsado ou scroll horizontal. _Modifica templates de lista._

- [ ] **Responsividade do detalhe**: cabeçalho em coluna única no mobile. Modal full-width. _Modifica template de detalhe e `modal.html`._

- [ ] **Accessibility pass**: verificar checklist do design-system.md para todas as telas construídas. Contraste badges (testar amber/green), `<table>` semântico com `thead`+`th scope`, `aria-current="page"` no nav, `aria-live` na zona de mensagens, foco no modal, Escape fecha modal. _Revisão transversal._

---

## Revisão

- [ ] **Design review**: executar `/design-review` contra os 3 briefs após todas as telas construídas.
