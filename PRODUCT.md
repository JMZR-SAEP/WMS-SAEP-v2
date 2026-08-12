# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Usuários internos da SAEP (Superintendência de Administração e Engenharia de Pátios), todos autenticados e vinculados a exatamente um Setor. O papel não é atributo fixo do Usuário: é **papel efetivo**, derivado do ator diante de um Setor ou requisição específicos.

- **Solicitante** — condição implícita de todo usuário ativo; cria requisições para si. Opera **no celular**, entre outras tarefas, fora de estação de trabalho.
- **Auxiliar de setor** — cria requisições em nome de outros usuários do mesmo Setor.
- **Chefe de setor** — autoriza ou recusa as requisições do seu Setor. Opera **no desktop**, no escritório, em blocos de decisão.
- **Auxiliar de almoxarifado** — executa separação, atendimento e devolução. A **separação acontece em pé, no galpão**, longe de mesa e teclado.
- **Chefe de almoxarifado** — único papel autorizado a estornar e a registrar saída excepcional.
- **Superuser/staff** — flag técnica do Django, fora do domínio; acessa o admin.

Um usuário pode acumular papéis; a navegação mostra a união dos links permitidos.

## Product Purpose

Controlar o ciclo completo da requisição de material — rascunho → autorização → atendimento/separação → retirada, com devolução, cancelamento e estorno — mais o controle de estoque que sustenta esse ciclo (reserva, consumo, saída excepcional, movimentações, importação SCPI).

Sucesso: cada pedido de material tem número público, dono, estado inequívoco e trilha de auditoria; o saldo de estoque nunca muda sem uma Movimentação correspondente na mesma transação.

## Positioning

WMS-SAEP **coexiste indefinidamente com o SCPI** — não o substitui e não pretende substituir. O SCPI permanece em produção e a conferência entre os dois é uma realidade operacional recorrente, não uma fase de migração com prazo.

Consequências que o design não pode contrariar:
- WMS é fonte da verdade do **saldo do WMS**; a importação SCPI **nunca sobrescreve saldo** — registra alertas de divergência para ajuste manual posterior no SCPI.
- Divergência entre os dois sistemas é estado normal e esperado, não erro. A interface a evidencia por delta, para conferência humana, em vez de tentar reconciliá-la sozinha.
- Fluxos de importação precisam ser reexecutados periodicamente por gente que confia mais no papel do que no software.

## Operating Context

- Sistema administrativo interno, atrás de login, sem público externo e sem aquisição.
- **Três cenas físicas distintas para o mesmo produto**: o celular do solicitante, o desktop do chefe de setor e o galpão do almoxarifado (usuário em pé, mãos ocupadas, material físico à frente).
- O fluxo atravessa pessoas e tempo: quem digita não é necessariamente quem recebe (Criador ≠ Beneficiário), e quem retira pode não ser o Beneficiário (Retirante).
- Uma requisição pertence ao Setor do **Beneficiário**, nunca ao do Criador — isso define a fila de autorização.
- Filas de trabalho são o centro da rotina: Fila de Autorização (chefe de setor) e Fila de Atendimentos (almoxarifado).
- Importação SCPI é ritual recorrente com preview read-only, alertas não bloqueantes e confirmação explícita antes de gravar.

## Capabilities and Constraints

**Stack:** Django 6 + HTMX + Alpine.js + Tailwind CSS v4, server-rendered, **sem camada de API REST** e sem SPA. Estado de domínio nunca vive no JavaScript. PostgreSQL. Python 3.13+.

**Funcionalidades confirmadas:** requisições (criar, enviar, autorizar, recusar, retornar a rascunho, separar, atender, devolver, estornar, cancelar/descartar), catálogo de materiais, saldos e reservas, saída excepcional (`SXP-AAAA-NNNNNN`), movimentações de estoque (livro-razão append-only), importação SCPI com preview/alertas/histórico, notificações, RBAC por papel efetivo.

**Restrições de domínio que a UI consome, não redefine:**
- **Ações disponíveis** vêm de uma fonte única (tabela de transições + policies). O botão é apresentação; a Operação é domínio. A interface nunca reconstrói o grafo de estados.
- Estado ≠ evento de timeline. Estado da saída excepcional é `registrada`/`estornada`; evento é `registro`/`estorno`.
- **Entregue líquida** é sempre derivada das movimentações, nunca armazenada.
- Material é único por documento (requisição ou saída).
- Cancelamento tem variantes: **descarte** (rascunho sem número, sem timeline) e **cancelamento** (preserva número público, libera reservas a partir da autorização).

**Terminologia (linguagem ubíqua, PT-BR):** ver `CONTEXT.md`, que é o glossário canônico. Identificadores de domínio, labels de UI e slugs de URL usam PT-BR. Termos a evitar estão marcados lá (`_Avoid_`) e valem também para copy de interface.

**Fora de escopo declarado:** doação e empréstimo não fazem parte do MVP de saída excepcional. O bootstrap de saldo da importação SCPI fica fora do ledger nesta fase.

## Brand Commitments

Não há identidade de marca. O design system declara explicitamente: "não é identidade de marca. É ferramenta de trabalho." Não existem logo, assets de marca ou tipografia própria no repositório.

O sistema visual incumbente está documentado em `docs/design-system.md` (tokens, componentes, padrões de interação) e os handoffs por tela vivem em `.design/`. Princípios já fixados: pragmático, operacional, neutro, simples, progressivo.

## Evidence on Hand

- `CONTEXT.md` — glossário de domínio com diálogo de especialista e ambiguidades resolvidas.
- `docs/` — ADRs, `CONVENTIONS.md`, `design-system.md`, `matriz-permissoes.md`, `matriz-invariantes.md`, `estado-transicoes-requisicao.md`, processos de almoxarifado e de saída excepcional.
- `.design/` — `INFORMATION_ARCHITECTURE.md`, `TASKS.md`, `AUDITORIA_UIUX.md` e briefs por área (login, telas operacionais, detalhe da requisição, movimentações, saída excepcional, topbar).
- `.design/audit-uiux-2026-07/screenshots/` — capturas desktop 1280 e mobile 375 dos fluxos reais.
- Suíte de testes e CI verdes como evidência de comportamento.

**Não existe e não deve ser fabricado:** depoimento, cliente, benchmark, número de adoção, preço, licenciamento ou claim de deploy. O produto não tem público externo nem superfície de marketing.

## Product Principles

1. **O domínio manda na interface.** Ações, estados e permissões vêm da fonte única; a tela apresenta, não decide.
2. **Auditabilidade acima de conveniência.** Número público, timeline e movimentação imutável valem mais que um atalho que apaga o rastro.
3. **Projetar para a cena, não para a média.** Celular do solicitante, desktop do chefe e galpão do almoxarifado são contextos diferentes — a mesma tela genérica falha em pelo menos um.
4. **Divergência é informação, não falha.** A coexistência com o SCPI exige evidenciar deltas para conferência humana em vez de esconder ou autocorrigir.
5. **Progressivo, nunca pesado.** HTMX/Alpine para interação incremental; nada de estado de domínio no cliente.

## Accessibility & Inclusion

WCAG AA como meta interna de qualidade (contraste mínimo 4.5:1, foco visível, navegação por teclado), já obrigatório no `docs/design-system.md`. **Sem mandato legal** aplicável e sem auditoria externa prevista; nenhuma necessidade específica de usuário foi identificada no elenco atual.
